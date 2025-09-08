from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import AIModel, PredictionLog, TrainingSession
import json
import time
import random
from datetime import datetime

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'message': 'POC AI Services is running successfully',
        'version': '1.0.0-poc',
        'timestamp': datetime.now().isoformat()
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    """API status endpoint"""
    models_count = AIModel.objects.filter(is_active=True).count()
    predictions_count = PredictionLog.objects.count()
    training_sessions_count = TrainingSession.objects.count()
    
    return Response({
        'api_status': 'active',
        'statistics': {
            'active_models': models_count,
            'total_predictions': predictions_count,
            'training_sessions': training_sessions_count
        },
        'endpoints': {
            'health': '/health/',
            'api_status': '/api/status/',
            'models': '/api/models/',
            'predict': '/api/predict/',
            'train': '/api/train/',
            'admin': '/admin/'
        },
        'message': 'All AI services operational for POC'
    })

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def models_endpoint(request):
    """Models management endpoint"""
    if request.method == 'GET':
        models = AIModel.objects.filter(is_active=True)
        models_data = []
        for model in models:
            models_data.append({
                'id': model.id,
                'name': model.name,
                'description': model.description,
                'model_type': model.model_type,
                'accuracy': model.accuracy,
                'created_at': model.created_at.isoformat(),
                'is_active': model.is_active
            })
        
        return Response({
            'models': models_data,
            'count': len(models_data)
        })
    
    elif request.method == 'POST':
        try:
            data = request.data
            model = AIModel.objects.create(
                name=data.get('name', 'Demo Model'),
                description=data.get('description', 'Demo AI Model for POC'),
                model_type=data.get('model_type', 'classification'),
                accuracy=data.get('accuracy', round(random.uniform(0.8, 0.95), 3))
            )
            
            return Response({
                'message': 'Model created successfully',
                'model': {
                    'id': model.id,
                    'name': model.name,
                    'description': model.description,
                    'model_type': model.model_type,
                    'accuracy': model.accuracy
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': f'Failed to create model: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def predict_endpoint(request):
    """Prediction endpoint"""
    try:
        data = request.data
        model_id = data.get('model_id')
        input_data = data.get('input_data', {})
        
        if not model_id:
            return Response({
                'error': 'model_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ai_model = AIModel.objects.get(id=model_id, is_active=True)
        except AIModel.DoesNotExist:
            return Response({
                'error': 'Model not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Simulate prediction processing
        start_time = time.time()
        time.sleep(0.1)  # Simulate processing time
        
        # Generate mock prediction result
        if ai_model.model_type == 'classification':
            prediction_result = {
                'class': random.choice(['Class A', 'Class B', 'Class C']),
                'probabilities': {
                    'Class A': round(random.uniform(0.1, 0.9), 3),
                    'Class B': round(random.uniform(0.1, 0.9), 3),
                    'Class C': round(random.uniform(0.1, 0.9), 3)
                }
            }
        elif ai_model.model_type == 'regression':
            prediction_result = {
                'value': round(random.uniform(10, 100), 2),
                'confidence_interval': [round(random.uniform(5, 15), 2), round(random.uniform(95, 105), 2)]
            }
        elif ai_model.model_type == 'nlp':
            prediction_result = {
                'sentiment': random.choice(['positive', 'negative', 'neutral']),
                'confidence': round(random.uniform(0.7, 0.95), 3),
                'keywords': ['demo', 'poc', 'ai']
            }
        else:
            prediction_result = {
                'result': 'Demo prediction result',
                'score': round(random.uniform(0.5, 1.0), 3)
            }
        
        processing_time = time.time() - start_time
        confidence_score = round(random.uniform(0.8, 0.95), 3)
        
        # Log prediction
        prediction_log = PredictionLog.objects.create(
            model=ai_model,
            input_data=input_data,
            prediction_result=prediction_result,
            confidence_score=confidence_score,
            processing_time=processing_time,
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({
            'prediction_id': prediction_log.id,
            'model_name': ai_model.name,
            'input_data': input_data,
            'prediction_result': prediction_result,
            'confidence_score': confidence_score,
            'processing_time': processing_time,
            'timestamp': prediction_log.created_at.isoformat()
        })
    
    except Exception as e:
        return Response({
            'error': f'Prediction failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def train_endpoint(request):
    """Training endpoint"""
    try:
        data = request.data
        model_id = data.get('model_id')
        dataset_info = data.get('dataset_info', {})
        training_parameters = data.get('training_parameters', {})
        
        if not model_id:
            return Response({
                'error': 'model_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ai_model = AIModel.objects.get(id=model_id, is_active=True)
        except AIModel.DoesNotExist:
            return Response({
                'error': 'Model not found or inactive'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create training session
        training_session = TrainingSession.objects.create(
            model=ai_model,
            dataset_info=dataset_info,
            training_parameters=training_parameters,
            status='running'
        )
        
        # Simulate training (in real implementation, this would be async)
        time.sleep(0.5)  # Simulate training time
        
        # Generate mock training metrics
        metrics = {
            'accuracy': round(random.uniform(0.85, 0.95), 3),
            'precision': round(random.uniform(0.80, 0.90), 3),
            'recall': round(random.uniform(0.80, 0.90), 3),
            'f1_score': round(random.uniform(0.80, 0.90), 3),
            'loss': round(random.uniform(0.05, 0.15), 4),
            'epochs': training_parameters.get('epochs', 10),
            'training_samples': dataset_info.get('training_samples', 1000),
            'validation_samples': dataset_info.get('validation_samples', 200)
        }
        
        # Update training session
        training_session.status = 'completed'
        training_session.metrics = metrics
        training_session.completed_at = datetime.now()
        training_session.save()
        
        # Update model accuracy
        ai_model.accuracy = metrics['accuracy']
        ai_model.save()
        
        return Response({
            'training_session_id': training_session.id,
            'model_name': ai_model.name,
            'status': 'completed',
            'metrics': metrics,
            'message': 'Training completed successfully'
        })
    
    except Exception as e:
        return Response({
            'error': f'Training failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def predictions_history(request):
    """Get predictions history"""
    predictions = PredictionLog.objects.all()[:50]  # Last 50 predictions
    predictions_data = []
    
    for pred in predictions:
        predictions_data.append({
            'id': pred.id,
            'model_name': pred.model.name,
            'confidence_score': pred.confidence_score,
            'processing_time': pred.processing_time,
            'created_at': pred.created_at.isoformat()
        })
    
    return Response({
        'predictions': predictions_data,
        'count': len(predictions_data)
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def training_history(request):
    """Get training history"""
    sessions = TrainingSession.objects.all()[:20]  # Last 20 sessions
    sessions_data = []
    
    for session in sessions:
        sessions_data.append({
            'id': session.id,
            'model_name': session.model.name,
            'status': session.status,
            'metrics': session.metrics,
            'started_at': session.started_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        })
    
    return Response({
        'training_sessions': sessions_data,
        'count': len(sessions_data)
    })