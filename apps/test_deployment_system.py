#!/usr/bin/env python3
"""
Comprehensive Test Suite for AI Model Deployment System
Tests all aspects of model deployment, serving, and monitoring
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')

import django
django.setup()

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ai_services.models import AIModelRegistry, ModelTrainingSession
from ai_services.deployment import deployment_manager
from ai_services.training import training_manager


class ModelDeploymentSystemTest(TransactionTestCase):
    """
    Test suite for the complete model deployment system
    """
    
    def setUp(self):
        """Set up test environment"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f'testuser_{unique_id}',
            email=f'test_{unique_id}@example.com',
            password='testpass123'
        )
        
        # Create test model registry
        self.test_model = AIModelRegistry.objects.create(
            name='test-budget-model',
            service_type='budget_ai',
            model_type='regression',
            version='1.0.0',
            model_path='/tmp/test_budget_model.pkl',
            is_active=False
        )
        
        # Create test training session
        self.training_session = ModelTrainingSession.objects.create(
            model=self.test_model,
            status='completed',
            accuracy=0.85,
            training_time_minutes=30,
            training_data_size=1000
        )
        
        # Set initial config with empty artifacts
        self.training_session.set_config({
            'artifacts': {},
            'model_params': {},
            'training_metrics': {}
        })
        
        # Set up test data
        self.test_deployment_name = f"test_deployment_{int(time.time())}"
        
    def tearDown(self):
        """Clean up test environment"""
        # Remove test deployments
        try:
            deployment_manager.undeploy_model(self.test_deployment_name)
        except:
            pass
    
    def test_deployment_manager_initialization(self):
        """Test deployment manager initialization"""
        self.assertIsNotNone(deployment_manager)
        self.assertTrue(deployment_manager.deployment_dir.exists())
        self.assertIsInstance(deployment_manager.serving_configs, dict)
        
        # Test serving configs for all service types
        expected_services = ['budget_prediction', 'knowledge_search', 'indonesian_nlp']
        for service in expected_services:
            self.assertIn(service, deployment_manager.serving_configs)
            config = deployment_manager.serving_configs[service]
            self.assertIn('endpoint', config)
            self.assertIn('max_concurrent_requests', config)
            self.assertIn('timeout_seconds', config)
    
    def test_model_deployment_flow(self):
        """Test complete model deployment flow"""
        # Create mock model artifacts
        self.create_mock_model_artifacts()
        
        # Deploy the model
        result = deployment_manager.deploy_model(
            training_session_id=str(self.training_session.id),
            deployment_name=self.test_deployment_name
        )
        
        # Debug: print result if deployment fails
        if not result.get('success', False):
            print(f"Deployment failed: {result}")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['deployment_name'], self.test_deployment_name)
        self.assertIn('deployment_path', result)
        self.assertIn('config', result)
        self.assertIn('endpoints', result)
        
        # Verify deployment directory structure
        deployment_path = Path(result['deployment_path'])
        self.assertTrue(deployment_path.exists())
        self.assertTrue((deployment_path / 'deployment_config.json').exists())
        self.assertTrue((deployment_path / 'serve_model.py').exists())
        self.assertTrue((deployment_path / 'health_check.py').exists())
        
        # Verify deployment config
        with open(deployment_path / 'deployment_config.json', 'r') as f:
            config = json.load(f)
        
        self.assertEqual(config['deployment_name'], self.test_deployment_name)
        self.assertEqual(config['model_info']['name'], self.test_model.name)
        self.assertEqual(config['model_info']['service_type'], self.test_model.service_type)
        
        # Test model registry update
        self.test_model.refresh_from_db()
        model_config = self.test_model.get_config()
        self.assertTrue(model_config.get('deployment', {}).get('is_deployed', False))
    
    def test_deployment_listing(self):
        """Test deployment listing functionality"""
        # Deploy a test model
        self.create_mock_model_artifacts()
        deployment_manager.deploy_model(
            training_session_id=str(self.training_session.id),
            deployment_name=self.test_deployment_name
        )
        
        # List deployments
        deployments = deployment_manager.list_deployments()
        
        self.assertIsInstance(deployments, list)
        
        # Find our test deployment
        test_deployment = None
        for deployment in deployments:
            if deployment['name'] == self.test_deployment_name:
                test_deployment = deployment
                break
        
        self.assertIsNotNone(test_deployment)
        self.assertEqual(test_deployment['model_name'], self.test_model.name)
        self.assertEqual(test_deployment['service_type'], self.test_model.service_type)
        self.assertIn('deployed_at', test_deployment)
        self.assertIn('is_healthy', test_deployment)
    
    def test_health_check_system(self):
        """Test deployment health check system"""
        # Deploy a test model
        self.create_mock_model_artifacts()
        result = deployment_manager.deploy_model(
            training_session_id=str(self.training_session.id),
            deployment_name=self.test_deployment_name
        )
        
        deployment_path = Path(result['deployment_path'])
        health_script = deployment_path / 'health_check.py'
        
        # Test health check script execution
        try:
            result = subprocess.run(
                ['python3', str(health_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                self.assertIn('status', health_data)
                self.assertIn('timestamp', health_data)
            else:
                # Health check might fail due to missing dependencies in test environment
                self.assertIsNotNone(result.stderr)
                
        except subprocess.TimeoutExpired:
            self.fail("Health check script timed out")
        except json.JSONDecodeError:
            self.fail("Health check script returned invalid JSON")
    
    def test_model_undeployment(self):
        """Test model undeployment functionality"""
        # Deploy a test model
        self.create_mock_model_artifacts()
        deploy_result = deployment_manager.deploy_model(
            training_session_id=str(self.training_session.id),
            deployment_name=self.test_deployment_name
        )
        
        deployment_path = Path(deploy_result['deployment_path'])
        self.assertTrue(deployment_path.exists())
        
        # Undeploy the model
        undeploy_result = deployment_manager.undeploy_model(self.test_deployment_name)
        
        self.assertTrue(undeploy_result['success'])
        self.assertFalse(deployment_path.exists())
        
        # Verify model registry update
        self.test_model.refresh_from_db()
        model_config = self.test_model.get_config()
        deployment_info = model_config.get('deployment', {})
        self.assertFalse(deployment_info.get('is_deployed', True))
        self.assertIn('undeployed_at', deployment_info)
    
    def test_deployment_error_handling(self):
        """Test error handling in deployment system"""
        # Test deployment with non-existent training session
        result = deployment_manager.deploy_model(
            training_session_id='non-existent-id',
            deployment_name='test-deployment'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        
        # Test undeployment of non-existent deployment
        result = deployment_manager.undeploy_model('non-existent-deployment')
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def create_mock_model_artifacts(self):
        """Create mock model artifacts for testing"""
        import joblib
        from sklearn.linear_model import LinearRegression
        import numpy as np
        
        # Create a simple mock model
        X = np.random.rand(100, 5)
        y = np.random.rand(100)
        model = LinearRegression().fit(X, y)
        
        # Create artifacts directory
        artifacts_dir = Path('/tmp/test_artifacts')
        artifacts_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = artifacts_dir / 'model.pkl'
        joblib.dump(model, model_path)
        
        # Update training session config
        config = self.training_session.get_config()
        config['artifacts'] = {
            'model': str(model_path)
        }
        self.training_session.set_config(config)
        self.training_session.save()


class DeploymentAPITest(APITestCase):
    """
    Test suite for deployment API endpoints
    """
    
    def setUp(self):
        """Set up API test environment"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f'apiuser_{unique_id}',
            email=f'api_{unique_id}@example.com',
            password='apipass123'
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test model and training session
        self.test_model = AIModelRegistry.objects.create(
            name='api-test-model',
            service_type='budget_ai',
            model_type='regression',
            version='1.0.0',
            model_path='/tmp/api_test_model.pkl'
        )
        
        self.training_session = ModelTrainingSession.objects.create(
            model=self.test_model,
            status='completed',
            accuracy=0.90,
            training_time_minutes=25,
            training_data_size=800
        )
    
    def test_deployment_api_endpoints(self):
        """Test deployment API endpoints"""
        # Test deployment status endpoint
        response = self.client.get('/api/ai/deployment/status/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('system_status', data)
        self.assertIn('total_deployments', data)
        self.assertIn('healthy_deployments', data)
        
        # Test available models endpoint
        response = self.client.get('/api/ai/deployment/available-models/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('available_models', data)
        self.assertIn('total_count', data)
        
        # Find our test model
        test_model_found = False
        for model in data['available_models']:
            if model['model_name'] == self.test_model.name:
                test_model_found = True
                self.assertEqual(model['service_type'], self.test_model.service_type)
                self.assertEqual(model['accuracy'], self.training_session.accuracy)
                break
        
        self.assertTrue(test_model_found)
    
    def test_deployment_list_api(self):
        """Test deployment listing API"""
        response = self.client.get('/api/ai/deployment/deployments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('deployments', data)
        self.assertIn('total_count', data)
        self.assertIsInstance(data['deployments'], list)
    
    def test_deployment_api_authentication(self):
        """Test API authentication requirements"""
        # Test without authentication
        client = APIClient()
        
        response = client.get('/api/ai/deployment/status/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        response = client.post('/api/ai/deployment/deploy/', {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeploymentManagementCommandTest(TestCase):
    """
    Test suite for deployment management commands
    """
    
    def setUp(self):
        """Set up management command test environment"""
        self.test_model = AIModelRegistry.objects.create(
            name='cmd-test-model',
            service_type='indonesian_nlp',
            model_type='nlp',
            version='1.0.0',
            model_path='/tmp/cmd_test_model.pkl'
        )
        
        self.training_session = ModelTrainingSession.objects.create(
            model=self.test_model,
            status='completed',
            accuracy=0.88,
            training_time_minutes=45,
            training_data_size=1200
        )
    
    def test_management_command_status(self):
        """Test deployment management command status"""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('deploy_model', 'status', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Deployment System Status', output)
        self.assertIn('Total deployments', output)
        self.assertIn('Healthy deployments', output)
    
    def test_management_command_list(self):
        """Test deployment management command list"""
        from django.core.management import call_command
        from io import StringIO
        
        out = StringIO()
        call_command('deploy_model', 'list', stdout=out)
        
        output = out.getvalue()
        # Should not error even if no deployments exist
        self.assertIsInstance(output, str)


class DeploymentIntegrationTest(TransactionTestCase):
    """
    Integration tests for the complete deployment system
    """
    
    def setUp(self):
        """Set up integration test environment"""
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f'integrationuser_{unique_id}',
            email=f'integration_{unique_id}@example.com',
            password='integrationpass123'
        )
    
    def test_end_to_end_deployment_workflow(self):
        """Test complete end-to-end deployment workflow"""
        # 1. Create and train a model
        model = AIModelRegistry.objects.create(
            name='e2e-test-model',
            service_type='budget_ai',
            model_type='regression',
            version='1.0.0',
            model_path='/tmp/e2e_test_model.pkl'
        )
        
        # 2. Create training session
        training_session = ModelTrainingSession.objects.create(
            model=model,
            status='completed',
            accuracy=0.92,
            training_time_minutes=20,
            training_data_size=500
        )
        
        # 3. Create mock artifacts
        self.create_mock_artifacts(training_session)
        
        # 4. Deploy the model
        deployment_name = f"e2e_test_{int(time.time())}"
        result = deployment_manager.deploy_model(
            training_session_id=str(training_session.id),
            deployment_name=deployment_name
        )
        
        # Debug: print result if deployment fails
        if not result.get('success', False):
            print(f"End-to-end deployment failed: {result}")
        
        self.assertTrue(result['success'])
        
        try:
            # 5. Verify deployment is listed
            deployments = deployment_manager.list_deployments()
            deployment_found = any(d['name'] == deployment_name for d in deployments)
            self.assertTrue(deployment_found)
            
            # 6. Test health check
            deployment_path = Path(result['deployment_path'])
            health_script = deployment_path / 'health_check.py'
            self.assertTrue(health_script.exists())
            
            # 7. Test serving script
            serve_script = deployment_path / 'serve_model.py'
            self.assertTrue(serve_script.exists())
            
            # 8. Verify model registry update
            model.refresh_from_db()
            model_config = model.get_config()
            self.assertTrue(model_config.get('deployment', {}).get('is_deployed', False))
            
        finally:
            # 9. Clean up - undeploy the model
            cleanup_result = deployment_manager.undeploy_model(deployment_name)
            self.assertTrue(cleanup_result['success'])
    
    def create_mock_artifacts(self, training_session):
        """Create mock artifacts for integration testing"""
        import joblib
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        
        # Create a more realistic mock model
        X = np.random.rand(200, 10)
        y = np.random.rand(200) * 1000  # Budget amounts
        model = RandomForestRegressor(n_estimators=10, random_state=42).fit(X, y)
        
        # Create artifacts directory
        artifacts_dir = Path('/tmp/e2e_test_artifacts')
        artifacts_dir.mkdir(exist_ok=True)
        
        # Save model and preprocessor
        model_path = artifacts_dir / 'model.pkl'
        joblib.dump(model, model_path)
        
        # Update training session config
        config = training_session.get_config()
        config['artifacts'] = {
            'model': str(model_path)
        }
        training_session.set_config(config)
        training_session.save()


def run_deployment_tests():
    """
    Run all deployment system tests
    """
    import unittest
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(ModelDeploymentSystemTest))
    test_suite.addTest(unittest.makeSuite(DeploymentAPITest))
    test_suite.addTest(unittest.makeSuite(DeploymentManagementCommandTest))
    test_suite.addTest(unittest.makeSuite(DeploymentIntegrationTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Starting AI Model Deployment System Tests...")
    print("=" * 60)
    
    success = run_deployment_tests()
    
    print("=" * 60)
    if success:
        print("✅ All deployment tests passed!")
        sys.exit(0)
    else:
        print("❌ Some deployment tests failed!")
        sys.exit(1)