from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    RecruitmentRAGViewSet,
    WorkflowAutomationViewSet,
    CandidateEnhancedViewSet,
    TaskStatusAPIView
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'rag', RecruitmentRAGViewSet, basename='recruitment-rag')
router.register(r'workflow', WorkflowAutomationViewSet, basename='workflow-automation')
router.register(r'candidates', CandidateEnhancedViewSet, basename='candidates-enhanced')

# URL patterns
urlpatterns = [
    # API ViewSets
    path('api/v1/', include(router.urls)),
    
    # Individual API endpoints
    path('api/v1/task-status/', TaskStatusAPIView.as_view(), name='task-status'),
    
    # RAG System endpoints
    path('api/v1/rag/analyze-resume/', 
         RecruitmentRAGViewSet.as_view({'post': 'analyze_resume'}), 
         name='rag-analyze-resume'),
    
    path('api/v1/rag/batch-analyze/', 
         RecruitmentRAGViewSet.as_view({'post': 'batch_analyze'}), 
         name='rag-batch-analyze'),
    
    path('api/v1/rag/find-similar/', 
         RecruitmentRAGViewSet.as_view({'post': 'find_similar_candidates'}), 
         name='rag-find-similar'),
    
    path('api/v1/rag/analysis-status/', 
         RecruitmentRAGViewSet.as_view({'get': 'analysis_status'}), 
         name='rag-analysis-status'),
    
    # Workflow Automation endpoints
    path('api/v1/workflow/trigger/', 
         WorkflowAutomationViewSet.as_view({'post': 'trigger_workflow'}), 
         name='workflow-trigger'),
    
    path('api/v1/workflow/status/', 
         WorkflowAutomationViewSet.as_view({'get': 'workflow_status'}), 
         name='workflow-status'),
    
    path('api/v1/workflow/health/', 
         WorkflowAutomationViewSet.as_view({'get': 'service_health'}), 
         name='workflow-health'),
    
    # Enhanced Candidate endpoints
    path('api/v1/candidates/<int:pk>/analyze/', 
         CandidateEnhancedViewSet.as_view({'post': 'analyze_with_ai'}), 
         name='candidate-analyze'),
    
    path('api/v1/candidates/<int:pk>/trigger-workflow/', 
         CandidateEnhancedViewSet.as_view({'post': 'trigger_workflow'}), 
         name='candidate-trigger-workflow'),
    
    path('api/v1/candidates/analytics/', 
         CandidateEnhancedViewSet.as_view({'get': 'analytics'}), 
         name='candidate-analytics'),
]

# API Documentation patterns (optional)
api_info_patterns = [
    # Health check endpoint
    path('api/v1/health/', 
         WorkflowAutomationViewSet.as_view({'get': 'service_health'}), 
         name='api-health'),
]

urlpatterns += api_info_patterns