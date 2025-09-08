#!/usr/bin/env python3
import os
import sys
import django
import requests

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

# Import Django models after setup
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

print("Testing Budget Dashboard API Endpoints")
print("=" * 50)

# Test direct access to dashboard endpoint
base_url = "http://127.0.0.1:8000"

# Create a session for testing
session = requests.Session()

# First, get CSRF token
print("\n1. Getting CSRF token...")
csrf_response = session.get(f"{base_url}/admin/login/")
if csrf_response.status_code == 200:
    csrf_token = session.cookies.get('csrftoken')
    print(f"CSRF token obtained: {csrf_token[:20]}...")
else:
    print(f"Failed to get CSRF token: {csrf_response.status_code}")
    sys.exit(1)

# Login via admin interface
print("\n2. Logging in as admin...")
login_data = {
    'username': 'admin',
    'password': 'admin123',
    'csrfmiddlewaretoken': csrf_token,
    'next': '/admin/'
}

login_response = session.post(f"{base_url}/admin/login/", data=login_data)
print(f"Login response status: {login_response.status_code}")
print(f"Login response URL: {login_response.url}")

if 'admin' in login_response.url:
    print("✓ Login successful")
else:
    print("✗ Login failed")
    print(f"Response content: {login_response.text[:500]}")
    sys.exit(1)

# Test dashboard endpoint
print("\n3. Testing dashboard endpoint...")
dashboard_response = session.get(f"{base_url}/api/budget/dashboard/")
print(f"Dashboard response status: {dashboard_response.status_code}")
print(f"Dashboard response headers: {dict(dashboard_response.headers)}")

if dashboard_response.status_code == 200:
    print("✓ Dashboard endpoint accessible")
    try:
        data = dashboard_response.json()
        print(f"Dashboard data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
    except:
        print("Response is not JSON")
        print(f"Response content: {dashboard_response.text[:500]}")
else:
    print("✗ Dashboard endpoint failed")
    print(f"Response content: {dashboard_response.text[:500]}")

# Test budget plans endpoint
print("\n4. Testing budget plans endpoint...")
plans_response = session.get(f"{base_url}/api/budget/plans/")
print(f"Plans response status: {plans_response.status_code}")

if plans_response.status_code == 200:
    print("✓ Budget plans endpoint accessible")
    try:
        data = plans_response.json()
        print(f"Plans data: {data}")
    except:
        print("Response is not JSON")
        print(f"Response content: {plans_response.text[:500]}")
else:
    print("✗ Budget plans endpoint failed")
    print(f"Response content: {plans_response.text[:500]}")

# Test expenses endpoint
print("\n5. Testing expenses endpoint...")
expenses_response = session.get(f"{base_url}/api/budget/expenses/")
print(f"Expenses response status: {expenses_response.status_code}")

if expenses_response.status_code == 200:
    print("✓ Expenses endpoint accessible")
    try:
        data = expenses_response.json()
        print(f"Expenses data: {data}")
    except:
        print("Response is not JSON")
        print(f"Response content: {expenses_response.text[:500]}")
else:
    print("✗ Expenses endpoint failed")
    print(f"Response content: {expenses_response.text[:500]}")

print("\n" + "=" * 50)
print("API Testing Complete")
print("=" * 50)