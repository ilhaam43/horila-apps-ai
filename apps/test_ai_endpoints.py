#!/usr/bin/env python3
"""
Script untuk menguji semua endpoint AI services
"""

import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse

def test_ai_endpoints():
    """
    Test all AI service endpoints
    """
    client = Client()
    
    # Create or get test user
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
    
    # Test endpoints
    endpoints = [
        ('/api/ai/system/health/', 'GET', 'System Health'),
        ('/api/ai/performance/stats/', 'GET', 'Performance Stats'),
        ('/api/ai/monitoring/status/', 'GET', 'Monitoring Status'),
        ('/api/ai/health/', 'GET', 'AI Health Check'),
        ('/api/ai/status/', 'GET', 'AI Service Status'),
    ]
    
    print("=== TESTING AI ENDPOINTS ===")
    print(f"Testing with user: {user.username}")
    print("=" * 50)
    
    for url, method, name in endpoints:
        try:
            if method == 'GET':
                response = client.get(url)
            elif method == 'POST':
                response = client.post(url, content_type='application/json')
            
            print(f"\n{name}:")
            print(f"  URL: {url}")
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"  Response: {response.content.decode()[:200]}...")
            else:
                print(f"  Error: {response.content.decode()[:200]}")
                
        except Exception as e:
            print(f"\n{name}: ERROR - {str(e)}")
    
    print("\n=== TESTING PERFORMANCE OPTIMIZATION ===")
    
    # Test performance optimization endpoint
    try:
        response = client.post('/api/ai/performance/optimize/', 
                             content_type='application/json')
        print(f"\nPerformance Optimization:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
        else:
            print(f"  Error: {response.content.decode()}")
    except Exception as e:
        print(f"Performance Optimization: ERROR - {str(e)}")
    
    print("\n=== TESTING MONITORING CONTROLS ===")
    
    # Test start monitoring
    try:
        response = client.post('/api/ai/monitoring/start/', 
                             json.dumps({'interval': 30}),
                             content_type='application/json')
        print(f"\nStart Monitoring:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
        else:
            print(f"  Error: {response.content.decode()}")
    except Exception as e:
        print(f"Start Monitoring: ERROR - {str(e)}")
    
    # Test stop monitoring
    try:
        response = client.post('/api/ai/monitoring/stop/', 
                             content_type='application/json')
        print(f"\nStop Monitoring:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)}")
        else:
            print(f"  Error: {response.content.decode()}")
    except Exception as e:
        print(f"Stop Monitoring: ERROR - {str(e)}")
    
    print("\n=== TESTING BOTTLENECK ANALYSIS ===")
    
    # Test bottleneck analysis
    try:
        response = client.get('/api/ai/analysis/bottlenecks/')
        print(f"\nBottleneck Analysis:")
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Response: {json.dumps(data, indent=2)[:300]}...")
        else:
            print(f"  Error: {response.content.decode()}")
    except Exception as e:
        print(f"Bottleneck Analysis: ERROR - {str(e)}")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == '__main__':
    test_ai_endpoints()