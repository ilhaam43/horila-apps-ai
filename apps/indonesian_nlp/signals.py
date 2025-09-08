from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import logging
import os
import shutil
from typing import Optional

from .models import (
    NLPModel, TextAnalysisJob, NLPConfiguration,
    SentimentAnalysisResult, NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics
)
from .client import IndonesianNLPClient

logger = logging.getLogger(__name__)

# Custom signals
model_loaded = Signal()
model_unloaded = Signal()
job_started = Signal()
job_completed = Signal()
job_failed = Signal()
analysis_completed = Signal()
model_performance_updated = Signal()
system_health_check = Signal()


@receiver(post_save, sender=NLPConfiguration)
def handle_configuration_save(sender, instance, created, **kwargs):
    """Handle NLP configuration save events"""
    try:
        if created:
            logger.info(f"New NLP configuration created: {instance.name}")
        else:
            logger.info(f"NLP configuration updated: {instance.name}")
        
        # Clear configuration cache
        cache.delete('active_nlp_config')
        cache.delete(f'nlp_config_{instance.id}')
        
        # If this configuration is set as active, deactivate others
        if instance.is_active:
            NLPConfiguration.objects.exclude(id=instance.id).update(is_active=False)
            logger.info(f"Configuration {instance.name} set as active")
        
        # Update client configuration if this is the active config
        if instance.is_active:
            try:
                client = IndonesianNLPClient()
                client._update_configuration(instance)
                logger.info("NLP client configuration updated")
            except Exception as e:
                logger.error(f"Failed to update client configuration: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error handling configuration save: {str(e)}")


@receiver(pre_delete, sender=NLPConfiguration)
def handle_configuration_delete(sender, instance, **kwargs):
    """Handle NLP configuration deletion"""
    try:
        logger.info(f"Deleting NLP configuration: {instance.name}")
        
        # Clear cache
        cache.delete('active_nlp_config')
        cache.delete(f'nlp_config_{instance.id}')
        
        # If this was the active configuration, activate another one
        if instance.is_active:
            other_config = NLPConfiguration.objects.exclude(id=instance.id).first()
            if other_config:
                other_config.is_active = True
                other_config.save()
                logger.info(f"Configuration {other_config.name} set as new active config")
    
    except Exception as e:
        logger.error(f"Error handling configuration deletion: {str(e)}")


@receiver(post_save, sender=NLPModel)
def handle_model_save(sender, instance, created, **kwargs):
    """Handle NLP model save events"""
    try:
        if created:
            logger.info(f"New NLP model created: {instance.name} ({instance.model_type})")
            
            # Create initial usage statistics
            now = timezone.now()
            ModelUsageStatistics.objects.get_or_create(
                model=instance,
                date=now.date(),
                hour=now.hour,
                defaults={
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'avg_processing_time': 0.0,
                    'min_processing_time': 0.0,
                    'max_processing_time': 0.0,
                    'total_cpu_time': 0.0,
                    'peak_memory_usage': 0.0,
                }
            )
        else:
            logger.info(f"NLP model updated: {instance.name}")
        
        # Clear model cache
        cache.delete(f'nlp_model_{instance.id}')
        cache.delete(f'nlp_model_{instance.name}')
        cache.delete('active_nlp_models')
        
        # If model is deactivated, unload it
        if not instance.is_active and instance.is_loaded:
            try:
                client = IndonesianNLPClient()
                client.unload_model(instance.name)
                logger.info(f"Model {instance.name} unloaded due to deactivation")
            except Exception as e:
                logger.error(f"Failed to unload deactivated model {instance.name}: {str(e)}")
        
        # Validate model files if path is provided
        if instance.model_path and not os.path.exists(instance.model_path):
            logger.warning(f"Model file not found: {instance.model_path}")
    
    except Exception as e:
        logger.error(f"Error handling model save: {str(e)}")


