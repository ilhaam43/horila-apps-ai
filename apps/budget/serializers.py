from rest_framework import serializers
from django.db.models import Sum
from django.utils import timezone
from .models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense,
    ExpenseAttachment, BudgetAlert, FinancialReport
)
from employee.models import Employee


class BudgetCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = BudgetCategory
        fields = '__all__'
    
    def get_children(self, obj):
        children = BudgetCategory.objects.filter(parent_category=obj)
        return BudgetCategorySerializer(children, many=True).data


class ExpenseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseType
        fields = '__all__'


class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    
    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else 'N/A'
    
    class Meta:
        model = ExpenseAttachment
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'uploaded_at', 'file_size']


class ExpenseSerializer(serializers.ModelSerializer):
    attachments = ExpenseAttachmentSerializer(many=True, read_only=True)
    requested_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    expense_type_name = serializers.CharField(source='expense_type.name', read_only=True)
    budget_plan_name = serializers.CharField(source='budget_plan.name', read_only=True)
    
    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() if obj.requested_by else 'N/A'
    
    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else 'N/A'
    
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['requested_by', 'approved_by', 'approved_at', 'paid_at']
    
    def create(self, validated_data):
        try:
            validated_data['requested_by'] = self.context['request'].user.employee_get
        except AttributeError:
            # Handle case where user doesn't have employee profile
            validated_data['requested_by'] = None
        return super().create(validated_data)


class ExpenseCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for expense creation"""
    
    class Meta:
        model = Expense
        fields = [
            'budget_plan', 'expense_type', 'title', 'description',
            'amount', 'expense_date', 'receipt_number', 'vendor_name', 'priority'
        ]
    
    def create(self, validated_data):
        try:
            validated_data['requested_by'] = self.context['request'].user.employee_get
        except AttributeError:
            # Handle case where user doesn't have employee profile
            validated_data['requested_by'] = None
        return super().create(validated_data)


class BudgetAlertSerializer(serializers.ModelSerializer):
    sent_to_names = serializers.SerializerMethodField()
    budget_plan_name = serializers.CharField(source='budget_plan.name', read_only=True)
    
    class Meta:
        model = BudgetAlert
        fields = '__all__'
    
    def get_sent_to_names(self, obj):
        return [emp.get_full_name() for emp in obj.sent_to.all()]


class BudgetPlanSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else 'N/A'
    
    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else 'N/A'
    expenses = ExpenseSerializer(many=True, read_only=True)
    alerts = BudgetAlertSerializer(many=True, read_only=True)
    utilization_percentage = serializers.ReadOnlyField()
    is_over_budget = serializers.ReadOnlyField()
    expense_count = serializers.SerializerMethodField()
    pending_expenses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BudgetPlan
        fields = '__all__'
        read_only_fields = [
            'spent_amount', 'remaining_amount', 'created_by', 
            'approved_by', 'approved_at'
        ]
    
    def get_expense_count(self, obj):
        return obj.expenses.count()
    
    def get_pending_expenses_count(self, obj):
        return obj.expenses.filter(status='pending').count()
    
    def create(self, validated_data):
        try:
            validated_data['created_by'] = self.context['request'].user.employee_get
        except AttributeError:
            # Handle case where user doesn't have employee profile
            validated_data['created_by'] = None
        return super().create(validated_data)


class BudgetPlanSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for budget plan summaries"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    utilization_percentage = serializers.ReadOnlyField()
    is_over_budget = serializers.ReadOnlyField()
    
    class Meta:
        model = BudgetPlan
        fields = [
            'id', 'name', 'category_name', 'period_type', 'start_date', 'end_date',
            'allocated_amount', 'spent_amount', 'remaining_amount', 'status',
            'utilization_percentage', 'is_over_budget'
        ]


class FinancialReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.SerializerMethodField()
    
    def get_generated_by_name(self, obj):
        return obj.generated_by.get_full_name() if obj.generated_by else 'N/A'
    
    class Meta:
        model = FinancialReport
        fields = '__all__'
        read_only_fields = ['generated_by', 'file_path']
    
    def create(self, validated_data):
        try:
            validated_data['generated_by'] = self.context['request'].user.employee_get
        except AttributeError:
            # Handle case where user doesn't have employee profile
            validated_data['generated_by'] = None
        return super().create(validated_data)


class BudgetDashboardSerializer(serializers.Serializer):
    """Serializer for budget dashboard data"""
    total_budgets = serializers.IntegerField()
    active_budgets = serializers.IntegerField()
    total_allocated = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    over_budget_count = serializers.IntegerField()
    pending_expenses = serializers.IntegerField()
    recent_expenses = serializers.ListField()
    budget_utilization = serializers.ListField()
    monthly_spending = serializers.ListField()


class ExpenseApprovalSerializer(serializers.ModelSerializer):
    """Serializer for expense approval workflow"""
    
    class Meta:
        model = Expense
        fields = ['id', 'status', 'approved_by', 'approved_at']
        read_only_fields = ['approved_by', 'approved_at']
    
    def update(self, instance, validated_data):
        if validated_data.get('status') == 'approved':
            try:
                validated_data['approved_by'] = self.context['request'].user.employee_get
            except AttributeError:
                validated_data['approved_by'] = None
            validated_data['approved_at'] = timezone.now()
        return super().update(instance, validated_data)


class BudgetAnalyticsSerializer(serializers.Serializer):
    """Serializer for budget analytics data"""
    period = serializers.CharField()
    total_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    utilization_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    variance = serializers.DecimalField(max_digits=15, decimal_places=2)
    category_breakdown = serializers.ListField()
    trend_data = serializers.ListField()