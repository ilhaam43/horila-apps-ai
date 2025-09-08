from django.urls import path, include
from . import api_views

app_name = 'ai_services'

urlpatterns = [
    # HR Assistant Endpoints
    path('hr/', include('ai_services.hr_assistant_urls', namespace='hr_assistant')),
    # Chatbot Endpoints
    path('chatbot/', include('ai_services.chatbot_urls')),
    path('hr-admin/', include('ai_services.hr_admin_urls')),
    # Training Data Management Endpoints
    path('', include('ai_services.training_urls')),
    # Budget AI Endpoints
    path('budget/prediction/', api_views.budget_prediction, name='budget_prediction'),
    path('budget/anomaly-detection/', api_views.budget_anomaly_detection, name='budget_anomaly_detection'),
    path('budget/analytics/', api_views.budget_analytics, name='budget_analytics'),
    
    # Knowledge AI Endpoints
    path('knowledge/query/', api_views.knowledge_query, name='knowledge_query'),
    path('knowledge/add-document/', api_views.knowledge_add_document, name='knowledge_add_document'),
    
    # Indonesian NLP Endpoints
    path('nlp/analyze/', api_views.indonesian_nlp_analyze, name='indonesian_nlp_analyze'),
    path('nlp/sentiment/', api_views.sentiment_analysis, name='sentiment_analysis'),
    
    # RAG + N8N Integration Endpoints
    path('rag-n8n/process/', api_views.rag_n8n_process, name='rag_n8n_process'),
    path('rag-n8n/recruitment/', api_views.trigger_recruitment_workflow, name='trigger_recruitment_workflow'),
    
    # Document Classification Endpoints
    path('documents/classify/', api_views.classify_document, name='classify_document'),
    path('documents/classify-file/', api_views.classify_document_file, name='classify_document_file'),
    path('documents/batch-classify/', api_views.batch_classify_documents, name='batch_classify_documents'),
    path('documents/categories/', api_views.document_categories, name='document_categories'),
    
    # Intelligent Search Endpoints
    path('search/intelligent/', api_views.intelligent_search, name='intelligent_search'),
    path('search/rebuild-index/', api_views.rebuild_search_index, name='rebuild_search_index'),
    path('search/statistics/', api_views.search_statistics, name='search_statistics'),
    
    # General AI Service Endpoints
    path('status/', api_views.ai_service_status, name='ai_service_status'),
    path('batch-request/', api_views.batch_ai_request, name='batch_ai_request'),
    path('health/', api_views.ai_health_check, name='ai_health_check'),
    
    # Preprocessing Endpoints
    path('preprocess/', api_views.preprocess_data, name='preprocess_data'),
    path('batch-preprocess/', api_views.batch_preprocess_data, name='batch_preprocess_data'),
    
    # Model Deployment Endpoints
    path('deployment/deploy/', api_views.deploy_model, name='deploy_model'),
    path('deployment/list/', api_views.list_deployments, name='list_deployments'),
    path('deployment/status/<str:deployment_id>/', api_views.deployment_status, name='deployment_status'),
    path('deployment/undeploy/<str:deployment_id>/', api_views.undeploy_model, name='undeploy_model'),
    path('deployment/status/', api_views.deployment_system_status, name='deployment_system_status'),
    path('deployment/available-models/', api_views.available_models, name='available_models'),
    path('deployment/deployments/', api_views.list_deployments, name='list_all_deployments'),
    
    # Public endpoints (no auth required)
    path('public/health/', api_views.public_system_health, name='public_system_health'),
    path('public/stats/', api_views.public_performance_stats, name='public_performance_stats'),
    
    # Async Processing Endpoints
    path('async/process/', api_views.AsyncAIProcessingView.as_view(), name='async_ai_processing'),
    
    # Performance and Monitoring Endpoints
    path('system/health/', api_views.system_health, name='system_health'),
    path('performance/optimize/', api_views.optimize_performance, name='optimize_performance'),
    path('performance/stats/', api_views.performance_stats, name='performance_stats'),
    path('monitoring/status/', api_views.monitoring_status, name='monitoring_status'),
    path('monitoring/start/', api_views.start_monitoring, name='start_monitoring'),
    path('monitoring/stop/', api_views.stop_monitoring, name='stop_monitoring'),
    path('analysis/bottlenecks/', api_views.bottleneck_analysis, name='bottleneck_analysis'),
]