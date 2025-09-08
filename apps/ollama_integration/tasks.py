from celery import shared_task, current_task
from celery.exceptions import Retry
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db import transaction
import logging
import json
import time
import requests
from typing import Dict, Any, Optional

from .models import (
    OllamaModel,
    OllamaProcessingJob,
    OllamaConfiguration,
    OllamaModelUsage
)
from .client import OllamaClient, OllamaModelManager
from .signals import (
    model_health_check,
    model_pull_completed,
    job_processing_started,
    job_processing_completed
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_job(self, job_id: int) -> Dict[str, Any]:
    """
    Process an Ollama job asynchronously
    
    Args:
        job_id: ID of the OllamaProcessingJob to process
    
    Returns:
        Dict containing job result and metadata
    """
    try:
        # Get the job
        job = OllamaProcessingJob.objects.select_related('model', 'model__configuration').get(id=job_id)
        
        # Check if job is still pending
        if job.status != 'pending':
            logger.warning(f"Job {job_id} is not pending (status: {job.status})")
            return {'success': False, 'error': 'Job is not pending'}
        
        # Send processing started signal
        job_processing_started.send(sender=process_job, job_id=job_id)
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Starting job processing'}
        )
        
        # Get the best model for this task
        manager = OllamaModelManager()
        selected_model = manager.get_best_model(job.task_type)
        
        if not selected_model:
            error_msg = f"No available model for task type: {job.task_type}"
            logger.error(error_msg)
            job_processing_completed.send(
                sender=process_job,
                job_id=job_id,
                success=False,
                error=error_msg
            )
            return {'success': False, 'error': error_msg}
        
        # Update job with selected model
        job.model = selected_model
        job.save(update_fields=['model'])
        
        # Update progress
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 20, 'total': 100, 'status': f'Using model: {selected_model.name}'}
        )
        
        # Create client
        client = OllamaClient(selected_model.configuration.name)
        
        try:
            # Prepare parameters
            params = {
                'temperature': selected_model.temperature,
                'max_tokens': selected_model.max_tokens,
                'top_p': selected_model.top_p,
                'top_k': selected_model.top_k,
            }
            
            # Add custom parameters
            if selected_model.custom_parameters:
                try:
                    custom_params = json.loads(selected_model.custom_parameters)
                    params.update(custom_params)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid custom parameters for model {selected_model.name}")
            
            # Add input data if available
            if job.input_data:
                try:
                    input_data = json.loads(job.input_data)
                    params.update(input_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid input data for job {job_id}")
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'current': 40, 'total': 100, 'status': 'Generating response'}
            )
            
            # Process based on task type
            if job.task_type == 'chat':
                # For chat tasks, use chat endpoint
                messages = [
                    {'role': 'system', 'content': job.system_prompt or selected_model.system_prompt or ''},
                    {'role': 'user', 'content': job.prompt}
                ]
                response = client.chat(selected_model.model_name, messages, **params)
            
            elif job.task_type == 'embedding':
                # For embedding tasks
                response = client.embed(selected_model.model_name, job.prompt)
            
            else:
                # For other tasks, use generate endpoint
                system_prompt = job.system_prompt or selected_model.system_prompt
                response = client.generate(
                    selected_model.model_name,
                    job.prompt,
                    system_prompt=system_prompt,
                    **params
                )
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'current': 80, 'total': 100, 'status': 'Processing response'}
            )
            
            # Check response
            if response.success:
                # Prepare result
                result = {
                    'text': response.text,
                    'model': selected_model.model_name,
                    'tokens': getattr(response, 'tokens', 0),
                    'processing_time': getattr(response, 'processing_time', 0),
                    'metadata': getattr(response, 'metadata', {})
                }
                
                # Update progress
                current_task.update_state(
                    state='PROGRESS',
                    meta={'current': 100, 'total': 100, 'status': 'Completed successfully'}
                )
                
                # Send completion signal
                job_processing_completed.send(
                    sender=process_job,
                    job_id=job_id,
                    success=True,
                    result=json.dumps(result)
                )
                
                logger.info(f"Job {job_id} completed successfully")
                return {'success': True, 'result': result}
            
            else:
                error_msg = response.error or 'Unknown error occurred'
                logger.error(f"Job {job_id} failed: {error_msg}")
                
                # Send completion signal
                job_processing_completed.send(
                    sender=process_job,
                    job_id=job_id,
                    success=False,
                    error=error_msg
                )
                
                return {'success': False, 'error': error_msg}
        
        finally:
            client.close()
    
    except OllamaProcessingJob.DoesNotExist:
        error_msg = f"Job {job_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Unexpected error processing job {job_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry on certain errors
        if 'connection' in str(e).lower() or 'timeout' in str(e).lower():
            logger.info(f"Retrying job {job_id} due to connection error")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        # Send completion signal for non-retryable errors
        try:
            job_processing_completed.send(
                sender=process_job,
                job_id=job_id,
                success=False,
                error=error_msg
            )
        except:
            pass
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=2)
def test_model(self, model_id: int) -> Dict[str, Any]:
    """
    Test an Ollama model asynchronously
    
    Args:
        model_id: ID of the OllamaModel to test
    
    Returns:
        Dict containing test result
    """
    try:
        model = OllamaModel.objects.select_related('configuration').get(id=model_id)
        
        logger.info(f"Testing model {model.name} (ID: {model_id})")
        
        # Create client
        client = OllamaClient(model.configuration.name)
        
        try:
            # Test with a simple prompt
            response = client.generate(
                model.model_name,
                "Hello, this is a test. Please respond with 'Test successful'.",
                temperature=0.1,
                max_tokens=50
            )
            
            is_healthy = response.success
            error_msg = response.error if not response.success else None
            
            # Send health check signal
            model_health_check.send(
                sender=test_model,
                model_id=model_id,
                is_healthy=is_healthy
            )
            
            if is_healthy:
                logger.info(f"Model {model.name} test successful")
                return {'success': True, 'response': response.text}
            else:
                logger.warning(f"Model {model.name} test failed: {error_msg}")
                return {'success': False, 'error': error_msg}
        
        finally:
            client.close()
    
    except OllamaModel.DoesNotExist:
        error_msg = f"Model {model_id} not found"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    
    except Exception as e:
        error_msg = f"Error testing model {model_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry on connection errors
        if 'connection' in str(e).lower() or 'timeout' in str(e).lower():
            logger.info(f"Retrying model test {model_id} due to connection error")
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        
        return {'success': False, 'error': error_msg}


