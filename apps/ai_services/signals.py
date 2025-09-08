from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
import logging
import hashlib
import json
from datetime import timedelta

from .models import (
    AIModelRegistry,
    AIPrediction,
    KnowledgeBase,
    DocumentClassification,
    SearchQuery,
    NLPAnalysis,
    WorkflowExecution,
    AIServiceLog,
    AIAnalytics
)

logger = logging.getLogger(__name__)

# AI Model Registry Signals
@receiver(post_save, sender=AIModelRegistry)
def ai_model_registry_post_save(sender, instance, created, **kwargs):
    """Handle AI model registry changes."""
    try:
        # Clear model cache when registry changes
        cache_key = f"ai_model_{instance.service_type}_{instance.name}"
        cache.delete(cache_key)
        
        # Clear service cache
        service_cache_key = f"ai_service_{instance.service_type}"
        cache.delete(service_cache_key)
        
        # Log the change
        action = "created" if created else "updated"
        AIServiceLog.objects.create(
            service_type=instance.service_type,
            operation=f"model_registry_{action}",
            log_level="INFO",
            message=f"AI model {instance.name} v{instance.version} was {action}",
            extra_data={
                'model_id': str(instance.id),
                'model_name': instance.name,
                'model_type': instance.model_type,
                'is_active': instance.is_active
            }
        )
        
        logger.info(f"AI model {instance.name} v{instance.version} was {action}")
        
    except Exception as e:
        logger.error(f"Error in ai_model_registry_post_save: {str(e)}")

@receiver(pre_delete, sender=AIModelRegistry)
def ai_model_registry_pre_delete(sender, instance, **kwargs):
    """Handle AI model registry deletion."""
    try:
        # Log the deletion
        AIServiceLog.objects.create(
            service_type=instance.service_type,
            operation="model_registry_deleted",
            log_level="WARNING",
            message=f"AI model {instance.name} v{instance.version} was deleted",
            extra_data={
                'model_id': str(instance.id),
                'model_name': instance.name,
                'model_type': instance.model_type,
                'predictions_count': instance.predictions.count()
            }
        )
        
        logger.warning(f"AI model {instance.name} v{instance.version} was deleted")
        
    except Exception as e:
        logger.error(f"Error in ai_model_registry_pre_delete: {str(e)}")

