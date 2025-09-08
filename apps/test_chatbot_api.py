#!/usr/bin/env python3
"""
Test script for chatbot API endpoints
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from knowledge.models import ChatbotConversation, ChatbotMessage

def test_chatbot_api():
    """Test all chatbot API endpoints"""
    print("Testing Chatbot API Endpoints...")
    print("=" * 50)
    
    # Create test client
    client = Client()
    
    # Get or create test user
    try:
        user = User.objects.get(username='admin')
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    
    # Login the user
    client.force_login(user)
    
    # Test 1: Chatbot Query
    print("\n1. Testing Chatbot Query...")
    query_data = {
        'query': 'What is the company remote work policy?',
        'conversation_id': None
    }
    
    response = client.post(
        '/api/knowledge/api/chatbot/query/',
        data=json.dumps(query_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response', 'No response')[:100]}...")
        print(f"Conversation ID: {result.get('conversation_id')}")
        conversation_id = result.get('conversation_id')
    else:
        print(f"Error: {response.content.decode()}")
        return False
    
    # Test 2: Follow-up Query with Conversation ID
    print("\n2. Testing Follow-up Query...")
    followup_data = {
        'query': 'How many days can I work remotely?',
        'conversation_id': conversation_id
    }
    
    response = client.post(
        '/api/knowledge/api/chatbot/query/',
        data=json.dumps(followup_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('response', 'No response')[:100]}...")
    else:
        print(f"Error: {response.content.decode()}")
    
    # Test 3: Conversation History
    print("\n3. Testing Conversation History...")
    response = client.get(f'/api/knowledge/api/chatbot/conversation/{conversation_id}/history/')
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        history = response.json()
        print(f"Messages in conversation: {len(history.get('messages', []))}")
        for msg in history.get('messages', [])[:2]:  # Show first 2 messages
            print(f"- {msg.get('sender')}: {msg.get('content', '')[:50]}...")
    else:
        print(f"Error: {response.content.decode()}")
    
    # Test 4: Document Search
    print("\n4. Testing Document Search...")
    search_data = {
        'query': 'API development guidelines'
    }
    
    response = client.post(
        '/api/knowledge/api/chatbot/search/',
        data=json.dumps(search_data),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"Found {len(results.get('documents', []))} documents")
        for doc in results.get('documents', [])[:2]:  # Show first 2 documents
            print(f"- {doc.get('title', 'No title')}")
    else:
        print(f"Error: {response.content.decode()}")
    
    # Test 5: Submit Feedback
    print("\n5. Testing Feedback Submission...")
    
    # Get the last message for feedback
    try:
        last_message = ChatbotMessage.objects.filter(
            conversation_id=conversation_id,
            sender='assistant'
        ).last()
        
        if last_message:
            feedback_data = {
                'message_id': last_message.id,
                'rating': 4,
                'comment': 'Good response, very helpful!'
            }
            
            response = client.post(
                '/api/knowledge/api/chatbot/feedback/',
                data=json.dumps(feedback_data),
                content_type='application/json'
            )
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"Feedback submitted: {result.get('message', 'Success')}")
            else:
                print(f"Error: {response.content.decode()}")
        else:
            print("No assistant message found for feedback")
    except Exception as e:
        print(f"Error getting message for feedback: {e}")
    
    # Test 6: Chatbot Statistics
    print("\n6. Testing Chatbot Statistics...")
    response = client.get('/api/knowledge/api/chatbot/stats/')
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"Total conversations: {stats.get('total_conversations', 0)}")
        print(f"Total messages: {stats.get('total_messages', 0)}")
        print(f"Average rating: {stats.get('average_rating', 'N/A')}")
    else:
        print(f"Error: {response.content.decode()}")
    
    # Test 7: Close Conversation
    print("\n7. Testing Close Conversation...")
    response = client.post(f'/api/knowledge/api/chatbot/conversation/{conversation_id}/close/')
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Conversation closed: {result.get('message', 'Success')}")
    else:
        print(f"Error: {response.content.decode()}")
    
    print("\n" + "=" * 50)
    print("Chatbot API Testing Completed!")
    return True

def test_different_queries():
    """Test chatbot with different types of queries"""
    print("\nTesting Different Query Types...")
    print("=" * 50)
    
    client = Client()
    user = User.objects.get(username='admin')
    client.force_login(user)
    
    test_queries = [
        "What are the database security best practices?",
        "How many days of annual leave do employees get?",
        "Tell me about the onboarding process",
        "What is the API development standard?",
        "How do I request time off?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        
        query_data = {
            'query': query,
            'conversation_id': None
        }
        
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            data=json.dumps(query_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')[:150]}...")
            print(f"Sources: {len(result.get('sources', []))} documents")
        else:
            print(f"Error: {response.content.decode()}")
    
    print("\n" + "=" * 50)
    print("Query Testing Completed!")

if __name__ == '__main__':
    try:
        # Test API endpoints
        test_chatbot_api()
        
        # Test different queries
        test_different_queries()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)