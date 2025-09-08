#!/usr/bin/env python3

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

# Disable debug logging
import logging
logging.disable(logging.DEBUG)

print('=== Testing /budget/reports/ endpoint ===')

try:
    # Get admin user
    admin_user = User.objects.get(username='admin')
    print(f'✓ Admin user: {admin_user.username}')
    
    # Create test client and login
    client = Client()
    login_success = client.force_login(admin_user)
    print(f'✓ Login successful')
    
    # Try to access /budget/reports/
    print('\n--- Accessing /budget/reports/ ---')
    response = client.get('/budget/reports/')
    print(f'Status Code: {response.status_code}')
    
    if response.status_code == 500:
        print('✗ Server Error (500) occurred')
        # Try to get error details from response content
        content = response.content.decode('utf-8')
        if 'ValueError' in content:
            print('Error contains ValueError')
        if 'Cannot query' in content:
            print('Error contains "Cannot query"')
        if 'Must be "Employee" instance' in content:
            print('Error contains "Must be Employee instance"')
    elif response.status_code == 200:
        print('✓ Page loaded successfully')
    else:
        print(f'Unexpected status code: {response.status_code}')
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()