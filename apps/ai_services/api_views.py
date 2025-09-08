from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

from .budget_ai import BudgetAIService
from .knowledge_ai import KnowledgeAIService
from .indonesian_nlp import IndonesianNLPService
from .rag_n8n_integration import RAGN8NIntegrationService
from .document_classifier import DocumentClassifierService
from .intelligent_search import IntelligentSearchService
from .exceptions import AIServiceError, ValidationError, PredictionError
from .performance import (
    get_system_health,
    optimize_all_services,
    performance_optimizer,
    batch_processor
)
from .monitoring import ai_monitor, PerformanceAnalyzer
from .cache import AICache
from .models import AIServiceLog, AIAnalytics
from .preprocessing import DataPreprocessor, create_preprocessing_pipeline

logger = logging.getLogger(__name__)

# Initialize AI services
budget_ai_service = None
knowledge_ai_service = None
indonesian_nlp_service = None
rag_n8n_service = None
document_classifier_service = None
intelligent_search_service = None

def get_or_initialize_service(service_type: str):
    """
    Get atau initialize AI service berdasarkan type.
    """
    global budget_ai_service, knowledge_ai_service, indonesian_nlp_service
    global rag_n8n_service, document_classifier_service, intelligent_search_service
    
    try:
        if service_type == 'budget_ai':
            if budget_ai_service is None:
                budget_ai_service = BudgetAIService()
                budget_ai_service.load_model()
            return budget_ai_service
        
        elif service_type == 'knowledge_ai':
            if knowledge_ai_service is None:
                knowledge_ai_service = KnowledgeAIService()
                knowledge_ai_service.load_model()
            return knowledge_ai_service
        
        elif service_type == 'indonesian_nlp':
            if indonesian_nlp_service is None:
                indonesian_nlp_service = IndonesianNLPService()
                indonesian_nlp_service.load_model()
            return indonesian_nlp_service
        
        elif service_type == 'rag_n8n':
            if rag_n8n_service is None:
                rag_n8n_service = RAGN8NIntegrationService()
                rag_n8n_service.load_model()
            return rag_n8n_service
        
        elif service_type == 'document_classifier':
            if document_classifier_service is None:
                document_classifier_service = DocumentClassifierService()
                document_classifier_service.load_model()
            return document_classifier_service
        
        elif service_type == 'intelligent_search':
            if intelligent_search_service is None:
                intelligent_search_service = IntelligentSearchService()
                intelligent_search_service.load_model()
            return intelligent_search_service
        
        else:
            raise ValueError(f"Unknown service type: {service_type}")
    
    except Exception as e:
        logger.error(f"Failed to initialize {service_type} service: {str(e)}")
        raise AIServiceError(f"Service initialization failed: {str(e)}")

