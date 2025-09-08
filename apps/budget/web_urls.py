from django.urls import path
from . import web_views

app_name = 'budget'

urlpatterns = [
    # Dashboard
    path('', web_views.BudgetDashboardView.as_view(), name='dashboard'),
    path('simple/', web_views.SimpleBudgetDashboardView.as_view(), name='simple_dashboard'),
    
    # Budget Plans
    path('plans/', web_views.BudgetPlanListView.as_view(), name='plan_list'),
    path('plans/create/', web_views.BudgetPlanCreateView.as_view(), name='plan_create'),
    path('plans/<int:pk>/', web_views.BudgetPlanDetailView.as_view(), name='plan_detail'),
    path('plans/<int:pk>/edit/', web_views.BudgetPlanUpdateView.as_view(), name='plan_edit'),
    path('plans/<int:pk>/delete/', web_views.BudgetPlanDeleteView.as_view(), name='plan_delete'),
    
    # Expenses
    path('expenses/', web_views.ExpenseListView.as_view(), name='expense_list'),
    path('expenses/create/', web_views.ExpenseCreateView.as_view(), name='expense_create'),
    path('expenses/<int:pk>/', web_views.ExpenseDetailView.as_view(), name='expense_detail'),
    path('expenses/<int:pk>/edit/', web_views.ExpenseUpdateView.as_view(), name='expense_edit'),
    path('expenses/<int:pk>/delete/', web_views.ExpenseDeleteView.as_view(), name='expense_delete'),
    path('expenses/<int:pk>/approve/', web_views.approve_expense, name='expense_approve'),
    path('expenses/<int:pk>/reject/', web_views.reject_expense, name='expense_reject'),
    
    # Budget Categories
    path('categories/', web_views.BudgetCategoryListView.as_view(), name='category_list'),
    path('categories/create/', web_views.BudgetCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', web_views.BudgetCategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', web_views.BudgetCategoryDeleteView.as_view(), name='category_delete'),
    
    # Expense Types
    path('expense-types/', web_views.ExpenseTypeListView.as_view(), name='expense_type_list'),
    path('expense-types/create/', web_views.ExpenseTypeCreateView.as_view(), name='expense_type_create'),
    path('expense-types/<int:pk>/edit/', web_views.ExpenseTypeUpdateView.as_view(), name='expense_type_edit'),
    path('expense-types/<int:pk>/delete/', web_views.ExpenseTypeDeleteView.as_view(), name='expense_type_delete'),
    
    # Reports and Analytics
    path('reports/', web_views.BudgetReportsView.as_view(), name='report_list'),
    path('reports/export/', web_views.export_reports, name='export_reports'),
    path('reports/<int:pk>/', web_views.view_report, name='view_report'),
    path('reports/<int:pk>/download/', web_views.download_report, name='download_report'),
    path('reports/<int:pk>/delete/', web_views.delete_report, name='delete_report'),
    path('reports/generate/', web_views.generate_report, name='generate_report'),
    path('api/analytics/', web_views.budget_analytics_api, name='analytics_api'),
    
    # Settings
    path('settings/', web_views.budget_settings, name='budget_settings'),
]