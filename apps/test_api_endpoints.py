#!/usr/bin/env python3
"""
Test script to verify budget API endpoints functionality
"""

import os
import sys
import django
import requests
from django.test import Client
from django.contrib.auth import authenticate

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

def test_budget_api_endpoints():
    print("Testing Budget API Endpoints...")
    
    # Create a test client
    client = Client()
    
    # Login as admin user
    login_success = client.login(username='admin', password='admin123')
    if not login_success:
        print("❌ Failed to login as admin user")
        return False
    
    print("✅ Successfully logged in as admin")
    
    # Test budget plans endpoint
    print("\nTesting /api/budget/plans/ endpoint...")
    try:
        response = client.get('/api/budget/plans/')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Budget plans endpoint working")
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"❌ Budget plans endpoint failed: {response.content}")
    except Exception as e:
        print(f"❌ Error testing budget plans: {e}")
    
    # Test expenses endpoint
    print("\nTesting /api/budget/expenses/ endpoint...")
    try:
        response = client.get('/api/budget/expenses/')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Expenses endpoint working")
            data = response.json()
            print(f"Response: {data}")
        else:
            print(f"❌ Expenses endpoint failed: {response.content}")
    except Exception as e:
        print(f"❌ Error testing expenses: {e}")
    
    # Test dashboard endpoint
    print("\nTesting /api/budget/dashboard/ endpoint...")
    try:
        response = client.get('/api/budget/dashboard/')
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ Dashboard endpoint working")
            data = response.json()
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        else:
            print(f"❌ Dashboard endpoint failed: {response.content}")
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
    
    print("\n" + "="*50)
    print("API Endpoint Testing Complete")
    print("="*50)

if __name__ == '__main__':
    test_budget_api_endpoints()