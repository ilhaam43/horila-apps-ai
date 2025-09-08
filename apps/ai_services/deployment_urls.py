#!/usr/bin/env python3
"""
URL Configuration for AI Model Deployment APIs
"""

from django.urls import path, include
from . import deployment_views

app_name = 'ai_deployment'

urlpatterns = [
    # Main deployment management endpoints
    path('deploy/', deployment_views.ModelDeploymentAPIView.as_view(), name='deploy_model'),
    path('deployments/', deployment_views.ModelDeploymentAPIView.as_view(), name='list_deployments'),
    path('undeploy/', deployment_views.ModelDeploymentAPIView.as_view(), name='undeploy_model'),
    
    # Health check endpoints
    path('health/<str:deployment_name>/', deployment_views.DeploymentHealthCheckAPIView.as_view(), name='deployment_health'),
    
    # Prediction endpoints
    path('predict/<str:deployment_name>/', deployment_views.ModelPredictionAPIView.as_view(), name='model_prediction'),
    
    # Metrics and monitoring endpoints
    path('metrics/', deployment_views.DeploymentMetricsAPIView.as_view(), name='all_deployment_metrics'),
    path('metrics/<str:deployment_name>/', deployment_views.DeploymentMetricsAPIView.as_view(), name='deployment_metrics'),
    
    # System status endpoints
    path('status/', deployment_views.deployment_status, name='deployment_status'),
    path('available-models/', deployment_views.available_models_for_deployment, name='available_models'),
    path('batch-deploy/', deployment_views.batch_deploy_models, name='batch_deploy'),
]