#!/usr/bin/env python3

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.contrib.auth import authenticate, login
from budget.views import FinancialReportViewSet
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

print('=== Testing Budget Reports ViewSet Directly ===')

try:
    # Get admin user
    admin_user = User.objects.get(username='admin')
    print(f'✓ Admin user: {admin_user.username}')
    print(f'✓ Employee: {admin_user.employee_get.get_full_name()}')
    
    # Create a request factory
    factory = APIRequestFactory()
    
    # Create a GET request to /budget/reports/
    request = factory.get('/budget/reports/')
    
    # Convert to DRF Request and set user
    drf_request = Request(request)
    drf_request.user = admin_user
    
    print('\n--- Testing FinancialReportViewSet.list() ---')
    
    # Create viewset instance
    viewset = FinancialReportViewSet()
    viewset.request = drf_request
    viewset.format_kwarg = None
    
    # Try to call list method
    try:
        response = viewset.list(drf_request)
        print(f'✓ ViewSet list() successful, status: {response.status_code}')
    except Exception as e:
        print(f'✗ Error in ViewSet list(): {e}')
        print(f'  Error type: {type(e).__name__}')
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f'✗ Setup error: {e}')
    import traceback
    traceback.print_exc()