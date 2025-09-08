#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User, Group
from employee.models import Employee

# Create or get admin user
user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True
    }
)

if created:
    user.set_password('admin123')
    user.save()
    print(f'Created admin user: {user.username}')
else:
    print(f'Admin user already exists: {user.username}')

# Create budget groups if they don't exist
budget_groups = ['Budget Manager', 'Finance Team', 'Budget Viewer']
for group_name in budget_groups:
    group, created = Group.objects.get_or_create(name=group_name)
    if created:
        print(f'Created group: {group_name}')
    else:
        print(f'Group already exists: {group_name}')
    
    # Add admin user to all budget groups
    user.groups.add(group)

print('Admin user has been added to all budget groups')

# Create employee profile if it doesn't exist
try:
    employee = user.employee_get
    print(f'Employee profile already exists: {employee}')
except:
    # Create basic employee profile
    employee = Employee.objects.create(
        employee_user_id=user,
        employee_first_name='Admin',
        employee_last_name='User',
        email='admin@example.com',
        is_active=True
    )
    print(f'Created employee profile: {employee}')

print('\nSetup complete!')
print('You can now login with:')
print('Username: admin')
print('Password: admin123')