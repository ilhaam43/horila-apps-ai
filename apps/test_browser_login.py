#!/usr/bin/env python3
"""
Test script untuk menguji login melalui browser dengan selenium atau requests
"""

import requests
from bs4 import BeautifulSoup
import time

def test_complete_login_flow():
    """Test complete login flow with both passwords"""
    print("=== Testing Complete Login Flow ===")
    
    base_url = 'http://127.0.0.1:8000'
    
    # Test with new password
    print("\n1. Testing with NEW password (Lagisenang1):")
    success_new = test_login_with_password(base_url, 'admin', 'Lagisenang1')
    
    # Test with old password
    print("\n2. Testing with OLD password (admin123):")
    success_old = test_login_with_password(base_url, 'admin', 'admin123')
    
    print("\n=== Summary ===")
    print(f"New password (Lagisenang1): {'✓ SUCCESS' if success_new else '✗ FAILED'}")
    print(f"Old password (admin123): {'✗ FAILED' if not success_old else '✓ SUCCESS (unexpected)'}")
    
    if success_new and not success_old:
        print("\n🎉 INTEGRATION FIXED! Password change is working correctly.")
        return True
    elif success_new and success_old:
        print("\n⚠️  Both passwords work - old password not properly invalidated")
        return False
    elif not success_new and success_old:
        print("\n❌ New password doesn't work, old password still works")
        return False
    else:
        print("\n❌ Neither password works - authentication broken")
        return False

def test_login_with_password(base_url, username, password):
    """Test login with specific password"""
    session = requests.Session()
    
    try:
        # Get login page
        login_url = f'{base_url}/login/'
        response = session.get(login_url)
        
        if response.status_code != 200:
            print(f"  ✗ Cannot access login page: {response.status_code}")
            return False
        
        # Extract CSRF token
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            print("  ✗ Cannot find CSRF token")
            return False
        
        csrf_value = csrf_token.get('value')
        
        # Attempt login
        login_data = {
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': csrf_value
        }
        
        response = session.post(login_url, data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            # Login successful - check redirect
            redirect_url = response.headers.get('Location', '')
            print(f"  ✓ Login successful - redirected to: {redirect_url}")
            
            # Verify we can access protected content
            if redirect_url.startswith('/'):
                full_redirect_url = f'{base_url}{redirect_url}'
            else:
                full_redirect_url = redirect_url
            
            response = session.get(full_redirect_url)
            if response.status_code == 200:
                print(f"  ✓ Dashboard accessible: {response.status_code}")
                
                # Test budget module access
                budget_url = f'{base_url}/budget/'
                response = session.get(budget_url)
                if response.status_code == 200:
                    print(f"  ✓ Budget module accessible: {response.status_code}")
                    return True
                else:
                    print(f"  ⚠️  Budget module not accessible: {response.status_code}")
                    return True  # Login still successful
            else:
                print(f"  ✗ Dashboard not accessible: {response.status_code}")
                return False
                
        elif response.status_code == 200:
            # Login failed - stayed on login page
            print("  ✗ Login failed - stayed on login page")
            
            # Check for error messages
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for various error message containers
            error_selectors = [
                '.alert',
                '.error',
                '.message',
                '.oh-alert',
                '[class*="alert"]',
                '[class*="error"]',
                '[class*="message"]'
            ]
            
            for selector in error_selectors:
                error_msgs = soup.select(selector)
                for msg in error_msgs:
                    text = msg.get_text().strip()
                    if text and len(text) > 0:
                        print(f"  Error: {text}")
            
            return False
        else:
            print(f"  ✗ Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ✗ Cannot connect to server - make sure it's running")
        return False
    except Exception as e:
        print(f"  ✗ Error during login test: {e}")
        return False

def test_budget_module_direct():
    """Test direct access to budget module after login"""
    print("\n=== Testing Budget Module Access ===")
    
    base_url = 'http://127.0.0.1:8000'
    session = requests.Session()
    
    # Login first
    login_url = f'{base_url}/login/'
    response = session.get(login_url)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if csrf_token:
            csrf_value = csrf_token.get('value')
            
            login_data = {
                'username': 'admin',
                'password': 'Lagisenang1',
                'csrfmiddlewaretoken': csrf_value
            }
            
            response = session.post(login_url, data=login_data)
            
            if response.status_code == 200 and 'login' not in response.url:
                print("✓ Login successful")
                
                # Test budget module
                budget_url = f'{base_url}/budget/'
                response = session.get(budget_url)
                print(f"Budget module status: {response.status_code}")
                
                if response.status_code == 200:
                    print("✓ Budget module accessible with new password")
                    return True
                else:
                    print(f"✗ Budget module not accessible: {response.status_code}")
                    return False
            else:
                print("✗ Login failed")
                return False
    
    return False

if __name__ == '__main__':
    print("Testing Browser Login Integration")
    print("=" * 50)
    
    # Test complete flow
    integration_fixed = test_complete_login_flow()
    
    # Test budget module specifically
    budget_accessible = test_budget_module_direct()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    print(f"Integration Status: {'✅ FIXED' if integration_fixed else '❌ BROKEN'}")
    print(f"Budget Module: {'✅ ACCESSIBLE' if budget_accessible else '❌ NOT ACCESSIBLE'}")
    
    if integration_fixed and budget_accessible:
        print("\n🎉 SUCCESS: Password change integration is working correctly!")
        print("   - New password (Lagisenang1) works")
        print("   - Old password (admin123) is rejected")
        print("   - Budget module is accessible")
    else:
        print("\n❌ Issues still exist with the integration")