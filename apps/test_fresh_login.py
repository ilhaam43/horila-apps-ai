#!/usr/bin/env python3
"""
Test login dengan session bersih untuk memastikan tidak ada cache
"""

import requests
import re
from bs4 import BeautifulSoup

def test_fresh_login():
    base_url = 'http://localhost:8000'
    
    print("=== Testing Fresh Login (No Cache/Session) ===")
    
    # Test dengan password baru
    print("\n1. Testing with NEW password (Lagisenang1)")
    session_new = requests.Session()  # Fresh session
    
    try:
        # Get login page
        login_response = session_new.get(f'{base_url}/login/')
        print(f"   Login page status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            # Parse CSRF token
            soup = BeautifulSoup(login_response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
            print(f"   CSRF token obtained: {csrf_token[:20]}...")
            
            # Attempt login with new password
            login_data = {
                'username': 'admin',
                'password': 'Lagisenang1',
                'csrfmiddlewaretoken': csrf_token
            }
            
            login_post = session_new.post(
                f'{base_url}/login/',
                data=login_data,
                headers={'Referer': f'{base_url}/login/'},
                allow_redirects=False
            )
            
            print(f"   Login POST status: {login_post.status_code}")
            
            if login_post.status_code == 302:
                print(f"   Redirect location: {login_post.headers.get('Location', 'None')}")
                
                # Follow redirect to check if we're logged in
                dashboard_response = session_new.get(f'{base_url}/')
                print(f"   Dashboard access status: {dashboard_response.status_code}")
                
                if 'login' not in dashboard_response.url.lower():
                    print("   ✅ NEW PASSWORD LOGIN: SUCCESS")
                else:
                    print("   ❌ NEW PASSWORD LOGIN: FAILED (redirected to login)")
            else:
                print("   ❌ NEW PASSWORD LOGIN: FAILED (no redirect)")
                
    except Exception as e:
        print(f"   ❌ NEW PASSWORD LOGIN: ERROR - {e}")
    
    # Test dengan password lama
    print("\n2. Testing with OLD password (admin123)")
    session_old = requests.Session()  # Fresh session
    
    try:
        # Get login page
        login_response = session_old.get(f'{base_url}/login/')
        print(f"   Login page status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            # Parse CSRF token
            soup = BeautifulSoup(login_response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
            print(f"   CSRF token obtained: {csrf_token[:20]}...")
            
            # Attempt login with old password
            login_data = {
                'username': 'admin',
                'password': 'admin123',
                'csrfmiddlewaretoken': csrf_token
            }
            
            login_post = session_old.post(
                f'{base_url}/login/',
                data=login_data,
                headers={'Referer': f'{base_url}/login/'},
                allow_redirects=False
            )
            
            print(f"   Login POST status: {login_post.status_code}")
            
            if login_post.status_code == 302:
                print(f"   Redirect location: {login_post.headers.get('Location', 'None')}")
                
                # Follow redirect to check if we're logged in
                dashboard_response = session_old.get(f'{base_url}/')
                print(f"   Dashboard access status: {dashboard_response.status_code}")
                
                if 'login' not in dashboard_response.url.lower():
                    print("   ❌ OLD PASSWORD LOGIN: SUCCESS (This should NOT happen!)")
                else:
                    print("   ✅ OLD PASSWORD LOGIN: FAILED (correctly rejected)")
            else:
                print("   ✅ OLD PASSWORD LOGIN: FAILED (no redirect - correctly rejected)")
                
    except Exception as e:
        print(f"   ❌ OLD PASSWORD LOGIN: ERROR - {e}")
    
    # Test akses budget module dengan session yang berhasil login
    if 'session_new' in locals():
        print("\n3. Testing Budget Module Access (with new password session)")
        try:
            budget_response = session_new.get(f'{base_url}/budget/')
            print(f"   Budget module status: {budget_response.status_code}")
            
            if budget_response.status_code == 200 and 'login' not in budget_response.url.lower():
                print("   ✅ Budget module accessible")
            else:
                print("   ❌ Budget module not accessible")
                
        except Exception as e:
            print(f"   ❌ Budget module test: ERROR - {e}")
    
    print("\n=== Test Complete ===")

if __name__ == '__main__':
    test_fresh_login()