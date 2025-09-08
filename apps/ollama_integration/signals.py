from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from celery import current_app
import logging
import json

from .models import (
    OllamaModel,
    OllamaProcessingJob,
    OllamaConfiguration,
    OllamaModelUsage,
    OllamaPromptTemplate
)
from .client import OllamaClient, OllamaModelManager

logger = logging.getLogger(__name__)


@receiver(post_save, sender=OllamaConfiguration)
def configuration_post_save(sender, instance, created, **kwargs):
    """Handle configuration save events"""
    try:
        # Clear cache when configuration changes
        cache_key = f'ollama_config_{instance.name}'
        cache.delete(cache_key)
        cache.delete('ollama_active_configs')
        
        # Log configuration changes
        action = 'created' if created else 'updated'
        logger.info(f"Ollama configuration '{instance.name}' {action}")
        
        # Test connection if configuration is active
        if instance.is_active and not created:
            try:
                client = OllamaClient(instance.name)
                is_healthy = client.health_check()
                client.close()
                
                if not is_healthy:
                    logger.warning(f"Health check failed for configuration '{instance.name}'")
                    # Optionally disable the configuration
                    # instance.is_active = False
                    # instance.save(update_fields=['is_active'])
                else:
                    logger.info(f"Health check passed for configuration '{instance.name}'")
                    
            except Exception as e:
                logger.error(f"Error testing configuration '{instance.name}': {str(e)}")
        
        # Update related models if configuration was deactivated
        if not instance.is_active:
            affected_models = OllamaModel.objects.filter(
                configuration=instance,
                is_active=True
            )
            if affected_models.exists():
                affected_models.update(is_active=False)
                logger.info(f"Deactivated {affected_models.count()} models due to configuration deactivation")
        
    except Exception as e:
        logger.error(f"Error in configuration post_save signal: {str(e)}")


@receiver(pre_delete, sender=OllamaConfiguration)
def configuration_pre_delete(sender, instance, **kwargs):
    """Handle configuration deletion"""
    try:
        # Cancel pending jobs using this configuration
        pending_jobs = OllamaProcessingJob.objects.filter(
            model__configuration=instance,
            status__in=['pending', 'processing']
        )
        
        for job in pending_jobs:
            job.status = 'cancelled'
            job.error_message = f"Configuration '{instance.name}' was deleted"
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at'])
        
        if pending_jobs.exists():
            logger.info(f"Cancelled {pending_jobs.count()} jobs due to configuration deletion")
        
        # Clear cache
        cache_key = f'ollama_config_{instance.name}'
        cache.delete(cache_key)
        cache.delete('ollama_active_configs')
        
        logger.info(f"Ollama configuration '{instance.name}' is being deleted")
        
    except Exception as e:
        logger.error(f"Error in configuration pre_delete signal: {str(e)}")


@receiver(post_save, sender=OllamaModel)
def model_post_save(sender, instance, created, **kwargs):
    """Handle model save events"""
    try:
        # Clear model cache
        cache_key = f'ollama_model_{instance.id}'
        cache.delete(cache_key)
        cache.delete('ollama_active_models')
        cache.delete(f'ollama_models_{instance.task_type}')
        
        # Log model changes
        action = 'created' if created else 'updated'
        logger.info(f"Ollama model '{instance.name}' {action}")
        
        # Test model if it's newly created and active
        if created and instance.is_active:
            try:
                # Schedule a background task to test the model
                if hasattr(current_app, 'send_task'):
                    current_app.send_task(
                        'ollama_integration.tasks.test_model',
                        args=[instance.id],
                        countdown=5  # Wait 5 seconds before testing
                    )
                else:
                    # Fallback: test synchronously
                    client = OllamaClient(instance.configuration.name)
                    response = client.generate(
                        instance.model_name,
                        "Hello, this is a test.",
                        temperature=0.1,
                        max_tokens=50
                    )
                    client.close()
                    
                    if response.success:
                        logger.info(f"Model '{instance.name}' test successful")
                    else:
                        logger.warning(f"Model '{instance.name}' test failed: {response.error}")
                        
            except Exception as e:
                logger.error(f"Error testing model '{instance.name}': {str(e)}")
        
        # Update model manager cache
        if instance.is_active:
            try:
                manager = OllamaModelManager()
                manager._load_models()  # Refresh model cache
            except Exception as e:
                logger.error(f"Error refreshing model manager: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in model post_save signal: {str(e)}")


