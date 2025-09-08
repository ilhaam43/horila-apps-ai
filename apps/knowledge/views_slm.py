from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import logging
import time
from typing import Dict, Any

from .models import ChatbotConversation, ChatbotMessage
from ai_services.chatbot_slm_service import chatbot_slm_service
from .serializers import (
    ChatbotConversationSerializer,
    ChatbotMessageSerializer,
    ChatbotQuerySerializer
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def slm_chat_query(request):
    """
    Process chatbot query using Small Language Model (SLM) instead of Ollama.
    Alternative endpoint for chatbot functionality.
    """
    try:
        # Validate request data
        serializer = ChatbotQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Invalid request data',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        conversation_id = serializer.validated_data.get('conversation_id')
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = ChatbotConversation.objects.get(
                    conversation_id=conversation_id,
                    user=request.user
                )
            except ChatbotConversation.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Conversation not found'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            conversation = chatbot_slm_service.create_conversation(
                user=request.user,
                initial_query=query
            )
        
        # Add user message
        user_message = chatbot_slm_service.add_message(
            conversation=conversation,
            sender='user',
            content=query,
            message_type='text'
        )
        
        # Retrieve relevant documents
        start_time = time.time()
        relevant_docs = chatbot_slm_service.retrieve_relevant_documents(
            query=query,
            user=request.user,
            max_results=5
        )
        retrieval_time = time.time() - start_time
        
        # Generate AI response
        response_data = chatbot_slm_service.generate_response(
            query=query,
            relevant_docs=relevant_docs,
            conversation=conversation
        )
        
        if response_data['success']:
            # Add AI response message
            ai_message = chatbot_slm_service.add_message(
                conversation=conversation,
                sender='ai',
                content=response_data['response'],
                message_type='text',
                confidence_score=response_data.get('confidence_score', 0.0),
                processing_time=response_data.get('processing_time', 0.0),
                model_used=response_data.get('model_used', 'unknown'),
                approach=response_data.get('approach', 'unknown')
            )
            
            # Prepare referenced documents info
            referenced_docs = []
            for doc in response_data.get('referenced_documents', []):
                referenced_docs.append({
                    'id': doc.id,
                    'title': doc.title,
                    'category': doc.category.name if doc.category else None,
                    'url': f'/knowledge/documents/{doc.id}/'
                })
            
            return Response({
                'success': True,
                'conversation_id': str(conversation.conversation_id),
                'response': response_data['response'],
                'confidence_score': response_data.get('confidence_score', 0.0),
                'processing_time': response_data.get('processing_time', 0.0),
                'retrieval_time': retrieval_time,
                'model_used': response_data.get('model_used', 'unknown'),
                'approach': response_data.get('approach', 'slm'),
                'context_used': response_data.get('context_used', 0),
                'referenced_documents': referenced_docs,
                'message_id': str(ai_message.id),
                'timestamp': ai_message.created_at.isoformat()
            }, status=status.HTTP_200_OK)
        
        else:
            # Add error message
            error_message = chatbot_slm_service.add_message(
                conversation=conversation,
                sender='ai',
                content=response_data.get('response', 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.'),
                message_type='error',
                error_details=response_data.get('error', '')
            )
            
            return Response({
                'success': False,
                'conversation_id': str(conversation.conversation_id),
                'error': response_data.get('error', 'Unknown error'),
                'response': response_data.get('response', 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.'),
                'message_id': str(error_message.id),
                'timestamp': error_message.created_at.isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        logger.error(f"SLM chat query failed: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slm_conversation_list(request):
    """
    Get list of user's chatbot conversations (SLM version).
    """
    try:
        conversations = ChatbotConversation.objects.filter(
            user=request.user
        ).order_by('-last_activity')[:20]
        
        serializer = ChatbotConversationSerializer(conversations, many=True)
        
        return Response({
            'success': True,
            'conversations': serializer.data,
            'count': len(serializer.data)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to get SLM conversations: {e}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve conversations'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slm_conversation_detail(request, conversation_id):
    """
    Get detailed conversation with messages (SLM version).
    """
    try:
        conversation = get_object_or_404(
            ChatbotConversation,
            conversation_id=conversation_id,
            user=request.user
        )
        
        # Get messages
        messages = conversation.messages.order_by('created_at')
        
        conversation_data = ChatbotConversationSerializer(conversation).data
        messages_data = ChatbotMessageSerializer(messages, many=True).data
        
        return Response({
            'success': True,
            'conversation': conversation_data,
            'messages': messages_data,
            'message_count': len(messages_data)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to get SLM conversation detail: {e}")
        return Response({
            'success': False,
            'error': 'Failed to retrieve conversation details'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def slm_conversation_create(request):
    """
    Create new chatbot conversation (SLM version).
    """
    try:
        title = request.data.get('title', 'New SLM Conversation')
        
        conversation = chatbot_slm_service.create_conversation(
            user=request.user,
            initial_query=title
        )
        
        serializer = ChatbotConversationSerializer(conversation)
        
        return Response({
            'success': True,
            'conversation': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        logger.error(f"Failed to create SLM conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to create conversation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def slm_conversation_delete(request, conversation_id):
    """
    Delete chatbot conversation (SLM version).
    """
    try:
        conversation = get_object_or_404(
            ChatbotConversation,
            conversation_id=conversation_id,
            user=request.user
        )
        
        conversation.delete()
        
        return Response({
            'success': True,
            'message': 'Conversation deleted successfully'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to delete SLM conversation: {e}")
        return Response({
            'success': False,
            'error': 'Failed to delete conversation'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def slm_service_status(request):
    """
    Get SLM service status and configuration.
    """
    try:
        # Check if SLM service is available
        service_status = {
            'slm_service_available': hasattr(chatbot_slm_service, 'slm_service'),
            'embedding_model_available': chatbot_slm_service.embedding_model is not None,
            'knowledge_ai_available': chatbot_slm_service.knowledge_ai is not None,
            'configuration': {
                'max_context_length': chatbot_slm_service.max_context_length,
                'similarity_threshold': chatbot_slm_service.similarity_threshold,
                'slm_config': chatbot_slm_service.slm_config
            }
        }
        
        # Test SLM service
        if hasattr(chatbot_slm_service, 'slm_service'):
            try:
                test_result = chatbot_slm_service.slm_service.generate_text(
                    prompt="Test prompt",
                    model_key="gpt2",
                    max_length=10
                )
                service_status['slm_test_success'] = test_result.get('success', False)
            except Exception as e:
                service_status['slm_test_success'] = False
                service_status['slm_test_error'] = str(e)
        
        return Response({
            'success': True,
            'service_status': service_status,
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Failed to get SLM service status: {e}")
        return Response({
            'success': False,
            'error': 'Failed to get service status'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def slm_document_search(request):
    """
    Search documents using SLM service (for testing purposes).
    """
    try:
        query = request.data.get('query', '')
        max_results = request.data.get('max_results', 5)
        
        if not query:
            return Response({
                'success': False,
                'error': 'Query is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Search documents
        relevant_docs = chatbot_slm_service.retrieve_relevant_documents(
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
                'category': doc.category.name if doc.category else None,
                'similarity_score': doc_data.get('similarity_score', 0.0),
                'snippet': doc_data.get('snippet', ''),
                'method': doc_data.get('method', 'unknown'),
                'url': f'/knowledge/documents/{doc.id}/'
            })
        
        return Response({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"SLM document search failed: {e}")
        return Response({
            'success': False,
            'error': 'Document search failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)