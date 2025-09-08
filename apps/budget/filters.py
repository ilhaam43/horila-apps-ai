import django_filters
from django.db import models
from .models import BudgetPlan, Expense, BudgetCategory, ExpenseType


class BudgetPlanFilter(django_filters.FilterSet):
    """Filter for BudgetPlan model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.ModelChoiceFilter(queryset=BudgetCategory.objects.filter(is_active=True))
    status = django_filters.ChoiceFilter(choices=BudgetPlan.STATUS_CHOICES)
    period_type = django_filters.MultipleChoiceFilter(choices=BudgetPlan.PERIOD_CHOICES)
    start_date = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    date_range = django_filters.DateFromToRangeFilter(field_name='start_date')
    allocated_amount_min = django_filters.NumberFilter(field_name='allocated_amount', lookup_expr='gte')
    allocated_amount_max = django_filters.NumberFilter(field_name='allocated_amount', lookup_expr='lte')
    spent_amount_min = django_filters.NumberFilter(field_name='spent_amount', lookup_expr='gte')
    spent_amount_max = django_filters.NumberFilter(field_name='spent_amount', lookup_expr='lte')
    utilization_min = django_filters.NumberFilter(method='filter_utilization_min')
    utilization_max = django_filters.NumberFilter(method='filter_utilization_max')
    is_over_budget = django_filters.BooleanFilter(method='filter_over_budget')
    created_by = django_filters.CharFilter(field_name='created_by__employee_id')
    approved_by = django_filters.CharFilter(field_name='approved_by__employee_id')
    
    class Meta:
        model = BudgetPlan
        fields = [
            'name', 'category', 'status', 'period_type', 'start_date', 'end_date',
            'allocated_amount_min', 'allocated_amount_max', 'spent_amount_min', 'spent_amount_max',
            'utilization_min', 'utilization_max', 'is_over_budget', 'created_by', 'approved_by'
        ]
    
    def filter_utilization_min(self, queryset, name, value):
        """Filter by minimum utilization percentage"""
        return queryset.annotate(
            utilization=models.Case(
                models.When(allocated_amount=0, then=0),
                default=models.F('spent_amount') / models.F('allocated_amount') * 100,
                output_field=models.DecimalField()
            )
        ).filter(utilization__gte=value)
    
    def filter_utilization_max(self, queryset, name, value):
        """Filter by maximum utilization percentage"""
        return queryset.annotate(
            utilization=models.Case(
                models.When(allocated_amount=0, then=0),
                default=models.F('spent_amount') / models.F('allocated_amount') * 100,
                output_field=models.DecimalField()
            )
        ).filter(utilization__lte=value)
    
    def filter_over_budget(self, queryset, name, value):
        """Filter budgets that are over or under budget"""
        if value:
            return queryset.filter(spent_amount__gt=models.F('allocated_amount'))
        else:
            return queryset.filter(spent_amount__lte=models.F('allocated_amount'))


class ExpenseFilter(django_filters.FilterSet):
    """Filter for Expense model"""
    title = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    budget_plan = django_filters.ModelChoiceFilter(queryset=BudgetPlan.objects.all())
    expense_type = django_filters.ModelChoiceFilter(queryset=ExpenseType.objects.filter(is_active=True))
    status = django_filters.ChoiceFilter(choices=Expense.STATUS_CHOICES)
    priority = django_filters.ChoiceFilter(choices=Expense.PRIORITY_CHOICES)
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    expense_date = django_filters.DateFilter()
    expense_date_range = django_filters.DateFromToRangeFilter(field_name='expense_date')
    vendor_name = django_filters.CharFilter(lookup_expr='icontains')
    receipt_number = django_filters.CharFilter(lookup_expr='icontains')
    requested_by = django_filters.CharFilter(field_name='requested_by__employee_id')
    approved_by = django_filters.CharFilter(field_name='approved_by__employee_id')
    created_date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    has_attachments = django_filters.BooleanFilter(method='filter_has_attachments')
    
    class Meta:
        model = Expense
        fields = [
            'title', 'description', 'budget_plan', 'expense_type', 'status', 'priority',
            'amount_min', 'amount_max', 'expense_date', 'expense_date_range',
            'vendor_name', 'receipt_number', 'requested_by', 'approved_by',
            'created_date_range', 'has_attachments'
        ]
    
    def filter_has_attachments(self, queryset, name, value):
        """Filter expenses that have or don't have attachments"""
        if value:
            return queryset.filter(attachments__isnull=False).distinct()
        else:
            return queryset.filter(attachments__isnull=True)


class BudgetCategoryFilter(django_filters.FilterSet):
    """Filter for BudgetCategory model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    parent_category = django_filters.ModelChoiceFilter(queryset=BudgetCategory.objects.all())
    is_active = django_filters.BooleanFilter()
    has_children = django_filters.BooleanFilter(method='filter_has_children')
    
    class Meta:
        model = BudgetCategory
        fields = ['name', 'description', 'parent_category', 'is_active', 'has_children']
    
    def filter_has_children(self, queryset, name, value):
        """Filter categories that have or don't have child categories"""
        if value:
            return queryset.filter(budgetcategory__isnull=False).distinct()
        else:
            return queryset.filter(budgetcategory__isnull=True)


class ExpenseTypeFilter(django_filters.FilterSet):
    """Filter for ExpenseType model"""
    name = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = ExpenseType
        fields = ['name', 'description', 'is_active']