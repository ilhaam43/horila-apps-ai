from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def index_view(request):
    """Simple index view for testing."""
    return JsonResponse({
        'status': 'success',
        'message': 'Indonesian NLP module is working',
        'module': 'indonesian_nlp'
    })


def test_view(request):
    """Simple test view for testing."""
    return JsonResponse({
        'status': 'success',
        'message': 'Test endpoint is working',
        'timestamp': str(timezone.now())
    })