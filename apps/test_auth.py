#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

# Test authentication
print("Testing authentication for admin user...")
user = authenticate(username='admin', password='admin123')
print(f'Authentication result: {user}')
print(f'User authenticated: {user is not None}')

if user:
    print(f'User details:')
    print(f'  Username: {user.username}')
    print(f'  Email: {user.email}')
    print(f'  Active: {user.is_active}')
    print(f'  Staff: {user.is_staff}')
    print(f'  Superuser: {user.is_superuser}')
else:
    print('Authentication failed!')
    # Check if user exists
    try:
        user_obj = User.objects.get(username='admin')
        print(f'User exists but authentication failed:')
        print(f'  Username: {user_obj.username}')
        print(f'  Active: {user_obj.is_active}')
        print(f'  Has usable password: {user_obj.has_usable_password()}')
    except User.DoesNotExist:
        print('User does not exist!')