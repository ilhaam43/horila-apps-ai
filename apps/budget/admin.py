from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense, 
    ExpenseAttachment, BudgetAlert, FinancialReport, BudgetSettings
)


@admin.register(BudgetCategory)
class BudgetCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_category', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['name']


class ExpenseInline(admin.TabularInline):
    model = Expense
    extra = 0
    fields = ['title', 'amount', 'expense_date', 'status', 'priority']
    readonly_fields = ['created_at']


class BudgetAlertInline(admin.TabularInline):
    model = BudgetAlert
    extra = 0
    fields = ['alert_type', 'threshold_percentage', 'is_active', 'is_sent']


@admin.register(BudgetPlan)
class BudgetPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'period_type', 'start_date', 'end_date',
        'allocated_amount', 'spent_amount', 'utilization_display', 'status'
    ]
    list_filter = ['status', 'period_type', 'category', 'created_at']
    search_fields = ['name', 'description']
    date_hierarchy = 'start_date'
    readonly_fields = ['spent_amount', 'remaining_amount', 'utilization_percentage', 'is_over_budget']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Budget Details', {
            'fields': ('period_type', 'start_date', 'end_date', 'allocated_amount')
        }),
        ('Financial Status', {
            'fields': ('spent_amount', 'remaining_amount', 'utilization_percentage', 'is_over_budget'),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('status', 'created_by', 'approved_by', 'approved_at')
        })
    )
    inlines = [ExpenseInline, BudgetAlertInline]
    
    def utilization_display(self, obj):
        percentage = float(obj.utilization_percentage or 0)
        if percentage > 100:
            color = 'red'
        elif percentage > 80:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}">{:.1f}%</span>',
            color, percentage
        )
    utilization_display.short_description = 'Utilization'
    utilization_display.admin_order_field = 'spent_amount'


@admin.register(ExpenseType)
class ExpenseTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0
    fields = ['filename', 'file_size', 'uploaded_by', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'budget_plan', 'expense_type', 'amount', 
        'expense_date', 'status', 'priority', 'requested_by'
    ]
    list_filter = ['status', 'priority', 'expense_type', 'expense_date', 'created_at']
    search_fields = ['title', 'description', 'vendor_name', 'receipt_number']
    date_hierarchy = 'expense_date'
    fieldsets = (
        ('Expense Information', {
            'fields': ('budget_plan', 'expense_type', 'title', 'description')
        }),
        ('Financial Details', {
            'fields': ('amount', 'expense_date', 'receipt_number', 'vendor_name')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority')
        }),
        ('Approval Workflow', {
            'fields': ('requested_by', 'approved_by', 'approved_at', 'paid_at'),
            'classes': ('collapse',)
        })
    )
    inlines = [ExpenseAttachmentInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'budget_plan', 'expense_type', 'requested_by', 'approved_by'
        )


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ['filename', 'expense', 'file_size', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'expense__title']
    readonly_fields = ['file_size', 'uploaded_at']


@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    list_display = [
        'budget_plan', 'alert_type', 'threshold_percentage', 
        'is_active', 'is_sent', 'created_at'
    ]
    list_filter = ['alert_type', 'is_active', 'is_sent', 'created_at']
    search_fields = ['budget_plan__name', 'message']
    filter_horizontal = ['sent_to']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('budget_plan')


@admin.register(FinancialReport)
class FinancialReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'report_type', 'start_date', 'end_date', 
        'generated_by', 'created_at', 'download_link'
    ]
    list_filter = ['report_type', 'created_at']
    search_fields = ['name']
    date_hierarchy = 'created_at'
    readonly_fields = ['file_path', 'created_at']
    
    def download_link(self, obj):
        if obj.file_path:
            return format_html(
                '<a href="{}" target="_blank">Download</a>',
                obj.file_path
            )
        return 'No file'
    download_link.short_description = 'Download'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('generated_by')


@admin.register(BudgetSettings)
class BudgetSettingsAdmin(admin.ModelAdmin):
    list_display = ['currency_symbol', 'position', 'company_id']
    list_filter = ['position', 'company_id']
    fieldsets = (
        ('Currency Configuration', {
            'fields': ('currency_symbol', 'position', 'company_id')
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance per company
        return not BudgetSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False