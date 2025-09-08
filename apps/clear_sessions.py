#!/usr/bin/env python3
"""
Script untuk membersihkan semua session dan memaksa logout semua user
Jalankan dengan: python3 manage.py shell < clear_sessions.py
"""

from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.cache import cache

def clear_all_sessions():
    """Clear all active sessions"""
    print("=== Clearing All Sessions ===")
    
    try:
        # Get session count before clearing
        session_count = Session.objects.count()
        print(f"Active sessions before clearing: {session_count}")
        
        # Clear all sessions
        Session.objects.all().delete()
        
        # Verify sessions are cleared
        remaining_sessions = Session.objects.count()
        print(f"Active sessions after clearing: {remaining_sessions}")
        
        print("✓ All sessions cleared successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error clearing sessions: {e}")
        return False

def clear_cache():
    """Clear application cache"""
    print("\n=== Clearing Application Cache ===")
    
    try:
        cache.clear()
        print("✓ Application cache cleared")
        return True
    except Exception as e:
        print(f"✗ Error clearing cache: {e}")
        return False

def force_user_logout():
    """Force logout by updating last_login timestamp"""
    print("\n=== Forcing User Logout ===")
    
    try:
        admin_user = User.objects.get(username='admin')
        
        # Update last_login to force session invalidation
        admin_user.last_login = timezone.now()
        admin_user.save()
        
        print(f"✓ Updated last_login for user: {admin_user.username}")
        return True
        
    except User.DoesNotExist:
        print("✗ Admin user not found")
        return False
    except Exception as e:
        print(f"✗ Error forcing logout: {e}")
        return False

def test_authentication_after_cleanup():
    """Test authentication after cleanup"""
    print("\n=== Testing Authentication After Cleanup ===")
    
    try:
        # Test new password
        new_auth = authenticate(username='admin', password='Lagisenang1')
        print(f"New password (Lagisenang1): {'✓ SUCCESS' if new_auth else '✗ FAILED'}")
        
        # Test old password
        old_auth = authenticate(username='admin', password='admin123')
        print(f"Old password (admin123): {'✓ PROPERLY REJECTED' if not old_auth else '✗ STILL WORKS (PROBLEM!)'}")
        
        return new_auth and not old_auth
        
    except Exception as e:
        print(f"✗ Error testing authentication: {e}")
        return False

def check_session_backend():
    """Check session backend configuration"""
    print("\n=== Checking Session Backend ===")
    
    from django.conf import settings
    
    session_engine = getattr(settings, 'SESSION_ENGINE', 'Not set')
    print(f"Session engine: {session_engine}")
    
    if 'cached_db' in session_engine:
        print("Using cached_db session backend - clearing both cache and database")
        return True
    elif 'cache' in session_engine:
        print("Using cache session backend - clearing cache")
        return True
    elif 'db' in session_engine:
        print("Using database session backend - clearing database sessions")
        return True
    else:
        print(f"Unknown session backend: {session_engine}")
        return False

def restart_recommendation():
    """Provide restart recommendation"""
    print("\n=== Restart Recommendation ===")
    print("For complete session cleanup, consider:")
    print("1. Restart the Django development server")
    print("2. Clear browser cookies/cache")
    print("3. Use incognito/private browsing mode for testing")
    print("\nTo restart server:")
    print("  - Stop current server (Ctrl+C)")
    print("  - Run: python3 manage.py runserver")

# Main execution
print("Session Cleanup and Authentication Fix")
print("=" * 50)

# Step 1: Check session backend
backend_ok = check_session_backend()

# Step 2: Clear cache first (important for cached_db backend)
cache_cleared = clear_cache()

# Step 3: Clear all sessions
sessions_cleared = clear_all_sessions()

# Step 4: Force user logout
logout_forced = force_user_logout()

# Step 5: Test authentication
auth_working = test_authentication_after_cleanup()

# Step 6: Provide recommendations
restart_recommendation()

print("\n" + "=" * 50)
print("CLEANUP SUMMARY:")
print(f"Cache cleared: {'✓' if cache_cleared else '✗'}")
print(f"Sessions cleared: {'✓' if sessions_cleared else '✗'}")
print(f"User logout forced: {'✓' if logout_forced else '✗'}")
print(f"Authentication working: {'✓' if auth_working else '✗'}")

if auth_working:
    print("\n🎉 SUCCESS: Authentication is now working correctly!")
    print("   Please restart the server and test again in a fresh browser session.")
else:
    print("\n⚠️  Authentication may still have issues.")
    print("   Please restart the server and clear browser cache.")

print("\nCleanup complete.")