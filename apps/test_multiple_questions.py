#!/usr/bin/env python3
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

def test_multiple_questions():
    """Test chatbot with multiple questions"""
    client = Client()
    User = get_user_model()
    
    # Get superuser
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found")
        return
    
    # Login user
    client.force_login(user)
    
    # Test queries
    test_queries = [
        "How to create a leave request?",
        "How to export work records?",
        "How to create a shift request?",
        "What is recruitment pipeline?",
        "Bagaimana cara membuat cuti?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n=== Test {i}: {query} ===")
        
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            {'query': query},
            content_type='application/json'
        )
        
        # Parse response
        data = json.loads(response.content)
        
        print(f"Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Model Used: {data.get('model_used')}")
        print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
        print(f"Response: {data.get('response')[:200]}...")
        
        # Show top FAQ
        faqs = data.get('referenced_faqs', [])
        if faqs:
            print(f"Top FAQ: {faqs[0].get('question')}")

if __name__ == '__main__':
    test_multiple_questions()