#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

# Test authentication with new password
print("Testing authentication for admin user with new password...")
user = authenticate(username='admin', password='Lagisenang1')
print(f'Authentication result with new password: {user}')
print(f'User authenticated with new password: {user is not None}')

# Test authentication with old password
print("\nTesting authentication for admin user with old password...")
user_old = authenticate(username='admin', password='admin123')
print(f'Authentication result with old password: {user_old}')
print(f'User authenticated with old password: {user_old is not None}')

# Check user details
try:
    user_obj = User.objects.get(username='admin')
    print(f'\nUser details:')
    print(f'  Username: {user_obj.username}')
    print(f'  Email: {user_obj.email}')
    print(f'  Active: {user_obj.is_active}')
    print(f'  Staff: {user_obj.is_staff}')
    print(f'  Superuser: {user_obj.is_superuser}')
    print(f'  Has usable password: {user_obj.has_usable_password()}')
    print(f'  Password hash: {user_obj.password[:50]}...')
except User.DoesNotExist:
    print('User does not exist!')