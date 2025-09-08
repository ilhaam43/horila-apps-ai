#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_reports_page():
    """Test budget reports page"""
    client = Client(SERVER_NAME='localhost')
    
    # Get or create admin user
    try:
        user = User.objects.get(username='admin')
        print(f"Using existing user: {user.username}")
    except User.DoesNotExist:
        user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print(f"Created new superuser: {user.username}")
    
    # Login
    login_success = client.login(username='admin', password='admin123')
    print(f"Login successful: {login_success}")
    
    if not login_success:
        print("❌ Login failed")
        return False
    
    # Test budget reports page
    try:
        response = client.get('/budget/reports/')
        print(f"✅ /budget/reports/: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Error: {response.content.decode()[:500]}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == '__main__':
    success = test_reports_page()
    sys.exit(0 if success else 1)