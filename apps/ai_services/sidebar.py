from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth.context_processors import PermWrapper

MENU = _('AI Services')
IMG_SRC = 'images/ui/ai-services.svg'
ACCESSIBILITY = 'ai_services.sidebar.menu_accessibility'

SUBMENUS = [
    {
        'menu': _('Training Data Dashboard'),
        'redirect': reverse('ai_services:training_data_dashboard'),
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
    {
        'menu': _('Upload Training Data'),
        'redirect': reverse('ai_services:training_data_upload'),
        'accessibility': 'ai_services.sidebar.training_data_upload_accessibility',
    },
    {
        'menu': _('All Training Data'),
        'redirect': reverse('ai_services:training_data_dashboard'),
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
    {
        'menu': _('Pending Data'),
        'redirect': reverse('ai_services:training_data_dashboard') + '?status=pending',
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
    {
        'menu': _('Processing Data'),
        'redirect': reverse('ai_services:training_data_dashboard') + '?status=processing',
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
    {
        'menu': _('Completed Data'),
        'redirect': reverse('ai_services:training_data_dashboard') + '?status=completed',
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
    {
        'menu': _('Failed Data'),
        'redirect': reverse('ai_services:training_data_dashboard') + '?status=failed',
        'accessibility': 'ai_services.sidebar.training_data_accessibility',
    },
]


def menu_accessibility(request, menu: str = "", user_perms: PermWrapper = [], *args, **kwargs) -> bool:
    """
    Check if user has access to AI Services menu.
    Only superuser, HR_ADMIN, and MANAGER can access.
    """
    user = request.user
    
    # Allow superuser
    if user.is_superuser:
        return True
    
    # Check if user has employee profile and role
    try:
        employee = user.employee_get
        if hasattr(employee, 'employee_work_info') and employee.employee_work_info:
            job_role = employee.employee_work_info.job_role
            if job_role and job_role.name in ['HR_ADMIN', 'MANAGER']:
                return True
    except:
        pass
    
    # Check specific permissions
    return (
        user.has_perm('ai_services.can_upload_training_data') or
        user.has_perm('ai_services.can_manage_training_data') or
        user.has_perm('ai_services.can_process_training_data')
    )


def training_data_accessibility(request, submenu: str = "", user_perms: PermWrapper = [], *args, **kwargs) -> bool:
    """
    Check if user has access to training data features.
    """
    return menu_accessibility(request, submenu, user_perms, *args, **kwargs)


def training_data_upload_accessibility(request, submenu: str = "", user_perms: PermWrapper = [], *args, **kwargs) -> bool:
    """
    Check if user has access to upload training data.
    """
    user = request.user
    
    # Allow superuser
    if user.is_superuser:
        return True
    
    # Check if user has employee profile and role
    try:
        employee = user.employee_get
        if hasattr(employee, 'employee_work_info') and employee.employee_work_info:
            job_role = employee.employee_work_info.job_role
            if job_role and job_role.name in ['HR_ADMIN', 'MANAGER']:
                return True
    except:
        pass
    
    # Check specific upload permission
    return user.has_perm('ai_services.can_upload_training_data')