#!/usr/bin/env python3
import requests
import json
from requests.sessions import Session

def test_live_server_auth():
    print("=== Testing Live Server Authentication ===")
    
    base_url = "http://localhost:8000"
    session = Session()
    
    # Test 1: Get login page and CSRF token
    print("\n1. Getting login page...")
    try:
        login_page = session.get(f"{base_url}/login/")
        print(f"   Login page status: {login_page.status_code}")
        
        # Extract CSRF token
        csrf_token = None
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
            print(f"   ✅ CSRF token obtained: {csrf_token[:20]}...")
        else:
            print("   ⚠️  No CSRF token found")
            
    except Exception as e:
        print(f"   ❌ Error getting login page: {e}")
        return
    
    # Test 2: Login with new password
    print("\n2. Testing login with new password (Lagisenang1)...")
    try:
        login_data = {
            'username': 'admin',
            'password': 'Lagisenang1',
        }
        
        if csrf_token:
            login_data['csrfmiddlewaretoken'] = csrf_token
            
        headers = {
            'Referer': f"{base_url}/login/",
            'X-CSRFToken': csrf_token if csrf_token else ''
        }
        
        login_response = session.post(f"{base_url}/login/", data=login_data, headers=headers)
        print(f"   Login response status: {login_response.status_code}")
        
        if login_response.status_code == 302:
            redirect_url = login_response.headers.get('Location', '')
            print(f"   ✅ Login successful, redirected to: {redirect_url}")
        elif login_response.status_code == 200:
            if 'Invalid' in login_response.text or 'error' in login_response.text.lower():
                print("   ❌ Login failed - invalid credentials")
            else:
                print("   ✅ Login successful (stayed on same page)")
        else:
            print(f"   ❌ Unexpected login response: {login_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error during login: {e}")
        return
    
    # Test 3: Access budget module
    print("\n3. Testing budget module access...")
    try:
        budget_response = session.get(f"{base_url}/budget/")
        print(f"   Budget module status: {budget_response.status_code}")
        
        if budget_response.status_code == 200:
            print("   ✅ Budget module accessible")
            if 'Budget' in budget_response.text:
                print("   ✅ Budget content loaded")
        elif budget_response.status_code == 302:
            redirect_url = budget_response.headers.get('Location', '')
            print(f"   ↗️  Redirected to: {redirect_url}")
        else:
            print(f"   ❌ Budget module error: {budget_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accessing budget: {e}")
    
    # Test 4: Test old password should fail
    print("\n4. Testing old password rejection...")
    try:
        # Create new session for old password test
        old_session = Session()
        old_login_page = old_session.get(f"{base_url}/login/")
        old_csrf = old_session.cookies.get('csrftoken', '')
        
        old_login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrfmiddlewaretoken': old_csrf
        }
        
        old_headers = {
            'Referer': f"{base_url}/login/",
            'X-CSRFToken': old_csrf
        }
        
        old_login_response = old_session.post(f"{base_url}/login/", data=old_login_data, headers=old_headers)
        
        if old_login_response.status_code == 200 and ('Invalid' in old_login_response.text or 'error' in old_login_response.text.lower()):
            print("   ✅ Old password correctly rejected")
        elif old_login_response.status_code == 302:
            print("   ❌ Old password still works (unexpected!)")
        else:
            print(f"   ⚠️  Unclear result: {old_login_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing old password: {e}")
    
    print("\n=== Live Server Test Complete ===")

if __name__ == '__main__':
    test_live_server_auth()