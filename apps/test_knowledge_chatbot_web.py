#!/usr/bin/env python3

import json
from django.test import Client
from django.contrib.auth.models import User

def test_knowledge_chatbot_web():
    """
    Test Knowledge Chatbot Web Interface dengan FAQ integration
    """
    print("=== Testing Knowledge Chatbot Web Interface ===")
    
    # Create test client
    client = Client()
    
    # Login as admin user
    try:
        user = User.objects.get(username='admin')
        client.force_login(user)
        print(f"✅ Logged in as: {user.username}")
    except User.DoesNotExist:
        print("❌ Admin user not found")
        return
    
    # Test Knowledge Chatbot Query endpoint
    print("\n--- Testing Knowledge Chatbot Query ---")
    
    query_data = {
        'query': 'How do I create a new employee?',
        'conversation_id': None
    }
    
    try:
        # Test knowledge chatbot endpoint
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            data=json.dumps(query_data),
            content_type='application/json'
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response received")
            print(f"Success: {data.get('success', False)}")
            print(f"Response: {data.get('response', 'No response')}")
            print(f"Confidence: {data.get('confidence_score', 'N/A')}")
            print(f"Referenced Documents: {len(data.get('referenced_documents', []))}")
            print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
            
            # Show referenced FAQs
            if data.get('referenced_faqs'):
                print("\n--- Referenced FAQs ---")
                for faq in data.get('referenced_faqs', []):
                    print(f"Q: {faq.get('question', 'N/A')}")
                    print(f"A: {faq.get('answer', 'N/A')}")
                    print("---")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.content.decode()}")
            
    except Exception as e:
        print(f"❌ Error testing knowledge chatbot: {str(e)}")
    
    # Test alternative query
    print("\n--- Testing Alternative Query ---")
    
    query_data2 = {
        'query': 'How to create a leave request?',
        'conversation_id': None
    }
    
    try:
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            data=json.dumps(query_data2),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Second query successful")
            print(f"Response: {data.get('response', 'No response')[:100]}...")
            print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
        else:
            print(f"❌ Second query failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error with second query: {str(e)}")
    
    print("\n=== Knowledge Chatbot Web Test Complete ===")

if __name__ == '__main__':
    test_knowledge_chatbot_web()

# Run the test
test_knowledge_chatbot_web()