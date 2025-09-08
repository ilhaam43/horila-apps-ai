#!/usr/bin/env python3
import os
import sys
import django
import requests
from requests.auth import HTTPBasicAuth

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth import authenticate
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

def test_authentication_integration():
    print("=== Testing Authentication Integration ===")
    
    # Test 1: Direct Django authentication
    print("\n1. Testing Django Authentication:")
    user = authenticate(username='admin', password='Lagisenang1')
    print(f"   ✅ Django auth successful: {user is not None}")
    
    # Test 2: Django test client login
    print("\n2. Testing Django Test Client Login:")
    client = Client()
    login_success = client.login(username='admin', password='Lagisenang1')
    print(f"   ✅ Test client login successful: {login_success}")
    
    # Test 3: Try to access budget views
    print("\n3. Testing Budget Module Access:")
    try:
        # Try to access budget dashboard
        response = client.get('/budget/')
        print(f"   Budget dashboard status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Budget dashboard accessible")
        elif response.status_code == 302:
            print(f"   ↗️  Redirected to: {response.get('Location', 'unknown')}")
        else:
            print(f"   ❌ Budget dashboard error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Budget access error: {e}")
    
    # Test 4: API Authentication
    print("\n4. Testing API Authentication:")
    try:
        # Test API login endpoint
        api_data = {
            'username': 'admin',
            'password': 'Lagisenang1'
        }
        api_response = client.post('/api/auth/login/', data=api_data, content_type='application/json')
        print(f"   API login status: {api_response.status_code}")
        if api_response.status_code == 200:
            print("   ✅ API authentication successful")
        else:
            print(f"   ❌ API authentication failed: {api_response.status_code}")
    except Exception as e:
        print(f"   ❌ API test error: {e}")
    
    # Test 5: Session persistence
    print("\n5. Testing Session Persistence:")
    try:
        # Make another request to see if session persists
        response2 = client.get('/budget/')
        print(f"   Second request status: {response2.status_code}")
        if response2.status_code == 200:
            print("   ✅ Session persists correctly")
        else:
            print(f"   ⚠️  Session issue: {response2.status_code}")
    except Exception as e:
        print(f"   ❌ Session test error: {e}")
    
    # Test 6: Old password should fail
    print("\n6. Testing Old Password Rejection:")
    old_user = authenticate(username='admin', password='admin123')
    print(f"   ❌ Old password rejected: {old_user is None}")
    
    print("\n=== Integration Test Complete ===")

if __name__ == '__main__':
    test_authentication_integration()