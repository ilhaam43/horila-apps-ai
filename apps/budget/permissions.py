from rest_framework import permissions
from django.contrib.auth.models import Group


class BudgetPermission(permissions.BasePermission):
    """Custom permission for budget module"""
    
    def has_permission(self, request, view):
        """Check if user has permission to access budget module"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        # Check if user has budget-related groups
        budget_groups = ['Budget Manager', 'Finance Team', 'Budget Viewer']
        user_groups = request.user.groups.values_list('name', flat=True)
        
        return any(group in budget_groups for group in user_groups)
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        if not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        
        # Budget Managers can do everything
        if 'Budget Manager' in user_groups:
            return True
        
        # Finance Team can approve expenses and manage budgets
        if 'Finance Team' in user_groups:
            if view.action in ['retrieve', 'list', 'approve', 'reject', 'mark_paid']:
                return True
            # Can create/update their own expenses
            if hasattr(obj, 'requested_by') and obj.requested_by == request.user.employee_get:
                return True
        
        # Budget Viewers can only read
        if 'Budget Viewer' in user_groups:
            return view.action in ['retrieve', 'list']
        
        # Users can manage their own expenses
        if hasattr(obj, 'requested_by') and obj.requested_by == request.user.employee_get:
            return view.action in ['retrieve', 'list', 'create', 'update', 'partial_update']
        
        # Users can view budgets they are involved in
        if hasattr(obj, 'created_by') and obj.created_by == request.user.employee_get:
            return view.action in ['retrieve', 'list']
        
        return False


class BudgetManagerPermission(permissions.BasePermission):
    """Permission for budget managers only"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return 'Budget Manager' in user_groups


class FinanceTeamPermission(permissions.BasePermission):
    """Permission for finance team members"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['Budget Manager', 'Finance Team'] for group in user_groups)


class ExpenseApprovalPermission(permissions.BasePermission):
    """Permission for expense approval actions"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Only Budget Managers and Finance Team can approve expenses
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['Budget Manager', 'Finance Team'] for group in user_groups)
    
    def has_object_permission(self, request, view, obj):
        """Users cannot approve their own expenses"""
        if hasattr(obj, 'requested_by') and obj.requested_by == request.user.employee_get:
            return False
        return True


class ReportGenerationPermission(permissions.BasePermission):
    """Permission for generating financial reports"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Budget Managers and Finance Team can generate reports
        user_groups = request.user.groups.values_list('name', flat=True)
        return any(group in ['Budget Manager', 'Finance Team'] for group in user_groups)