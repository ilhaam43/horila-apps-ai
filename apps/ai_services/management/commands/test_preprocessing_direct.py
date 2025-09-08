#!/usr/bin/env python3
"""
Test script untuk preprocessing API integration - Direct Django Test
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

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.contrib.auth import authenticate, login
from ai_services.models import AIModelRegistry
from ai_services.api_views import preprocess_data, batch_preprocess_data
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.authtoken.models import Token

class Command(BaseCommand):
    help = 'Test preprocessing API integration directly'
    
    def handle(self, *args, **options):
        self.stdout.write("=== Testing Preprocessing API Direct Integration ===")
        
        # Create or get test user
        try:
            user = User.objects.get(username='testuser_preprocessing')
        except User.DoesNotExist:
            user = User.objects.create_user(
                username='testuser_preprocessing',
                email='test_preprocessing@example.com',
                password='testpass123'
            )
        
        self.stdout.write(f"✅ Using user: {user.username}")
        
        # Test data samples
        test_data_samples = {
            'budget_ai': {
                'department': 'IT',
                'category': 'Software',
                'amount': 50000,
                'quarter': 'Q1',
                'year': 2024
            },
            'knowledge_ai': {
                'query': 'What is the company policy on remote work?',
                'context': 'HR policies'
            },
            'indonesian_nlp': {
                'text': 'Saya sangat senang dengan layanan ini',
                'task': 'sentiment_analysis'
            }
        }
        
        # Use APIRequestFactory for testing
        factory = APIRequestFactory()
        
        self.stdout.write("\n=== Test 1: Single Data Preprocessing ===")
        
        for service_type, data in test_data_samples.items():
            self.stdout.write(f"\nTesting preprocessing for {service_type}...")
            
            payload = {
                'service_type': service_type,
                'data': data
            }
            
            try:
                # Create request
                request = factory.post(
                    '/api/ai/preprocess/',
                    data=json.dumps(payload),
                    content_type='application/json'
                )
                
                # Force authenticate
                force_authenticate(request, user=user)
                
                # Call view directly
                response = preprocess_data(request)
                
                self.stdout.write(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    # Render response content first
                    response.render()
                    result = json.loads(response.content)
                    self.stdout.write(self.style.SUCCESS(f"✅ Success: {result['success']}"))
                    self.stdout.write(f"Service Type: {result['service_type']}")
                    self.stdout.write(f"Preprocessing Info: {result['preprocessing_info']}")
                    self.stdout.write(f"Original Shape: {result['preprocessing_info']['original_shape']}")
                    self.stdout.write(f"Processed Shape: {result['preprocessing_info']['processed_shape']}")
                else:
                    # Render response content first
                    response.render()
                    result = json.loads(response.content)
                    self.stdout.write(self.style.ERROR(f"❌ Error: {result.get('error', 'Unknown error')}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Exception: {str(e)}"))
        
        self.stdout.write("\n=== Test 2: Batch Data Preprocessing ===")
        
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
            # Create request
            request = factory.post(
                '/api/ai/batch-preprocess/',
                data=json.dumps(batch_payload),
                content_type='application/json'
            )
            
            # Force authenticate
            force_authenticate(request, user=user)
            
            # Call view directly
            response = batch_preprocess_data(request)
            
            self.stdout.write(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                # Render response content first
                response.render()
                result = json.loads(response.content)
                self.stdout.write(self.style.SUCCESS(f"✅ Batch Success: {result['success']}"))
                self.stdout.write(f"Total Requests: {result.get('total_requests', 'N/A')}")
                self.stdout.write(f"Successful: {result.get('successful', 'N/A')}")
                self.stdout.write(f"Failed: {result.get('failed', 'N/A')}")
                
                if 'results' in result:
                    for i, res in enumerate(result['results']):
                        self.stdout.write(f"  Request {i+1}: {res.get('success', 'N/A')} - {res.get('service_type', 'N/A')}")
                else:
                    self.stdout.write("  No detailed results available")
            else:
                # Render response content first
                response.render()
                result = json.loads(response.content)
                self.stdout.write(self.style.ERROR(f"❌ Batch Error: {result.get('error', 'Unknown error')}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Batch Exception: {str(e)}"))
        
        self.stdout.write("\n=== Test 3: Error Handling ===")
        
        # Test with missing data
        try:
            payload = {
                'service_type': 'budget_ai'
                # Missing 'data' field
            }
            
            request = factory.post(
                '/api/ai/preprocess/',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            force_authenticate(request, user=user)
            response = preprocess_data(request)
            
            self.stdout.write(f"Missing Data Test Status: {response.status_code}")
            
            if response.status_code == 400:
                # Render response content first
                response.render()
                result = json.loads(response.content)
                self.stdout.write(self.style.SUCCESS(f"✅ Error handling works: {result.get('error', 'Unknown error')}"))
            else:
                # Render response content first
                response.render()
                self.stdout.write(self.style.ERROR(f"❌ Expected 400, got {response.status_code}"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Missing Data Exception: {str(e)}"))
        
        # Cleanup
        try:
            user.delete()
            self.stdout.write("✅ Test user cleaned up")
        except:
            pass
        
        self.stdout.write(self.style.SUCCESS("\n✅ All preprocessing direct tests completed!"))