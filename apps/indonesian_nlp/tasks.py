from celery import shared_task, current_task
from celery.exceptions import Retry, WorkerLostError
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db import transaction
import logging
import time
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple
import psutil
import gc

from .models import (
    NLPModel, TextAnalysisJob, NLPConfiguration,
    SentimentAnalysisResult, NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics
)
from .client import IndonesianNLPClient
from .signals import (
    job_started, job_completed, job_failed,
    model_loaded, model_unloaded, system_health_check
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_text_analysis_job(self, job_id: int) -> Dict[str, Any]:
    """Process a text analysis job"""
    job = None
    start_time = time.time()
    
    try:
        # Get job from database
        job = TextAnalysisJob.objects.select_related('model').get(id=job_id)
        
        # Check if job is already processed or cancelled
        if job.status in ['completed', 'cancelled']:
            logger.info(f"Job {job.job_id} already {job.status}, skipping")
            return {'status': job.status, 'message': f'Job already {job.status}'}
        
        # Update job status to processing
        job.status = 'processing'
        job.started_at = timezone.now()
        job.progress = 0
        job.save(update_fields=['status', 'started_at', 'progress'])
        
        logger.info(f"Starting job {job.job_id} for model {job.model.name}")
        
        # Send job started signal
        job_started.send(
            sender=TextAnalysisJob,
            job=job,
            task_id=self.request.id
        )
        
        # Initialize NLP client
        client = IndonesianNLPClient()
        
        # Update progress
        job.progress = 10
        job.save(update_fields=['progress'])
        
        # Load model if not already loaded
        if not job.model.is_loaded:
            logger.info(f"Loading model {job.model.name}")
            client.load_model(job.model.name)
            job.progress = 30
            job.save(update_fields=['progress'])
        
        # Perform analysis based on model type
        result = None
        confidence_score = 0.0
        
        job.progress = 50
        job.save(update_fields=['progress'])
        
        if job.model.model_type == 'sentiment':
            result = client.analyze_sentiment(
                text=job.input_text,
                model_name=job.model.name,
                **job.parameters
            )
            confidence_score = result.get('confidence', 0.0)
            
            # Save detailed result
            SentimentAnalysisResult.objects.create(
                job=job,
                sentiment=result.get('sentiment', 'neutral'),
                confidence=confidence_score,
                positive_score=result.get('positive_score', 0.0),
                negative_score=result.get('negative_score', 0.0),
                neutral_score=result.get('neutral_score', 0.0),
                subjectivity=result.get('subjectivity', 0.0),
                emotion_scores=result.get('emotion_scores', {}),
                keywords=result.get('keywords', [])
            )
            
        elif job.model.model_type == 'ner':
            result = client.extract_entities(
                text=job.input_text,
                model_name=job.model.name,
                **job.parameters
            )
            
            entities = result.get('entities', [])
            confidence_scores = [entity.get('confidence', 0.0) for entity in entities]
            confidence_score = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Save detailed results
            for entity in entities:
                NamedEntityResult.objects.create(
                    job=job,
                    text=entity.get('text', ''),
                    label=entity.get('label', ''),
                    start_pos=entity.get('start', 0),
                    end_pos=entity.get('end', 0),
                    confidence=entity.get('confidence', 0.0),
                    normalized_text=entity.get('normalized_text', ''),
                    context=entity.get('context', '')
                )
            
        elif job.model.model_type == 'classification':
            result = client.classify_text(
                text=job.input_text,
                model_name=job.model.name,
                **job.parameters
            )
            confidence_score = result.get('confidence', 0.0)
            
            # Save detailed result
            TextClassificationResult.objects.create(
                job=job,
                predicted_class=result.get('predicted_class', ''),
                confidence=confidence_score,
                class_probabilities=result.get('class_probabilities', {}),
                top_features=result.get('top_features', []),
                feature_weights=result.get('feature_weights', {})
            )
        
        else:
            raise ValueError(f"Unsupported model type: {job.model.model_type}")
        
        # Update progress
        job.progress = 90
        job.save(update_fields=['progress'])
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update job with results
        job.status = 'completed'
        job.result = result
        job.confidence_score = confidence_score
        job.processing_time = processing_time
        job.completed_at = timezone.now()
        job.progress = 100
        job.save(update_fields=[
            'status', 'result', 'confidence_score', 'processing_time',
            'completed_at', 'progress'
        ])
        
        logger.info(f"Job {job.job_id} completed successfully in {processing_time:.2f}s")
        
        # Send job completed signal
        job_completed.send(
            sender=TextAnalysisJob,
            job=job,
            result=result,
            completed_at=timezone.now(),
            processing_time=processing_time
        )
        
        return {
            'status': 'completed',
            'job_id': job.job_id,
            'result': result,
            'confidence_score': confidence_score,
            'processing_time': processing_time
        }
    
    except Exception as exc:
        processing_time = time.time() - start_time
        error_message = str(exc)
        error_traceback = traceback.format_exc()
        
        logger.error(f"Job {job.job_id if job else 'unknown'} failed: {error_message}")
        logger.error(f"Traceback: {error_traceback}")
        
        if job:
            # Update job with error
            job.status = 'failed'
            job.error_message = error_message
            job.processing_time = processing_time
            job.completed_at = timezone.now()
            job.save(update_fields=[
                'status', 'error_message', 'processing_time', 'completed_at'
            ])
            
            # Send job failed signal
            job_failed.send(
                sender=TextAnalysisJob,
                job=job,
                error=error_message,
                failed_at=timezone.now(),
                traceback=error_traceback
            )
            
            # Retry logic
            if self.request.retries < self.max_retries:
                job.retry_count += 1
                job.save(update_fields=['retry_count'])
                
                logger.info(f"Retrying job {job.job_id} (attempt {self.request.retries + 1})")
                raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return {
            'status': 'failed',
            'error': error_message,
            'processing_time': processing_time
        }


@shared_task(bind=True, max_retries=2)
def load_nlp_model(self, model_name: str) -> Dict[str, Any]:
    """Load an NLP model"""
    start_time = time.time()
    
    try:
        # Get model from database
        model = NLPModel.objects.get(name=model_name, is_active=True)
        
        if model.is_loaded:
            logger.info(f"Model {model_name} is already loaded")
            return {'status': 'already_loaded', 'model_name': model_name}
        
        logger.info(f"Loading model {model_name}")
        
        # Initialize client and load model
        client = IndonesianNLPClient()
        load_result = client.load_model(model_name)
        
        load_time = time.time() - start_time
        memory_usage = load_result.get('memory_usage', 0.0)
        
        # Send model loaded signal
        model_loaded.send(
            sender=NLPModel,
            model_name=model_name,
            load_time=load_time,
            memory_usage=memory_usage
        )
        
        logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
        
        return {
            'status': 'loaded',
            'model_name': model_name,
            'load_time': load_time,
            'memory_usage': memory_usage
        }
    
    except Exception as exc:
        load_time = time.time() - start_time
        error_message = str(exc)
        
        logger.error(f"Failed to load model {model_name}: {error_message}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying model load {model_name} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        
        return {
            'status': 'failed',
            'model_name': model_name,
            'error': error_message,
            'load_time': load_time
        }


@shared_task
def unload_nlp_model(model_name: str) -> Dict[str, Any]:
    """Unload an NLP model"""
    try:
        # Get model from database
        model = NLPModel.objects.get(name=model_name)
        
        if not model.is_loaded:
            logger.info(f"Model {model_name} is not loaded")
            return {'status': 'not_loaded', 'model_name': model_name}
        
        logger.info(f"Unloading model {model_name}")
        
        # Initialize client and unload model
        client = IndonesianNLPClient()
        client.unload_model(model_name)
        
        # Send model unloaded signal
        model_unloaded.send(
            sender=NLPModel,
            model_name=model_name
        )
        
        logger.info(f"Model {model_name} unloaded successfully")
        
        return {
            'status': 'unloaded',
            'model_name': model_name
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Failed to unload model {model_name}: {error_message}")
        
        return {
            'status': 'failed',
            'model_name': model_name,
            'error': error_message
        }


@shared_task
def test_nlp_model(model_name: str, test_text: str = None) -> Dict[str, Any]:
    """Test an NLP model with sample text"""
    try:
        # Get model from database
        model = NLPModel.objects.get(name=model_name, is_active=True)
        
        # Use default test text if not provided
        if not test_text:
            test_text = "Saya sangat senang dengan layanan ini."
        
        logger.info(f"Testing model {model_name} with text: {test_text[:50]}...")
        
        # Initialize client
        client = IndonesianNLPClient()
        
        # Load model if not loaded
        if not model.is_loaded:
            client.load_model(model_name)
        
        start_time = time.time()
        
        # Perform test based on model type
        if model.model_type == 'sentiment':
            result = client.analyze_sentiment(test_text, model_name)
        elif model.model_type == 'ner':
            result = client.extract_entities(test_text, model_name)
        elif model.model_type == 'classification':
            result = client.classify_text(test_text, model_name)
        else:
            raise ValueError(f"Unsupported model type: {model.model_type}")
        
        processing_time = time.time() - start_time
        
        logger.info(f"Model {model_name} test completed in {processing_time:.2f}s")
        
        return {
            'status': 'success',
            'model_name': model_name,
            'test_text': test_text,
            'result': result,
            'processing_time': processing_time
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Model {model_name} test failed: {error_message}")
        
        return {
            'status': 'failed',
            'model_name': model_name,
            'error': error_message
        }


@shared_task(bind=True)
def batch_process_texts(self, texts: List[str], analysis_type: str, model_name: str = None, 
                       parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process multiple texts in batch"""
    try:
        if not texts:
            return {'status': 'failed', 'error': 'No texts provided'}
        
        if len(texts) > 100:
            return {'status': 'failed', 'error': 'Too many texts (max 100)'}
        
        logger.info(f"Starting batch processing of {len(texts)} texts for {analysis_type}")
        
        # Initialize client
        client = IndonesianNLPClient()
        
        # Get appropriate model if not specified
        if not model_name:
            model = NLPModel.objects.filter(
                model_type=analysis_type,
                is_active=True
            ).first()
            if not model:
                return {'status': 'failed', 'error': f'No active model found for {analysis_type}'}
            model_name = model.name
        
        # Load model if needed
        model = NLPModel.objects.get(name=model_name)
        if not model.is_loaded:
            client.load_model(model_name)
        
        results = []
        start_time = time.time()
        
        for i, text in enumerate(texts):
            try:
                if analysis_type == 'sentiment':
                    result = client.analyze_sentiment(text, model_name, **(parameters or {}))
                elif analysis_type == 'ner':
                    result = client.extract_entities(text, model_name, **(parameters or {}))
                elif analysis_type == 'classification':
                    result = client.classify_text(text, model_name, **(parameters or {}))
                else:
                    raise ValueError(f"Unsupported analysis type: {analysis_type}")
                
                results.append({
                    'index': i,
                    'text': text,
                    'result': result,
                    'status': 'success'
                })
                
            except Exception as e:
                results.append({
                    'index': i,
                    'text': text,
                    'error': str(e),
                    'status': 'failed'
                })
        
        processing_time = time.time() - start_time
        successful_count = sum(1 for r in results if r['status'] == 'success')
        
        logger.info(f"Batch processing completed: {successful_count}/{len(texts)} successful in {processing_time:.2f}s")
        
        return {
            'status': 'completed',
            'total_texts': len(texts),
            'successful_count': successful_count,
            'failed_count': len(texts) - successful_count,
            'processing_time': processing_time,
            'results': results
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Batch processing failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def cleanup_old_jobs(days: int = 30) -> Dict[str, Any]:
    """Clean up old completed/failed jobs"""
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Delete old jobs
        old_jobs = TextAnalysisJob.objects.filter(
            status__in=['completed', 'failed', 'cancelled'],
            completed_at__lt=cutoff_date
        )
        
        count = old_jobs.count()
        old_jobs.delete()
        
        logger.info(f"Cleaned up {count} old jobs older than {days} days")
        
        return {
            'status': 'completed',
            'deleted_count': count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Job cleanup failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def update_usage_statistics() -> Dict[str, Any]:
    """Update usage statistics for all models"""
    try:
        logger.info("Updating usage statistics")
        
        models = NLPModel.objects.filter(is_active=True)
        updated_count = 0
        
        for model in models:
            # Get today's jobs for this model
            today = timezone.now().date()
            jobs_today = TextAnalysisJob.objects.filter(
                model=model,
                created_at__date=today
            )
            
            if jobs_today.exists():
                # Calculate statistics
                total_jobs = jobs_today.count()
                successful_jobs = jobs_today.filter(status='completed').count()
                failed_jobs = jobs_today.filter(status='failed').count()
                
                # Calculate average processing time
                completed_jobs = jobs_today.filter(
                    status='completed',
                    processing_time__isnull=False
                )
                
                if completed_jobs.exists():
                    avg_time = completed_jobs.aggregate(
                        avg=models.Avg('processing_time')
                    )['avg'] or 0.0
                    min_time = completed_jobs.aggregate(
                        min=models.Min('processing_time')
                    )['min'] or 0.0
                    max_time = completed_jobs.aggregate(
                        max=models.Max('processing_time')
                    )['max'] or 0.0
                else:
                    avg_time = min_time = max_time = 0.0
                
                # Update or create statistics
                current_hour = timezone.now().hour
                stats, created = ModelUsageStatistics.objects.update_or_create(
                    model=model,
                    date=today,
                    hour=current_hour,
                    defaults={
                        'total_requests': total_jobs,
                        'successful_requests': successful_jobs,
                        'failed_requests': failed_jobs,
                        'avg_processing_time': avg_time,
                        'min_processing_time': min_time,
                        'max_processing_time': max_time,
                    }
                )
                
                updated_count += 1
        
        logger.info(f"Updated usage statistics for {updated_count} models")
        
        return {
            'status': 'completed',
            'updated_models': updated_count
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Usage statistics update failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def process_pending_jobs() -> Dict[str, Any]:
    """Process pending jobs that haven't been picked up"""
    try:
        # Get configuration
        config = NLPConfiguration.get_active_config()
        max_concurrent = config.max_concurrent_jobs if config else 5
        
        # Check currently processing jobs
        processing_count = TextAnalysisJob.objects.filter(status='processing').count()
        
        if processing_count >= max_concurrent:
            logger.info(f"Max concurrent jobs ({max_concurrent}) reached, skipping")
            return {
                'status': 'skipped',
                'reason': 'max_concurrent_reached',
                'processing_count': processing_count
            }
        
        # Get pending jobs
        available_slots = max_concurrent - processing_count
        pending_jobs = TextAnalysisJob.objects.filter(
            status='pending'
        ).order_by('priority', 'created_at')[:available_slots]
        
        processed_count = 0
        
        for job in pending_jobs:
            try:
                # Start processing job
                process_text_analysis_job.delay(job.id)
                processed_count += 1
                logger.info(f"Queued job {job.job_id} for processing")
            except Exception as e:
                logger.error(f"Failed to queue job {job.job_id}: {str(e)}")
        
        logger.info(f"Processed {processed_count} pending jobs")
        
        return {
            'status': 'completed',
            'processed_count': processed_count,
            'available_slots': available_slots
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Pending jobs processing failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def health_check_models() -> Dict[str, Any]:
    """Perform health check on all loaded models"""
    try:
        logger.info("Performing model health check")
        
        loaded_models = NLPModel.objects.filter(is_loaded=True, is_active=True)
        results = []
        
        client = IndonesianNLPClient()
        
        for model in loaded_models:
            try:
                # Test model with simple text
                test_text = "Test kesehatan model."
                start_time = time.time()
                
                if model.model_type == 'sentiment':
                    result = client.analyze_sentiment(test_text, model.name)
                elif model.model_type == 'ner':
                    result = client.extract_entities(test_text, model.name)
                elif model.model_type == 'classification':
                    result = client.classify_text(test_text, model.name)
                else:
                    continue
                
                response_time = time.time() - start_time
                
                results.append({
                    'model_name': model.name,
                    'status': 'healthy',
                    'response_time': response_time,
                    'memory_usage': model.memory_usage
                })
                
            except Exception as e:
                results.append({
                    'model_name': model.name,
                    'status': 'unhealthy',
                    'error': str(e)
                })
        
        healthy_count = sum(1 for r in results if r['status'] == 'healthy')
        
        # Send system health check signal
        system_health_check.send(
            sender=None,
            results=results,
            healthy_count=healthy_count,
            total_count=len(results)
        )
        
        logger.info(f"Health check completed: {healthy_count}/{len(results)} models healthy")
        
        return {
            'status': 'completed',
            'total_models': len(results),
            'healthy_models': healthy_count,
            'unhealthy_models': len(results) - healthy_count,
            'results': results
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Model health check failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def cleanup_unused_models() -> Dict[str, Any]:
    """Unload models that haven't been used recently"""
    try:
        config = NLPConfiguration.get_active_config()
        timeout_minutes = config.model_unload_timeout // 60 if config else 60
        
        cutoff_time = timezone.now() - timezone.timedelta(minutes=timeout_minutes)
        
        # Find loaded models that haven't been used recently
        unused_models = NLPModel.objects.filter(
            is_loaded=True,
            last_used__lt=cutoff_time
        )
        
        unloaded_count = 0
        client = IndonesianNLPClient()
        
        for model in unused_models:
            try:
                client.unload_model(model.name)
                unloaded_count += 1
                logger.info(f"Unloaded unused model: {model.name}")
            except Exception as e:
                logger.error(f"Failed to unload model {model.name}: {str(e)}")
        
        # Force garbage collection
        gc.collect()
        
        logger.info(f"Cleaned up {unloaded_count} unused models")
        
        return {
            'status': 'completed',
            'unloaded_count': unloaded_count,
            'cutoff_time': cutoff_time.isoformat()
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"Model cleanup failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


@shared_task
def system_monitoring() -> Dict[str, Any]:
    """Monitor system resources and performance"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get NLP-specific metrics
        total_models = NLPModel.objects.count()
        active_models = NLPModel.objects.filter(is_active=True).count()
        loaded_models = NLPModel.objects.filter(is_loaded=True).count()
        
        pending_jobs = TextAnalysisJob.objects.filter(status='pending').count()
        processing_jobs = TextAnalysisJob.objects.filter(status='processing').count()
        
        # Check if system is under stress
        alerts = []
        if cpu_percent > 80:
            alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
        if memory.percent > 85:
            alerts.append(f"High memory usage: {memory.percent:.1f}%")
        if disk.percent > 90:
            alerts.append(f"High disk usage: {disk.percent:.1f}%")
        if pending_jobs > 50:
            alerts.append(f"High job queue: {pending_jobs} pending jobs")
        
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3)
            },
            'nlp': {
                'total_models': total_models,
                'active_models': active_models,
                'loaded_models': loaded_models,
                'pending_jobs': pending_jobs,
                'processing_jobs': processing_jobs
            },
            'alerts': alerts
        }
        
        # Cache metrics for dashboard
        cache.set('system_metrics', metrics, timeout=300)  # 5 minutes
        
        if alerts:
            logger.warning(f"System alerts: {', '.join(alerts)}")
        else:
            logger.info("System monitoring: all metrics normal")
        
        return {
            'status': 'completed',
            'metrics': metrics,
            'alert_count': len(alerts)
        }
    
    except Exception as exc:
        error_message = str(exc)
        logger.error(f"System monitoring failed: {error_message}")
        
        return {
            'status': 'failed',
            'error': error_message
        }


# Periodic tasks (to be configured in Celery beat)
@shared_task
def periodic_cleanup():
    """Run periodic cleanup tasks"""
    logger.info("Running periodic cleanup tasks")
    
    # Clean up old jobs (30 days)
    cleanup_old_jobs.delay(30)
    
    # Update usage statistics
    update_usage_statistics.delay()
    
    # Clean up unused models
    cleanup_unused_models.delay()
    
    # System monitoring
    system_monitoring.delay()
    
    return {'status': 'scheduled'}


@shared_task
def periodic_health_check():
    """Run periodic health checks"""
    logger.info("Running periodic health check")
    
    # Check model health
    health_check_models.delay()
    
    # Process pending jobs
    process_pending_jobs.delay()
    
    return {'status': 'scheduled'}