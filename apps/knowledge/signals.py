from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import os
import logging
from .models import (
    KnowledgeDocument, DocumentVersion, DocumentAccess, 
    AIProcessingJob, SearchQuery, KnowledgeBase
)
from .utils import process_document_with_ai

logger = logging.getLogger(__name__)


@receiver(post_save, sender=KnowledgeDocument)
def handle_document_created_or_updated(sender, instance, created, **kwargs):
    """Handle document creation or update"""
    try:
        if created:
            logger.info(f"New document created: {instance.title} (ID: {instance.id})")
            
            # Create initial version
            DocumentVersion.objects.create(
                document=instance,
                version_number=1,
                content=instance.content,
                file=instance.file,
                created_by=instance.created_by,
                change_summary="Initial version"
            )
            
            # Grant access to creator
            DocumentAccess.objects.get_or_create(
                document=instance,
                user=instance.created_by,
                defaults={
                    'access_type': 'edit',
                    'granted_by': instance.created_by
                }
            )
            
            # Trigger AI processing if enabled
            if getattr(settings, 'KNOWLEDGE_AUTO_AI_PROCESSING', True):
                try:
                    process_document_with_ai.delay(instance.id)
                    logger.info(f"AI processing triggered for document {instance.id}")
                except Exception as e:
                    logger.error(f"Failed to trigger AI processing for document {instance.id}: {str(e)}")
            
            # Update knowledge base statistics
            if instance.knowledge_base:
                instance.knowledge_base.update_statistics()
        
        else:
            logger.info(f"Document updated: {instance.title} (ID: {instance.id})")
            
            # Create new version if content changed
            latest_version = instance.versions.order_by('-version_number').first()
            if latest_version:
                content_changed = (
                    latest_version.content != instance.content or
                    (latest_version.file and instance.file and 
                     latest_version.file.name != instance.file.name)
                )
                
                if content_changed:
                    new_version_number = latest_version.version_number + 1
                    DocumentVersion.objects.create(
                        document=instance,
                        version_number=new_version_number,
                        content=instance.content,
                        file=instance.file,
                        created_by=instance.updated_by or instance.created_by,
                        change_summary=f"Updated to version {new_version_number}"
                    )
                    
                    # Re-trigger AI processing for significant changes
                    if getattr(settings, 'KNOWLEDGE_AUTO_AI_PROCESSING', True):
                        try:
                            process_document_with_ai.delay(instance.id)
                            logger.info(f"AI re-processing triggered for updated document {instance.id}")
                        except Exception as e:
                            logger.error(f"Failed to trigger AI re-processing: {str(e)}")
        
        # Update document statistics
        instance.update_statistics()
        
        # Clear related caches
        cache_keys = [
            f'document_{instance.id}',
            f'document_list_{instance.category_id if instance.category else "all"}',
            'knowledge_dashboard_stats',
            'popular_documents',
        ]
        cache.delete_many(cache_keys)
        
    except Exception as e:
        logger.error(f"Error in document post_save signal: {str(e)}")


@receiver(pre_delete, sender=KnowledgeDocument)
def handle_document_pre_delete(sender, instance, **kwargs):
    """Handle document deletion preparation"""
    try:
        # Store file path for cleanup
        if instance.file:
            instance._file_path_to_delete = instance.file.path
        
        # Cancel any pending AI processing jobs
        pending_jobs = AIProcessingJob.objects.filter(
            document=instance,
            status__in=['pending', 'processing']
        )
        
        for job in pending_jobs:
            job.status = 'cancelled'
            job.completed_at = timezone.now()
            job.error_message = "Document deleted"
            job.save()
        
        logger.info(f"Cancelled {pending_jobs.count()} AI processing jobs for document {instance.id}")
        
    except Exception as e:
        logger.error(f"Error in document pre_delete signal: {str(e)}")


@receiver(post_delete, sender=KnowledgeDocument)
def handle_document_deleted(sender, instance, **kwargs):
    """Handle document deletion cleanup"""
    try:
        # Clean up file from storage
        if hasattr(instance, '_file_path_to_delete'):
            try:
                if os.path.exists(instance._file_path_to_delete):
                    os.remove(instance._file_path_to_delete)
                    logger.info(f"Deleted file: {instance._file_path_to_delete}")
            except Exception as e:
                logger.error(f"Failed to delete file {instance._file_path_to_delete}: {str(e)}")
        
        # Update knowledge base statistics
        if hasattr(instance, 'knowledge_base') and instance.knowledge_base:
            instance.knowledge_base.update_statistics()
        
        # Clear caches
        cache_keys = [
            f'document_{instance.id}',
            'knowledge_dashboard_stats',
            'popular_documents',
        ]
        cache.delete_many(cache_keys)
        
        logger.info(f"Document deleted: {instance.title} (ID: {instance.id})")
        
    except Exception as e:
        logger.error(f"Error in document post_delete signal: {str(e)}")


