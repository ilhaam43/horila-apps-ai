#!/usr/bin/env python3
"""
Script untuk memeriksa flag pengguna yang mungkin mempengaruhi autentikasi
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from employee.models import Employee
from django.contrib.auth import authenticate

def check_user_flags():
    print("=== Checking User Flags and Employee Status ===")
    
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
        print(f"  Date joined: {admin_user.date_joined}")
        
        # Check for is_new_employee attribute
        if hasattr(admin_user, 'is_new_employee'):
            print(f"  is_new_employee: {admin_user.is_new_employee}")
        else:
            print(f"  is_new_employee: Not set (default behavior)")
            
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
            print(f"  Email: {employee.email}")
            
            # Check for any flags that might affect authentication
            for attr in dir(employee):
                if 'new' in attr.lower() or 'password' in attr.lower() or 'force' in attr.lower():
                    try:
                        value = getattr(employee, attr)
                        if not callable(value) and not attr.startswith('_'):
                            print(f"  {attr}: {value}")
                    except:
                        pass
                        
        except Employee.DoesNotExist:
            print(f"\nNo Employee record found for admin user")
            
        # Test authentication with both passwords
        print(f"\n=== Authentication Tests ===")
        
        # Test new password
        auth_new = authenticate(username='admin', password='Lagisenang1')
        print(f"Authentication with new password: {'SUCCESS' if auth_new else 'FAILED'}")
        
        # Test old password
        auth_old = authenticate(username='admin', password='admin123')
        print(f"Authentication with old password: {'SUCCESS' if auth_old else 'FAILED'}")
        
        # Check if there are multiple admin users
        print(f"\n=== Multiple Admin Check ===")
        admin_users = User.objects.filter(username__icontains='admin')
        print(f"Users with 'admin' in username: {admin_users.count()}")
        for user in admin_users:
            print(f"  - {user.username} (ID: {user.id}, Active: {user.is_active})")
            
        superusers = User.objects.filter(is_superuser=True)
        print(f"\nSuperusers: {superusers.count()}")
        for user in superusers:
            print(f"  - {user.username} (ID: {user.id}, Active: {user.is_active})")
            
    except User.DoesNotExist:
        print("Admin user not found!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_user_flags()