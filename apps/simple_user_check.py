#!/usr/bin/env python3
"""
Simple script to check user details without debug output
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

# Disable debug logging
import logging
logging.disable(logging.DEBUG)

from django.contrib.auth.models import User
from employee.models import Employee
from django.contrib.auth import authenticate

def main():
    print("=== User and Employee Check ===")
    
    try:
        # Get admin user
        admin_user = User.objects.get(username='admin')
        print(f"\nAdmin User Details:")
        print(f"  Username: {admin_user.username}")
        print(f"  Email: {admin_user.email}")
        print(f"  Active: {admin_user.is_active}")
        print(f"  Staff: {admin_user.is_staff}")
        print(f"  Superuser: {admin_user.is_superuser}")
        print(f"  Last login: {admin_user.last_login}")
        
        # Check for is_new_employee attribute
        if hasattr(admin_user, 'is_new_employee'):
            print(f"  is_new_employee: {admin_user.is_new_employee}")
        else:
            print(f"  is_new_employee: Not found")
            
        # Check Employee model
        try:
            employee = Employee.objects.get(employee_user_id=admin_user)
            print(f"\nEmployee Details:")
            print(f"  ID: {employee.id}")
            print(f"  Badge ID: {employee.badge_id}")
            print(f"  Phone: {employee.phone}")
            print(f"  Is active: {employee.is_active}")
            print(f"  First name: {employee.employee_first_name}")
            print(f"  Last name: {employee.employee_last_name}")
            
        except Employee.DoesNotExist:
            print(f"\nNo Employee record found for admin user")
            
        # Test authentication
        print(f"\n=== Authentication Tests ===")
        
        # Test new password
        auth_new = authenticate(username='admin', password='Lagisenang1')
        print(f"New password (Lagisenang1): {'SUCCESS' if auth_new else 'FAILED'}")
        
        # Test old password
        auth_old = authenticate(username='admin', password='admin123')
        print(f"Old password (admin123): {'SUCCESS' if auth_old else 'FAILED'}")
        
        # Check multiple users
        print(f"\n=== User Count Check ===")
        admin_users = User.objects.filter(username__icontains='admin')
        print(f"Users with 'admin' in username: {admin_users.count()}")
        for user in admin_users:
            print(f"  - {user.username} (ID: {user.id}, Active: {user.is_active})")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()