def handle_ai_request(service_type: str, input_data: Dict[str, Any], use_preprocessing: bool = True) -> Dict[str, Any]:
    """
    Handle AI request dengan error handling, logging, dan preprocessing.
    """
    try:
        service = get_or_initialize_service(service_type)
        
        # Validate input
        if not service.validate_input(input_data):
            raise ValidationError("Invalid input data", service_type, input_data)
        
        # Apply preprocessing if enabled
        processed_data = input_data
        preprocessing_info = None
        
        if use_preprocessing and 'data' in input_data:
            try:
                # Create preprocessing pipeline based on service type
                preprocessor = create_preprocessing_pipeline(service_type)
                
                # Apply preprocessing
                if isinstance(input_data['data'], (list, dict)):
                    processed_data = input_data.copy()
                    processed_data['data'] = preprocessor.transform(input_data['data'])
                    
                    preprocessing_info = {
                        'applied': True,
                        'pipeline_type': service_type,
                        'original_shape': str(type(input_data['data'])),
                        'processed_shape': str(type(processed_data['data']))
                    }
                    
                    logger.info(f"Preprocessing applied for {service_type}: {preprocessing_info}")
                    
            except Exception as preprocessing_error:
                logger.warning(f"Preprocessing failed for {service_type}: {str(preprocessing_error)}")
                preprocessing_info = {
                    'applied': False,
                    'error': str(preprocessing_error)
                }
        
        # Make prediction with processed data
        result = service.safe_predict(processed_data, use_cache=True)
        
        response = {
            'success': True,
            'service': service_type,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add preprocessing info if available
        if preprocessing_info:
            response['preprocessing'] = preprocessing_info
            
        return response
    
    except Exception as e:
        logger.error(f"AI request failed for {service_type}: {str(e)}")
        return {
            'success': False,
            'service': service_type,
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.now().isoformat()
        }

# Budget AI Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def budget_prediction(request):
    """
    Endpoint untuk Budget AI prediction.
    """
    try:
        input_data = request.data
        result = handle_ai_request('budget_ai', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def budget_anomaly_detection(request):
    """
    Endpoint untuk Budget anomaly detection.
    """
    try:
        service = get_or_initialize_service('budget_ai')
        input_data = request.data
        
        # Specific method untuk anomaly detection
        result = service.detect_anomalies(input_data)
        
        return Response({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_analytics(request):
    """
    Endpoint untuk Budget analytics dashboard.
    """
    try:
        service = get_or_initialize_service('budget_ai')
        
        # Get analytics data
        analytics = service.get_budget_analytics()
        
        return Response({
            'success': True,
            'analytics': analytics,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Knowledge AI Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def knowledge_query(request):
    """
    Endpoint untuk Knowledge AI query.
    """
    try:
        input_data = request.data
        result = handle_ai_request('knowledge_ai', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def knowledge_add_document(request):
    """
    Endpoint untuk menambahkan dokumen ke knowledge base.
    """
    try:
        service = get_or_initialize_service('knowledge_ai')
        
        document_data = {
            'content': request.data.get('content', ''),
            'title': request.data.get('title', ''),
            'metadata': request.data.get('metadata', {})
        }
        
        result = service.add_document(document_data)
        
        return Response({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Indonesian NLP Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def indonesian_nlp_analyze(request):
    """
    Endpoint untuk Indonesian NLP analysis.
    """
    try:
        input_data = request.data
        result = handle_ai_request('indonesian_nlp', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sentiment_analysis(request):
    """
    Endpoint khusus untuk sentiment analysis.
    """
    try:
        service = get_or_initialize_service('indonesian_nlp')
        text = request.data.get('text', '')
        
        if not text:
            return Response({
                'success': False,
                'error': 'Text is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = service.analyze_sentiment(text)
        
        return Response({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# RAG + N8N Integration Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_n8n_process(request):
    """
    Endpoint untuk RAG + N8N workflow processing.
    """
    try:
        input_data = request.data
        result = handle_ai_request('rag_n8n', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_recruitment_workflow(request):
    """
    Endpoint untuk trigger recruitment workflow.
    """
    try:
        service = get_or_initialize_service('rag_n8n')
        
        input_data = {
            'action': 'trigger_workflow',
            'workflow_name': request.data.get('workflow_name', 'candidate_screening'),
            'data': {
                'candidate_data': request.data.get('candidate_data', {}),
                'job_requirements': request.data.get('job_requirements', {})
            }
        }
        
        result = service.predict(input_data)
        
        return Response({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Document Classification Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classify_document(request):
    """
    Endpoint untuk document classification.
    """
    try:
        input_data = request.data
        result = handle_ai_request('document_classifier', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def classify_document_file(request):
    """
    Endpoint untuk document classification dari uploaded file.
    """
    try:
        if 'file' not in request.FILES:
            return Response({
                'success': False,
                'error': 'No file uploaded'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Save file temporarily
        file_path = default_storage.save(
            f'temp_documents/{uploaded_file.name}',
            ContentFile(uploaded_file.read())
        )
        
        try:
            # Prepare input data
            input_data = {
                'document': {
                    'file_path': default_storage.path(file_path),
                    'name': uploaded_file.name
                },
                'methods': request.data.get('methods', ['all'])
            }
            
            result = handle_ai_request('document_classifier', input_data)
            
            return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
        
        finally:
            # Clean up temporary file
            try:
                default_storage.delete(file_path)
            except:
                pass
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_classify_documents(request):
    """
    Endpoint untuk batch document classification.
    """
    try:
        service = get_or_initialize_service('document_classifier')
        documents = request.data.get('documents', [])
        
        if not documents:
            return Response({
                'success': False,
                'error': 'No documents provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = service.batch_classify_documents(documents)
        
        return Response({
            'success': True,
            'result': result,
            'total_processed': len(result),
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_categories(request):
    """
    Endpoint untuk mendapatkan available document categories.
    """
    try:
        service = get_or_initialize_service('document_classifier')
        categories = service.get_document_categories()
        
        return Response({
            'success': True,
            'categories': categories,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Intelligent Search Endpoints
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def intelligent_search(request):
    """
    Endpoint untuk intelligent search.
    """
    try:
        input_data = request.data
        result = handle_ai_request('intelligent_search', input_data)
        
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rebuild_search_index(request):
    """
    Endpoint untuk rebuild search index.
    """
    try:
        service = get_or_initialize_service('intelligent_search')
        result = service.rebuild_search_index()
        
        return Response({
            'success': True,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_statistics(request):
    """
    Endpoint untuk search statistics.
    """
    try:
        service = get_or_initialize_service('intelligent_search')
        stats = service.get_search_statistics()
        
        return Response({
            'success': True,
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# General AI Service Endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_service_status(request):
    """
    Endpoint untuk mendapatkan status semua AI services.
    """
    try:
        services_status = {}
        service_types = ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 'rag_n8n', 'document_classifier', 'intelligent_search']
        
        for service_type in service_types:
            try:
                service = get_or_initialize_service(service_type)
                services_status[service_type] = {
                    'status': 'active',
                    'loaded': service.is_loaded,
                    'model_info': service.get_model_info()
                }
            except Exception as e:
                services_status[service_type] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return Response({
            'success': True,
            'services': services_status,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_ai_request(request):
    """
    Endpoint untuk batch AI requests.
    """
    try:
        requests_data = request.data.get('requests', [])
        
        if not requests_data:
            return Response({
                'success': False,
                'error': 'No requests provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        
        # Process requests in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for req_data in requests_data:
                service_type = req_data.get('service_type')
                input_data = req_data.get('input_data', {})
                
                if service_type:
                    future = executor.submit(handle_ai_request, service_type, input_data)
                    futures.append((req_data.get('request_id', len(futures)), future))
            
            # Collect results
            for request_id, future in futures:
                try:
                    result = future.result(timeout=30)  # 30 second timeout
                    result['request_id'] = request_id
                    results.append(result)
                except Exception as e:
                    results.append({
                        'request_id': request_id,
                        'success': False,
                        'error': str(e)
                    })
        
        return Response({
            'success': True,
            'results': results,
            'total_processed': len(results),
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Health Check Endpoint
@api_view(['GET'])
def ai_health_check(request):
    """
    Health check endpoint untuk AI services.
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        service_types = ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 'rag_n8n', 'document_classifier', 'intelligent_search']
        
        for service_type in service_types:
            try:
                # Try to initialize service
                service = get_or_initialize_service(service_type)
                health_status['services'][service_type] = {
                    'status': 'healthy',
                    'loaded': service.is_loaded
                }
            except Exception as e:
                health_status['services'][service_type] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
        
        return Response(health_status, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([])
def public_system_health(request):
    """
    Public system health endpoint for monitoring (no auth required)
    """
    try:
        health_data = get_system_health()
        return Response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'system_health': health_data,
            'services': {
                'budget_ai': 'active' if budget_ai_service else 'inactive',
                'knowledge_ai': 'active' if knowledge_ai_service else 'inactive',
                'indonesian_nlp': 'active' if indonesian_nlp_service else 'inactive',
                'document_classifier': 'active' if document_classifier_service else 'inactive',
                'intelligent_search': 'active' if intelligent_search_service else 'inactive',
                'rag_n8n': 'active' if rag_n8n_service else 'inactive'
            }
        })
    except Exception as e:
        logger.error(f"Public health check failed: {str(e)}")
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)

@api_view(['GET'])
@permission_classes([])
def public_performance_stats(request):
    """
    Public performance stats endpoint (no auth required)
    """
    try:
        from .metrics import metrics_collector
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': metrics_collector.get_system_metrics(),
            'ai_service_metrics': metrics_collector.get_ai_metrics(),
            'cache_stats': {},  # Simplified for now
            'performance_summary': {
                'total_requests': metrics_collector.get_counter('ai_requests_total'),
                'avg_response_time': metrics_collector.get_histogram_avg('ai_response_time'),
                'error_rate': metrics_collector.get_counter('ai_errors_total') / max(metrics_collector.get_counter('ai_requests_total'), 1)
            }
        }
        
        return Response({
            'status': 'success',
            'data': stats
        })
    except Exception as e:
        logger.error(f"Performance stats failed: {str(e)}")
        return Response({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)

# Async endpoint untuk long-running tasks
@method_decorator(csrf_exempt, name='dispatch')
class AsyncAIProcessingView(View):
    """
    View untuk async AI processing tasks.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            task_type = data.get('task_type')
            task_data = data.get('task_data', {})
            
            if task_type == 'rebuild_all_indices':
                # Trigger async index rebuild
                return self._trigger_async_index_rebuild()
            
            elif task_type == 'batch_document_processing':
                # Trigger async batch processing
                return self._trigger_async_batch_processing(task_data)
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }, status=400)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

# Preprocessing Endpoints
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preprocess_data(request):
    """
    Endpoint untuk preprocessing data secara terpisah.
    
    Expected payload:
    {
        "service_type": "budget_ai",
        "data": {...}  # Data yang akan dipreprocess
    }
    """
    try:
        service_type = request.data.get('service_type')
        data = request.data.get('data')
        
        if not service_type or data is None:
            return Response({
                'success': False,
                'error': 'service_type and data are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create preprocessing pipeline
        preprocessor = create_preprocessing_pipeline(service_type)
        
        # Apply preprocessing
        processed_data = preprocessor.transform(data)
        
        return Response({
            'success': True,
            'service_type': service_type,
            'original_data': data,
            'processed_data': processed_data,
            'preprocessing_info': {
                'pipeline_type': service_type,
                'original_shape': str(type(data)),
                'processed_shape': str(type(processed_data)),
                'timestamp': datetime.now().isoformat()
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_preprocess_data(request):
    """
    Endpoint untuk batch preprocessing data.
    
    Expected payload:
    {
        "requests": [
            {
                "service_type": "budget_ai",
                "data": {...},
                "request_id": "optional_id"
            },
            ...
        ]
    }
    """
    try:
        requests_data = request.data.get('requests', [])
        
        if not requests_data:
            return Response({
                'success': False,
                'error': 'No requests provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        
        for i, req_data in enumerate(requests_data):
            try:
                service_type = req_data.get('service_type')
                data = req_data.get('data')
                request_id = req_data.get('request_id', f'req_{i}')
                
                if not service_type or data is None:
                    results.append({
                        'request_id': request_id,
                        'success': False,
                        'error': 'service_type and data are required'
                    })
                    continue
                
                # Create preprocessing pipeline
                preprocessor = create_preprocessing_pipeline(service_type)
                
                # Apply preprocessing
                processed_data = preprocessor.transform(data)
                
                results.append({
                    'request_id': request_id,
                    'success': True,
                    'service_type': service_type,
                    'processed_data': processed_data,
                    'preprocessing_info': {
                        'pipeline_type': service_type,
                        'original_shape': str(type(data)),
                        'processed_shape': str(type(processed_data))
                    }
                })
                
            except Exception as e:
                results.append({
                    'request_id': req_data.get('request_id', f'req_{i}'),
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        return Response({
            'success': True,
            'total_requests': len(requests_data),
            'successful_requests': len([r for r in results if r['success']]),
            'failed_requests': len([r for r in results if not r['success']]),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Batch preprocessing failed: {str(e)}")
        return Response({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Performance and Monitoring Endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health(request):
    """
    Get current system health metrics
    """
    try:
        health_data = get_system_health()
        return Response({
            'status': 'success',
            'data': health_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"System health API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_performance(request):
    """
    Trigger performance optimization
    """
    try:
        result = optimize_all_services()
        
        # Log the optimization request
        AIServiceLog.objects.create(
            service_name='performance_api',
            operation='optimize_performance',
            status='success' if result['status'] == 'success' else 'error',
            details=result,
            created_by=request.user
        )
        
        return Response({
            'status': result['status'],
            'message': result['message'],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Performance optimization API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_stats(request):
    """
    Get performance statistics for AI services
    """
    try:
        service_name = request.GET.get('service')
        
        if service_name:
            # Get stats for specific service
            stats = performance_optimizer.get_performance_stats(service_name)
            return Response({
                'status': 'success',
                'service': service_name,
                'data': stats,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Get stats for all services
            services = ['budget_ai', 'knowledge_ai', 'indonesian_nlp', 
                       'document_classifier', 'intelligent_search', 'rag_n8n']
            
            all_stats = {}
            for service in services:
                all_stats[service] = performance_optimizer.get_performance_stats(service)
            
            return Response({
                'status': 'success',
                'data': all_stats,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Performance stats API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monitoring_status(request):
    """
    Get monitoring system status and recent alerts
    """
    try:
        from django.core.cache import cache
        summary = ai_monitor.get_service_summary()
        recent_alerts = cache.get('ai_recent_alerts', [])
        
        return Response({
            'status': 'success',
            'monitoring_active': ai_monitor.monitoring_active,
            'summary': summary,
            'recent_alerts': recent_alerts[-10:],  # Last 10 alerts
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Monitoring status API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_monitoring(request):
    """
    Start real-time monitoring
    """
    try:
        interval = request.data.get('interval', 60)  # Default 60 seconds
        
        if ai_monitor.monitoring_active:
            return Response({
                'status': 'info',
                'message': 'Monitoring is already active'
            })
        
        ai_monitor.start_monitoring(interval=interval)
        
        return Response({
            'status': 'success',
            'message': f'Monitoring started with {interval}s interval',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Start monitoring API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_monitoring(request):
    """
    Stop real-time monitoring
    """
    try:
        if not ai_monitor.monitoring_active:
            return Response({
                'status': 'info',
                'message': 'Monitoring is not active'
            })
        
        ai_monitor.stop_monitoring()
        
        return Response({
            'status': 'success',
            'message': 'Monitoring stopped',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Stop monitoring API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bottleneck_analysis(request):
    """
    Get bottleneck analysis for all AI services
    """
    try:
        analysis = PerformanceAnalyzer.get_bottleneck_analysis()
        return Response({
            'status': 'success',
            'data': analysis,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Bottleneck analysis API error: {e}")
        return Response({
            'status': 'error',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Model Deployment API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deploy_model(request):
    """
    Deploy a trained model for inference
    """
    try:
        from .deployment import deployment_manager
        
        training_session_id = request.data.get('training_session_id')
        deployment_name = request.data.get('deployment_name')
        
        if not training_session_id:
            return Response({
                'error': 'training_session_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = deployment_manager.deploy_model(training_session_id, deployment_name)
        
        if result['success']:
            return Response({
                'success': True,
                'deployment_name': result['deployment_name'],
                'deployment_path': result['deployment_path'],
                'message': 'Model deployed successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Deployment failed')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Model deployment error: {str(e)}")
        return Response({
            'error': 'Failed to deploy model',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_deployments(request):
    """
    List all active deployments
    """
    try:
        from .deployment import deployment_manager
        
        deployments = deployment_manager.list_deployments()
        
        return Response({
            'success': True,
            'deployments': deployments,
            'total_count': len(deployments)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"List deployments error: {str(e)}")
        return Response({
            'error': 'Failed to list deployments',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deployment_status(request, deployment_id):
    """
    Get status of a specific deployment
    """
    try:
        from .deployment import deployment_manager
        
        status_info = deployment_manager.get_deployment_status(deployment_id)
        
        if status_info:
            return Response({
                'success': True,
                'status': status_info
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Deployment not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Deployment status error: {str(e)}")
        return Response({
            'error': 'Failed to get deployment status',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def undeploy_model(request, deployment_id):
    """
    Undeploy a model
    """
    try:
        from .deployment import deployment_manager
        
        result = deployment_manager.undeploy_model(deployment_id)
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Model undeployed successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'Undeployment failed')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Model undeployment error: {str(e)}")
        return Response({
             'error': 'Failed to undeploy model',
             'details': str(e)
         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deployment_system_status(request):
    """
    Get overall deployment system status
    """
    try:
        from .deployment import deployment_manager
        from .models import AIModelRegistry, ModelTrainingSession
        
        deployments = deployment_manager.list_deployments()
        total_deployments = len(deployments)
        healthy_deployments = len([d for d in deployments if d.get('status') == 'active'])
        
        return Response({
            'system_status': 'healthy' if healthy_deployments == total_deployments else 'degraded',
            'total_deployments': total_deployments,
            'healthy_deployments': healthy_deployments,
            'timestamp': datetime.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Deployment system status error: {str(e)}")
        return Response({
            'error': 'Failed to get system status',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_models(request):
    """
    Get list of available models for deployment
    """
    try:
        from .models import AIModelRegistry, ModelTrainingSession
        
        models = AIModelRegistry.objects.filter(is_active=True)
        available_models = []
        
        for model in models:
            # Get latest training session for this model
            latest_session = ModelTrainingSession.objects.filter(
                model=model,
                status='completed'
            ).order_by('-created_at').first()
            
            model_info = {
                'model_id': model.id,
                'model_name': model.name,
                'service_type': model.service_type,
                'model_type': model.model_type,
                'version': model.version,
                'accuracy': latest_session.accuracy if latest_session else None,
                'training_date': latest_session.created_at.isoformat() if latest_session else None
            }
            available_models.append(model_info)
        
        return Response({
            'available_models': available_models,
            'total_count': len(available_models)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Available models error: {str(e)}")
        return Response({
            'error': 'Failed to get available models',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _trigger_async_index_rebuild(self):
        """
        Trigger async index rebuild untuk search service.
        """
        try:
            # This would typically use Celery or similar task queue
            # For now, we'll simulate async processing
            
            task_id = f"rebuild_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # In production, this would be:
            # from .tasks import rebuild_search_index_task
            # result = rebuild_search_index_task.delay()
            
            return JsonResponse({
                'success': True,
                'task_id': task_id,
                'status': 'started',
                'message': 'Index rebuild task started'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _trigger_async_batch_processing(self, task_data):
        """
        Trigger async batch document processing.
        """
        try:
            documents = task_data.get('documents', [])
            processing_type = task_data.get('processing_type', 'classification')
            
            task_id = f"batch_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # In production, this would be:
            # from .tasks import batch_process_documents_task
            # result = batch_process_documents_task.delay(documents, processing_type)
            
            return JsonResponse({
                'success': True,
                'task_id': task_id,
                'status': 'started',
                'total_documents': len(documents),
                'processing_type': processing_type,
                'message': 'Batch processing task started'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)