@shared_task(bind=True, max_retries=3)
def pull_model(self, model_name: str, configuration_name: str) -> Dict[str, Any]:
    """
    Pull an Ollama model asynchronously
    
    Args:
        model_name: Name of the model to pull
        configuration_name: Name of the configuration to use
    
    Returns:
        Dict containing pull result
    """
    try:
        logger.info(f"Pulling model {model_name} using configuration {configuration_name}")
        
        # Update task progress
        current_task.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': f'Starting pull for {model_name}'}
        )
        
        # Create client
        client = OllamaClient(configuration_name)
        
        try:
            # Pull the model
            success = client.pull_model(model_name)
            
            # Update progress
            current_task.update_state(
                state='PROGRESS',
                meta={'current': 100, 'total': 100, 'status': 'Pull completed'}
            )
            
            # Send completion signal
            model_pull_completed.send(
                sender=pull_model,
                model_name=model_name,
                success=success
            )
            
            if success:
                logger.info(f"Successfully pulled model {model_name}")
                return {'success': True, 'model': model_name}
            else:
                error_msg = f"Failed to pull model {model_name}"
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
        
        finally:
            client.close()
    
    except Exception as e:
        error_msg = f"Error pulling model {model_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Retry on connection errors
        if 'connection' in str(e).lower() or 'timeout' in str(e).lower():
            logger.info(f"Retrying model pull {model_name} due to connection error")
            raise self.retry(exc=e, countdown=120 * (self.request.retries + 1))
        
        # Send completion signal for failures
        try:
            model_pull_completed.send(
                sender=pull_model,
                model_name=model_name,
                success=False
            )
        except:
            pass
        
        return {'success': False, 'error': error_msg}


