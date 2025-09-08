from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Basic health checks
    path('health/', views.HealthCheckView.as_view(), name='health'),
    path('health/ready/', views.ReadinessCheckView.as_view(), name='ready'),
    path('health/live/', views.LivenessCheckView.as_view(), name='live'),
    
    # Detailed monitoring
    path('health/detailed/', views.DetailedHealthCheckView.as_view(), name='detailed_health'),
    path('metrics/', views.metrics_view, name='metrics'),
]