@receiver(pre_delete, sender=OllamaModel)
def model_pre_delete(sender, instance, **kwargs):
    """Handle model deletion"""
    try:
        # Cancel pending jobs using this model
        pending_jobs = OllamaProcessingJob.objects.filter(
            model=instance,
            status__in=['pending', 'processing']
        )
        
        for job in pending_jobs:
            job.status = 'cancelled'
            job.error_message = f"Model '{instance.name}' was deleted"
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at'])
        
        if pending_jobs.exists():
            logger.info(f"Cancelled {pending_jobs.count()} jobs due to model deletion")
        
        # Clear cache
        cache_key = f'ollama_model_{instance.id}'
        cache.delete(cache_key)
        cache.delete('ollama_active_models')
        cache.delete(f'ollama_models_{instance.task_type}')
        
        logger.info(f"Ollama model '{instance.name}' is being deleted")
        
    except Exception as e:
        logger.error(f"Error in model pre_delete signal: {str(e)}")


@receiver(post_save, sender=OllamaProcessingJob)
def job_post_save(sender, instance, created, **kwargs):
    """Handle processing job save events"""
    try:
        # Log job status changes
        if created:
            logger.info(f"Processing job '{instance.name}' created with ID {instance.id}")
            
            # Schedule job processing if it's pending
            if instance.status == 'pending':
                try:
                    if hasattr(current_app, 'send_task'):
                        current_app.send_task(
                            'ollama_integration.tasks.process_job',
                            args=[instance.id],
                            countdown=1
                        )
                        logger.info(f"Scheduled processing for job {instance.id}")
                    else:
                        # Fallback: process synchronously (not recommended for production)
                        logger.warning("Celery not available, processing job synchronously")
                        manager = OllamaModelManager()
                        manager.process_job(instance.id)
                        
                except Exception as e:
                    logger.error(f"Error scheduling job {instance.id}: {str(e)}")
                    instance.status = 'failed'
                    instance.error_message = f"Failed to schedule job: {str(e)}"
                    instance.completed_at = timezone.now()
                    instance.save(update_fields=['status', 'error_message', 'completed_at'])
        
        else:
            # Job was updated
            if instance.status in ['completed', 'failed', 'cancelled']:
                logger.info(f"Processing job {instance.id} finished with status: {instance.status}")
                
                # Send notification if configured
                if hasattr(settings, 'OLLAMA_NOTIFICATIONS') and settings.OLLAMA_NOTIFICATIONS.get('JOB_COMPLETION'):
                    try:
                        send_job_completion_notification(instance)
                    except Exception as e:
                        logger.error(f"Error sending job completion notification: {str(e)}")
                
                # Update usage statistics
                if instance.status == 'completed' and instance.model:
                    try:
                        update_model_usage_stats(instance)
                    except Exception as e:
                        logger.error(f"Error updating usage stats: {str(e)}")
        
        # Clear job cache
        cache.delete(f'ollama_job_{instance.id}')
        cache.delete('ollama_pending_jobs')
        
    except Exception as e:
        logger.error(f"Error in job post_save signal: {str(e)}")


@receiver(post_save, sender=OllamaPromptTemplate)
def template_post_save(sender, instance, created, **kwargs):
    """Handle prompt template save events"""
    try:
        # Clear template cache
        cache_key = f'ollama_template_{instance.id}'
        cache.delete(cache_key)
        cache.delete('ollama_active_templates')
        cache.delete(f'ollama_templates_{instance.task_type}')
        
        # Log template changes
        action = 'created' if created else 'updated'
        logger.info(f"Prompt template '{instance.name}' {action}")
        
        # Validate template if it's active
        if instance.is_active:
            try:
                from string import Template
                Template(instance.template)
                logger.info(f"Template '{instance.name}' validation successful")
            except Exception as e:
                logger.warning(f"Template '{instance.name}' validation failed: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error in template post_save signal: {str(e)}")


def send_job_completion_notification(job):
    """Send email notification for job completion"""
    try:
        if not job.created_by or not job.created_by.email:
            return
        
        subject = f"Ollama Job Completed: {job.name}"
        
        context = {
            'job': job,
            'user': job.created_by,
            'status': job.status,
            'duration': job.get_duration() if hasattr(job, 'get_duration') else None,
        }
        
        # Render email templates
        html_message = render_to_string('ollama_integration/emails/job_completion.html', context)
        text_message = render_to_string('ollama_integration/emails/job_completion.txt', context)
        
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[job.created_by.email],
            fail_silently=True
        )
        
        logger.info(f"Job completion notification sent to {job.created_by.email}")
        
    except Exception as e:
        logger.error(f"Error sending job completion notification: {str(e)}")


