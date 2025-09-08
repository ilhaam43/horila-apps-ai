#!/usr/bin/env python3
import os
import sys
import django
import requests
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

print("=== Testing Chatbot Web Interface ===")

try:
    # Get a user
    user = User.objects.first()
    if not user:
        print("No user found")
        sys.exit(1)
    
    print(f"Using user: {user.username}")
    
    # Create Django test client
    client = Client()
    
    # Login user
    client.force_login(user)
    
    # Test chatbot endpoint
    print("\n=== Testing Chatbot API Endpoint ===")
    
    # Test query about creating employee
    test_queries = [
        "How to create an Employee?",
        "How do I add a new employee?",
        "What are the steps to create employee?"
    ]
    
    for query in test_queries:
        print(f"\nTesting query: {query}")
        
        try:
            # Use correct chatbot URL
            response = client.post('/ai_services/chatbot/chat/', {
                'query': query
            })
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Response: {data.get('response', 'No response')}")
                    print(f"Success: {data.get('success', False)}")
                    print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
                except json.JSONDecodeError:
                    print(f"Response (HTML): {response.content[:200]}...")
            else:
                print(f"HTTP {response.status_code}: {response.content[:200]}...")
                
        except Exception as e:
            print(f"Error testing query '{query}': {e}")
    
    print("\n=== Testing Alternative Endpoints ===")
    
    # Try alternative endpoints
    alternative_urls = [
        '/chatbot/chat/',
        '/api/chatbot/chat/',
        '/knowledge/chat/',
        '/ai/chat/'
    ]
    
    for url in alternative_urls:
        try:
            response = client.post(url, {'query': 'How to create an Employee?'})
            print(f"{url}: HTTP {response.status_code}")
            if response.status_code == 200:
                print(f"  Found working endpoint!")
                break
        except Exception as e:
            print(f"{url}: Error - {e}")
    
except Exception as e:
    print(f"\nError during web testing: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Web Test Complete ===")