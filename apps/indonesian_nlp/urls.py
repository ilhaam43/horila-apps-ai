"""URL configuration for Indonesian NLP module."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .api_views import (
    NLPModelViewSet,
    TextAnalysisJobViewSet,
    QuickAnalysisView,
    BatchAnalysisView,
    ModelStatsView
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'models', NLPModelViewSet, basename='model')
router.register(r'jobs', TextAnalysisJobViewSet, basename='job')

app_name = 'indonesian_nlp'

urlpatterns = [
    # Basic views
    path('', views.index_view, name='index'),
    path('test/', views.test_view, name='test'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/quick-analysis/', QuickAnalysisView.as_view(), name='quick-analysis'),
    path('api/batch-analysis/', BatchAnalysisView.as_view(), name='batch-analysis'),
    path('api/models/stats/', ModelStatsView.as_view(), name='model-stats'),
    
    # Router URLs (for compatibility with test cases)
    path('', include(router.urls)),
]