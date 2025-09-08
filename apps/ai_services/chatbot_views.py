from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging

from .chatbot_service import ChatbotService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ChatbotAPIView(View):
    """
    API View untuk HR Chatbot
    """
    
    def __init__(self):
        super().__init__()
        self.chatbot_service = ChatbotService()
    
    def post(self, request):
        """
        Process chat message
        """
        try:
            data = json.loads(request.body)
            message = data.get('message', '').strip()
            session_id = data.get('session_id')
            
            if not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message is required'
                }, status=400)
            
            # Process message
            response = self.chatbot_service.process_message(
                user_id=request.user.id,
                message=message,
                session_id=session_id
            )
            
            return JsonResponse(response)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error in chatbot API: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)
    
    def get(self, request):
        """
        Get chat history
        """
        try:
            session_id = request.GET.get('session_id')
            limit = int(request.GET.get('limit', 20))
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Session ID is required'
                }, status=400)
            
            response = self.chatbot_service.get_chat_history(
                session_id=session_id,
                limit=limit
            )
            
            return JsonResponse(response)
            
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid limit parameter'
            }, status=400)
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Internal server error'
            }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def end_chat_session(request, session_id):
    """
    End a chat session
    """
    try:
        chatbot_service = ChatbotService()
        response = chatbot_service.end_session(session_id)
        
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Error ending chat session: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def quick_hr_query(request):
    """
    Quick HR query without session management
    Useful for simple one-off questions
    """
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)
        
        chatbot_service = ChatbotService()
        
        # Process query directly with HR orchestrator
        hr_response = chatbot_service.hr_orchestrator.process_query(
            query=query,
            user_id=request.user.id
        )
        
        # Generate formatted response
        formatted_response = chatbot_service._generate_response(hr_response, query)
        
        return JsonResponse({
            'success': True,
            'response': formatted_response,
            'query': query,
            'user_id': request.user.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in quick HR query: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def hr_assistant_status(request):
    """
    Get HR Assistant status and capabilities
    """
    try:
        return JsonResponse({
            'success': True,
            'status': 'active',
            'capabilities': [
                'Employee Information',
                'Leave Management',
                'Performance Data',
                'Payroll Information',
                'HR Insights'
            ],
            'supported_queries': [
                'Siapa manajer saya?',
                'Berapa saldo cuti saya?',
                'Bagaimana kinerja saya bulan ini?',
                'Kapan gaji saya dibayar?',
                'Siapa rekan kerja di departemen saya?'
            ],
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Error getting HR assistant status: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def user_hr_summary(request):
    """
    Get comprehensive HR summary for the current user
    """
    try:
        chatbot_service = ChatbotService()
        
        # Get HR summary from orchestrator
        summary = chatbot_service.hr_orchestrator.get_hr_summary(
            user_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'user_id': request.user.id,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting user HR summary: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)