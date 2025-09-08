from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Count, Avg
import logging
import json
from typing import Dict, List, Any

from .models import Candidate, Recruitment, Stage
from .serializers import CandidateSerializer, RecruitmentSerializer, StageSerializer
from .services import RecruitmentRAGService, N8NClient
from .tasks import process_candidate_analysis, trigger_recruitment_workflow_task, batch_analyze_candidates

logger = logging.getLogger(__name__)


class RecruitmentRAGViewSet(viewsets.ViewSet):
    """ViewSet for RAG-powered recruitment operations"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_service = RecruitmentRAGService()
    
    @action(detail=False, methods=['post'])
    def analyze_resume(self, request):
        """Analyze candidate resume using RAG system"""
        try:
            candidate_id = request.data.get('candidate_id')
            job_description = request.data.get('job_description', '')
            async_processing = request.data.get('async', False)
            
            if not candidate_id:
                return Response({
                    'error': 'candidate_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if candidate exists
            try:
                candidate = Candidate.objects.get(id=candidate_id)
            except Candidate.DoesNotExist:
                return Response({
                    'error': 'Candidate not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check cache first
            cached_result = cache.get(f"resume_analysis_{candidate_id}")
            if cached_result and not request.data.get('force_refresh', False):
                return Response({
                    'status': 'success',
                    'data': cached_result,
                    'cached': True
                })
            
            if async_processing:
                # Process asynchronously
                task = process_candidate_analysis.delay(candidate_id)
                return Response({
                    'status': 'processing',
                    'task_id': task.id,
                    'message': 'Analysis started. Use task_id to check status.'
                })
            else:
                # Process synchronously
                result = self.rag_service.analyze_resume(candidate_id, job_description)
                return Response({
                    'status': 'success',
                    'data': result
                })
                
        except Exception as e:
            logger.error(f"Error in resume analysis: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def batch_analyze(self, request):
        """Batch analyze multiple candidates"""
        try:
            candidate_ids = request.data.get('candidate_ids', [])
            
            if not candidate_ids or not isinstance(candidate_ids, list):
                return Response({
                    'error': 'candidate_ids must be a non-empty list'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate candidates exist
            existing_candidates = Candidate.objects.filter(id__in=candidate_ids)
            if len(existing_candidates) != len(candidate_ids):
                return Response({
                    'error': 'Some candidates not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Start batch processing
            task = batch_analyze_candidates.delay(candidate_ids)
            
            return Response({
                'status': 'processing',
                'task_id': task.id,
                'candidate_count': len(candidate_ids),
                'message': 'Batch analysis started'
            })
            
        except Exception as e:
            logger.error(f"Error in batch analysis: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def find_similar_candidates(self, request):
        """Find candidates similar to job requirements"""
        try:
            job_description = request.data.get('job_description', '')
            limit = request.data.get('limit', 10)
            
            if not job_description:
                return Response({
                    'error': 'job_description is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            similar_candidates = self.rag_service.find_similar_candidates(
                job_description, limit=limit
            )
            
            return Response({
                'status': 'success',
                'data': similar_candidates,
                'count': len(similar_candidates)
            })
            
        except Exception as e:
            logger.error(f"Error finding similar candidates: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def analysis_status(self, request):
        """Get analysis status for a candidate"""
        try:
            candidate_id = request.query_params.get('candidate_id')
            
            if not candidate_id:
                return Response({
                    'error': 'candidate_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check cache for result
            cached_result = cache.get(f"resume_analysis_{candidate_id}")
            
            if cached_result:
                return Response({
                    'status': 'completed',
                    'data': cached_result
                })
            else:
                return Response({
                    'status': 'not_found',
                    'message': 'No analysis found for this candidate'
                })
                
        except Exception as e:
            logger.error(f"Error getting analysis status: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkflowAutomationViewSet(viewsets.ViewSet):
    """ViewSet for N8N workflow automation"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n8n_client = N8NClient()
        self.rag_service = RecruitmentRAGService()
    
    @action(detail=False, methods=['post'])
    def trigger_workflow(self, request):
        """Trigger N8N workflow for candidate"""
        try:
            candidate_id = request.data.get('candidate_id')
            workflow_type = request.data.get('workflow_type')
            async_processing = request.data.get('async', True)
            
            if not candidate_id or not workflow_type:
                return Response({
                    'error': 'candidate_id and workflow_type are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate workflow type
            valid_workflows = [
                'resume_screening', 'interview_scheduling', 
                'candidate_notification', 'hiring_decision', 'onboarding_trigger'
            ]
            
            if workflow_type not in valid_workflows:
                return Response({
                    'error': f'Invalid workflow_type. Must be one of: {", ".join(valid_workflows)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if candidate exists
            try:
                candidate = Candidate.objects.get(id=candidate_id)
            except Candidate.DoesNotExist:
                return Response({
                    'error': 'Candidate not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if async_processing:
                # Process asynchronously
                task = trigger_recruitment_workflow_task.delay(candidate_id, workflow_type)
                return Response({
                    'status': 'processing',
                    'task_id': task.id,
                    'workflow_type': workflow_type,
                    'message': 'Workflow trigger started'
                })
            else:
                # Process synchronously
                result = self.rag_service.trigger_recruitment_workflow(candidate_id, workflow_type)
                return Response({
                    'status': 'success',
                    'data': result
                })
                
        except Exception as e:
            logger.error(f"Error triggering workflow: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def workflow_status(self, request):
        """Get N8N workflow execution status"""
        try:
            execution_id = request.query_params.get('execution_id')
            
            if not execution_id:
                return Response({
                    'error': 'execution_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not self.n8n_client.is_available():
                return Response({
                    'error': 'N8N service is not available'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            status_result = self.n8n_client.get_workflow_status(execution_id)
            
            return Response({
                'status': 'success',
                'data': status_result
            })
            
        except Exception as e:
            logger.error(f"Error getting workflow status: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def service_health(self, request):
        """Check health of automation services"""
        try:
            n8n_available = self.n8n_client.is_available()
            ollama_available = self.rag_service.ollama_service.is_available()
            
            return Response({
                'status': 'success',
                'services': {
                    'n8n': {
                        'available': n8n_available,
                        'url': self.n8n_client.base_url
                    },
                    'ollama': {
                        'available': ollama_available,
                        'url': self.rag_service.ollama_service.base_url
                    },
                    'chroma_db': {
                        'available': True,  # Assume available if no exception
                        'collections': ['resumes', 'job_descriptions']
                    }
                },
                'overall_health': n8n_available and ollama_available
            })
            
        except Exception as e:
            logger.error(f"Error checking service health: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CandidateEnhancedViewSet(viewsets.ModelViewSet):
    """Enhanced Candidate ViewSet with RAG integration"""
    
    queryset = Candidate.objects.all()
    serializer_class = CandidateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'mobile']
    filterset_fields = ['recruitment_id', 'stage_id', 'hired', 'canceled']
    ordering_fields = ['created_at', 'name', 'email']
    ordering = ['-created_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rag_service = RecruitmentRAGService()
    
    @action(detail=True, methods=['post'])
    def analyze_with_ai(self, request, pk=None):
        """Analyze specific candidate with AI"""
        candidate = self.get_object()
        
        try:
            job_description = request.data.get('job_description', '')
            if not job_description and candidate.recruitment_id:
                job_description = candidate.recruitment_id.description or ''
            
            # Get or create analysis
            cached_result = cache.get(f"resume_analysis_{candidate.id}")
            if cached_result and not request.data.get('force_refresh', False):
                analysis_result = cached_result
            else:
                analysis_result = self.rag_service.analyze_resume(candidate.id, job_description)
            
            return Response({
                'status': 'success',
                'candidate': CandidateSerializer(candidate).data,
                'analysis': analysis_result
            })
            
        except Exception as e:
            logger.error(f"Error in AI analysis for candidate {pk}: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def trigger_workflow(self, request, pk=None):
        """Trigger workflow for specific candidate"""
        candidate = self.get_object()
        
        try:
            workflow_type = request.data.get('workflow_type', 'resume_screening')
            
            result = self.rag_service.trigger_recruitment_workflow(candidate.id, workflow_type)
            
            return Response({
                'status': 'success',
                'candidate': CandidateSerializer(candidate).data,
                'workflow_result': result
            })
            
        except Exception as e:
            logger.error(f"Error triggering workflow for candidate {pk}: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get recruitment analytics with AI insights"""
        try:
            # Basic statistics
            total_candidates = self.get_queryset().count()
            hired_candidates = self.get_queryset().filter(hired=True).count()
            active_candidates = self.get_queryset().filter(canceled=False, hired=False).count()
            
            # Stage distribution
            stage_distribution = self.get_queryset().values(
                'stage_id__stage'
            ).annotate(count=Count('id')).order_by('-count')
            
            # Recent analysis results
            recent_analyses = []
            recent_candidates = self.get_queryset().order_by('-created_at')[:10]
            
            for candidate in recent_candidates:
                cached_analysis = cache.get(f"resume_analysis_{candidate.id}")
                if cached_analysis:
                    recent_analyses.append({
                        'candidate_id': candidate.id,
                        'candidate_name': candidate.name,
                        'recommendation': cached_analysis.get('recommendation'),
                        'similarity_score': cached_analysis.get('similarity_score'),
                        'processed_at': cached_analysis.get('processed_at')
                    })
            
            return Response({
                'status': 'success',
                'statistics': {
                    'total_candidates': total_candidates,
                    'hired_candidates': hired_candidates,
                    'active_candidates': active_candidates,
                    'hiring_rate': (hired_candidates / total_candidates * 100) if total_candidates > 0 else 0
                },
                'stage_distribution': list(stage_distribution),
                'recent_ai_analyses': recent_analyses
            })
            
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskStatusAPIView(APIView):
    """API view to check Celery task status"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get task status by task_id"""
        try:
            task_id = request.query_params.get('task_id')
            
            if not task_id:
                return Response({
                    'error': 'task_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from celery.result import AsyncResult
            
            task_result = AsyncResult(task_id)
            
            response_data = {
                'task_id': task_id,
                'status': task_result.status,
                'ready': task_result.ready()
            }
            
            if task_result.ready():
                if task_result.successful():
                    response_data['result'] = task_result.result
                else:
                    response_data['error'] = str(task_result.info)
            
            return Response({
                'status': 'success',
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)