from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from employee.models import Employee
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from base.models import Company
from base.horilla_company_manager import HorillaCompanyManager
from horilla.models import HorillaModel


class BudgetCategory(models.Model):
    """Categories for organizing budget plans"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Budget Categories"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class BudgetPlan(models.Model):
    """Main budget planning model"""
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(BudgetCategory, on_delete=models.CASCADE)
    period_type = models.CharField(max_length=20, choices=PERIOD_CHOICES, default='monthly')
    start_date = models.DateField()
    end_date = models.DateField()
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], default=Decimal('0.00'))
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='created_budgets', null=True, blank=True)
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_budgets')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['category']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', 'created_by']),
        ]
        unique_together = ['name', 'period_type', 'start_date']
    
    def __str__(self):
        return f"{self.name} - {self.period_type} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        self.remaining_amount = self.allocated_amount - self.spent_amount
        super().save(*args, **kwargs)
    
    @property
    def utilization_percentage(self):
        if self.allocated_amount > 0:
            return (self.spent_amount / self.allocated_amount) * 100
        return 0
    
    @property
    def is_over_budget(self):
        return self.spent_amount > self.allocated_amount


class ExpenseType(models.Model):
    """Types of expenses for categorization"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class Expense(models.Model):
    """Individual expense records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    budget_plan = models.ForeignKey(BudgetPlan, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.ForeignKey(ExpenseType, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    expense_date = models.DateField(default=timezone.now)
    receipt_number = models.CharField(max_length=100, blank=True)
    vendor_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    requested_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='requested_expenses', null=True, blank=True)
    approved_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['budget_plan']),
            models.Index(fields=['expense_type']),
            models.Index(fields=['status']),
            models.Index(fields=['requested_by']),
            models.Index(fields=['expense_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'budget_plan']),
            models.Index(fields=['expense_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.amount} ({self.status})"


class ExpenseAttachment(models.Model):
    """File attachments for expenses (receipts, invoices, etc.)"""
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='budget/attachments/%Y/%m/')
    filename = models.CharField(max_length=255, default='attachment')
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.filename} - {self.expense.title}"


class BudgetAlert(models.Model):
    """Alert system for budget monitoring"""
    ALERT_TYPES = [
        ('threshold', 'Threshold Alert'),
        ('overbudget', 'Over Budget Alert'),
        ('expiry', 'Budget Expiry Alert'),
        ('approval', 'Approval Required Alert'),
    ]
    
    budget_plan = models.ForeignKey(BudgetPlan, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    threshold_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    is_sent = models.BooleanField(default=False)
    sent_to = models.ManyToManyField(Employee, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['budget_plan']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_sent']),
            models.Index(fields=['created_at']),
            models.Index(fields=['alert_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.budget_plan.name} - {self.alert_type}"


class FinancialReport(models.Model):
    """Generated financial reports"""
    REPORT_TYPES = [
        ('budget_summary', 'Budget Summary'),
        ('expense_analysis', 'Expense Analysis'),
        ('variance_report', 'Variance Report'),
        ('cash_flow', 'Cash Flow Report'),
        ('department_wise', 'Department Wise Report'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    generated_by = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report_type']),
            models.Index(fields=['generated_by']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['report_type', 'generated_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.report_type})"


class BudgetSettings(HorillaModel):
    """Budget configuration settings"""
    
    POSITION_CHOICES = [
        ("prefix", _("Prefix")),
        ("postfix", _("Postfix")),
    ]
    
    currency_symbol = models.CharField(
        max_length=5, 
        default="$", 
        null=True,
        verbose_name=_("Currency Symbol")
    )
    position = models.CharField(
        max_length=15, 
        choices=POSITION_CHOICES, 
        default="postfix",
        null=True,
        verbose_name=_("Position")
    )
    company_id = models.ForeignKey(
        Company, 
        null=True, 
        on_delete=models.PROTECT,
        verbose_name=_("Company")
    )
    
    objects = HorillaCompanyManager("company_id")
    
    class Meta:
        verbose_name = _("Budget Settings")
        verbose_name_plural = _("Budget Settings")
    
    def __str__(self):
        return f"Budget Settings {self.currency_symbol}"