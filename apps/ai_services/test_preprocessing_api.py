#!/usr/bin/env python3
"""
Test script untuk preprocessing API endpoints
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
sys.path.append('/Users/haryanto.bonti/apps')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from ai_services.models import AIModelRegistry

def test_preprocessing_endpoints():
    """
    Test preprocessing API endpoints
    """
    print("=== Testing Preprocessing API Endpoints ===")
    
    client = Client(enforce_csrf_checks=False)
    
    # Create or get test user
    try:
        user = User.objects.get(username='testuser_preprocessing')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser_preprocessing',
            email='test_preprocessing@example.com',
            password='testpass123'
        )
    
    # Login
    client.force_login(user)
    print(f"✅ Logged in as: {user.username}")
    
    # Test data samples
    test_data_samples = {
        'budget_ai': {
            'numerical_data': [100, 200, 300, 150, 250],
            'categorical_data': ['A', 'B', 'A', 'C', 'B'],
            'text_data': 'Budget analysis for Q1 2024'
        },
        'knowledge_ai': {
            'query': 'What is the company policy on remote work?',
            'context': 'HR policies and procedures'
        },
        'indonesian_nlp': {
            'text': 'Saya sangat senang dengan layanan ini. Terima kasih!',
            'language': 'id'
        }
    }
    
    print("\n=== Test 1: Single Data Preprocessing ===")
    
    for service_type, data in test_data_samples.items():
        print(f"\nTesting preprocessing for {service_type}...")
        
        payload = {
            'service_type': service_type,
            'data': data
        }
        
        try:
            response = client.post(
                '/api/ai/preprocess/',
                data=json.dumps(payload),
                content_type='application/json',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success: {result['success']}")
                print(f"Service Type: {result['service_type']}")
                print(f"Preprocessing Info: {result['preprocessing_info']}")
                print(f"Original Data Type: {result['preprocessing_info']['original_shape']}")
                print(f"Processed Data Type: {result['preprocessing_info']['processed_shape']}")
            else:
                result = response.json()
                print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    print("\n=== Test 2: Batch Data Preprocessing ===")
    
    batch_requests = []
    for i, (service_type, data) in enumerate(test_data_samples.items()):
        batch_requests.append({
            'service_type': service_type,
            'data': data,
            'request_id': f'batch_req_{i}'
        })
    
    batch_payload = {
        'requests': batch_requests
    }
    
    try:
        response = client.post(
            '/api/ai/batch-preprocess/',
            data=json.dumps(batch_payload),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch Success: {result['success']}")
            print(f"Total Requests: {result['total_requests']}")
            print(f"Successful: {result['successful_requests']}")
            print(f"Failed: {result['failed_requests']}")
            
            for res in result['results']:
                print(f"  Request {res['request_id']}: {'✅' if res['success'] else '❌'}")
                if res['success']:
                    print(f"    Service: {res['service_type']}")
                    print(f"    Preprocessing: {res['preprocessing_info']}")
                else:
                    print(f"    Error: {res.get('error', 'Unknown')}")
        else:
            result = response.json()
            print(f"❌ Batch Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Batch Exception: {str(e)}")
    
    print("\n=== Test 3: Integration with AI Prediction ===")
    
    # Test budget prediction with preprocessing
    budget_data = {
        'data': {
            'amount': 50000,
            'category': 'Marketing',
            'department': 'Sales',
            'quarter': 'Q1',
            'year': 2024
        },
        'prediction_type': 'budget_forecast'
    }
    
    try:
        response = client.post(
            '/api/ai/budget/prediction/',
            data=json.dumps(budget_data),
            content_type='application/json'
        )
        
        print(f"Budget Prediction Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Prediction Success: {result['success']}")
            print(f"Service: {result['service']}")
            
            # Check if preprocessing info is included
            if 'preprocessing' in result:
                print(f"✅ Preprocessing Applied: {result['preprocessing']['applied']}")
                if result['preprocessing']['applied']:
                    print(f"Pipeline Type: {result['preprocessing']['pipeline_type']}")
                    print(f"Data Shape Change: {result['preprocessing']['original_shape']} -> {result['preprocessing']['processed_shape']}")
                else:
                    print(f"Preprocessing Error: {result['preprocessing'].get('error', 'Unknown')}")
            else:
                print("⚠️  No preprocessing info in response")
                
        else:
            result = response.json()
            print(f"❌ Prediction Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Prediction Exception: {str(e)}")
    
    print("\n=== Test 4: Error Handling ===")
    
    # Test with invalid service type
    invalid_payload = {
        'service_type': 'invalid_service',
        'data': {'test': 'data'}
    }
    
    try:
        response = client.post(
            '/api/ai/preprocess/',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        
        print(f"Invalid Service Test Status: {response.status_code}")
        result = response.json()
        print(f"Expected Error: {not result['success']}")
        print(f"Error Message: {result.get('error', 'No error message')}")
        
    except Exception as e:
        print(f"❌ Error Handling Exception: {str(e)}")
    
    # Test with missing data
    missing_data_payload = {
        'service_type': 'budget_ai'
        # Missing 'data' field
    }
    
    try:
        response = client.post(
            '/api/ai/preprocess/',
            data=json.dumps(missing_data_payload),
            content_type='application/json'
        )
        
        print(f"\nMissing Data Test Status: {response.status_code}")
        result = response.json()
        print(f"Expected Error: {not result['success']}")
        print(f"Error Message: {result.get('error', 'No error message')}")
        
    except Exception as e:
        print(f"❌ Missing Data Exception: {str(e)}")
    
    print("\n✅ All preprocessing API tests completed!")

if __name__ == '__main__':
    test_preprocessing_endpoints()