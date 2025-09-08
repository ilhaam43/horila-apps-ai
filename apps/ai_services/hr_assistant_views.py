"""HR Assistant Views

API endpoints untuk HR Assistant Service
"""

import json
import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.models import User

from .hr_assistant_service import HRAssistantService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class HRAssistantChatView(View):
    """Main chat endpoint for HR Assistant"""
    
    def __init__(self):
        super().__init__()
        self.hr_service = HRAssistantService()
    
    def post(self, request):
        """Process HR chat query"""
        try:
            # Parse request data
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            context = data.get('context', {})
            
            if not query:
                return JsonResponse({
                    'success': False,
                    'error': 'Query tidak boleh kosong',
                    'response': 'Silakan masukkan pertanyaan Anda.'
                }, status=400)
            
            # Process query with HR service
            result = self.hr_service.process_query(
                query=query,
                user=request.user,
                context=context
            )
            
            # Log the interaction
            logger.info(f"HR Assistant query from user {request.user.id}: {query[:100]}...")
            
            return JsonResponse(result)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Format JSON tidak valid',
                'response': 'Terjadi kesalahan dalam format permintaan.'
            }, status=400)
        
        except Exception as e:
            logger.error(f"Error in HR Assistant chat: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Terjadi kesalahan server',
                'response': 'Maaf, terjadi kesalahan. Silakan coba lagi.'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class HRInsightsView(View):
    """Endpoint for HR insights"""
    
    def __init__(self):
        super().__init__()
        self.hr_service = HRAssistantService()
    
    def get(self, request):
        """Get HR insights for current user"""
        try:
            result = self.hr_service.get_hr_insights(request.user)
            
            logger.info(f"HR insights requested by user {request.user.id}")
            
            return JsonResponse(result)
        
        except Exception as e:
            logger.error(f"Error getting HR insights: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Terjadi kesalahan server',
                'response': 'Tidak dapat mengambil insights saat ini.'
            }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def hr_assistant_quick_query(request):
    """Quick query endpoint for simple HR questions"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query tidak boleh kosong'
            }, status=400)
        
        hr_service = HRAssistantService()
        result = hr_service.process_query(query, request.user)
        
        # Return simplified response for quick queries
        return JsonResponse({
            'success': result.get('success', False),
            'response': result.get('response', ''),
            'intent': result.get('intent', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"Error in quick query: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Terjadi kesalahan server'
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def hr_assistant_status(request):
    """Get HR Assistant status and capabilities"""
    try:
        return JsonResponse({
            'success': True,
            'status': 'active',
            'capabilities': {
                'knowledge_management': True,
                'employee_data': True,
                'leave_management': True,
                'performance_tracking': True,
                'payroll_info': True,
                'contract_info': True,
                'insights': True
            },
            'supported_languages': ['id', 'en'],
            'version': '1.0.0'
        })
    
    except Exception as e:
        logger.error(f"Error getting HR Assistant status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Tidak dapat mengambil status'
        }, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def hr_assistant_feedback(request):
    """Collect feedback on HR Assistant responses"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        response = data.get('response', '')
        rating = data.get('rating', 0)  # 1-5 scale
        feedback = data.get('feedback', '')
        
        # Log feedback for analysis
        logger.info(f"HR Assistant feedback from user {request.user.id}: "
                   f"Rating={rating}, Query={query[:50]}..., Feedback={feedback[:100]}...")
        
        # Here you could save feedback to database for analysis
        # For now, just acknowledge receipt
        
        return JsonResponse({
            'success': True,
            'message': 'Terima kasih atas feedback Anda. Ini akan membantu kami meningkatkan layanan.'
        })
    
    except Exception as e:
        logger.error(f"Error collecting feedback: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Tidak dapat menyimpan feedback'
        }, status=500)