from django.utils.translation import gettext_lazy as _
from django.urls import reverse

MENU = _('Knowledge Management')
IMG_SRC = 'images/ui/knowledge.svg'
ACCESSIBILITY = 'knowledge.sidebar.menu_accessibility'

SUBMENUS = [
    {
        'menu': _('Dashboard'),
        'redirect': '/knowledge/',
        'accessibility': 'knowledge.sidebar.dashboard_accessibility',
    },
    {
        'menu': _('Documents'),
        'redirect': '/knowledge/documents/',
        'accessibility': 'knowledge.sidebar.documents_accessibility',
    },
    {
        'menu': _('Categories'),
        'redirect': '/knowledge/categories/',
        'accessibility': 'knowledge.sidebar.categories_accessibility',
    },
    {
        'menu': _('Search'),
        'redirect': '/knowledge/search/',
        'accessibility': 'knowledge.sidebar.search_accessibility',
    },
    {
        'menu': _('AI Assistant'),
        'redirect': '/knowledge/ai-assistant/',
        'accessibility': 'knowledge.sidebar.ai_assistant_accessibility',
    },
]


def menu_accessibility(request, menu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access knowledge management menu
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_knowledgedocument')
        or request.user.has_perm('knowledge.add_knowledgedocument')
        or request.user.has_perm('knowledge.change_knowledgedocument')
    )


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access knowledge dashboard
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_knowledgedocument')
    )


def documents_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access documents
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_knowledgedocument')
    )


def categories_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access categories
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_documentcategory')
    )


def search_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access search
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_knowledgedocument')
    )


def ai_assistant_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access AI assistant
    """
    return (
        request.user.is_superuser
        or request.user.has_perm('knowledge.view_knowledgedocument')
    )