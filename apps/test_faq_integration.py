#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from knowledge.chatbot_service import ChatbotRAGService
from helpdesk.models import FAQ

print("=== Testing Complete FAQ Integration ===")

# Test chatbot service with FAQ question
try:
    # Get a user (assuming admin user exists)
    user = User.objects.first()
    if not user:
        print("No user found")
        sys.exit(1)
    
    print(f"Using user: {user.username}")
    
    # Initialize chatbot service
    rag_service = ChatbotRAGService()
    
    # Test with FAQ question
    query = "How to create an Employee?"
    print(f"\nQuery: {query}")
    
    # Retrieve relevant documents/FAQs
    relevant_docs = rag_service.retrieve_relevant_documents(
        query=query,
        user=user,
        max_results=5
    )
    
    print(f"\nFound {len(relevant_docs)} relevant results:")
    faq_found = False
    for i, doc_data in enumerate(relevant_docs, 1):
        print(f"\n{i}. Type: {doc_data.get('type', 'document')}")
        print(f"   Method: {doc_data.get('method', 'unknown')}")
        print(f"   Score: {doc_data.get('similarity_score', 0.0):.3f}")
        
        if doc_data.get('type') == 'faq':
            faq = doc_data['faq']
            print(f"   FAQ Question: {faq.question}")
            print(f"   FAQ Answer: {faq.answer}")
            if 'create an Employee' in faq.question:
                faq_found = True
        else:
            doc = doc_data.get('document')
            if doc:
                print(f"   Document: {doc.title}")
                print(f"   Snippet: {doc_data.get('snippet', '')[:100]}...")
    
    if faq_found and relevant_docs:
        print("\n=== Testing AI Response Generation ===")
        # Create a test conversation
        conversation = rag_service.create_conversation(user, query)
        
        # Generate response
        response_data = rag_service.generate_response(
            query=query,
            relevant_docs=relevant_docs,
            conversation=conversation
        )
        
        if response_data['success']:
            print(f"\nAI Response: {response_data['response']}")
            print(f"Confidence: {response_data.get('confidence_score', 0.0):.3f}")
            print(f"Referenced Documents: {len(response_data.get('referenced_documents', []))}") 
            print(f"Referenced FAQs: {len(response_data.get('referenced_faqs', []))}") 
            
            # Show referenced FAQs
            if response_data.get('referenced_faqs'):
                print("\nReferenced FAQs:")
                for faq in response_data['referenced_faqs']:
                    print(f"- Q: {faq.question}")
                    print(f"  A: {faq.answer}")
        else:
            print(f"\nResponse generation failed: {response_data.get('error', 'Unknown error')}")
    else:
        print("\nTarget FAQ not found in results!")
        
except Exception as e:
    print(f"\nError during testing: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Test Complete ===")