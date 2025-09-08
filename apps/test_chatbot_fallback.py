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

def test_chatbot_fallback():
    """Test chatbot with SLM fallback system"""
    client = Client()
    User = get_user_model()
    
    # Get superuser
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        print("No superuser found")
        return
    
    # Login user
    client.force_login(user)
    
    # Test query
    query = "How to create a leave request?"
    response = client.post(
        '/api/knowledge/api/chatbot/query/',
        {'query': query},
        content_type='application/json'
    )
    
    # Parse response
    data = json.loads(response.content)
    
    print(f"Status: {response.status_code}")
    print(f"Success: {data.get('success')}")
    print(f"Response: {data.get('response')}")
    print(f"Model Used: {data.get('model_used')}")
    print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
    
    print("\nFAQ Questions:")
    for faq in data.get('referenced_faqs', [])[:3]:
        print(f"- {faq.get('question')}")
    
    print("\nFull Response Data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    test_chatbot_fallback()