from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Sum, Q, Count, F, Avg
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
from decimal import Decimal
from .models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense,
    ExpenseAttachment, BudgetAlert, FinancialReport, BudgetSettings
)
from .forms import BudgetPlanForm, ExpenseForm, BudgetCategoryForm, ExpenseTypeForm, BudgetSettingsForm
from .filters import BudgetPlanFilter, ExpenseFilter


class SimpleBudgetDashboardView(LoginRequiredMixin, ListView):
    """Simple Budget Dashboard View"""
    template_name = 'budget/simple_dashboard.html'  # Force template reload
    context_object_name = 'dashboard_data'
    
    def get_queryset(self):
        return None  # We'll use get_context_data instead
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate simple dashboard metrics
        budget_stats = BudgetPlan.objects.aggregate(
            total_budgets=Count('id'),
            active_budgets=Count('id', filter=Q(status='active')),
            total_allocated=Sum('allocated_amount', filter=Q(status='active')),
            total_spent=Sum('spent_amount', filter=Q(status='active')),
            total_remaining=Sum('remaining_amount', filter=Q(status='active')),
        )
        
        # Handle None values and convert to float for JSON serialization
        total_allocated = float(budget_stats['total_allocated'] or 0)
        total_spent = float(budget_stats['total_spent'] or 0)
        total_remaining = float(budget_stats['total_remaining'] or 0)
        
        # Calculate utilization percentage
        utilization_percentage = 0
        if total_allocated > 0:
            utilization_percentage = (total_spent / total_allocated) * 100
        
        # Get recent expenses (last 5)
        recent_expenses = Expense.objects.select_related(
            'budget_plan', 'expense_type'
        ).order_by('-created_at')[:5]
        
        # Get top spending categories with proper aggregation
        top_categories = BudgetCategory.objects.annotate(
            total_spent=Sum('budgetplan__expenses__amount', filter=Q(budgetplan__status='active'))
        ).filter(total_spent__gt=0).order_by('-total_spent')[:5]
        
        # Monthly spending trend removed - no longer needed
        
        # Format category data for chart
        category_data = []
        for category in top_categories:
            category_data.append({
                'name': category.name,
                'total': float(category.total_spent or 0)
            })
        
        # Format recent expenses data
        expenses_data = []
        for expense in recent_expenses:
            expenses_data.append({
                'description': expense.description,
                'amount': float(expense.amount),
                'date': expense.created_at.strftime('%Y-%m-%d'),
                'category': expense.expense_type.name if expense.expense_type else 'N/A'
            })
        
        import json
        
        context.update({
            'total_allocated': total_allocated,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'utilization_percentage': round(utilization_percentage, 1),
            'budget_stats': {
                'total_budgets': budget_stats['total_budgets'] or 0,
                'active_budgets': budget_stats['active_budgets'] or 0,
            },
            'recent_expenses': json.dumps(expenses_data),
            'top_categories': json.dumps(category_data),
        })
        
        return context


class BudgetDashboardView(LoginRequiredMixin, ListView):
    """Budget Dashboard View"""
    template_name = 'budget/dashboard.html'
    context_object_name = 'dashboard_data'
    
    def get_queryset(self):
        return None  # We'll use get_context_data instead
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Try to get cached dashboard data
        cache_key = f'budget_dashboard_{self.request.user.id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
            return context
        
        # Calculate dashboard metrics with optimized queries
        budget_stats = BudgetPlan.objects.aggregate(
            total_budgets=Count('id'),
            active_budgets=Count('id', filter=Q(status='active')),
            total_allocated=Sum('allocated_amount', filter=Q(status='active')),
            total_spent=Sum('spent_amount', filter=Q(status='active')),
            total_remaining=Sum('remaining_amount', filter=Q(status='active')),
            over_budget_count=Count('id', filter=Q(status='active', spent_amount__gt=F('allocated_amount')))
        )
        
        pending_expenses = Expense.objects.filter(status='pending').count()
        
        # Recent expenses with optimized select_related
        recent_expenses = Expense.objects.select_related(
            'budget_plan', 'expense_type', 'requested_by__employee_user_id'
        ).order_by('-created_at')[:10]
        
        # Budget utilization data
        budget_utilization = list(BudgetPlan.objects.filter(status='active').values(
            'name', 'allocated_amount', 'spent_amount'
        ))
        
        # Monthly spending trend removed - no longer needed
        
        dashboard_data = {
            'total_budgets': budget_stats['total_budgets'] or 0,
            'active_budgets': budget_stats['active_budgets'] or 0,
            'total_allocated': budget_stats['total_allocated'] or Decimal('0'),
            'total_spent': budget_stats['total_spent'] or Decimal('0'),
            'total_remaining': budget_stats['total_remaining'] or Decimal('0'),
            'over_budget_count': budget_stats['over_budget_count'] or 0,
            'pending_expenses': pending_expenses,
            'recent_expenses': recent_expenses,
            'budget_utilization': budget_utilization
        }
        
        # Cache dashboard data for 15 minutes
        cache.set(cache_key, dashboard_data, 900)
        
        context.update(dashboard_data)
        return context


