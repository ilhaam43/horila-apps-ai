from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BudgetCategoryViewSet, BudgetPlanViewSet, ExpenseTypeViewSet,
    ExpenseViewSet, ExpenseAttachmentViewSet, BudgetAlertViewSet,
    FinancialReportViewSet, BudgetDashboardViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', BudgetCategoryViewSet, basename='budget-category')
router.register(r'expense-types', ExpenseTypeViewSet, basename='expense-type')
router.register(r'plans', BudgetPlanViewSet, basename='budget-plan')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'attachments', ExpenseAttachmentViewSet, basename='expense-attachment')
router.register(r'alerts', BudgetAlertViewSet, basename='budget-alert')
router.register(r'reports', FinancialReportViewSet, basename='financial-report')
router.register(r'dashboard', BudgetDashboardViewSet, basename='budget-dashboard')

app_name = 'budget_api'

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    
    # Additional custom endpoints can be added here
    # path('custom-endpoint/', custom_view, name='custom-endpoint'),
]