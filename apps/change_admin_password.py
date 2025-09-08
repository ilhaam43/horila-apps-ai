#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def change_admin_password():
    try:
        # Get admin user
        admin_user = User.objects.get(username='admin')
        print(f'Found admin user: {admin_user.username}')
        
        # Test current password
        current_auth = authenticate(username='admin', password='admin123')
        print(f'Current authentication with admin123: {current_auth is not None}')
        
        # Change password to new one
        admin_user.set_password('Lagisenang1')
        admin_user.save()
        print('Password changed successfully to: Lagisenang1')
        
        # Test new password
        new_auth = authenticate(username='admin', password='Lagisenang1')
        print(f'New authentication with Lagisenang1: {new_auth is not None}')
        
        # Test old password should fail now
        old_auth = authenticate(username='admin', password='admin123')
        print(f'Old authentication with admin123: {old_auth is not None}')
        
        if new_auth and not old_auth:
            print('\n✅ Password change successful!')
            print('✅ New password works')
            print('✅ Old password no longer works')
        else:
            print('\n❌ Password change failed!')
            
    except User.DoesNotExist:
        print('❌ Admin user not found!')
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    change_admin_password()