class BudgetPlanListView(LoginRequiredMixin, ListView):
    """Budget Plan List View"""
    model = BudgetPlan
    template_name = 'budget/budget_plan_list.html'
    context_object_name = 'budget_plans'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = BudgetPlan.objects.select_related(
            'category', 'created_by__employee_user_id', 'approved_by__employee_user_id'
        ).prefetch_related('expenses')
        self.filterset = BudgetPlanFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['categories'] = BudgetCategory.objects.filter(is_active=True).order_by('name')
        return context


class BudgetPlanDetailView(LoginRequiredMixin, DetailView):
    """Budget Plan Detail View"""
    model = BudgetPlan
    template_name = 'budget/budget_plan_detail.html'
    context_object_name = 'budget_plan'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget_plan = self.get_object()
        
        # Get related expenses
        expenses = Expense.objects.filter(budget_plan=budget_plan).select_related(
            'expense_type', 'requested_by', 'approved_by'
        ).order_by('-created_at')
        
        context['expenses'] = expenses
        context['expense_summary'] = expenses.aggregate(
            total_pending=Sum('amount', filter=Q(status='pending')),
            total_approved=Sum('amount', filter=Q(status='approved')),
            total_paid=Sum('amount', filter=Q(status='paid')),
            total_rejected=Sum('amount', filter=Q(status='rejected'))
        )
        
        return context


class BudgetPlanCreateView(LoginRequiredMixin, CreateView):
    """Budget Plan Create View"""
    model = BudgetPlan
    form_class = BudgetPlanForm
    template_name = 'budget/budget_plan_form.html'
    success_url = reverse_lazy('budget:plan_list')
    
    def form_valid(self, form):
        try:
            form.instance.created_by = self.request.user.employee_get
        except AttributeError:
            # User doesn't have an employee instance (e.g., admin user)
            if self.request.user.is_superuser or self.request.user.is_staff:
                form.instance.created_by = None
            else:
                messages.error(self.request, 'You need to have an employee profile to create budget plans.')
                return self.form_invalid(form)
        
        messages.success(self.request, 'Budget plan created successfully!')
        return super().form_valid(form)


class BudgetPlanUpdateView(LoginRequiredMixin, UpdateView):
    """Budget Plan Update View"""
    model = BudgetPlan
    form_class = BudgetPlanForm
    template_name = 'budget/budget_plan_form.html'
    success_url = reverse_lazy('budget:plan_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Budget plan updated successfully!')
        return super().form_valid(form)