@shared_task
def health_check_all_models() -> Dict[str, Any]:
    """
    Perform health check on all active models
    
    Returns:
        Dict containing health check results
    """
    try:
        logger.info("Starting health check for all active models")
        
        active_models = OllamaModel.objects.filter(is_active=True).select_related('configuration')
        results = []
        
        for model in active_models:
            try:
                # Schedule individual model test
                task_result = test_model.delay(model.id)
                results.append({
                    'model_id': model.id,
                    'model_name': model.name,
                    'task_id': task_result.id
                })
            except Exception as e:
                logger.error(f"Error scheduling health check for model {model.name}: {str(e)}")
                results.append({
                    'model_id': model.id,
                    'model_name': model.name,
                    'error': str(e)
                })
        
        logger.info(f"Scheduled health checks for {len(results)} models")
        return {'success': True, 'results': results, 'total_models': len(results)}
    
    except Exception as e:
        error_msg = f"Error in health_check_all_models: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


@shared_task
def cleanup_old_jobs(days: int = 30) -> Dict[str, Any]:
    """
    Clean up old completed/failed jobs
    
    Args:
        days: Number of days to keep jobs
    
    Returns:
        Dict containing cleanup results
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Find old jobs
        old_jobs = OllamaProcessingJob.objects.filter(
            status__in=['completed', 'failed', 'cancelled'],
            completed_at__lt=cutoff_date
        )
        
        count = old_jobs.count()
        
        if count > 0:
            # Delete old jobs
            old_jobs.delete()
            logger.info(f"Cleaned up {count} old jobs older than {days} days")
        else:
            logger.info(f"No old jobs found to clean up (older than {days} days)")
        
        return {'success': True, 'deleted_count': count}
    
    except Exception as e:
        error_msg = f"Error cleaning up old jobs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


@shared_task
def update_usage_statistics() -> Dict[str, Any]:
    """
    Update usage statistics for all models
    
    Returns:
        Dict containing update results
    """
    try:
        logger.info("Updating usage statistics")
        
        # Get all models with recent activity
        recent_date = timezone.now().date() - timezone.timedelta(days=7)
        active_models = OllamaModel.objects.filter(
            last_used_at__gte=recent_date
        )
        
        updated_count = 0
        
        for model in active_models:
            try:
                # Calculate statistics from recent jobs
                recent_jobs = OllamaProcessingJob.objects.filter(
                    model=model,
                    completed_at__gte=timezone.now() - timezone.timedelta(days=1),
                    status='completed'
                )
                
                if recent_jobs.exists():
                    # Update model statistics
                    total_jobs = recent_jobs.count()
                    avg_processing_time = recent_jobs.aggregate(
                        avg_time=models.Avg(
                            models.F('completed_at') - models.F('started_at')
                        )
                    )['avg_time']
                    
                    # Update usage record
                    today = timezone.now().date()
                    usage, created = OllamaModelUsage.objects.get_or_create(
                        model=model,
                        date=today,
                        defaults={
                            'request_count': total_jobs,
                            'success_count': total_jobs,
                            'total_processing_time': avg_processing_time.total_seconds() if avg_processing_time else 0,
                        }
                    )
                    
                    if not created:
                        usage.request_count += total_jobs
                        usage.success_count += total_jobs
                        if avg_processing_time:
                            usage.total_processing_time += avg_processing_time.total_seconds()
                        usage.save()
                    
                    updated_count += 1
            
            except Exception as e:
                logger.error(f"Error updating statistics for model {model.name}: {str(e)}")
        
        logger.info(f"Updated statistics for {updated_count} models")
        return {'success': True, 'updated_count': updated_count}
    
    except Exception as e:
        error_msg = f"Error updating usage statistics: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


@shared_task
def process_pending_jobs() -> Dict[str, Any]:
    """
    Process all pending jobs in the queue
    
    Returns:
        Dict containing processing results
    """
    try:
        logger.info("Processing pending jobs")
        
        # Get pending jobs ordered by priority and creation time
        pending_jobs = OllamaProcessingJob.objects.filter(
            status='pending'
        ).order_by('-priority', 'created_at')
        
        scheduled_count = 0
        
        for job in pending_jobs:
            try:
                # Schedule job processing
                process_job.delay(job.id)
                scheduled_count += 1
                logger.debug(f"Scheduled processing for job {job.id}")
            except Exception as e:
                logger.error(f"Error scheduling job {job.id}: {str(e)}")
        
        logger.info(f"Scheduled {scheduled_count} pending jobs for processing")
        return {'success': True, 'scheduled_count': scheduled_count}
    
    except Exception as e:
        error_msg = f"Error processing pending jobs: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


@shared_task
def backup_configuration() -> Dict[str, Any]:
    """
    Create a backup of all Ollama configurations
    
    Returns:
        Dict containing backup results
    """
    try:
        logger.info("Creating configuration backup")
        
        # Export configurations
        configurations = OllamaConfiguration.objects.all()
        models = OllamaModel.objects.all()
        templates = OllamaPromptTemplate.objects.all()
        
        backup_data = {
            'timestamp': timezone.now().isoformat(),
            'configurations': [],
            'models': [],
            'templates': []
        }
        
        # Serialize configurations
        for config in configurations:
            backup_data['configurations'].append({
                'name': config.name,
                'description': config.description,
                'host': config.host,
                'port': config.port,
                'use_ssl': config.use_ssl,
                'timeout': config.timeout,
                'max_retries': config.max_retries,
                'retry_delay': config.retry_delay,
                'max_concurrent_requests': config.max_concurrent_requests,
                'request_queue_size': config.request_queue_size,
                'is_active': config.is_active
            })
        
        # Serialize models
        for model in models:
            backup_data['models'].append({
                'name': model.name,
                'model_name': model.model_name,
                'description': model.description,
                'task_type': model.task_type,
                'configuration_name': model.configuration.name,
                'is_active': model.is_active,
                'priority': model.priority,
                'temperature': model.temperature,
                'max_tokens': model.max_tokens,
                'top_p': model.top_p,
                'top_k': model.top_k,
                'system_prompt': model.system_prompt,
                'custom_parameters': model.custom_parameters
            })
        
        # Serialize templates
        for template in templates:
            backup_data['templates'].append({
                'name': template.name,
                'description': template.description,
                'task_type': template.task_type,
                'template': template.template,
                'system_prompt': template.system_prompt,
                'variables': template.variables,
                'default_parameters': template.default_parameters,
                'is_active': template.is_active
            })
        
        # Save backup to cache or file
        backup_key = f"ollama_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        cache.set(backup_key, backup_data, timeout=86400 * 7)  # Keep for 7 days
        
        logger.info(f"Configuration backup created with key: {backup_key}")
        return {
            'success': True,
            'backup_key': backup_key,
            'configurations_count': len(backup_data['configurations']),
            'models_count': len(backup_data['models']),
            'templates_count': len(backup_data['templates'])
        }
    
    except Exception as e:
        error_msg = f"Error creating configuration backup: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {'success': False, 'error': error_msg}


# Periodic tasks (to be configured in Celery beat)
@shared_task
def periodic_health_check():
    """Periodic health check for all models"""
    return health_check_all_models.delay()


@shared_task
def periodic_cleanup():
    """Periodic cleanup of old jobs"""
    return cleanup_old_jobs.delay()


@shared_task
def periodic_statistics_update():
    """Periodic update of usage statistics"""
    return update_usage_statistics.delay()


@shared_task
def periodic_backup():
    """Periodic configuration backup"""
    return backup_configuration.delay()