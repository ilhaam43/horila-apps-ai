#!/usr/bin/env python3
import os
import django
import json
import requests
from django.test import Client
from django.contrib.auth.models import User

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

def test_api_direct():
    """Test the knowledge chatbot API directly"""
    print("=== Testing Knowledge Chatbot API Directly ===")
    
    # Create test client
    client = Client()
    
    # Login as admin
    login_success = client.login(username='admin', password='admin')
    if not login_success:
        print("❌ Login failed")
        return
    
    print("✅ Login successful")
    
    # Test query
    query_data = {
        'query': 'How do I create a new employee?'
    }
    
    try:
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            data=json.dumps(query_data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Query successful")
            print(f"Response: {data.get('response', '')[:100]}...")
            print(f"Referenced Documents: {len(data.get('referenced_documents', []))}")
            print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
            
            # Show FAQ details
            faqs = data.get('referenced_faqs', [])
            if faqs:
                print("\n📋 Referenced FAQs:")
                for i, faq in enumerate(faqs[:3], 1):
                    print(f"  {i}. {faq.get('question', 'N/A')}")
                    print(f"     Category: {faq.get('category', 'N/A')}")
                    print(f"     Score: {faq.get('similarity_score', 0):.3f}")
            else:
                print("⚠️ No FAQs referenced")
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == '__main__':
    test_api_direct()