class BudgetPlanDeleteView(LoginRequiredMixin, DeleteView):
    """Budget Plan Delete View"""
    model = BudgetPlan
    template_name = 'budget/budget_plan_confirm_delete.html'
    success_url = reverse_lazy('budget:plan_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Budget plan deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ExpenseListView(LoginRequiredMixin, ListView):
    """Expense List View"""
    model = Expense
    template_name = 'budget/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Expense.objects.select_related(
            'budget_plan', 'expense_type', 'requested_by__employee_user_id', 
            'approved_by__employee_user_id'
        ).prefetch_related('attachments')
        self.filterset = ExpenseFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter'] = self.filterset
        context['budget_plans'] = BudgetPlan.objects.filter(status='active').order_by('name')
        context['expense_types'] = ExpenseType.objects.filter(is_active=True).order_by('name')
        return context


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    """Expense Detail View"""
    model = Expense
    template_name = 'budget/expense_detail.html'
    context_object_name = 'expense'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expense = self.get_object()
        
        # Get attachments
        context['attachments'] = ExpenseAttachment.objects.filter(expense=expense)
        
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """Expense Create View"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'budget/expense_form.html'
    success_url = reverse_lazy('budget:expense_list')
    
    def form_valid(self, form):
        try:
            form.instance.requested_by = self.request.user.employee_get
        except AttributeError:
            # User doesn't have an employee instance (e.g., admin user)
            if self.request.user.is_superuser or self.request.user.is_staff:
                form.instance.requested_by = None
            else:
                messages.error(self.request, 'You need to have an employee profile to create expenses.')
                return self.form_invalid(form)
        
        messages.success(self.request, 'Expense created successfully!')
        return super().form_valid(form)


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """Expense Update View"""
    model = Expense
    form_class = ExpenseForm
    template_name = 'budget/expense_form.html'
    success_url = reverse_lazy('budget:expense_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense updated successfully!')
        return super().form_valid(form)


class BudgetCategoryListView(LoginRequiredMixin, ListView):
    """Budget Category List View"""
    model = BudgetCategory
    template_name = 'budget/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = BudgetCategory.objects.select_related('parent_category').prefetch_related(
            'budgetplan_set'
        ).annotate(
            total_allocated=Sum('budgetplan__allocated_amount'),
            budget_plans_count=Count('budgetplan')
        )
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Apply sorting
        sort = self.request.GET.get('sort', 'name')
        if sort in ['name', '-name', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('name')
        
        return queryset


class BudgetCategoryCreateView(LoginRequiredMixin, CreateView):
    """Budget Category Create View"""
    model = BudgetCategory
    form_class = BudgetCategoryForm
    template_name = 'budget/category_form.html'
    success_url = reverse_lazy('budget:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Budget category created successfully!')
        return super().form_valid(form)


class ExpenseTypeListView(LoginRequiredMixin, ListView):
    """Expense Type List View"""
    model = ExpenseType
    template_name = 'budget/expense_type_list.html'
    context_object_name = 'expense_types'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ExpenseType.objects.prefetch_related('expense_set')
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Apply sorting
        sort = self.request.GET.get('sort', 'name')
        if sort in ['name', '-name', 'created_at', '-created_at']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('name')
        
        return queryset


class ExpenseTypeCreateView(LoginRequiredMixin, CreateView):
    """Expense Type Create View"""
    model = ExpenseType
    form_class = ExpenseTypeForm
    template_name = 'budget/expense_type_form.html'
    success_url = reverse_lazy('budget:expense_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense type created successfully!')
        return super().form_valid(form)


class ExpenseTypeUpdateView(LoginRequiredMixin, UpdateView):
    """Expense Type Update View"""
    model = ExpenseType
    form_class = ExpenseTypeForm
    template_name = 'budget/expense_type_form.html'
    success_url = reverse_lazy('budget:expense_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Expense type updated successfully!')
        return super().form_valid(form)


class ExpenseTypeDeleteView(LoginRequiredMixin, DeleteView):
    """Expense Type Delete View"""
    model = ExpenseType
    template_name = 'budget/expense_type_confirm_delete.html'
    success_url = reverse_lazy('budget:expense_type_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense type deleted successfully!')
        return super().delete(request, *args, **kwargs)


class BudgetCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Budget Category Update View"""
    model = BudgetCategory
    form_class = BudgetCategoryForm
    template_name = 'budget/category_form.html'
    success_url = reverse_lazy('budget:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Budget category updated successfully!')
        return super().form_valid(form)


class BudgetCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Budget Category Delete View"""
    model = BudgetCategory
    template_name = 'budget/category_confirm_delete.html'
    success_url = reverse_lazy('budget:category_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Budget category deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """Expense Delete View"""
    model = Expense
    template_name = 'budget/expense_confirm_delete.html'
    success_url = reverse_lazy('budget:expense_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Expense deleted successfully!')
        return super().delete(request, *args, **kwargs)


class BudgetReportsView(LoginRequiredMixin, ListView):
    """Budget Reports View"""
    template_name = 'budget/report_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        try:
            employee = self.request.user.employee_get
            queryset = FinancialReport.objects.filter(generated_by=employee).select_related('generated_by__employee_user_id')
        except AttributeError:
            # User doesn't have an employee instance (e.g., admin user)
            if self.request.user.is_superuser or self.request.user.is_staff:
                # Show all reports for admin/staff users
                queryset = FinancialReport.objects.select_related('generated_by__employee_user_id')
            else:
                # Regular user without employee profile - show empty data
                queryset = FinancialReport.objects.none()
        
        # Apply filters
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(report_type__icontains=search)
            )
        
        report_type = self.request.GET.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            try:
                from datetime import datetime
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from_obj)
            except ValueError:
                pass
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            try:
                from datetime import datetime
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to_obj)
            except ValueError:
                pass
        
        # Apply sorting
        sort = self.request.GET.get('sort', '-created_at')
        if sort in ['name', '-name', 'created_at', '-created_at', 'report_type', '-report_type']:
            queryset = queryset.order_by(sort)
        else:
            queryset = queryset.order_by('-created_at')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get budget data for the current user
        try:
            employee = self.request.user.employee_get
            user_budget_plans = BudgetPlan.objects.filter(created_by=employee)
            total_expenses = Expense.objects.filter(
                budget_plan__created_by=employee
            ).aggregate(total=Sum('amount'))['total'] or 0
        except AttributeError:
            # User doesn't have an employee instance (e.g., admin user)
            if self.request.user.is_superuser or self.request.user.is_staff:
                # Show all budget plans for admin/staff users
                user_budget_plans = BudgetPlan.objects.all()
                total_expenses = Expense.objects.all().aggregate(total=Sum('amount'))['total'] or 0
            else:
                # Regular user without employee profile - show empty data
                user_budget_plans = BudgetPlan.objects.none()
                total_expenses = 0
        
        total_budget = user_budget_plans.aggregate(total=Sum('allocated_amount'))['total'] or 0
        
        # Calculate budget utilization and remaining budget
        budget_utilization = 0
        remaining_budget = 0
        if total_budget > 0:
            budget_utilization = (total_expenses / total_budget) * 100
            remaining_budget = total_budget - total_expenses
        
        context.update({
            'total_budget': total_budget,
            'total_expenses': total_expenses,
            'budget_utilization': budget_utilization,
            'remaining_budget': remaining_budget,
            'budget_plans': user_budget_plans,
            'last_updated': timezone.now(),
        })
        return context


@login_required
def export_reports(request):
    """Export reports view"""
    import pandas as pd
    from django.http import HttpResponse
    from datetime import datetime
    from .utils import (
        generate_budget_summary_report,
        generate_expense_analysis_report,
        generate_variance_report
    )
    
    # Get parameters from request
    export_format = request.GET.get('format', 'excel')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    budget_plan_id = request.GET.get('budget_plan')
    
    # Set default date range if not provided
    if not date_from:
        date_from = datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')
    if not date_to:
        date_to = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # Get user's budget plans
        user_budget_plans = BudgetPlan.objects.filter(created_by=request.user)
        if budget_plan_id:
            user_budget_plans = user_budget_plans.filter(id=budget_plan_id)
        
        # Get expenses for the user
        user_expenses = Expense.objects.filter(
            budget_plan__created_by=request.user,
            expense_date__range=[date_from, date_to]
        )
        
        if export_format == 'excel':
            # Create Excel workbook with multiple sheets
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="budget_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
            
            with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'bg_color': '#4472C4',
                    'font_color': 'white',
                    'border': 1
                })
                currency_format = workbook.add_format({'num_format': 'IDR #,##0'})
                
                # Budget Summary Sheet
                budget_data = []
                for plan in user_budget_plans:
                    total_expenses = user_expenses.filter(budget_plan=plan).aggregate(
                        total=Sum('amount')
                    )['total'] or 0
                    
                    budget_data.append({
                        'Budget Plan': plan.name,
                        'Category': plan.category.name if plan.category else 'N/A',
                        'Allocated Amount (IDR)': plan.allocated_amount,
                        'Spent Amount (IDR)': total_expenses,
                        'Remaining Amount (IDR)': plan.allocated_amount - total_expenses,
                        'Utilization (%)': (total_expenses / plan.allocated_amount * 100) if plan.allocated_amount > 0 else 0,
                        'Status': plan.status,
                        'Start Date': plan.start_date,
                        'End Date': plan.end_date
                    })
                
                if budget_data:
                    budget_df = pd.DataFrame(budget_data)
                    budget_df.to_excel(writer, sheet_name='Budget Summary', index=False)
                    
                    # Format the Budget Summary sheet
                    worksheet = writer.sheets['Budget Summary']
                    worksheet.set_row(0, None, header_format)
                    worksheet.set_column('A:A', 20)
                    worksheet.set_column('B:B', 15)
                    worksheet.set_column('C:E', 18, currency_format)
                    worksheet.set_column('F:F', 15)
                    worksheet.set_column('G:G', 10)
                    worksheet.set_column('H:I', 12)
                
                # Expense Analysis Sheet
                expense_data = []
                for expense in user_expenses:
                    expense_data.append({
                        'Date': expense.expense_date,
                        'Description': expense.description,
                        'Amount (IDR)': expense.amount,
                        'Expense Type': expense.expense_type.name if expense.expense_type else 'N/A',
                        'Budget Plan': expense.budget_plan.name,
                        'Category': expense.budget_plan.category.name if expense.budget_plan.category else 'N/A',
                        'Status': expense.status,
                        'Created By': expense.created_by.get_full_name() if expense.created_by else 'N/A'
                    })
                
                if expense_data:
                    expense_df = pd.DataFrame(expense_data)
                    expense_df.to_excel(writer, sheet_name='Expense Details', index=False)
                    
                    # Format the Expense Details sheet
                    worksheet = writer.sheets['Expense Details']
                    worksheet.set_row(0, None, header_format)
                    worksheet.set_column('A:A', 12)
                    worksheet.set_column('B:B', 30)
                    worksheet.set_column('C:C', 15, currency_format)
                    worksheet.set_column('D:H', 15)
                
                # Expense by Type Analysis
                expense_by_type = user_expenses.values('expense_type__name').annotate(
                    total_amount=Sum('amount'),
                    count=Count('id'),
                    avg_amount=Avg('amount')
                ).order_by('-total_amount')
                
                type_data = []
                for item in expense_by_type:
                    type_data.append({
                        'Expense Type': item['expense_type__name'] or 'No Type',
                        'Total Amount (IDR)': item['total_amount'],
                        'Number of Expenses': item['count'],
                        'Average Amount (IDR)': item['avg_amount']
                    })
                
                if type_data:
                    type_df = pd.DataFrame(type_data)
                    type_df.to_excel(writer, sheet_name='Expense by Type', index=False)
                    
                    # Format the Expense by Type sheet
                    worksheet = writer.sheets['Expense by Type']
                    worksheet.set_row(0, None, header_format)
                    worksheet.set_column('A:A', 20)
                    worksheet.set_column('B:B', 18, currency_format)
                    worksheet.set_column('C:C', 18)
                    worksheet.set_column('D:D', 18, currency_format)
                
                # Summary Statistics Sheet
                total_budget = user_budget_plans.aggregate(total=Sum('allocated_amount'))['total'] or 0
                total_expenses = user_expenses.aggregate(total=Sum('amount'))['total'] or 0
                
                summary_data = [{
                    'Metric': 'Total Budget Allocated',
                    'Value (IDR)': total_budget
                }, {
                    'Metric': 'Total Expenses',
                    'Value (IDR)': total_expenses
                }, {
                    'Metric': 'Remaining Budget',
                    'Value (IDR)': total_budget - total_expenses
                }, {
                    'Metric': 'Budget Utilization (%)',
                    'Value (IDR)': (total_expenses / total_budget * 100) if total_budget > 0 else 0
                }, {
                    'Metric': 'Number of Budget Plans',
                    'Value (IDR)': user_budget_plans.count()
                }, {
                    'Metric': 'Number of Expenses',
                    'Value (IDR)': user_expenses.count()
                }]
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary Statistics', index=False)
                
                # Format the Summary Statistics sheet
                worksheet = writer.sheets['Summary Statistics']
                worksheet.set_row(0, None, header_format)
                worksheet.set_column('A:A', 25)
                worksheet.set_column('B:B', 20)
            
            return response
        
        else:
            messages.error(request, 'Unsupported export format.')
            return redirect('budget:report_list')
            
    except Exception as e:
        messages.error(request, f'Error exporting reports: {str(e)}')
        return redirect('budget:report_list')


@login_required
def view_report(request, pk):
    """View report detail"""
    try:
        employee = request.user.employee_get
        report = get_object_or_404(FinancialReport, pk=pk, generated_by=employee)
    except AttributeError:
        # User doesn't have an employee instance (e.g., admin user)
        # Allow superuser or admin to view all reports
        if request.user.is_superuser or request.user.is_staff:
            report = get_object_or_404(FinancialReport, pk=pk)
        else:
            messages.error(request, 'You need to have an employee profile to access reports.')
            return redirect('budget:report_list')
    
    # Get budget data for the current user
    user_budget_plans = BudgetPlan.objects.filter(created_by=request.user)
    total_budget = user_budget_plans.aggregate(total=Sum('allocated_amount'))['total'] or 0
    total_expenses = Expense.objects.filter(
        budget_plan__created_by=request.user
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate budget utilization and remaining budget
    budget_utilization = 0
    remaining_budget = 0
    if total_budget > 0:
        budget_utilization = (total_expenses / total_budget) * 100
        remaining_budget = total_budget - total_expenses
    
    context = {
        'report': report,
        'total_budget': total_budget,
        'total_expenses': total_expenses,
        'budget_utilization': budget_utilization,
        'remaining_budget': remaining_budget,
    }
    return render(request, 'budget/report_detail.html', context)


@login_required
def download_report(request, pk):
    """Download report view"""
    try:
        employee = request.user.employee_get
        report = get_object_or_404(FinancialReport, pk=pk, generated_by=employee)
    except AttributeError:
        # User doesn't have an employee instance (e.g., admin user)
        if request.user.is_superuser or request.user.is_staff:
            report = get_object_or_404(FinancialReport, pk=pk)
        else:
            messages.error(request, 'You need to have an employee profile to access reports.')
            return redirect('budget:report_list')
    
    messages.info(request, 'Download report feature will be available soon.')
    return redirect('budget:report_list')


@login_required
def delete_report(request, pk):
    """Delete report view"""
    try:
        employee = request.user.employee_get
        report = get_object_or_404(FinancialReport, pk=pk, generated_by=employee)
    except AttributeError:
        # User doesn't have an employee instance (e.g., admin user)
        if request.user.is_superuser or request.user.is_staff:
            report = get_object_or_404(FinancialReport, pk=pk)
        else:
            messages.error(request, 'You need to have an employee profile to access reports.')
            return redirect('budget:report_list')
    
    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Report deleted successfully!')
        return redirect('budget:report_list')
    return render(request, 'budget/report_confirm_delete.html', {'report': report})


@login_required
def approve_expense(request, pk):
    """Approve an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        if expense.status != 'pending':
            messages.error(request, 'Only pending expenses can be approved.')
        else:
            try:
                employee = request.user.employee_get
            except AttributeError:
                # User doesn't have an employee instance (e.g., admin user)
                if request.user.is_superuser or request.user.is_staff:
                    employee = None
                else:
                    messages.error(request, 'You need to have an employee profile to approve expenses.')
                    return redirect('budget:expense_detail', pk=pk)
            
            expense.status = 'approved'
            expense.approved_by = employee
            expense.approved_at = timezone.now()
            expense.save()
            
            # Update budget plan spent amount
            expense.budget_plan.spent_amount += expense.amount
            expense.budget_plan.save()
            
            messages.success(request, 'Expense approved successfully!')
    
    return redirect('budget:expense_detail', pk=pk)


