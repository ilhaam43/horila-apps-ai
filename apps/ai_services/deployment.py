#!/usr/bin/env python3
"""
AI Model Deployment System
Handles deployment, versioning, and serving of trained AI models
"""

import os
import json
import shutil
import logging
import pickle
import joblib
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

import django
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

# Setup Django if not already configured
if not django.conf.settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
    django.setup()

from ai_services.models import AIModelRegistry, ModelTrainingSession
from ai_services.base import BaseAIService

logger = logging.getLogger(__name__)

class ModelDeploymentManager:
    """
    Manages deployment of trained AI models to production environment
    """
    
    def __init__(self):
        self.deployment_dir = Path(settings.BASE_DIR) / 'deployed_models'
        self.deployment_dir.mkdir(exist_ok=True)
        
        # Model serving configurations
        self.serving_configs = {
            'budget_prediction': {
                'endpoint': '/api/ai/budget/predict/',
                'max_concurrent_requests': 10,
                'timeout_seconds': 30,
                'cache_predictions': True,
                'cache_ttl': 3600  # 1 hour
            },
            'knowledge_search': {
                'endpoint': '/api/ai/knowledge/search/',
                'max_concurrent_requests': 20,
                'timeout_seconds': 15,
                'cache_predictions': True,
                'cache_ttl': 1800  # 30 minutes
            },
            'indonesian_nlp': {
                'endpoint': '/api/ai/nlp/analyze/',
                'max_concurrent_requests': 15,
                'timeout_seconds': 20,
                'cache_predictions': True,
                'cache_ttl': 2400  # 40 minutes
            }
        }
    
    def deploy_model(self, training_session_id: str, deployment_name: str = None) -> Dict[str, Any]:
        """
        Deploy a trained model to production
        
        Args:
            training_session_id: ID of the training session
            deployment_name: Optional custom deployment name
            
        Returns:
            Dict containing deployment information
        """
        try:
            # Get training session
            training_session = ModelTrainingSession.objects.get(id=training_session_id)
            
            if training_session.status != 'completed':
                raise ValueError(f"Training session {training_session_id} is not completed")
            
            # Generate deployment info
            deployment_name = deployment_name or f"{training_session.model.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            deployment_path = self.deployment_dir / deployment_name
            deployment_path.mkdir(exist_ok=True)
            
            # Copy model files
            model_info = self._copy_model_files(training_session, deployment_path)
            
            # Create deployment configuration
            deployment_config = self._create_deployment_config(
                training_session, deployment_name, deployment_path, model_info
            )
            
            # Save deployment config
            config_path = deployment_path / 'deployment_config.json'
            with open(config_path, 'w') as f:
                json.dump(deployment_config, f, indent=2, default=str)
            
            # Update model registry
            self._update_model_registry(training_session, deployment_config)
            
            # Create serving script
            self._create_serving_script(deployment_path, deployment_config)
            
            # Create health check script
            self._create_health_check_script(deployment_path, deployment_config)
            
            logger.info(f"Model deployed successfully: {deployment_name}")
            
            return {
                'success': True,
                'deployment_name': deployment_name,
                'deployment_path': str(deployment_path),
                'config': deployment_config,
                'endpoints': self._get_model_endpoints(training_session.model.service_type)
            }
            
        except Exception as e:
            logger.error(f"Model deployment failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _copy_model_files(self, training_session: ModelTrainingSession, deployment_path: Path) -> Dict[str, Any]:
        """
        Copy trained model files to deployment directory
        """
        model_info = {
            'files_copied': [],
            'model_size_mb': 0
        }
        
        # Get model artifacts from training session
        artifacts = training_session.get_config().get('artifacts', {})
        
        for artifact_type, artifact_path in artifacts.items():
            if os.path.exists(artifact_path):
                # Copy file to deployment directory
                dest_path = deployment_path / f"{artifact_type}.pkl"
                shutil.copy2(artifact_path, dest_path)
                
                # Get file size
                file_size = os.path.getsize(dest_path) / (1024 * 1024)  # MB
                model_info['model_size_mb'] += file_size
                model_info['files_copied'].append({
                    'type': artifact_type,
                    'path': str(dest_path),
                    'size_mb': round(file_size, 2)
                })
        
        return model_info
    
    def _create_deployment_config(self, training_session: ModelTrainingSession, 
                                deployment_name: str, deployment_path: Path, 
                                model_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create deployment configuration
        """
        service_type = training_session.model.service_type
        serving_config = self.serving_configs.get(service_type, {})
        
        config = {
            'deployment_name': deployment_name,
            'deployment_path': str(deployment_path),
            'created_at': timezone.now().isoformat(),
            'model_info': {
                'id': str(training_session.model.id),
                'name': training_session.model.name,
                'service_type': service_type,
                'version': training_session.model.version,
                'model_type': training_session.model.model_type,
                'framework': 'scikit-learn'  # Default framework
            },
            'training_info': {
                'session_id': str(training_session.id),
                'accuracy': training_session.accuracy,
                'training_time': training_session.training_time_minutes,
                'data_size': training_session.training_data_size,
                'completed_at': training_session.completed_at.isoformat() if training_session.completed_at else None
            },
            'serving_config': serving_config,
            'model_files': model_info,
            'environment': {
                'python_version': '3.9+',
                'django_version': '4.2+',
                'required_packages': self._get_required_packages(service_type)
            },
            'monitoring': {
                'health_check_endpoint': f'/health/{deployment_name}/',
                'metrics_endpoint': f'/metrics/{deployment_name}/',
                'log_level': 'INFO'
            }
        }
        
        return config
    
    def _get_required_packages(self, service_type: str) -> List[str]:
        """
        Get required packages for model serving
        """
        base_packages = [
            'django>=4.2.0',
            'djangorestframework>=3.14.0',
            'redis>=4.5.0',
            'celery>=5.3.0',
            'numpy>=1.24.0',
            'pandas>=2.0.0'
        ]
        
        service_packages = {
            'budget_prediction': [
                'scikit-learn>=1.3.0',
                'xgboost>=1.7.0',
                'lightgbm>=4.0.0'
            ],
            'knowledge_search': [
                'sentence-transformers>=2.2.0',
                'chromadb>=0.4.0',
                'faiss-cpu>=1.7.0'
            ],
            'indonesian_nlp': [
                'transformers>=4.30.0',
                'torch>=2.0.0',
                'Sastrawi>=1.0.1'
            ]
        }
        
        return base_packages + service_packages.get(service_type, [])
    
    def _update_model_registry(self, training_session: ModelTrainingSession, 
                             deployment_config: Dict[str, Any]):
        """
        Update model registry with deployment information
        """
        model = training_session.model
        
        # Update model config with deployment info
        model_config = model.get_config()
        model_config['deployment'] = {
            'is_deployed': True,
            'deployment_name': deployment_config['deployment_name'],
            'deployment_path': deployment_config['deployment_path'],
            'deployed_at': deployment_config['created_at'],
            'serving_config': deployment_config['serving_config']
        }
        
        model.set_config(model_config)
        model.is_active = True
        model.save()
    
    def _create_serving_script(self, deployment_path: Path, config: Dict[str, Any]):
        """
        Create model serving script
        """
        script_content = f'''#!/usr/bin/env python3
"""
Model Serving Script for {config['deployment_name']}
Generated on {config['created_at']}
"""

import os
import sys
import django
import logging
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from ai_services.models import AIModelRegistry
from ai_services.base import BaseAIService

logger = logging.getLogger(__name__)

class {config['model_info']['name'].replace('-', '_').title()}Serving(BaseAIService):
    """
    Serving class for {config['model_info']['name']} model
    """
    
    def __init__(self):
        super().__init__()
        self.deployment_path = Path(__file__).parent
        self.model = None
        self.load_model()
    
    def load_model(self):
        """Load the deployed model"""
        try:
            # Load model files based on service type
            service_type = "{config['model_info']['service_type']}"
            
            if service_type == 'budget_prediction':
                import joblib
                model_path = self.deployment_path / 'model.pkl'
                self.model = joblib.load(model_path)
            
            elif service_type == 'knowledge_search':
                import pickle
                model_path = self.deployment_path / 'vectorizer.pkl'
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
            
            elif service_type == 'indonesian_nlp':
                from transformers import AutoTokenizer, AutoModel
                model_path = self.deployment_path / 'model'
                self.model = AutoModel.from_pretrained(model_path)
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            
            logger.info(f"Model loaded successfully: {{self.model}}")
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load model: {{e}}")
            self.is_loaded = False
    
    def predict(self, input_data):
        """Make prediction using the loaded model"""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Implement prediction logic based on service type
            service_type = "{config['model_info']['service_type']}"
            
            if service_type == 'budget_prediction':
                return self._predict_budget(input_data)
            elif service_type == 'knowledge_search':
                return self._search_knowledge(input_data)
            elif service_type == 'indonesian_nlp':
                return self._analyze_text(input_data)
            else:
                raise NotImplementedError(f"Prediction not implemented for {{service_type}}")
                
        except Exception as e:
            logger.error(f"Prediction failed: {{e}}")
            raise
    
    def _predict_budget(self, input_data):
        """Budget prediction logic"""
        # Implement budget prediction
        prediction = self.model.predict([input_data])
        return {{
            'prediction': float(prediction[0]),
            'confidence': 0.85,  # Calculate actual confidence
            'model_version': "{config['model_info']['version']}"
        }}
    
    def _search_knowledge(self, input_data):
        """Knowledge search logic"""
        # Implement knowledge search
        query = input_data.get('query', '')
        # Use vectorizer to find similar documents
        results = []
        return {{
            'results': results,
            'total_found': len(results),
            'model_version': "{config['model_info']['version']}"
        }}
    
    def _analyze_text(self, input_data):
        """Indonesian NLP analysis logic"""
        # Implement text analysis
        text = input_data.get('text', '')
        # Use transformer model for analysis
        analysis = {{
            'sentiment': 'positive',
            'confidence': 0.9,
            'entities': [],
            'keywords': []
        }}
        return analysis

if __name__ == '__main__':
    # Test the serving script
    serving = {config['model_info']['name'].replace('-', '_').title()}Serving()
    print(f"Model serving ready: {{serving.is_loaded}}")
'''
        
        script_path = deployment_path / 'serve_model.py'
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
    
    def _create_health_check_script(self, deployment_path: Path, config: Dict[str, Any]):
        """
        Create health check script for the deployed model
        """
        script_content = f'''#!/usr/bin/env python3
"""
Health Check Script for {config['deployment_name']}
"""

import json
import time
import sys
from pathlib import Path

def check_model_health():
    """Check if the deployed model is healthy"""
    try:
        # Import the serving class
        sys.path.append(str(Path(__file__).parent))
        from serve_model import {config['model_info']['name'].replace('-', '_').title()}Serving
        
        # Initialize serving
        serving = {config['model_info']['name'].replace('-', '_').title()}Serving()
        
        if not serving.is_loaded:
            return {{
                'status': 'unhealthy',
                'error': 'Model not loaded',
                'timestamp': time.time()
            }}
        
        # Test prediction with dummy data
        test_data = {{
            'budget_prediction': {{'amount': 1000, 'category': 'test'}},
            'knowledge_search': {{'query': 'test query'}},
            'indonesian_nlp': {{'text': 'test text'}}
        }}
        
        service_type = "{config['model_info']['service_type']}"
        dummy_input = test_data.get(service_type, {{}})
        
        start_time = time.time()
        result = serving.predict(dummy_input)
        response_time = time.time() - start_time
        
        return {{
            'status': 'healthy',
            'model_loaded': True,
            'response_time_ms': round(response_time * 1000, 2),
            'test_prediction': result,
            'timestamp': time.time()
        }}
        
    except Exception as e:
        return {{
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }}

if __name__ == '__main__':
    health = check_model_health()
    print(json.dumps(health, indent=2))
    
    # Exit with error code if unhealthy
    if health['status'] != 'healthy':
        sys.exit(1)
'''
        
        script_path = deployment_path / 'health_check.py'
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
    
    def _get_model_endpoints(self, service_type: str) -> List[Dict[str, str]]:
        """
        Get available endpoints for the model service type
        """
        endpoints = {
            'budget_prediction': [
                {'method': 'POST', 'path': '/api/ai/budget/predict/', 'description': 'Budget prediction'},
                {'method': 'GET', 'path': '/api/ai/budget/models/', 'description': 'List available models'}
            ],
            'knowledge_search': [
                {'method': 'POST', 'path': '/api/ai/knowledge/search/', 'description': 'Knowledge search'},
                {'method': 'GET', 'path': '/api/ai/knowledge/stats/', 'description': 'Search statistics'}
            ],
            'indonesian_nlp': [
                {'method': 'POST', 'path': '/api/ai/nlp/analyze/', 'description': 'Text analysis'},
                {'method': 'POST', 'path': '/api/ai/nlp/sentiment/', 'description': 'Sentiment analysis'}
            ]
        }
        
        return endpoints.get(service_type, [])
    
    def list_deployments(self) -> List[Dict[str, Any]]:
        """
        List all deployed models
        """
        deployments = []
        
        for deployment_dir in self.deployment_dir.iterdir():
            if deployment_dir.is_dir():
                config_path = deployment_dir / 'deployment_config.json'
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        
                        # Check if deployment is healthy
                        health_script = deployment_dir / 'health_check.py'
                        is_healthy = False
                        if health_script.exists():
                            import subprocess
                            try:
                                result = subprocess.run(
                                    ['python3', str(health_script)], 
                                    capture_output=True, 
                                    timeout=10
                                )
                                is_healthy = result.returncode == 0
                            except:
                                is_healthy = False
                        
                        deployments.append({
                            'name': config['deployment_name'],
                            'model_name': config['model_info']['name'],
                            'service_type': config['model_info']['service_type'],
                            'deployed_at': config['created_at'],
                            'is_healthy': is_healthy,
                            'path': str(deployment_dir)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error reading deployment config: {e}")
        
        return sorted(deployments, key=lambda x: x['deployed_at'], reverse=True)
    
    def undeploy_model(self, deployment_name: str) -> Dict[str, Any]:
        """
        Remove a deployed model
        """
        try:
            deployment_path = self.deployment_dir / deployment_name
            
            if not deployment_path.exists():
                return {
                    'success': False,
                    'error': f'Deployment {deployment_name} not found'
                }
            
            # Read deployment config to get model info
            config_path = deployment_path / 'deployment_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Update model registry
                try:
                    model = AIModelRegistry.objects.get(id=config['model_info']['id'])
                    model_config = model.get_config()
                    if 'deployment' in model_config:
                        model_config['deployment']['is_deployed'] = False
                        model_config['deployment']['undeployed_at'] = timezone.now().isoformat()
                        model.set_config(model_config)
                except AIModelRegistry.DoesNotExist:
                    pass
            
            # Remove deployment directory
            shutil.rmtree(deployment_path)
            
            logger.info(f"Model undeployed successfully: {deployment_name}")
            
            return {
                'success': True,
                'message': f'Deployment {deployment_name} removed successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to undeploy model: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global deployment manager instance
deployment_manager = ModelDeploymentManager()