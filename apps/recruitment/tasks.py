from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
import logging
import json
from typing import List, Dict, Any

from .models import Candidate, Recruitment
from .services import RecruitmentRAGService, N8NClient

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_candidate_analysis(self, candidate_id: int, job_description: str = ""):
    """Process candidate resume analysis asynchronously"""
    try:
        logger.info(f"Starting analysis for candidate {candidate_id}")
        
        # Check if candidate exists
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            logger.error(f"Candidate {candidate_id} not found")
            return {
                'status': 'error',
                'message': f'Candidate {candidate_id} not found'
            }
        
        # Initialize RAG service
        rag_service = RecruitmentRAGService()
        
        # Get job description if not provided
        if not job_description and candidate.recruitment_id:
            job_description = candidate.recruitment_id.description or ""
        
        # Perform analysis
        analysis_result = rag_service.analyze_resume(candidate_id, job_description)
        
        # Cache the result
        cache_key = f"resume_analysis_{candidate_id}"
        cache.set(cache_key, analysis_result, timeout=86400)  # Cache for 24 hours
        
        logger.info(f"Analysis completed for candidate {candidate_id}")
        
        return {
            'status': 'success',
            'candidate_id': candidate_id,
            'analysis': analysis_result,
            'processed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error analyzing candidate {candidate_id}: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying analysis for candidate {candidate_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'candidate_id': candidate_id,
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def trigger_recruitment_workflow_task(self, candidate_id: int, workflow_type: str):
    """Trigger N8N recruitment workflow asynchronously"""
    try:
        logger.info(f"Triggering {workflow_type} workflow for candidate {candidate_id}")
        
        # Check if candidate exists
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            logger.error(f"Candidate {candidate_id} not found")
            return {
                'status': 'error',
                'message': f'Candidate {candidate_id} not found'
            }
        
        # Initialize RAG service
        rag_service = RecruitmentRAGService()
        
        # Trigger workflow
        workflow_result = rag_service.trigger_recruitment_workflow(candidate_id, workflow_type)
        
        logger.info(f"Workflow {workflow_type} triggered successfully for candidate {candidate_id}")
        
        return {
            'status': 'success',
            'candidate_id': candidate_id,
            'workflow_type': workflow_type,
            'workflow_result': workflow_result,
            'triggered_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error triggering workflow for candidate {candidate_id}: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying workflow trigger for candidate {candidate_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'candidate_id': candidate_id,
            'workflow_type': workflow_type,
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def batch_analyze_candidates(self, candidate_ids: List[int], job_description: str = ""):
    """Batch analyze multiple candidates asynchronously"""
    try:
        logger.info(f"Starting batch analysis for {len(candidate_ids)} candidates")
        
        results = []
        failed_candidates = []
        
        # Initialize RAG service
        rag_service = RecruitmentRAGService()
        
        for candidate_id in candidate_ids:
            try:
                # Check if candidate exists
                candidate = Candidate.objects.get(id=candidate_id)
                
                # Get job description if not provided
                current_job_description = job_description
                if not current_job_description and candidate.recruitment_id:
                    current_job_description = candidate.recruitment_id.description or ""
                
                # Perform analysis
                analysis_result = rag_service.analyze_resume(candidate_id, current_job_description)
                
                # Cache the result
                cache_key = f"resume_analysis_{candidate_id}"
                cache.set(cache_key, analysis_result, timeout=86400)
                
                results.append({
                    'candidate_id': candidate_id,
                    'status': 'success',
                    'analysis': analysis_result
                })
                
                logger.info(f"Analysis completed for candidate {candidate_id}")
                
            except Candidate.DoesNotExist:
                logger.error(f"Candidate {candidate_id} not found")
                failed_candidates.append({
                    'candidate_id': candidate_id,
                    'error': 'Candidate not found'
                })
                
            except Exception as e:
                logger.error(f"Error analyzing candidate {candidate_id}: {str(e)}")
                failed_candidates.append({
                    'candidate_id': candidate_id,
                    'error': str(e)
                })
        
        logger.info(f"Batch analysis completed. Success: {len(results)}, Failed: {len(failed_candidates)}")
        
        return {
            'status': 'completed',
            'total_candidates': len(candidate_ids),
            'successful_analyses': len(results),
            'failed_analyses': len(failed_candidates),
            'results': results,
            'failures': failed_candidates,
            'processed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in batch analysis: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying batch analysis (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_candidate_to_vector_db(self, candidate_id: int):
    """Sync candidate resume to vector database"""
    try:
        logger.info(f"Syncing candidate {candidate_id} to vector database")
        
        # Check if candidate exists
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            logger.error(f"Candidate {candidate_id} not found")
            return {
                'status': 'error',
                'message': f'Candidate {candidate_id} not found'
            }
        
        # Initialize RAG service
        rag_service = RecruitmentRAGService()
        
        # Store resume in vector database
        result = rag_service.store_resume_embedding(candidate_id)
        
        logger.info(f"Candidate {candidate_id} synced to vector database successfully")
        
        return {
            'status': 'success',
            'candidate_id': candidate_id,
            'vector_result': result,
            'synced_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error syncing candidate {candidate_id} to vector DB: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying vector DB sync for candidate {candidate_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'candidate_id': candidate_id,
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def cleanup_old_analysis_cache(self):
    """Clean up old analysis results from cache"""
    try:
        logger.info("Starting cleanup of old analysis cache")
        
        # Get all candidates
        candidates = Candidate.objects.all()
        cleaned_count = 0
        
        for candidate in candidates:
            cache_key = f"resume_analysis_{candidate.id}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                # Check if analysis is older than 7 days
                processed_at = cached_result.get('processed_at')
                if processed_at:
                    from datetime import datetime, timedelta
                    processed_time = datetime.fromisoformat(processed_at.replace('Z', '+00:00'))
                    if timezone.now() - processed_time > timedelta(days=7):
                        cache.delete(cache_key)
                        cleaned_count += 1
        
        logger.info(f"Cleanup completed. Removed {cleaned_count} old cache entries")
        
        return {
            'status': 'success',
            'cleaned_entries': cleaned_count,
            'cleaned_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in cache cleanup: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying cache cleanup (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_candidate_stage_workflow(self, candidate_id: int, new_stage_id: int, trigger_workflow: bool = True):
    """Update candidate stage and optionally trigger workflow"""
    try:
        logger.info(f"Updating stage for candidate {candidate_id} to stage {new_stage_id}")
        
        # Check if candidate exists
        try:
            candidate = Candidate.objects.get(id=candidate_id)
        except Candidate.DoesNotExist:
            logger.error(f"Candidate {candidate_id} not found")
            return {
                'status': 'error',
                'message': f'Candidate {candidate_id} not found'
            }
        
        # Update candidate stage
        from .models import Stage
        try:
            new_stage = Stage.objects.get(id=new_stage_id)
            old_stage_id = candidate.stage_id.id if candidate.stage_id else None
            candidate.stage_id = new_stage
            candidate.save()
            
            logger.info(f"Candidate {candidate_id} stage updated from {old_stage_id} to {new_stage_id}")
            
        except Stage.DoesNotExist:
            logger.error(f"Stage {new_stage_id} not found")
            return {
                'status': 'error',
                'message': f'Stage {new_stage_id} not found'
            }
        
        # Trigger workflow if requested
        workflow_result = None
        if trigger_workflow:
            try:
                rag_service = RecruitmentRAGService()
                
                # Determine workflow type based on stage
                workflow_type = 'candidate_notification'
                if new_stage.stage_type == 'interview':
                    workflow_type = 'interview_scheduling'
                elif new_stage.stage_type == 'hired':
                    workflow_type = 'hiring_decision'
                
                workflow_result = rag_service.trigger_recruitment_workflow(candidate_id, workflow_type)
                logger.info(f"Workflow {workflow_type} triggered for candidate {candidate_id}")
                
            except Exception as workflow_exc:
                logger.error(f"Error triggering workflow: {str(workflow_exc)}")
                # Don't fail the entire task if workflow fails
                workflow_result = {'error': str(workflow_exc)}
        
        return {
            'status': 'success',
            'candidate_id': candidate_id,
            'old_stage_id': old_stage_id,
            'new_stage_id': new_stage_id,
            'workflow_triggered': trigger_workflow,
            'workflow_result': workflow_result,
            'updated_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error updating candidate stage: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying stage update for candidate {candidate_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'candidate_id': candidate_id,
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=180)
def generate_recruitment_insights(self, recruitment_id: int):
    """Generate AI-powered insights for a recruitment"""
    try:
        logger.info(f"Generating insights for recruitment {recruitment_id}")
        
        # Check if recruitment exists
        try:
            recruitment = Recruitment.objects.get(id=recruitment_id)
        except Recruitment.DoesNotExist:
            logger.error(f"Recruitment {recruitment_id} not found")
            return {
                'status': 'error',
                'message': f'Recruitment {recruitment_id} not found'
            }
        
        # Get all candidates for this recruitment
        candidates = recruitment.candidate_set.all()
        
        if not candidates.exists():
            return {
                'status': 'success',
                'recruitment_id': recruitment_id,
                'message': 'No candidates found for analysis',
                'insights': {}
            }
        
        # Initialize RAG service
        rag_service = RecruitmentRAGService()
        
        # Analyze all candidates
        insights = {
            'total_candidates': candidates.count(),
            'hired_candidates': candidates.filter(hired=True).count(),
            'active_candidates': candidates.filter(canceled=False, hired=False).count(),
            'top_candidates': [],
            'skill_gaps': [],
            'recommendations': []
        }
        
        # Get top candidates based on AI analysis
        top_candidates = []
        for candidate in candidates[:20]:  # Limit to top 20 for performance
            cache_key = f"resume_analysis_{candidate.id}"
            analysis = cache.get(cache_key)
            
            if analysis and analysis.get('similarity_score'):
                top_candidates.append({
                    'candidate_id': candidate.id,
                    'name': candidate.name,
                    'similarity_score': analysis['similarity_score'],
                    'recommendation': analysis.get('recommendation', '')
                })
        
        # Sort by similarity score
        top_candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
        insights['top_candidates'] = top_candidates[:10]
        
        # Cache insights
        cache_key = f"recruitment_insights_{recruitment_id}"
        cache.set(cache_key, insights, timeout=3600)  # Cache for 1 hour
        
        logger.info(f"Insights generated for recruitment {recruitment_id}")
        
        return {
            'status': 'success',
            'recruitment_id': recruitment_id,
            'insights': insights,
            'generated_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error generating insights for recruitment {recruitment_id}: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying insights generation for recruitment {recruitment_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        return {
            'status': 'error',
            'recruitment_id': recruitment_id,
            'message': str(exc),
            'failed_at': timezone.now().isoformat()
        }