@receiver(pre_delete, sender=NLPModel)
def handle_model_delete(sender, instance, **kwargs):
    """Handle NLP model deletion"""
    try:
        logger.info(f"Deleting NLP model: {instance.name}")
        
        # Unload model if loaded
        if instance.is_loaded:
            try:
                client = IndonesianNLPClient()
                client.unload_model(instance.name)
                logger.info(f"Model {instance.name} unloaded before deletion")
            except Exception as e:
                logger.error(f"Failed to unload model {instance.name}: {str(e)}")
        
        # Clear cache
        cache.delete(f'nlp_model_{instance.id}')
        cache.delete(f'nlp_model_{instance.name}')
        cache.delete('active_nlp_models')
        
        # Cancel any pending jobs for this model
        pending_jobs = TextAnalysisJob.objects.filter(
            model=instance,
            status__in=['pending', 'processing']
        )
        
        for job in pending_jobs:
            job.status = 'cancelled'
            job.error_message = 'Model was deleted'
            job.completed_at = timezone.now()
            job.save()
        
        if pending_jobs.exists():
            logger.info(f"Cancelled {pending_jobs.count()} pending jobs for deleted model")
    
    except Exception as e:
        logger.error(f"Error handling model deletion: {str(e)}")


@receiver(post_delete, sender=NLPModel)
def handle_model_post_delete(sender, instance, **kwargs):
    """Handle post-deletion cleanup for NLP model"""
    try:
        # Clean up model files if they exist and are in a managed directory
        if instance.model_path and os.path.exists(instance.model_path):
            # Only delete if in managed models directory
            models_dir = getattr(settings, 'NLP_MODELS_DIR', None)
            if models_dir and instance.model_path.startswith(models_dir):
                try:
                    if os.path.isfile(instance.model_path):
                        os.remove(instance.model_path)
                    elif os.path.isdir(instance.model_path):
                        shutil.rmtree(instance.model_path)
                    logger.info(f"Cleaned up model files: {instance.model_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up model files: {str(e)}")
        
        # Clean up tokenizer files
        if instance.tokenizer_path and os.path.exists(instance.tokenizer_path):
            models_dir = getattr(settings, 'NLP_MODELS_DIR', None)
            if models_dir and instance.tokenizer_path.startswith(models_dir):
                try:
                    if os.path.isfile(instance.tokenizer_path):
                        os.remove(instance.tokenizer_path)
                    elif os.path.isdir(instance.tokenizer_path):
                        shutil.rmtree(instance.tokenizer_path)
                    logger.info(f"Cleaned up tokenizer files: {instance.tokenizer_path}")
                except Exception as e:
                    logger.error(f"Failed to clean up tokenizer files: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in post-delete cleanup: {str(e)}")


@receiver(post_save, sender=TextAnalysisJob)
def handle_job_save(sender, instance, created, **kwargs):
    """Handle text analysis job save events"""
    try:
        if created:
            logger.info(f"New analysis job created: {instance.job_id} ({instance.model.name})")
            
            # Send job created signal
            job_started.send(
                sender=sender,
                job=instance,
                created_at=timezone.now()
            )
            
            # Update model last used timestamp
            instance.model.last_used = timezone.now()
            instance.model.save(update_fields=['last_used'])
        
        else:
            # Check if job status changed
            if hasattr(instance, '_original_status'):
                old_status = instance._original_status
                new_status = instance.status
                
                if old_status != new_status:
                    logger.info(f"Job {instance.job_id} status changed: {old_status} -> {new_status}")
                    
                    if new_status == 'completed':
                        job_completed.send(
                            sender=sender,
                            job=instance,
                            completed_at=timezone.now()
                        )
                        
                        # Update usage statistics
                        _update_model_usage_stats(instance)
                        
                    elif new_status == 'failed':
                        job_failed.send(
                            sender=sender,
                            job=instance,
                            error=instance.error_message,
                            failed_at=timezone.now()
                        )
                        
                        # Update failure statistics
                        _update_model_failure_stats(instance)
        
        # Clear job cache
        cache.delete(f'job_{instance.job_id}')
        cache.delete(f'job_{instance.id}')
    
    except Exception as e:
        logger.error(f"Error handling job save: {str(e)}")


