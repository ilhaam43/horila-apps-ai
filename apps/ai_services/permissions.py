from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import render


def admin_manager_required(view_func):
    """
    Decorator untuk membatasi akses hanya untuk admin dan manager.
    Mengecek apakah user adalah superuser atau berada dalam grup yang diizinkan.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Superuser selalu diizinkan
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Cek grup user
        user_groups = request.user.groups.values_list('name', flat=True)
        allowed_groups = [
            'HR_ADMIN', 
            'MANAGER', 
            'Budget Manager', 
            'Finance Team',
            'IT Manager',
            'System Administrator'
        ]
        
        # Cek apakah user ada di grup yang diizinkan
        if any(group in allowed_groups for group in user_groups):
            return view_func(request, *args, **kwargs)
        
        # Jika tidak memiliki akses, tampilkan halaman error
        return render(request, 'ai_services/access_denied.html', {
            'message': 'Anda tidak memiliki akses untuk mengelola training data. Hanya admin dan manager yang diizinkan.'
        }, status=403)
    
    return _wrapped_view


def training_data_upload_required(view_func):
    """
    Decorator khusus untuk upload training data.
    Lebih ketat dari admin_manager_required.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Superuser selalu diizinkan
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Cek permission khusus untuk upload training data
        if request.user.has_perm('ai_services.can_upload_training_data'):
            return view_func(request, *args, **kwargs)
        
        # Cek grup user untuk upload
        user_groups = request.user.groups.values_list('name', flat=True)
        upload_allowed_groups = [
            'HR_ADMIN', 
            'MANAGER', 
            'Budget Manager',
            'IT Manager'
        ]
        
        if any(group in upload_allowed_groups for group in user_groups):
            return view_func(request, *args, **kwargs)
        
        return render(request, 'ai_services/access_denied.html', {
            'message': 'Anda tidak memiliki akses untuk mengupload training data. Hubungi administrator sistem.'
        }, status=403)
    
    return _wrapped_view


def training_data_manage_required(view_func):
    """
    Decorator untuk mengelola (edit/delete) training data.
    Hanya untuk admin dan manager senior.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # Superuser selalu diizinkan
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Cek permission khusus untuk manage training data
        if request.user.has_perm('ai_services.can_manage_training_data'):
            return view_func(request, *args, **kwargs)
        
        # Cek grup user untuk manage
        user_groups = request.user.groups.values_list('name', flat=True)
        manage_allowed_groups = [
            'HR_ADMIN', 
            'Budget Manager',
            'IT Manager'
        ]
        
        if any(group in manage_allowed_groups for group in user_groups):
            return view_func(request, *args, **kwargs)
        
        return render(request, 'ai_services/access_denied.html', {
            'message': 'Anda tidak memiliki akses untuk mengelola training data. Hanya admin senior yang diizinkan.'
        }, status=403)
    
    return _wrapped_view


class TrainingDataPermissionMixin:
    """
    Mixin untuk class-based views yang memerlukan permission training data.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not self.has_training_data_permission(request.user):
            return render(request, 'ai_services/access_denied.html', {
                'message': 'Anda tidak memiliki akses untuk fitur training data.'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)
    
    def has_training_data_permission(self, user):
        """Check if user has training data permission"""
        if user.is_superuser:
            return True
        
        user_groups = user.groups.values_list('name', flat=True)
        allowed_groups = [
            'HR_ADMIN', 
            'MANAGER', 
            'Budget Manager', 
            'Finance Team',
            'IT Manager'
        ]
        
        return any(group in allowed_groups for group in user_groups)


def check_training_data_access(user):
    """
    Utility function untuk mengecek akses training data.
    Returns True jika user memiliki akses.
    """
    if user.is_superuser:
        return True
    
    if not user.is_authenticated:
        return False
    
    user_groups = user.groups.values_list('name', flat=True)
    allowed_groups = [
        'HR_ADMIN', 
        'MANAGER', 
        'Budget Manager', 
        'Finance Team',
        'IT Manager',
        'System Administrator'
    ]
    
    return any(group in allowed_groups for group in user_groups)