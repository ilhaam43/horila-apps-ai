#!/usr/bin/env python3
"""
Script untuk memverifikasi dan memperbaiki masalah password admin
Jalankan dengan: python3 manage.py shell < verify_password_change.py
"""

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.conf import settings

def verify_current_password_status():
    """Verify current password status in database"""
    print("=== Verifying Current Password Status ===")
    
    try:
        admin_user = User.objects.get(username='admin')
        print(f"Admin user found: {admin_user.username}")
        print(f"Email: {admin_user.email}")
        print(f"Is active: {admin_user.is_active}")
        print(f"Is staff: {admin_user.is_staff}")
        print(f"Is superuser: {admin_user.is_superuser}")
        print(f"Password hash: {admin_user.password[:50]}...")
        
        # Test both passwords
        print("\n=== Testing Password Authentication ===")
        
        # Test new password
        new_auth = authenticate(username='admin', password='Lagisenang1')
        print(f"New password (Lagisenang1): {'✓ SUCCESS' if new_auth else '✗ FAILED'}")
        
        # Test old password
        old_auth = authenticate(username='admin', password='admin123')
        print(f"Old password (admin123): {'✗ FAILED' if not old_auth else '✓ SUCCESS (PROBLEM!)'}")
        
        # Direct password check
        print("\n=== Direct Password Hash Check ===")
        new_check = check_password('Lagisenang1', admin_user.password)
        old_check = check_password('admin123', admin_user.password)
        
        print(f"New password hash check: {'✓ MATCH' if new_check else '✗ NO MATCH'}")
        print(f"Old password hash check: {'✗ NO MATCH' if not old_check else '✓ MATCH (PROBLEM!)'}")
        
        return admin_user, new_auth, old_auth
        
    except User.DoesNotExist:
        print("✗ Admin user not found!")
        return None, None, None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None, None, None

def force_password_change():
    """Force password change to new password only"""
    print("\n=== Forcing Password Change ===")
    
    try:
        admin_user = User.objects.get(username='admin')
        
        # Generate new password hash
        new_password_hash = make_password('Lagisenang1')
        print(f"New password hash generated: {new_password_hash[:50]}...")
        
        # Update password
        admin_user.password = new_password_hash
        admin_user.save()
        
        print("✓ Password updated in database")
        
        # Verify the change
        admin_user.refresh_from_db()
        
        # Test authentication again
        print("\n=== Verifying After Force Change ===")
        
        new_auth = authenticate(username='admin', password='Lagisenang1')
        old_auth = authenticate(username='admin', password='admin123')
        
        print(f"New password (Lagisenang1): {'✓ SUCCESS' if new_auth else '✗ FAILED'}")
        print(f"Old password (admin123): {'✓ PROPERLY REJECTED' if not old_auth else '✗ STILL WORKS (PROBLEM!)'}")
        
        return new_auth and not old_auth
        
    except Exception as e:
        print(f"✗ Error during force change: {e}")
        return False

def check_multiple_admin_users():
    """Check if there are multiple admin users"""
    print("\n=== Checking for Multiple Admin Users ===")
    
    try:
        # Check for users with username 'admin'
        admin_users = User.objects.filter(username='admin')
        print(f"Users with username 'admin': {admin_users.count()}")
        
        for i, user in enumerate(admin_users):
            print(f"  {i+1}. ID: {user.id}, Username: {user.username}, Email: {user.email}")
            print(f"     Password hash: {user.password[:50]}...")
        
        # Check for superusers
        superusers = User.objects.filter(is_superuser=True)
        print(f"\nTotal superusers: {superusers.count()}")
        
        for i, user in enumerate(superusers):
            print(f"  {i+1}. ID: {user.id}, Username: {user.username}, Email: {user.email}")
            
            # Test both passwords for each superuser
            new_auth = authenticate(username=user.username, password='Lagisenang1')
            old_auth = authenticate(username=user.username, password='admin123')
            
            print(f"     New password: {'✓' if new_auth else '✗'}")
            print(f"     Old password: {'✓' if old_auth else '✗'}")
        
        return admin_users.count(), superusers.count()
        
    except Exception as e:
        print(f"✗ Error checking users: {e}")
        return 0, 0

def check_session_issues():
    """Check for potential session-related issues"""
    print("\n=== Checking Session Configuration ===")
    
    print(f"SESSION_ENGINE: {getattr(settings, 'SESSION_ENGINE', 'Not set')}")
    print(f"SESSION_COOKIE_AGE: {getattr(settings, 'SESSION_COOKIE_AGE', 'Not set')}")
    print(f"SESSION_SAVE_EVERY_REQUEST: {getattr(settings, 'SESSION_SAVE_EVERY_REQUEST', 'Not set')}")
    print(f"SESSION_EXPIRE_AT_BROWSER_CLOSE: {getattr(settings, 'SESSION_EXPIRE_AT_BROWSER_CLOSE', 'Not set')}")
    
    # Check if there are custom authentication backends
    auth_backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
    print(f"\nAuthentication backends ({len(auth_backends)}):")
    for i, backend in enumerate(auth_backends):
        print(f"  {i+1}. {backend}")

# Main execution
print("Password Change Verification and Fix")
print("=" * 50)

# Step 1: Verify current status
admin_user, new_auth, old_auth = verify_current_password_status()

if not admin_user:
    print("Cannot proceed - admin user not found")
else:
    # Step 2: Check for multiple users
    admin_count, super_count = check_multiple_admin_users()
    
    # Step 3: Check session configuration
    check_session_issues()
    
    # Step 4: If old password still works, force change
    if old_auth:
        print("\n⚠️  Old password still works - forcing password change...")
        success = force_password_change()
        
        if success:
            print("\n🎉 SUCCESS: Password change completed successfully!")
            print("   - New password (Lagisenang1) works")
            print("   - Old password (admin123) is now rejected")
        else:
            print("\n❌ FAILED: Could not complete password change")
    else:
        print("\n✓ Password change appears to be working correctly")
    
    print("\n" + "=" * 50)
    print("Verification complete.")