from django.utils.translation import gettext_lazy as _


MENU = _('Budget')
IMG_SRC = 'images/ui/budget.svg'
ACCESSIBILITY = 'budget.sidebar.menu_accessibility'

SUBMENUS = [
    {
        'menu': _('Dashboard'),
        'redirect': '/budget/',
        'accessibility': 'budget.sidebar.dashboard_accessibility',
    },
    {
        'menu': _('Budget Plans'),
        'redirect': '/budget/plans/',
        'accessibility': 'budget.sidebar.plan_accessibility',
    },
    {
        'menu': _('Expenses'),
        'redirect': '/budget/expenses/',
        'accessibility': 'budget.sidebar.expense_accessibility',
    },
    {
        'menu': _('Categories'),
        'redirect': '/budget/categories/',
        'accessibility': 'budget.sidebar.category_accessibility',
    },
    {
        'menu': _('Expense Types'),
        'redirect': '/budget/expense-types/',
        'accessibility': 'budget.sidebar.expense_type_accessibility',
    },
    {
        'menu': _('Financial Reports'),
        'redirect': '/budget/reports/',
        'accessibility': 'budget.sidebar.report_accessibility',
    },
]


def menu_accessibility(request, menu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access budget menu
    """
    return request.user.has_perm('budget.view_budgetplan')


def dashboard_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access budget dashboard
    """
    return request.user.has_perm('budget.view_budgetplan')


def plan_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access budget plans
    """
    return request.user.has_perm('budget.view_budgetplan')


def expense_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access expenses
    """
    return request.user.has_perm('budget.view_expense')


def category_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access budget categories
    """
    return request.user.has_perm('budget.view_budgetcategory')


def expense_type_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access expense types
    """
    return request.user.has_perm('budget.view_expensetype')


def report_accessibility(request, submenu, user_perms, *args, **kwargs):
    """
    Check if user has permission to access financial reports
    """
    return request.user.has_perm('budget.view_financialreport')