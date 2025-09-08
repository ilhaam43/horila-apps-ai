#!/usr/bin/env python
"""
POC Server Runner
Script untuk menjalankan server POC dengan konfigurasi minimal
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.core.management.commands.runserver import Command as RunServerCommand

def setup_poc_environment():
    """Setup environment variables for POC"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings_poc')
    
    # Disable debug logging
    os.environ['DJANGO_LOG_LEVEL'] = 'ERROR'
    os.environ['DEBUG'] = 'True'  # Keep True for POC but with minimal logging
    
    # Setup Django
    django.setup()

def create_poc_database():
    """Create and migrate POC database"""
    print("Setting up POC database...")
    
    # Run migrations
    execute_from_command_line(['manage.py', 'migrate', '--run-syncdb'])
    
    print("POC database setup complete.")

def create_superuser():
    """Create superuser for POC if it doesn't exist"""
    from django.contrib.auth.models import User
    
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@poc.local',
                password='admin123'
            )
            print("Superuser created: admin/admin123")
        else:
            print("Superuser already exists")
    except Exception as e:
        print(f"Error creating superuser: {e}")

def run_poc_server():
    """Run the POC server"""
    print("\n" + "="*50)
    print("🚀 Starting POC Server")
    print("="*50)
    print("Server will be available at: http://127.0.0.1:8000")
    print("Admin interface: http://127.0.0.1:8000/admin/")
    print("Health check: http://127.0.0.1:8000/health/")
    print("API status: http://127.0.0.1:8000/api/status/")
    print("Admin credentials: admin/admin123")
    print("="*50 + "\n")
    
    # Run server
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])

def main():
    """Main function to run POC"""
    try:
        # Setup environment
        setup_poc_environment()
        
        # Create database
        create_poc_database()
        
        # Create superuser
        create_superuser()
        
        # Run server
        run_poc_server()
        
    except KeyboardInterrupt:
        print("\n\n🛑 POC Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error running POC server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()