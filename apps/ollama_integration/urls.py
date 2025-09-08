from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for API endpoints
router = DefaultRouter()
router.register(r'models', views.OllamaModelViewSet)
router.register(r'jobs', views.OllamaProcessingJobViewSet)
router.register(r'configurations', views.OllamaConfigurationViewSet)
router.register(r'templates', views.OllamaPromptTemplateViewSet)
router.register(r'usage', views.OllamaModelUsageViewSet)

app_name = 'ollama_integration'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Configuration URLs
    path('configurations/', views.ConfigurationListView.as_view(), name='configuration_list'),
    path('configurations/create/', views.ConfigurationCreateView.as_view(), name='configuration_create'),
    path('configurations/<int:pk>/', views.ConfigurationDetailView.as_view(), name='configuration_detail'),
    path('configurations/<int:pk>/edit/', views.ConfigurationUpdateView.as_view(), name='configuration_update'),
    path('configurations/<int:pk>/delete/', views.ConfigurationDeleteView.as_view(), name='configuration_delete'),
    path('configurations/<int:pk>/test/', views.test_configuration, name='configuration_test'),
    path('configurations/<int:pk>/toggle/', views.toggle_configuration, name='configuration_toggle'),
    
    # Model URLs
    path('models/', views.ModelListView.as_view(), name='model_list'),
    path('models/create/', views.ModelCreateView.as_view(), name='model_create'),
    path('models/<int:pk>/', views.ModelDetailView.as_view(), name='model_detail'),
    path('models/<int:pk>/edit/', views.ModelUpdateView.as_view(), name='model_update'),
    path('models/<int:pk>/delete/', views.ModelDeleteView.as_view(), name='model_delete'),
    path('models/<int:pk>/test/', views.test_model, name='model_test'),
    path('models/<int:pk>/toggle/', views.toggle_model, name='model_toggle'),
    path('models/<int:pk>/pull/', views.pull_model, name='model_pull'),
    path('models/<int:pk>/usage/', views.ModelUsageView.as_view(), name='model_usage'),
    
    # Processing Job URLs
    path('jobs/', views.JobListView.as_view(), name='job_list'),
    path('jobs/create/', views.JobCreateView.as_view(), name='job_create'),
    path('jobs/<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('jobs/<int:pk>/edit/', views.JobUpdateView.as_view(), name='job_update'),
    path('jobs/<int:pk>/delete/', views.JobDeleteView.as_view(), name='job_delete'),
    path('jobs/<int:pk>/retry/', views.retry_job, name='job_retry'),
    path('jobs/<int:pk>/cancel/', views.cancel_job, name='job_cancel'),
    path('jobs/<int:pk>/download/', views.download_job_result, name='job_download'),
    
    # Prompt Template URLs
    path('templates/', views.TemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.TemplateCreateView.as_view(), name='template_create'),
    path('templates/<int:pk>/', views.TemplateDetailView.as_view(), name='template_detail'),
    path('templates/<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='template_update'),
    path('templates/<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='template_delete'),
    path('templates/<int:pk>/test/', views.test_template, name='template_test'),
    path('templates/<int:pk>/render/', views.render_template, name='template_render'),
    
    # Quick Generation
    path('generate/', views.QuickGenerationView.as_view(), name='quick_generation'),
    path('generate/stream/', views.stream_generation, name='stream_generation'),
    
    # Analytics and Monitoring
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('monitoring/', views.MonitoringView.as_view(), name='monitoring'),
    path('logs/', views.LogsView.as_view(), name='logs'),
    
    # AJAX endpoints
    path('ajax/models/available/', views.get_available_models, name='ajax_available_models'),
    path('ajax/models/status/', views.get_model_status, name='ajax_model_status'),
    path('ajax/jobs/status/', views.get_job_status, name='ajax_job_status'),
    path('ajax/health/', views.health_check, name='ajax_health_check'),
    path('ajax/stats/', views.get_stats, name='ajax_stats'),
    path('ajax/templates/variables/', views.get_template_variables, name='ajax_template_variables'),
    
    # Bulk operations
    path('models/bulk/delete/', views.bulk_delete_models, name='bulk_delete_models'),
    path('models/bulk/toggle/', views.bulk_toggle_models, name='bulk_toggle_models'),
    path('jobs/bulk/delete/', views.bulk_delete_jobs, name='bulk_delete_jobs'),
    path('jobs/bulk/retry/', views.bulk_retry_jobs, name='bulk_retry_jobs'),
    path('jobs/bulk/cancel/', views.bulk_cancel_jobs, name='bulk_cancel_jobs'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Direct API endpoints (not using ViewSets)
    path('api/generate/', views.GenerateAPIView.as_view(), name='api_generate'),
    path('api/chat/', views.ChatAPIView.as_view(), name='api_chat'),
    path('api/embed/', views.EmbedAPIView.as_view(), name='api_embed'),
    path('api/stream/', views.StreamAPIView.as_view(), name='api_stream'),
    path('api/health/', views.HealthCheckAPIView.as_view(), name='api_health'),
    path('api/models/available/', views.AvailableModelsAPIView.as_view(), name='api_available_models'),
    path('api/models/pull/', views.PullModelAPIView.as_view(), name='api_pull_model'),
    path('api/templates/render/', views.RenderTemplateAPIView.as_view(), name='api_render_template'),
    
    # WebSocket endpoints (if using channels)
    # path('ws/stream/', views.StreamConsumer.as_asgi(), name='ws_stream'),
    # path('ws/jobs/', views.JobStatusConsumer.as_asgi(), name='ws_jobs'),
    
    # Export/Import
    path('export/models/', views.export_models, name='export_models'),
    path('export/jobs/', views.export_jobs, name='export_jobs'),
    path('export/templates/', views.export_templates, name='export_templates'),
    path('import/models/', views.import_models, name='import_models'),
    path('import/templates/', views.import_templates, name='import_templates'),
    
    # System Management
    path('system/cleanup/', views.cleanup_old_jobs, name='system_cleanup'),
    path('system/reset/', views.reset_statistics, name='system_reset'),
    path('system/backup/', views.backup_configuration, name='system_backup'),
    path('system/restore/', views.restore_configuration, name='system_restore'),
    
    # Documentation and Help
    path('help/', views.HelpView.as_view(), name='help'),
    path('help/api/', views.APIDocumentationView.as_view(), name='api_documentation'),
    path('help/models/', views.ModelDocumentationView.as_view(), name='model_documentation'),
    
    # Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('settings/notifications/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    path('settings/performance/', views.PerformanceSettingsView.as_view(), name='performance_settings'),
]

# Add debug URLs in development
from django.conf import settings
if settings.DEBUG:
    urlpatterns += [
        path('debug/test-connection/', views.debug_test_connection, name='debug_test_connection'),
        path('debug/model-info/', views.debug_model_info, name='debug_model_info'),
        path('debug/clear-cache/', views.debug_clear_cache, name='debug_clear_cache'),
    ]