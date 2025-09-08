from django.urls import path
from . import views

app_name = 'simple_poc_app'

urlpatterns = [
    # Health and status endpoints
    path('health/', views.health_check, name='health_check'),
    path('api/status/', views.api_status, name='api_status'),
    
    # AI Models endpoints
    path('api/models/', views.models_endpoint, name='models'),
    
    # Prediction endpoints
    path('api/predict/', views.predict_endpoint, name='predict'),
    
    # Training endpoints
    path('api/train/', views.train_endpoint, name='train'),
    
    # History endpoints
    path('api/predictions/', views.predictions_history, name='predictions_history'),
    path('api/training/', views.training_history, name='training_history'),
]