#!/usr/bin/env python3
import os
import sys
import django

# Add the project directory to Python path
sys.path.insert(0, '/Users/haryanto.bonti/apps')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from budget.models import FinancialReport

def test_budget_reports():
    """Test budget reports page with admin user"""
    client = Client(SERVER_NAME='localhost')
    
    # Get or create admin user
    try:
        admin_user = User.objects.get(username='admin')
        print(f"Found admin user: {admin_user.username}")
    except User.DoesNotExist:
        print("Admin user not found, creating one...")
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print(f"Created admin user: {admin_user.username}")
    
    # Login as admin
    login_success = client.login(username='admin', password='admin123')
    print(f"Login successful: {login_success}")
    
    if not login_success:
        print("Failed to login, trying to set password...")
        admin_user.set_password('admin123')
        admin_user.save()
        login_success = client.login(username='admin', password='admin123')
        print(f"Login after password reset: {login_success}")
    
    # Test budget reports page
    print("\nTesting /budget/reports/ page...")
    response = client.get('/budget/reports/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Budget reports page loaded successfully!")
        print(f"Template used: {response.templates[0].name if response.templates else 'Unknown'}")
        
        # Check if context data is available
        if hasattr(response, 'context') and response.context:
            reports = response.context.get('reports', [])
            print(f"Number of reports found: {len(list(reports)) if reports else 0}")
            
            # Check context data
            context_keys = list(response.context.keys()) if response.context else []
            print(f"Context keys: {context_keys}")
        
    elif response.status_code == 302:
        print(f"Redirected to: {response.url}")
    else:
        print(f"❌ Error: Status code {response.status_code}")
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8')[:500]
            print(f"Response content (first 500 chars): {content}")
    
    # Test other budget pages
    test_pages = [
        '/budget/',
        '/budget/plans/',
        '/budget/expenses/',
        '/budget/categories/',
    ]
    
    print("\nTesting other budget pages...")
    for page in test_pages:
        try:
            response = client.get(page)
            status = "✅" if response.status_code == 200 else "⚠️" if response.status_code == 302 else "❌"
            print(f"{status} {page}: {response.status_code}")
        except Exception as e:
            print(f"❌ {page}: Error - {str(e)}")

if __name__ == '__main__':
    test_budget_reports()