@receiver(pre_delete, sender=TextAnalysisJob)
def handle_job_delete(sender, instance, **kwargs):
    """Handle text analysis job deletion"""
    try:
        logger.info(f"Deleting analysis job: {instance.job_id}")
        
        # Clear cache
        cache.delete(f'job_{instance.job_id}')
        cache.delete(f'job_{instance.id}')
        
        # If job is still processing, try to cancel it
        if instance.status == 'processing':
            logger.warning(f"Deleting job {instance.job_id} while still processing")
    
    except Exception as e:
        logger.error(f"Error handling job deletion: {str(e)}")


@receiver(post_save, sender=SentimentAnalysisResult)
@receiver(post_save, sender=NamedEntityResult)
@receiver(post_save, sender=TextClassificationResult)
def handle_analysis_result_save(sender, instance, created, **kwargs):
    """Handle analysis result save events"""
    try:
        if created:
            result_type = sender.__name__.replace('Result', '').lower()
            logger.info(f"New {result_type} result created")
            
            # Send analysis completed signal
            analysis_completed.send(
                sender=sender,
                result=instance,
                result_type=result_type,
                created_at=timezone.now()
            )
    
    except Exception as e:
        logger.error(f"Error handling analysis result save: {str(e)}")


@receiver(model_loaded)
def handle_model_loaded(sender, model_name, load_time, memory_usage, **kwargs):
    """Handle model loaded signal"""
    try:
        logger.info(f"Model loaded: {model_name} (load_time: {load_time:.2f}s, memory: {memory_usage:.2f}MB)")
        
        # Update model status
        try:
            model = NLPModel.objects.get(name=model_name)
            model.is_loaded = True
            model.load_time = load_time
            model.memory_usage = memory_usage
            model.last_used = timezone.now()
            model.save(update_fields=['is_loaded', 'load_time', 'memory_usage', 'last_used'])
        except NLPModel.DoesNotExist:
            logger.error(f"Model {model_name} not found in database")
        
        # Clear cache
        cache.delete(f'nlp_model_{model_name}')
        cache.delete('active_nlp_models')
    
    except Exception as e:
        logger.error(f"Error handling model loaded signal: {str(e)}")


@receiver(model_unloaded)
def handle_model_unloaded(sender, model_name, **kwargs):
    """Handle model unloaded signal"""
    try:
        logger.info(f"Model unloaded: {model_name}")
        
        # Update model status
        try:
            model = NLPModel.objects.get(name=model_name)
            model.is_loaded = False
            model.load_time = None
            model.memory_usage = 0.0
            model.save(update_fields=['is_loaded', 'load_time', 'memory_usage'])
        except NLPModel.DoesNotExist:
            logger.error(f"Model {model_name} not found in database")
        
        # Clear cache
        cache.delete(f'nlp_model_{model_name}')
        cache.delete('active_nlp_models')
    
    except Exception as e:
        logger.error(f"Error handling model unloaded signal: {str(e)}")


@receiver(job_completed)
def handle_job_completed(sender, job, completed_at, **kwargs):
    """Handle job completed signal"""
    try:
        logger.info(f"Job completed: {job.job_id} (processing_time: {job.processing_time:.2f}s)")
        
        # Update model performance metrics
        model_performance_updated.send(
            sender=NLPModel,
            model=job.model,
            job=job,
            success=True
        )
    
    except Exception as e:
        logger.error(f"Error handling job completed signal: {str(e)}")


@receiver(job_failed)
def handle_job_failed(sender, job, error, failed_at, **kwargs):
    """Handle job failed signal"""
    try:
        logger.error(f"Job failed: {job.job_id} - {error}")
        
        # Update model performance metrics
        model_performance_updated.send(
            sender=NLPModel,
            model=job.model,
            job=job,
            success=False
        )
    
    except Exception as e:
        logger.error(f"Error handling job failed signal: {str(e)}")


