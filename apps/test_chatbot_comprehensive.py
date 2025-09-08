#!/usr/bin/env python3
"""
Comprehensive Chatbot Fallback System Test
Testing various scenarios to ensure the fallback system works properly
"""

import os
import sys
import django
import json
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

def test_chatbot_query(client, query, test_name):
    """Test a single chatbot query"""
    print(f"\n=== {test_name} ===")
    print(f"Query: {query}")
    
    try:
        response = client.post(
            '/api/knowledge/api/chatbot/query/',
            {'query': query},
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        
        print(f"Status: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Response: {data.get('response', '')[:150]}...")
        print(f"Model Used: {data.get('model_used')}")
        print(f"Confidence Score: {data.get('confidence_score')}")
        print(f"Referenced FAQs: {len(data.get('referenced_faqs', []))}")
        
        if data.get('referenced_faqs'):
            print("FAQ Topics:", [faq.get('question', 'N/A')[:50] for faq in data.get('referenced_faqs', [])[:3]])
        
        return data.get('success', False)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    # Initialize Django test client
    client = Client()
    
    # Get superuser for authentication
    User = get_user_model()
    user = User.objects.filter(is_superuser=True).first()
    
    if not user:
        print("No superuser found. Please create one first.")
        return
    
    # Login user
    client.force_login(user)
    
    # Test queries
    test_queries = [
        ("Bagaimana cara membuat cuti?", "Leave Request - Indonesian"),
        ("How to create a leave request?", "Leave Request - English"),
        ("Apa itu sistem payroll?", "Payroll System - Indonesian"),
        ("What are the company policies?", "Company Policies - English"),
        ("Bagaimana cara mengajukan overtime?", "Overtime Request - Indonesian"),
        ("How to check my attendance?", "Attendance Check - English"),
        ("Siapa yang bisa saya hubungi untuk masalah HR?", "HR Contact - Indonesian"),
        ("What is the employee handbook?", "Employee Handbook - English")
    ]
    
    print("Starting Comprehensive Chatbot Fallback System Test")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(test_queries)
    
    for query, test_name in test_queries:
        success = test_chatbot_query(client, query, test_name)
        if success:
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY:")
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_tests - success_count}")
    print(f"Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count == total_tests:
        print("\n✅ ALL TESTS PASSED! Chatbot fallback system is working properly.")
    else:
        print(f"\n⚠️  {total_tests - success_count} tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()