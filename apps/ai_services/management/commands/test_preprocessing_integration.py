#!/usr/bin/env python3
"""
Test script untuk preprocessing API integration
"""

import os
import sys
import django
import json
import requests
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
sys.path.append('/Users/haryanto.bonti/apps')
django.setup()

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.test import Client
from ai_services.models import AIModelRegistry

class Command(BaseCommand):
    help = 'Test preprocessing API integration'
    
    def handle(self, *args, **options):
        self.stdout.write("=== Testing Preprocessing API Integration ===")
        
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
        
        # Test direct API call using requests
        base_url = 'http://127.0.0.1:8080'
        
        # Create session for authentication
        session = requests.Session()
        
        # Login first
        login_data = {
            'username': 'admin',  # Assuming admin user exists
            'password': 'admin'   # Default password
        }
        
        try:
            # Get CSRF token
            csrf_response = session.get(f'{base_url}/login/')
            if 'csrftoken' in session.cookies:
                csrf_token = session.cookies['csrftoken']
            else:
                csrf_token = None
                
            self.stdout.write(f"CSRF Token: {csrf_token}")
            
            # Test preprocessing endpoint
            for service_type, data in test_data_samples.items():
                self.stdout.write(f"\nTesting preprocessing for {service_type}...")
                
                payload = {
                    'service_type': service_type,
                    'data': data
                }
                
                headers = {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                if csrf_token:
                    headers['X-CSRFToken'] = csrf_token
                
                try:
                    response = session.post(
                        f'{base_url}/api/ai/preprocess/',
                        data=json.dumps(payload),
                        headers=headers
                    )
                    
                    self.stdout.write(f"Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        self.stdout.write(self.style.SUCCESS(f"✅ Success: {result['success']}"))
                        self.stdout.write(f"Service Type: {result['service_type']}")
                        self.stdout.write(f"Preprocessing Info: {result['preprocessing_info']}")
                    else:
                        self.stdout.write(self.style.ERROR(f"❌ Error: {response.text}"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Exception: {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS("\n✅ All preprocessing integration tests completed!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {str(e)}"))