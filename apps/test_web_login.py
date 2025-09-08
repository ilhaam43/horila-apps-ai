#!/usr/bin/env python3
"""
Test script untuk menguji login web interface dengan password baru
"""

import os
import sys
import django
import requests
from bs4 import BeautifulSoup

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

def test_direct_authentication():
    """Test direct Django authentication"""
    print("=== Testing Direct Django Authentication ===")
    
    # Test with new password
    user = authenticate(username='admin', password='Lagisenang1')
    if user:
        print("✓ Direct authentication with new password: SUCCESS")
        print(f"  User: {user.username}, Active: {user.is_active}")
    else:
        print("✗ Direct authentication with new password: FAILED")
    
    # Test with old password
    user = authenticate(username='admin', password='admin123')
    if user:
        print("✗ Direct authentication with old password: SUCCESS (should fail)")
    else:
        print("✓ Direct authentication with old password: FAILED (correct)")

def test_django_client_login():
    """Test login using Django test client"""
    print("\n=== Testing Django Test Client Login ===")
    
    client = Client()
    
    # Get login page
    login_url = reverse('login')
    response = client.get(login_url)
    print(f"Login page status: {response.status_code}")
    
    if response.status_code == 200:
        # Test login with new password
        login_data = {
            'username': 'admin',
            'password': 'Lagisenang1'
        }
        
        response = client.post(login_url, login_data, follow=True)
        print(f"Login with new password status: {response.status_code}")
        
        if response.status_code == 200:
            # Check if we're redirected to dashboard or still on login page
            if 'login' in response.request['PATH_INFO']:
                print("✗ Still on login page - login failed")
                # Check for error messages in response content
                content = response.content.decode('utf-8')
                if 'Invalid username or password' in content:
                    print("  Error: Invalid username or password")
                elif 'Access Denied' in content:
                    print("  Error: Access denied")
                else:
                    print("  Unknown error")
            else:
                print("✓ Login successful - redirected to dashboard")
                print(f"  Final URL: {response.request['PATH_INFO']}")
        
        # Test login with old password
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        client = Client()  # Fresh client
        response = client.post(login_url, login_data, follow=True)
        print(f"Login with old password status: {response.status_code}")
        
        if 'login' in response.request['PATH_INFO']:
            print("✓ Old password rejected (correct)")
        else:
            print("✗ Old password accepted (should be rejected)")

def test_live_server_login():
    """Test login to live server"""
    print("\n=== Testing Live Server Login ===")
    
    session = requests.Session()
    base_url = 'http://127.0.0.1:8000'
    
    try:
        # Get login page and CSRF token
        login_url = f'{base_url}/login/'
        response = session.get(login_url)
        print(f"Login page status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
            
            if csrf_token:
                csrf_value = csrf_token.get('value')
                print(f"CSRF token obtained: {csrf_value[:20]}...")
                
                # Test login with new password
                login_data = {
                    'username': 'admin',
                    'password': 'Lagisenang1',
                    'csrfmiddlewaretoken': csrf_value
                }
                
                response = session.post(login_url, data=login_data, allow_redirects=False)
                print(f"Login attempt status: {response.status_code}")
                
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location', '')
                    print(f"✓ Login successful - redirected to: {redirect_url}")
                    
                    # Follow redirect to verify we're logged in
                    if redirect_url.startswith('/'):
                        full_redirect_url = f'{base_url}{redirect_url}'
                    else:
                        full_redirect_url = redirect_url
                    
                    response = session.get(full_redirect_url)
                    print(f"Dashboard access status: {response.status_code}")
                    
                elif response.status_code == 200:
                    print("✗ Login failed - stayed on login page")
                    # Check for error messages
                    soup = BeautifulSoup(response.content, 'html.parser')
                    error_msgs = soup.find_all(class_=['alert', 'error', 'message'])
                    for msg in error_msgs:
                        print(f"  Error message: {msg.get_text().strip()}")
                
            else:
                print("✗ Could not find CSRF token")
        
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server - make sure it's running")
    except Exception as e:
        print(f"✗ Error during live server test: {e}")

def check_user_status():
    """Check current user status in database"""
    print("\n=== Checking User Status ===")
    
    try:
        user = User.objects.get(username='admin')
        print(f"User found: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Active: {user.is_active}")
        print(f"  Staff: {user.is_staff}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Last login: {user.last_login}")
        print(f"  Date joined: {user.date_joined}")
        
        # Check if user has employee profile
        try:
            employee = user.employee_get
            print(f"  Employee profile: {employee}")
            print(f"  Employee active: {employee.is_active}")
        except AttributeError:
            print("  No employee profile found")
        
    except User.DoesNotExist:
        print("✗ User 'admin' not found")

if __name__ == '__main__':
    print("Testing Web Login Integration")
    print("=" * 50)
    
    check_user_status()
    test_direct_authentication()
    test_django_client_login()
    test_live_server_login()
    
    print("\n=== Test Complete ===")