# AI Prediction Signals
@receiver(post_save, sender=AIPrediction)
def ai_prediction_post_save(sender, instance, created, **kwargs):
    """Handle AI prediction creation/update."""
    if not created:
        return
    
    try:
        # Update analytics
        today = timezone.now().date()
        service_type = instance.model.service_type
        
        # Update daily prediction count
        analytics, created = AIAnalytics.objects.get_or_create(
            service_type=service_type,
            metric_name='daily_predictions',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        analytics.metric_value += 1
        analytics.save()
        
        # Update success rate if prediction failed
        if not instance.is_successful:
            error_analytics, created = AIAnalytics.objects.get_or_create(
                service_type=service_type,
                metric_name='daily_errors',
                date=today,
                defaults={'metric_value': 0, 'metric_data': {}}
            )
            error_analytics.metric_value += 1
            error_analytics.save()
            
            # Log error
            AIServiceLog.objects.create(
                service_type=service_type,
                operation="prediction_error",
                log_level="ERROR",
                message=f"Prediction failed: {instance.error_message}",
                extra_data={
                    'prediction_id': str(instance.id),
                    'model_name': instance.model.name,
                    'error_message': instance.error_message
                }
            )
        
        # Update average processing time
        if instance.processing_time_ms:
            time_analytics, created = AIAnalytics.objects.get_or_create(
                service_type=service_type,
                metric_name='avg_processing_time',
                date=today,
                defaults={
                    'metric_value': instance.processing_time_ms,
                    'metric_data': {'count': 1, 'total_time': instance.processing_time_ms}
                }
            )
            
            if not created:
                data = time_analytics.metric_data
                data['count'] += 1
                data['total_time'] += instance.processing_time_ms
                time_analytics.metric_value = data['total_time'] / data['count']
                time_analytics.metric_data = data
                time_analytics.save()
        
        logger.info(f"Prediction analytics updated for {service_type}")
        
    except Exception as e:
        logger.error(f"Error in ai_prediction_post_save: {str(e)}")

# Knowledge Base Signals
@receiver(post_save, sender=KnowledgeBase)
def knowledge_base_post_save(sender, instance, created, **kwargs):
    """Handle knowledge base changes."""
    try:
        # Clear knowledge base cache
        cache.delete('knowledge_base_index')
        cache.delete('knowledge_base_embeddings')
        
        # Generate text hash for caching
        if not instance.embedding_vector:
            text_content = f"{instance.title} {instance.content}"
            text_hash = hashlib.sha256(text_content.encode()).hexdigest()
            
            # This would trigger embedding generation in a background task
            # For now, we'll just log it
            logger.info(f"Knowledge base entry {instance.id} needs embedding generation")
        
        # Update analytics
        today = timezone.now().date()
        action = "created" if created else "updated"
        
        analytics, created_analytics = AIAnalytics.objects.get_or_create(
            service_type='knowledge_ai',
            metric_name=f'daily_knowledge_{action}',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        analytics.metric_value += 1
        analytics.save()
        
        # Log the change
        AIServiceLog.objects.create(
            service_type='knowledge_ai',
            operation=f"knowledge_{action}",
            log_level="INFO",
            message=f"Knowledge base entry '{instance.title}' was {action}",
            extra_data={
                'knowledge_id': str(instance.id),
                'title': instance.title,
                'content_type': instance.content_type,
                'category': instance.category
            }
        )
        
        logger.info(f"Knowledge base entry {instance.id} was {action}")
        
    except Exception as e:
        logger.error(f"Error in knowledge_base_post_save: {str(e)}")

@receiver(post_save, sender=KnowledgeBase)
def knowledge_base_increment_view(sender, instance, **kwargs):
    """Handle knowledge base view count updates."""
    # This is called when last_accessed is updated
    if hasattr(instance, '_view_incremented'):
        try:
            # Update daily views analytics
            today = timezone.now().date()
            
            analytics, created = AIAnalytics.objects.get_or_create(
                service_type='knowledge_ai',
                metric_name='daily_views',
                date=today,
                defaults={'metric_value': 0, 'metric_data': {}}
            )
            analytics.metric_value += 1
            analytics.save()
            
        except Exception as e:
            logger.error(f"Error updating knowledge base view analytics: {str(e)}")

# Document Classification Signals
@receiver(post_save, sender=DocumentClassification)
def document_classification_post_save(sender, instance, created, **kwargs):
    """Handle document classification changes."""
    if not created:
        return
    
    try:
        # Update analytics
        today = timezone.now().date()
        
        # Update daily classification count
        analytics, created = AIAnalytics.objects.get_or_create(
            service_type='document_classifier',
            metric_name='daily_classifications',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        analytics.metric_value += 1
        analytics.save()
        
        # Update category distribution
        category_analytics, created = AIAnalytics.objects.get_or_create(
            service_type='document_classifier',
            metric_name='category_distribution',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        
        data = category_analytics.metric_data
        category = instance.predicted_category
        data[category] = data.get(category, 0) + 1
        category_analytics.metric_data = data
        category_analytics.metric_value = sum(data.values())
        category_analytics.save()
        
        # Log classification
        AIServiceLog.objects.create(
            service_type='document_classifier',
            operation="document_classified",
            log_level="INFO",
            message=f"Document '{instance.document_name}' classified as '{instance.predicted_category}'",
            extra_data={
                'classification_id': str(instance.id),
                'document_name': instance.document_name,
                'predicted_category': instance.predicted_category,
                'confidence_score': instance.confidence_score,
                'classification_method': instance.classification_method
            }
        )
        
        logger.info(f"Document {instance.document_name} classified as {instance.predicted_category}")
        
    except Exception as e:
        logger.error(f"Error in document_classification_post_save: {str(e)}")

# Search Query Signals
@receiver(post_save, sender=SearchQuery)
def search_query_post_save(sender, instance, created, **kwargs):
    """Handle search query changes."""
    if not created:
        return
    
    try:
        # Update analytics
        today = timezone.now().date()
        
        # Update daily search count
        analytics, created = AIAnalytics.objects.get_or_create(
            service_type='intelligent_search',
            metric_name='daily_searches',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        analytics.metric_value += 1
        analytics.save()
        
        # Update search type distribution
        type_analytics, created = AIAnalytics.objects.get_or_create(
            service_type='intelligent_search',
            metric_name='search_type_distribution',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        
        data = type_analytics.metric_data
        search_type = instance.query_type
        data[search_type] = data.get(search_type, 0) + 1
        type_analytics.metric_data = data
        type_analytics.metric_value = sum(data.values())
        type_analytics.save()
        
        # Update average results count
        if instance.results_count > 0:
            results_analytics, created = AIAnalytics.objects.get_or_create(
                service_type='intelligent_search',
                metric_name='avg_results_count',
                date=today,
                defaults={
                    'metric_value': instance.results_count,
                    'metric_data': {'count': 1, 'total_results': instance.results_count}
                }
            )
            
            if not created:
                data = results_analytics.metric_data
                data['count'] += 1
                data['total_results'] += instance.results_count
                results_analytics.metric_value = data['total_results'] / data['count']
                results_analytics.metric_data = data
                results_analytics.save()
        
        # Log search
        AIServiceLog.objects.create(
            service_type='intelligent_search',
            operation="search_performed",
            log_level="INFO",
            message=f"Search performed: '{instance.query_text[:50]}...'",
            extra_data={
                'search_id': str(instance.id),
                'query_type': instance.query_type,
                'results_count': instance.results_count,
                'processing_time_ms': instance.processing_time_ms
            }
        )
        
        logger.info(f"Search query performed: {instance.query_text[:50]}...")
        
    except Exception as e:
        logger.error(f"Error in search_query_post_save: {str(e)}")

# NLP Analysis Signals
@receiver(post_save, sender=NLPAnalysis)
def nlp_analysis_post_save(sender, instance, created, **kwargs):
    """Handle NLP analysis changes."""
    if not created:
        return
    
    try:
        # Update analytics
        today = timezone.now().date()
        
        # Update daily analysis count
        analytics, created = AIAnalytics.objects.get_or_create(
            service_type='indonesian_nlp',
            metric_name='daily_analyses',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        analytics.metric_value += 1
        analytics.save()
        
        # Update sentiment distribution
        if instance.sentiment_label:
            sentiment_analytics, created = AIAnalytics.objects.get_or_create(
                service_type='indonesian_nlp',
                metric_name='sentiment_distribution',
                date=today,
                defaults={'metric_value': 0, 'metric_data': {}}
            )
            
            data = sentiment_analytics.metric_data
            sentiment = instance.sentiment_label
            data[sentiment] = data.get(sentiment, 0) + 1
            sentiment_analytics.metric_data = data
            sentiment_analytics.metric_value = sum(data.values())
            sentiment_analytics.save()
        
        # Log analysis
        AIServiceLog.objects.create(
            service_type='indonesian_nlp',
            operation="text_analyzed",
            log_level="INFO",
            message=f"Text analyzed: {instance.analysis_type}",
            extra_data={
                'analysis_id': str(instance.id),
                'analysis_type': instance.analysis_type,
                'sentiment_label': instance.sentiment_label,
                'sentiment_score': instance.sentiment_score,
                'text_length': len(instance.text)
            }
        )
        
        logger.info(f"NLP analysis completed: {instance.analysis_type}")
        
    except Exception as e:
        logger.error(f"Error in nlp_analysis_post_save: {str(e)}")

# Workflow Execution Signals
@receiver(post_save, sender=WorkflowExecution)
def workflow_execution_post_save(sender, instance, created, **kwargs):
    """Handle workflow execution changes."""
    try:
        # Update analytics
        today = timezone.now().date()
        
        if created:
            # Update daily workflow count
            analytics, created_analytics = AIAnalytics.objects.get_or_create(
                service_type='rag_n8n',
                metric_name='daily_workflows',
                date=today,
                defaults={'metric_value': 0, 'metric_data': {}}
            )
            analytics.metric_value += 1
            analytics.save()
        
        # Update status distribution
        status_analytics, created = AIAnalytics.objects.get_or_create(
            service_type='rag_n8n',
            metric_name='workflow_status_distribution',
            date=today,
            defaults={'metric_value': 0, 'metric_data': {}}
        )
        
        data = status_analytics.metric_data
        status = instance.n8n_status
        data[status] = data.get(status, 0) + 1
        status_analytics.metric_data = data
        status_analytics.metric_value = sum(data.values())
        status_analytics.save()
        
        # Log workflow status change
        AIServiceLog.objects.create(
            service_type='rag_n8n',
            operation="workflow_status_changed",
            log_level="INFO",
            message=f"Workflow '{instance.workflow_name}' status: {instance.n8n_status}",
            extra_data={
                'workflow_id': str(instance.id),
                'workflow_type': instance.workflow_type,
                'workflow_name': instance.workflow_name,
                'n8n_status': instance.n8n_status,
                'is_successful': instance.is_successful
            }
        )
        
        logger.info(f"Workflow {instance.workflow_name} status: {instance.n8n_status}")
        
    except Exception as e:
        logger.error(f"Error in workflow_execution_post_save: {str(e)}")

# Cache cleanup signals
@receiver(post_delete, sender=KnowledgeBase)
def knowledge_base_post_delete(sender, instance, **kwargs):
    """Clean up cache after knowledge base deletion."""
    try:
        cache.delete('knowledge_base_index')
        cache.delete('knowledge_base_embeddings')
        
        # Log deletion
        AIServiceLog.objects.create(
            service_type='knowledge_ai',
            operation="knowledge_deleted",
            log_level="WARNING",
            message=f"Knowledge base entry '{instance.title}' was deleted",
            extra_data={
                'knowledge_id': str(instance.id),
                'title': instance.title,
                'content_type': instance.content_type
            }
        )
        
        logger.warning(f"Knowledge base entry {instance.id} was deleted")
        
    except Exception as e:
        logger.error(f"Error in knowledge_base_post_delete: {str(e)}")

# Periodic cleanup task (would be better with Celery)
def cleanup_old_data():
    """Clean up old data periodically."""
    try:
        # Clean up old logs (older than 30 days)
        cutoff_date = timezone.now() - timedelta(days=30)
        old_logs = AIServiceLog.objects.filter(created_at__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        
        logger.info(f"Cleaned up {count} old log entries")
        
        # Clean up old analytics (older than 1 year)
        analytics_cutoff = timezone.now().date() - timedelta(days=365)
        old_analytics = AIAnalytics.objects.filter(date__lt=analytics_cutoff)
        analytics_count = old_analytics.count()
        old_analytics.delete()
        
        logger.info(f"Cleaned up {analytics_count} old analytics entries")
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_data: {str(e)}")