@receiver(model_performance_updated)
def handle_model_performance_updated(sender, model, job, success, **kwargs):
    """Handle model performance update signal"""
    try:
        # Update usage statistics
        today = timezone.now().date()
        current_hour = timezone.now().hour
        
        stats, created = ModelUsageStatistics.objects.get_or_create(
            model=model,
            date=today,
            hour=current_hour,
            defaults={
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'avg_processing_time': 0.0,
                'min_processing_time': float('inf'),
                'max_processing_time': 0.0,
                'total_cpu_time': 0.0,
                'peak_memory_usage': 0.0,
            }
        )
        
        # Update counters
        stats.total_requests += 1
        if success:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1
        
        # Update processing time statistics
        if job.processing_time:
            processing_time = job.processing_time
            
            # Update average
            total_time = stats.avg_processing_time * (stats.total_requests - 1) + processing_time
            stats.avg_processing_time = total_time / stats.total_requests
            
            # Update min/max
            if stats.min_processing_time == float('inf') or processing_time < stats.min_processing_time:
                stats.min_processing_time = processing_time
            if processing_time > stats.max_processing_time:
                stats.max_processing_time = processing_time
        
        stats.save()
        
        logger.debug(f"Updated performance stats for model {model.name}")
    
    except Exception as e:
        logger.error(f"Error updating model performance: {str(e)}")


@receiver(system_health_check)
def handle_system_health_check(sender, **kwargs):
    """Handle system health check signal"""
    try:
        logger.info("Performing system health check")
        
        # Check active models
        active_models = NLPModel.objects.filter(is_active=True)
        loaded_models = active_models.filter(is_loaded=True)
        
        logger.info(f"Active models: {active_models.count()}, Loaded models: {loaded_models.count()}")
        
        # Check pending jobs
        pending_jobs = TextAnalysisJob.objects.filter(status='pending').count()
        processing_jobs = TextAnalysisJob.objects.filter(status='processing').count()
        
        logger.info(f"Pending jobs: {pending_jobs}, Processing jobs: {processing_jobs}")
        
        # Check configuration
        active_config = NLPConfiguration.get_active_config()
        if active_config:
            logger.info(f"Active configuration: {active_config.name}")
        else:
            logger.warning("No active configuration found")
    
    except Exception as e:
        logger.error(f"Error during system health check: {str(e)}")


def _update_model_usage_stats(job: TextAnalysisJob) -> None:
    """Update model usage statistics for completed job"""
    try:
        today = timezone.now().date()
        current_hour = timezone.now().hour
        
        stats, created = ModelUsageStatistics.objects.get_or_create(
            model=job.model,
            date=today,
            hour=current_hour,
            defaults={
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'avg_processing_time': 0.0,
                'min_processing_time': float('inf'),
                'max_processing_time': 0.0,
                'total_cpu_time': 0.0,
                'peak_memory_usage': 0.0,
            }
        )
        
        stats.total_requests += 1
        stats.successful_requests += 1
        
        if job.processing_time:
            processing_time = job.processing_time
            
            # Update average processing time
            total_time = stats.avg_processing_time * (stats.successful_requests - 1) + processing_time
            stats.avg_processing_time = total_time / stats.successful_requests
            
            # Update min/max processing time
            if stats.min_processing_time == float('inf') or processing_time < stats.min_processing_time:
                stats.min_processing_time = processing_time
            if processing_time > stats.max_processing_time:
                stats.max_processing_time = processing_time
        
        stats.save()
    
    except Exception as e:
        logger.error(f"Error updating usage stats: {str(e)}")


def _update_model_failure_stats(job: TextAnalysisJob) -> None:
    """Update model failure statistics for failed job"""
    try:
        today = timezone.now().date()
        current_hour = timezone.now().hour
        
        stats, created = ModelUsageStatistics.objects.get_or_create(
            model=job.model,
            date=today,
            hour=current_hour,
            defaults={
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'avg_processing_time': 0.0,
                'min_processing_time': float('inf'),
                'max_processing_time': 0.0,
                'total_cpu_time': 0.0,
                'peak_memory_usage': 0.0,
            }
        )
        
        stats.total_requests += 1
        stats.failed_requests += 1
        stats.save()
    
    except Exception as e:
        logger.error(f"Error updating failure stats: {str(e)}")


# Connect signals to track original status for jobs
def _track_job_status(sender, instance, **kwargs):
    """Track original job status for comparison"""
    if instance.pk:
        try:
            original = TextAnalysisJob.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except TextAnalysisJob.DoesNotExist:
            instance._original_status = None
    else:
        instance._original_status = None

# Connect the status tracking
from django.db.models.signals import pre_save
pre_save.connect(_track_job_status, sender=TextAnalysisJob)