@login_required
def reject_expense(request, pk):
    """Reject an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        if expense.status != 'pending':
            messages.error(request, 'Only pending expenses can be rejected.')
        else:
            try:
                employee = request.user.employee_get
            except AttributeError:
                # User doesn't have an employee instance (e.g., admin user)
                if request.user.is_superuser or request.user.is_staff:
                    employee = None
                else:
                    messages.error(request, 'You need to have an employee profile to reject expenses.')
                    return redirect('budget:expense_detail', pk=pk)
            
            expense.status = 'rejected'
            expense.approved_by = employee
            expense.approved_at = timezone.now()
            expense.save()
            
            messages.success(request, 'Expense rejected successfully!')
    
    return redirect('budget:expense_detail', pk=pk)


@login_required
def budget_analytics_api(request):
    """API endpoint for budget analytics data"""
    # Calculate analytics data
    total_budgets = BudgetPlan.objects.count()
    active_budgets = BudgetPlan.objects.filter(status='active').count()
    
    budget_aggregates = BudgetPlan.objects.filter(status='active').aggregate(
        total_allocated=Sum('allocated_amount'),
        total_spent=Sum('spent_amount')
    )
    
    data = {
        'total_budgets': total_budgets,
        'active_budgets': active_budgets,
        'total_allocated': float(budget_aggregates['total_allocated'] or 0),
        'total_spent': float(budget_aggregates['total_spent'] or 0),
        'utilization_percentage': 0
    }
    
    if data['total_allocated'] > 0:
        data['utilization_percentage'] = (data['total_spent'] / data['total_allocated']) * 100
    
    return JsonResponse(data)


@login_required
def generate_report(request):
    """Generate financial report"""
    if request.method == 'POST':
        # Create a new financial report
        try:
            employee = request.user.employee_get
        except AttributeError:
            # User doesn't have an employee instance (e.g., admin user)
            employee = None
        
        report = FinancialReport.objects.create(
            name=f"Financial Report - {timezone.now().strftime('%Y-%m-%d')}",
            generated_by=employee,
            report_type='monthly',
            start_date=timezone.now().date(),
            end_date=timezone.now().date()
        )
        messages.success(request, 'Financial report generated successfully!')
        return redirect('budget:view_report', pk=report.pk)
    
    return render(request, 'budget/generate_report.html')


@login_required
def budget_settings(request):
    """Budget Settings View for Currency Configuration"""
    from base.models import Company
    
    # Get or create budget settings for the current company
    try:
        company = Company.objects.first()  # Get the first company
        budget_settings, created = BudgetSettings.objects.get_or_create(
            company_id=company,
            defaults={
                'currency_symbol': '$',
                'position': 'prefix'
            }
        )
    except:
        # If no company exists, create default settings
        budget_settings, created = BudgetSettings.objects.get_or_create(
            id=1,
            defaults={
                'currency_symbol': '$',
                'position': 'prefix'
            }
        )
    
    if request.method == 'POST':
        form = BudgetSettingsForm(request.POST, instance=budget_settings)
        if form.is_valid():
            form.save()
            # Clear any cached currency data
            if 'budget_currency' in request.session:
                del request.session['budget_currency']
            if 'budget_position' in request.session:
                del request.session['budget_position']
            messages.success(request, 'Budget currency settings updated successfully!')
            return redirect('budget:budget_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = BudgetSettingsForm(instance=budget_settings)
    
    context = {
        'form': form,
        'budget_settings': budget_settings,
        'title': 'Budget Currency Settings'
    }
    
    return render(request, 'budget/budget_settings.html', context)