@receiver(post_save, sender=DocumentVersion)
def handle_version_created(sender, instance, created, **kwargs):
    """Handle document version creation"""
    if created:
        try:
            logger.info(f"New version created for document {instance.document.id}: v{instance.version_number}")
            
            # Update document's updated_at timestamp
            instance.document.updated_at = timezone.now()
            instance.document.save(update_fields=['updated_at'])
            
            # Clear document cache
            cache.delete(f'document_{instance.document.id}')
            
        except Exception as e:
            logger.error(f"Error in version post_save signal: {str(e)}")


@receiver(post_save, sender=DocumentAccess)
def handle_access_granted(sender, instance, created, **kwargs):
    """Handle document access changes"""
    if created:
        try:
            logger.info(
                f"Access granted to user {instance.user.username} "
                f"for document {instance.document.id} ({instance.access_type})"
            )
            
            # Clear user's document list cache
            cache.delete(f'user_documents_{instance.user.id}')
            
        except Exception as e:
            logger.error(f"Error in access post_save signal: {str(e)}")


@receiver(post_save, sender=SearchQuery)
def handle_search_query(sender, instance, created, **kwargs):
    """Handle search query logging"""
    if created:
        try:
            # Update search analytics
            cache_key = 'search_analytics'
            analytics = cache.get(cache_key, {})
            
            # Update query frequency
            query_lower = instance.query.lower()
            analytics[query_lower] = analytics.get(query_lower, 0) + 1
            
            # Keep only top 100 queries
            if len(analytics) > 100:
                sorted_queries = sorted(analytics.items(), key=lambda x: x[1], reverse=True)
                analytics = dict(sorted_queries[:100])
            
            cache.set(cache_key, analytics, 3600 * 24)  # Cache for 24 hours
            
        except Exception as e:
            logger.error(f"Error in search query signal: {str(e)}")


@receiver(post_save, sender=AIProcessingJob)
def handle_ai_job_status_change(sender, instance, created, **kwargs):
    """Handle AI processing job status changes"""
    try:
        if not created and instance.status == 'completed':
            logger.info(f"AI processing job {instance.id} completed for document {instance.document.id}")
            
            # Update document with AI results if available
            if instance.output_data:
                document = instance.document
                output = instance.output_data
                
                # Update AI-generated fields
                if 'classification' in output:
                    classification = output['classification']
                    document.ai_confidence_score = classification.get('confidence', 0.0)
                    
                    # Auto-update document type if confidence is high
                    if classification.get('confidence', 0) > 0.8:
                        document.document_type = classification.get('category', 'other')
                
                if 'suggested_tags' in output:
                    document.ai_suggested_tags = output['suggested_tags']
                
                if 'keywords' in output:
                    document.ai_extracted_keywords = output['keywords']
                
                document.save(update_fields=[
                    'ai_confidence_score', 'document_type', 
                    'ai_suggested_tags', 'ai_extracted_keywords'
                ])
                
                # Clear document cache
                cache.delete(f'document_{document.id}')
        
        elif not created and instance.status == 'failed':
            logger.error(
                f"AI processing job {instance.id} failed for document {instance.document.id}: "
                f"{instance.error_message}"
            )
        
    except Exception as e:
        logger.error(f"Error in AI job signal: {str(e)}")


@receiver(post_save, sender=KnowledgeBase)
def handle_knowledge_base_created(sender, instance, created, **kwargs):
    """Handle knowledge base creation"""
    if created:
        try:
            logger.info(f"New knowledge base created: {instance.name} (ID: {instance.id})")
            
            # Grant admin access to creator
            if instance.created_by:
                DocumentAccess.objects.get_or_create(
                    knowledge_base=instance,
                    user=instance.created_by,
                    defaults={
                        'access_type': 'admin',
                        'granted_by': instance.created_by
                    }
                )
            
            # Initialize statistics
            instance.update_statistics()
            
        except Exception as e:
            logger.error(f"Error in knowledge base post_save signal: {str(e)}")


# Custom signal for document view tracking
from django.dispatch import Signal

document_viewed = Signal()


@receiver(document_viewed)
def handle_document_viewed(sender, document, user, **kwargs):
    """Handle document view event"""
    try:
        # Update view count
        document.view_count += 1
        document.last_accessed = timezone.now()
        document.save(update_fields=['view_count', 'last_accessed'])
        
        # Log search query if this came from search
        request = kwargs.get('request')
        if request and request.GET.get('q'):
            SearchQuery.objects.create(
                query=request.GET.get('q'),
                user=user if user.is_authenticated else None,
                results_count=1,
                clicked_document=document
            )
        
        # Update popular documents cache
        cache.delete('popular_documents')
        
        logger.debug(f"Document {document.id} viewed by user {user.username if user.is_authenticated else 'anonymous'}")
        
    except Exception as e:
        logger.error(f"Error in document viewed signal: {str(e)}")


# Utility function to trigger document view signal
def track_document_view(document, user, request=None):
    """Utility function to track document views"""
    document_viewed.send(
        sender=document.__class__,
        document=document,
        user=user,
        request=request
    )