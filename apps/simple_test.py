#!/usr/bin/env python3
"""
Simple test untuk endpoint AI
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
import json

def main():
    client = Client()
    
    # Create test user
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    # Login
    client.force_login(user)
    
    print("=== AI ENDPOINT TESTS ===")
    
    # Test system health
    response = client.get('/api/ai/system/health/')
    print(f"System Health: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.content.decode()}")
    
    print("\n" + "="*30)
    
    # Test performance stats
    response = client.get('/api/ai/performance/stats/')
    print(f"Performance Stats: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.content.decode()}")
    
    print("\n" + "="*30)
    
    # Test monitoring status
    response = client.get('/api/ai/monitoring/status/')
    print(f"Monitoring Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.content.decode()}")
    
    print("\n" + "="*30)
    
    # Test performance optimization
    response = client.post('/api/ai/performance/optimize/')
    print(f"Performance Optimize: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {response.json()}")
    else:
        print(f"Error: {response.content.decode()}")

if __name__ == '__main__':
    main()