def update_model_usage_stats(job):
    """Update model usage statistics"""
    try:
        if not job.model:
            return
        
        # Get or create usage record for today
        today = timezone.now().date()
        usage, created = OllamaModelUsage.objects.get_or_create(
            model=job.model,
            date=today,
            defaults={
                'request_count': 0,
                'total_tokens': 0,
                'total_processing_time': 0.0,
                'success_count': 0,
                'error_count': 0
            }
        )
        
        # Update statistics
        usage.request_count += 1
        
        if job.status == 'completed':
            usage.success_count += 1
            
            # Extract token count from result if available
            if job.result:
                try:
                    result_data = json.loads(job.result) if isinstance(job.result, str) else job.result
                    if 'tokens' in result_data:
                        usage.total_tokens += result_data['tokens']
                except (json.JSONDecodeError, TypeError):
                    pass
            
            # Calculate processing time
            if job.started_at and job.completed_at:
                processing_time = (job.completed_at - job.started_at).total_seconds()
                usage.total_processing_time += processing_time
        
        elif job.status == 'failed':
            usage.error_count += 1
        
        usage.save()
        
        # Update model's last used timestamp
        job.model.last_used_at = timezone.now()
        job.model.save(update_fields=['last_used_at'])
        
        logger.debug(f"Updated usage stats for model {job.model.name}")
        
    except Exception as e:
        logger.error(f"Error updating model usage stats: {str(e)}")


@receiver(post_delete, sender=OllamaProcessingJob)
def job_post_delete(sender, instance, **kwargs):
    """Handle job deletion"""
    try:
        # Clear job cache
        cache.delete(f'ollama_job_{instance.id}')
        cache.delete('ollama_pending_jobs')
        
        logger.info(f"Processing job {instance.id} deleted")
        
    except Exception as e:
        logger.error(f"Error in job post_delete signal: {str(e)}")


# Custom signal for model health checks
from django.dispatch import Signal

model_health_check = Signal()
model_pull_completed = Signal()
job_processing_started = Signal()
job_processing_completed = Signal()


@receiver(model_health_check)
def handle_model_health_check(sender, model_id, is_healthy, **kwargs):
    """Handle model health check results"""
    try:
        model = OllamaModel.objects.get(id=model_id)
        
        if not is_healthy and model.is_active:
            logger.warning(f"Model {model.name} failed health check, considering deactivation")
            
            # Optionally deactivate unhealthy models
            if hasattr(settings, 'OLLAMA_AUTO_DEACTIVATE_UNHEALTHY') and settings.OLLAMA_AUTO_DEACTIVATE_UNHEALTHY:
                model.is_active = False
                model.save(update_fields=['is_active'])
                logger.info(f"Automatically deactivated unhealthy model {model.name}")
        
    except OllamaModel.DoesNotExist:
        logger.error(f"Model with ID {model_id} not found for health check")
    except Exception as e:
        logger.error(f"Error handling model health check: {str(e)}")


@receiver(model_pull_completed)
def handle_model_pull_completed(sender, model_name, success, **kwargs):
    """Handle model pull completion"""
    try:
        if success:
            logger.info(f"Model {model_name} pulled successfully")
            
            # Try to activate any models waiting for this model
            waiting_models = OllamaModel.objects.filter(
                model_name=model_name,
                is_active=False
            )
            
            for model in waiting_models:
                # Test if model is now available
                try:
                    client = OllamaClient(model.configuration.name)
                    response = client.generate(
                        model.model_name,
                        "Test",
                        temperature=0.1,
                        max_tokens=10
                    )
                    client.close()
                    
                    if response.success:
                        model.is_active = True
                        model.save(update_fields=['is_active'])
                        logger.info(f"Activated model {model.name} after successful pull")
                        
                except Exception as e:
                    logger.error(f"Error testing pulled model {model.name}: {str(e)}")
        
        else:
            logger.error(f"Failed to pull model {model_name}")
        
    except Exception as e:
        logger.error(f"Error handling model pull completion: {str(e)}")


@receiver(job_processing_started)
def handle_job_processing_started(sender, job_id, **kwargs):
    """Handle job processing start"""
    try:
        job = OllamaProcessingJob.objects.get(id=job_id)
        job.started_at = timezone.now()
        job.status = 'processing'
        job.save(update_fields=['started_at', 'status'])
        
        logger.info(f"Job {job_id} processing started")
        
    except OllamaProcessingJob.DoesNotExist:
        logger.error(f"Job with ID {job_id} not found")
    except Exception as e:
        logger.error(f"Error handling job processing start: {str(e)}")


@receiver(job_processing_completed)
def handle_job_processing_completed(sender, job_id, success, result=None, error=None, **kwargs):
    """Handle job processing completion"""
    try:
        job = OllamaProcessingJob.objects.get(id=job_id)
        job.completed_at = timezone.now()
        
        if success:
            job.status = 'completed'
            job.result = result
        else:
            job.status = 'failed'
            job.error_message = error
        
        job.save(update_fields=['completed_at', 'status', 'result', 'error_message'])
        
        logger.info(f"Job {job_id} processing completed with status: {job.status}")
        
    except OllamaProcessingJob.DoesNotExist:
        logger.error(f"Job with ID {job_id} not found")
    except Exception as e:
        logger.error(f"Error handling job processing completion: {str(e)}")