#!/usr/bin/env python3
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_login_flow():
    print("Testing login flow...")
    
    # Test with Django test client
    client = Client()
    
    try:
        # Get login page
        login_response = client.get('/login/')
        print(f"Login page status: {login_response.status_code}")
        
        # Try to login
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        # Get CSRF token from login page
        csrf_token = None
        if hasattr(login_response, 'context') and login_response.context and 'csrfmiddlewaretoken' in login_response.context:
            csrf_token = login_response.context['csrfmiddlewaretoken']
        elif hasattr(login_response, 'cookies') and 'csrftoken' in login_response.cookies:
            csrf_token = login_response.cookies['csrftoken'].value
        
        # Extract CSRF token from HTML content if not found in context
        if not csrf_token and hasattr(login_response, 'content'):
            import re
            content = login_response.content.decode('utf-8')
            csrf_match = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', content)
            if csrf_match:
                csrf_token = csrf_match.group(1)
        
        if csrf_token:
            login_data['csrfmiddlewaretoken'] = csrf_token
            
        post_response = client.post('/login/', login_data, follow=True)
        print(f"Login POST status: {post_response.status_code}")
        print(f"Final URL after login: {post_response.request['PATH_INFO']}")
        
        # Check if user is authenticated
        if hasattr(post_response, 'wsgi_request') and post_response.wsgi_request.user.is_authenticated:
            print("✓ User is authenticated after login")
        else:
            print("✗ User is not authenticated after login")
            
        # Try to access home page
        home_response = client.get('/', follow=True)
        print(f"Home page status: {home_response.status_code}")
        print(f"Home page final URL: {home_response.request['PATH_INFO']}")
        
        # Check if redirected to login
        if '/login/' in home_response.request['PATH_INFO']:
            print("✗ Still redirected to login page")
        else:
            print("✓ Successfully accessed home page")
            
    except Exception as e:
        print(f"Error during login test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_login_flow()