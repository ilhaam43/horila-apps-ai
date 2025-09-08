#!/usr/bin/env python3
"""
AI Model Deployment API Views
Provides REST API endpoints for model deployment management
"""

import json
import logging
from typing import Dict, Any

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_services.models import AIModelRegistry, ModelTrainingSession
from ai_services.deployment import deployment_manager
from ai_services.permissions import IsAIServiceUser

logger = logging.getLogger(__name__)


class ModelDeploymentAPIView(APIView):
    """
    API view for model deployment operations
    """
    permission_classes = [IsAuthenticated, IsAIServiceUser]
    
    def post(self, request):
        """
        Deploy a trained model
        
        Expected payload:
        {
            "training_session_id": "uuid",
            "deployment_name": "optional_custom_name"
        }
        """
        try:
            data = request.data
            training_session_id = data.get('training_session_id')
            deployment_name = data.get('deployment_name')
            
            if not training_session_id:
                return Response(
                    {'error': 'training_session_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Deploy the model
            result = deployment_manager.deploy_model(
                training_session_id=training_session_id,
                deployment_name=deployment_name
            )
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Model deployment API error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request):
        """
        List all deployed models
        """
        try:
            deployments = deployment_manager.list_deployments()
            return Response({
                'deployments': deployments,
                'total_count': len(deployments)
            })
            
        except Exception as e:
            logger.error(f"List deployments API error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request):
        """
        Undeploy a model
        
        Expected payload:
        {
            "deployment_name": "deployment_name_to_remove"
        }
        """
        try:
            data = request.data
            deployment_name = data.get('deployment_name')
            
            if not deployment_name:
                return Response(
                    {'error': 'deployment_name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = deployment_manager.undeploy_model(deployment_name)
            
            if result['success']:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Model undeployment API error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeploymentHealthCheckAPIView(APIView):
    """
    API view for checking deployment health
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, deployment_name):
        """
        Check health of a specific deployment
        """
        try:
            import subprocess
            from pathlib import Path
            
            deployment_path = deployment_manager.deployment_dir / deployment_name
            health_script = deployment_path / 'health_check.py'
            
            if not health_script.exists():
                return Response(
                    {'error': f'Deployment {deployment_name} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Run health check script
            try:
                result = subprocess.run(
                    ['python3', str(health_script)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    health_data = json.loads(result.stdout)
                    return Response(health_data)
                else:
                    return Response({
                        'status': 'unhealthy',
                        'error': result.stderr or 'Health check failed',
                        'exit_code': result.returncode
                    })
                    
            except subprocess.TimeoutExpired:
                return Response({
                    'status': 'unhealthy',
                    'error': 'Health check timeout'
                })
            except json.JSONDecodeError:
                return Response({
                    'status': 'unhealthy',
                    'error': 'Invalid health check response'
                })
                
        except Exception as e:
            logger.error(f"Health check API error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelPredictionAPIView(APIView):
    """
    Generic API view for making predictions with deployed models
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, deployment_name):
        """
        Make prediction using a deployed model
        
        Expected payload:
        {
            "input_data": {...}  # Model-specific input data
        }
        """
        try:
            import sys
            from pathlib import Path
            
            deployment_path = deployment_manager.deployment_dir / deployment_name
            serve_script = deployment_path / 'serve_model.py'
            
            if not serve_script.exists():
                return Response(
                    {'error': f'Deployment {deployment_name} not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Load deployment config
            config_path = deployment_path / 'deployment_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Import serving class dynamically
            sys.path.insert(0, str(deployment_path))
            
            try:
                import serve_model
                
                # Get serving class name
                model_name = config['model_info']['name'].replace('-', '_').title()
                serving_class_name = f"{model_name}Serving"
                
                # Get serving class
                serving_class = getattr(serve_model, serving_class_name, None)
                if not serving_class:
                    return Response(
                        {'error': f'Serving class {serving_class_name} not found'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                # Initialize serving
                serving = serving_class()
                
                if not serving.is_loaded:
                    return Response(
                        {'error': 'Model not loaded'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                
                # Get input data
                input_data = request.data.get('input_data', {})
                
                if not input_data:
                    return Response(
                        {'error': 'input_data is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Make prediction
                prediction = serving.predict(input_data)
                
                return Response({
                    'prediction': prediction,
                    'deployment_name': deployment_name,
                    'model_info': config['model_info']
                })
                
            finally:
                # Clean up sys.path
                if str(deployment_path) in sys.path:
                    sys.path.remove(str(deployment_path))
                
        except Exception as e:
            logger.error(f"Prediction API error: {e}")
            return Response(
                {'error': f'Prediction failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeploymentMetricsAPIView(APIView):
    """
    API view for deployment metrics and monitoring
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, deployment_name=None):
        """
        Get deployment metrics
        """
        try:
            if deployment_name:
                # Get metrics for specific deployment
                metrics = self._get_deployment_metrics(deployment_name)
                if metrics:
                    return Response(metrics)
                else:
                    return Response(
                        {'error': f'Deployment {deployment_name} not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Get metrics for all deployments
                deployments = deployment_manager.list_deployments()
                all_metrics = []
                
                for deployment in deployments:
                    metrics = self._get_deployment_metrics(deployment['name'])
                    if metrics:
                        all_metrics.append(metrics)
                
                return Response({
                    'deployments_metrics': all_metrics,
                    'total_deployments': len(all_metrics)
                })
                
        except Exception as e:
            logger.error(f"Metrics API error: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_deployment_metrics(self, deployment_name: str) -> Dict[str, Any]:
        """
        Get metrics for a specific deployment
        """
        try:
            deployment_path = deployment_manager.deployment_dir / deployment_name
            config_path = deployment_path / 'deployment_config.json'
            
            if not config_path.exists():
                return None
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Get basic metrics
            metrics = {
                'deployment_name': deployment_name,
                'model_info': config['model_info'],
                'deployed_at': config['created_at'],
                'model_size_mb': sum(f['size_mb'] for f in config['model_files']['files_copied']),
                'serving_config': config['serving_config']
            }
            
            # Add health status
            health_script = deployment_path / 'health_check.py'
            if health_script.exists():
                import subprocess
                try:
                    result = subprocess.run(
                        ['python3', str(health_script)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        health_data = json.loads(result.stdout)
                        metrics['health'] = health_data
                    else:
                        metrics['health'] = {
                            'status': 'unhealthy',
                            'error': result.stderr
                        }
                except:
                    metrics['health'] = {
                        'status': 'unknown',
                        'error': 'Health check failed'
                    }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting metrics for {deployment_name}: {e}")
            return None


# Function-based views for simpler endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deployment_status(request):
    """
    Get overall deployment system status
    """
    try:
        deployments = deployment_manager.list_deployments()
        healthy_count = sum(1 for d in deployments if d['is_healthy'])
        
        return Response({
            'system_status': 'operational',
            'total_deployments': len(deployments),
            'healthy_deployments': healthy_count,
            'unhealthy_deployments': len(deployments) - healthy_count,
            'deployment_directory': str(deployment_manager.deployment_dir)
        })
        
    except Exception as e:
        logger.error(f"Deployment status error: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_models_for_deployment(request):
    """
    Get list of trained models available for deployment
    """
    try:
        # Get completed training sessions
        completed_sessions = ModelTrainingSession.objects.filter(
            status='completed'
        ).select_related('model').order_by('-completed_at')
        
        available_models = []
        for session in completed_sessions:
            # Check if already deployed
            model_config = session.model.get_config()
            is_deployed = model_config.get('deployment', {}).get('is_deployed', False)
            
            available_models.append({
                'training_session_id': str(session.id),
                'model_id': str(session.model.id),
                'model_name': session.model.name,
                'service_type': session.model.service_type,
                'version': session.model.version,
                'accuracy': session.accuracy,
                'training_completed_at': session.completed_at.isoformat() if session.completed_at else None,
                'is_deployed': is_deployed,
                'deployment_info': model_config.get('deployment', {}) if is_deployed else None
            })
        
        return Response({
            'available_models': available_models,
            'total_count': len(available_models)
        })
        
    except Exception as e:
        logger.error(f"Available models API error: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAIServiceUser])
def batch_deploy_models(request):
    """
    Deploy multiple models in batch
    
    Expected payload:
    {
        "deployments": [
            {
                "training_session_id": "uuid",
                "deployment_name": "optional_name"
            },
            ...
        ]
    }
    """
    try:
        data = request.data
        deployments_data = data.get('deployments', [])
        
        if not deployments_data:
            return Response(
                {'error': 'deployments list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        for deployment_data in deployments_data:
            training_session_id = deployment_data.get('training_session_id')
            deployment_name = deployment_data.get('deployment_name')
            
            if not training_session_id:
                results.append({
                    'training_session_id': training_session_id,
                    'success': False,
                    'error': 'training_session_id is required'
                })
                continue
            
            # Deploy the model
            result = deployment_manager.deploy_model(
                training_session_id=training_session_id,
                deployment_name=deployment_name
            )
            
            results.append({
                'training_session_id': training_session_id,
                'success': result['success'],
                'deployment_name': result.get('deployment_name'),
                'error': result.get('error')
            })
        
        successful_deployments = sum(1 for r in results if r['success'])
        
        return Response({
            'batch_results': results,
            'total_requested': len(deployments_data),
            'successful_deployments': successful_deployments,
            'failed_deployments': len(deployments_data) - successful_deployments
        })
        
    except Exception as e:
        logger.error(f"Batch deployment API error: {e}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )