import logging
import json
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.db import models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    ChatbotConversation, ChatbotMessage, ChatbotFeedback,
    KnowledgeDocument
)
from .chatbot_service import ChatbotRAGService
from ai_services.chatbot_slm_service import ChatbotSLMService
from .chatbot_serializers import (
    ChatbotConversationSerializer, ChatbotMessageSerializer,
    ChatbotFeedbackSerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_query(request):
    """
    Main chatbot query endpoint.
    Handles user questions and returns AI-generated responses.
    """
    try:
        data = request.data
        query = data.get('query', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not query:
            return Response({
                'success': False,
                'error': 'Query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        # Use SLM service directly (RAG service not available)
        slm_service = ChatbotSLMService()
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = ChatbotConversation.objects.get(
                    conversation_id=conversation_id,
                    user=request.user
                )
            except ChatbotConversation.DoesNotExist:
                conversation = slm_service.create_conversation(request.user, query)
        else:
            conversation = slm_service.create_conversation(request.user, query)
        
        # Add user message
        user_message = slm_service.add_message(
            conversation=conversation,
            sender='user',
            content=query,
            message_type='text'
        )
        
        # Retrieve relevant documents
        relevant_docs = slm_service.retrieve_relevant_documents(
            query=query,
            user=request.user,
            max_results=5
        )
        
        # Generate AI response using improved SLM service
        response_data = slm_service.generate_response(
            query=query,
            relevant_docs=relevant_docs,
            conversation=conversation
        )
        
        if response_data['success']:
            # Add AI response message
            ai_message = slm_service.add_message(
                conversation=conversation,
                sender='assistant',
                content=response_data['response'],
                message_type='text',
                ai_model=response_data.get('model_used', 'unknown'),
                confidence_score=response_data.get('confidence_score', 0.0),
                processing_time=response_data.get('processing_time', 0.0)
            )
            
            # Add document references
            for doc in response_data.get('referenced_documents', []):
                ai_message.referenced_documents.add(doc)
            
            # Prepare document and FAQ references for response
            doc_references = []
            faq_references = []
            
            for doc_data in relevant_docs:
                if doc_data.get('type') == 'faq':
                    # Handle FAQ references
                    faq = doc_data['faq']
                    faq_references.append({
                        'id': faq.id,
                        'question': faq.question,
                        'answer': faq.answer,
                        'category': faq.category.title,
                        'similarity_score': doc_data.get('similarity_score', 0.0)
                    })
                else:
                    # Handle document references
                    doc = doc_data['document']
                    doc_references.append({
                        'id': doc.id,
                        'title': doc.title,
                        'category': doc.category.name,
                        'similarity_score': doc_data.get('similarity_score', 0.0),
                        'snippet': doc_data.get('snippet', ''),
                        'url': f'/knowledge/documents/{doc.id}/'
                    })
            
            return Response({
                'success': True,
                'conversation_id': str(conversation.conversation_id),
                'response': response_data['response'],
                'confidence_score': response_data.get('confidence_score', 0.0),
                'processing_time': response_data.get('processing_time', 0.0),
                'referenced_documents': doc_references,
                'referenced_faqs': faq_references,
                'message_id': ai_message.id,
                'timestamp': ai_message.created_at.isoformat()
            }, status=status.HTTP_200_OK)
        else:
            # Add error message if SLM service fails
            error_message = slm_service.add_message(
                conversation=conversation,
                sender='system',
                content=response_data.get('response', 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.'),
                message_type='error'
            )
            
            return Response({
                'success': False,
                'conversation_id': str(conversation.conversation_id),
                'error': response_data.get('response', 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.'),
                'message_id': error_message.id
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"Chatbot query failed: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_history(request, conversation_id=None):
    """
    Get conversation history or list of conversations.
    """
    try:
        if conversation_id:
            # Get specific conversation
            try:
                conversation = ChatbotConversation.objects.get(
                    conversation_id=conversation_id,
                    user=request.user
                )
                
                # Get messages with pagination
                messages = conversation.messages.all().order_by('created_at')
                page = request.GET.get('page', 1)
                paginator = Paginator(messages, 50)
                page_obj = paginator.get_page(page)
                
                serializer = ChatbotMessageSerializer(page_obj, many=True)
                
                return Response({
                    'success': True,
                    'conversation': {
                        'id': str(conversation.conversation_id),
                        'title': conversation.get_title(),
                        'status': conversation.status,
                        'created_at': conversation.created_at.isoformat(),
                        'last_activity': conversation.last_activity.isoformat(),
                        'message_count': conversation.message_count
                    },
                    'messages': serializer.data,
                    'pagination': {
                        'current_page': page_obj.number,
                        'total_pages': paginator.num_pages,
                        'total_messages': paginator.count,
                        'has_next': page_obj.has_next(),
                        'has_previous': page_obj.has_previous()
                    }
                }, status=status.HTTP_200_OK)
                
            except ChatbotConversation.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
        
        else:
            # List user's conversations
            conversations = ChatbotConversation.objects.filter(
                user=request.user
            ).order_by('-last_activity')
            
            # Apply filters
            status_filter = request.GET.get('status')
            if status_filter:
                conversations = conversations.filter(status=status_filter)
            
            # Pagination
            page = request.GET.get('page', 1)
            paginator = Paginator(conversations, 20)
            page_obj = paginator.get_page(page)
            
            serializer = ChatbotConversationSerializer(page_obj, many=True)
            
            return Response({
                'success': True,
                'conversations': serializer.data,
                'pagination': {
                    'current_page': page_obj.number,
                    'total_pages': paginator.num_pages,
                    'total_conversations': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                }
            }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Conversation history retrieval failed: {e}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve conversation history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_feedback(request):
    """
    Submit feedback for chatbot responses.
    """
    try:
        data = request.data
        message_id = data.get('message_id')
        rating = data.get('rating')
        feedback_type = data.get('feedback_type', 'overall')
        comment = data.get('comment', '')
        
        if not message_id or not rating:
            return Response({
                'success': False,
                'error': 'Message ID and rating are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            message = ChatbotMessage.objects.get(
                id=message_id,
                conversation__user=request.user
            )
        except ChatbotMessage.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Message not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create or update feedback
        feedback, created = ChatbotFeedback.objects.update_or_create(
            message=message,
            user=request.user,
            feedback_type=feedback_type,
            defaults={
                'rating': rating,
                'comment': comment,
                'suggested_improvement': data.get('suggested_improvement', ''),
                'missing_information': data.get('missing_information', '')
            }
        )
        
        # Update message feedback fields
        if feedback_type == 'overall':
            message.is_helpful = rating >= 4
            message.feedback_comment = comment
            message.save()
        
        return Response({
            'success': True,
            'feedback_id': feedback.id,
            'created': created,
            'message': 'Feedback submitted successfully'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        return Response({
            'success': False,
            'error': 'Failed to submit feedback'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_documents(request):
    """
    Search documents for chatbot context.
    """
    try:
        query = request.GET.get('q', '').strip()
        category = request.GET.get('category')
        max_results = min(int(request.GET.get('max_results', 10)), 50)
        
        if not query:
            return Response({
                'success': False,
                'error': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize SLM service
        slm_service = ChatbotSLMService()
        
        # Search documents
        relevant_docs = slm_service.retrieve_relevant_documents(
            query=query,
            user=request.user,
            max_results=max_results
        )
        
        # Format results
        results = []
        for doc_data in relevant_docs:
            doc = doc_data['document']
            results.append({
                'id': doc.id,
                'title': doc.title,
                'description': doc.description,
                'category': doc.category.name,
                'document_type': doc.get_document_type_display(),
                'similarity_score': doc_data.get('similarity_score', 0.0),
                'snippet': doc_data.get('snippet', ''),
                'method': doc_data.get('method', 'unknown'),
                'url': f'/knowledge/documents/{doc.id}/',
                'created_at': doc.created_at.isoformat(),
                'updated_at': doc.updated_at.isoformat()
            })
        
        return Response({
            'success': True,
            'query': query,
            'results_count': len(results),
            'documents': results
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        return Response({
            'success': False,
            'error': 'Document search failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def close_conversation(request, conversation_id):
    """
    Close a chatbot conversation.
    """
    try:
        conversation = ChatbotConversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )
        
        conversation.status = 'closed'
        conversation.save()
        
        return Response({
            'success': True,
            'message': 'Conversation closed successfully'
        }, status=status.HTTP_200_OK)
    
    except ChatbotConversation.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Conversation not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Failed to close conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to close conversation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_stats(request):
    """
    Get chatbot usage statistics for the user.
    """
    try:
        user_conversations = ChatbotConversation.objects.filter(user=request.user)
        user_messages = ChatbotMessage.objects.filter(conversation__user=request.user)
        
        # Calculate statistics
        stats = {
            'total_conversations': user_conversations.count(),
            'active_conversations': user_conversations.filter(status='active').count(),
            'total_messages': user_messages.count(),
            'user_messages': user_messages.filter(sender='user').count(),
            'ai_responses': user_messages.filter(sender='assistant').count(),
            'average_response_time': user_messages.filter(
                sender='assistant',
                processing_time__isnull=False
            ).aggregate(avg_time=models.Avg('processing_time'))['avg_time'] or 0,
            'helpful_responses': user_messages.filter(
                sender='assistant',
                is_helpful=True
            ).count(),
            'feedback_count': ChatbotFeedback.objects.filter(
                message__conversation__user=request.user
            ).count(),
            'average_response_time': user_messages.filter(
                sender='assistant',
                processing_time__isnull=False
            ).aggregate(avg_time=models.Avg('processing_time'))['avg_time'] or 0
        }
        
        # Recent activity
        recent_conversations = user_conversations.order_by('-last_activity')[:5]
        recent_activity = []
        for conv in recent_conversations:
            recent_activity.append({
                'conversation_id': str(conv.conversation_id),
                'title': conv.get_title(),
                'last_activity': conv.last_activity.isoformat(),
                'message_count': conv.message_count,
                'status': conv.status
            })
        
        return Response({
            'success': True,
            'stats': stats,
            'recent_activity': recent_activity
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to get chatbot stats: {e}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve statistics'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# WebSocket support for real-time chat (optional)
class ChatbotWebSocketView(View):
    """
    WebSocket view for real-time chatbot communication.
    This would require additional WebSocket setup.
    """
    pass