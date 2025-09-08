from django.urls import path
from . import training_views

urlpatterns = [
    # Dashboard and main views
    path('training-data/', training_views.training_data_dashboard, name='training_data_dashboard'),
    path('training-data/upload/', training_views.training_data_upload, name='training_data_upload'),
    path('training-data/<uuid:pk>/', training_views.training_data_detail, name='training_data_detail'),
    path('training-data/<uuid:pk>/edit/', training_views.training_data_edit, name='training_data_edit'),
    path('training-data/<uuid:pk>/delete/', training_views.training_data_delete, name='training_data_delete'),
    
    # File operations
    path('training-data/<uuid:pk>/download/', training_views.training_data_download, name='training_data_download'),
    
    # Processing operations
    path('training-data/<uuid:pk>/process/', training_views.training_data_process, name='training_data_process'),
    
    # Evaluation and metrics
    path('training-data/<uuid:pk>/evaluation/', training_views.training_data_evaluation, name='training_data_evaluation'),
    path('training-data/performance/', training_views.training_data_performance_dashboard, name='training_data_performance_dashboard'),
    
    # API endpoints
    path('training-data/api/stats/', training_views.training_data_api_stats, name='training_data_stats_api'),
    path('training-data/<uuid:pk>/api/metrics/', training_views.training_data_metrics_api, name='training_data_metrics_api'),
    path('training-data/<uuid:pk>/api/update-metrics/', training_views.training_data_update_metrics, name='training_data_update_metrics'),
]