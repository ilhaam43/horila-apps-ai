from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from django.http import JsonResponse

def welcome_page(request):
    """Welcome page for POC"""
    # Check if request wants JSON (API call)
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'message': 'Welcome to AI Services POC',
            'version': '1.0.0-poc',
            'endpoints': {
                'admin': '/admin/',
                'health': '/health/',
                'api_status': '/api/status/',
                'models': '/api/models/',
                'predict': '/api/predict/',
                'train': '/api/train/',
                'predictions_history': '/api/predictions/',
                'training_history': '/api/training/'
            },
            'documentation': {
                'health_check': 'GET /health/ - Check server health',
                'api_status': 'GET /api/status/ - Get API status and statistics',
                'list_models': 'GET /api/models/ - List all AI models',
                'create_model': 'POST /api/models/ - Create new AI model',
                'predict': 'POST /api/predict/ - Make prediction with model',
                'train': 'POST /api/train/ - Train AI model',
                'predictions': 'GET /api/predictions/ - Get predictions history',
                'training': 'GET /api/training/ - Get training history'
            }
        })
    
    # Return HTML template for browser requests
    return render(request, 'welcome.html')

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Welcome page
    path('', welcome_page, name='welcome'),
    
    # Simple POC app endpoints
    path('', include('simple_poc_app.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)