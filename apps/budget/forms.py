from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from .models import BudgetPlan, Expense, BudgetCategory, ExpenseType, BudgetSettings


class BudgetPlanForm(forms.ModelForm):
    """Form for creating and editing budget plans"""
    
    class Meta:
        model = BudgetPlan
        fields = [
            'name', 'description', 'category', 'period_type',
            'allocated_amount', 'start_date', 'end_date', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter budget plan name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the purpose of this budget plan'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'period_type': forms.Select(attrs={'class': 'form-control'}),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-control'})
        }
    
    def clean_allocated_amount(self):
        allocated_amount = self.cleaned_data.get('allocated_amount')
        if allocated_amount:
            # Validate 12-digit support (max 999,999,999,999.99)
            if allocated_amount >= Decimal('1000000000000'):
                raise ValidationError('Amount cannot exceed 999,999,999,999.99 (12 digits maximum)')
            if allocated_amount <= 0:
                raise ValidationError('Allocated amount must be greater than zero.')
        return allocated_amount
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('End date must be after start date.')
        
        return cleaned_data


class ExpenseForm(forms.ModelForm):
    """Form for creating and editing expenses"""
    
    class Meta:
        model = Expense
        fields = [
            'title', 'description', 'budget_plan', 'expense_type',
            'amount', 'expense_date', 'receipt_number', 'vendor_name'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter expense title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the expense'
            }),
            'budget_plan': forms.Select(attrs={'class': 'form-control'}),
            'expense_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'expense_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Receipt/Invoice number'
            }),
            'vendor_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vendor/Supplier name'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter budget plans based on user permissions
        if user:
            if user.groups.filter(name='Budget Manager').exists():
                # Budget managers can see all active budget plans
                self.fields['budget_plan'].queryset = BudgetPlan.objects.filter(
                    status='active'
                )
            else:
                # Regular users can only see budget plans from their department
                if hasattr(user, 'employee_get') and user.employee_get.employee_work_info.department_id:
                    self.fields['budget_plan'].queryset = BudgetPlan.objects.filter(
                        department=user.employee_get.employee_work_info.department_id,
                        status='active'
                    )
                else:
                    self.fields['budget_plan'].queryset = BudgetPlan.objects.none()
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount:
            # Validate 12-digit support (max 999,999,999,999.99)
            if amount >= Decimal('1000000000000'):
                raise ValidationError('Amount cannot exceed 999,999,999,999.99 (12 digits maximum)')
            if amount <= 0:
                raise ValidationError('Amount must be greater than zero.')
        return amount
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        budget_plan = cleaned_data.get('budget_plan')
        expense_date = cleaned_data.get('expense_date')
        
        if amount and amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        
        if budget_plan and expense_date:
            if expense_date < budget_plan.start_date or expense_date > budget_plan.end_date:
                raise ValidationError(
                    f'Expense date must be between {budget_plan.start_date} and {budget_plan.end_date}.'
                )
        
        return cleaned_data


class BudgetCategoryForm(forms.ModelForm):
    """Form for creating and editing budget categories"""
    
    class Meta:
        model = BudgetCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter category name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this category'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class ExpenseTypeForm(forms.ModelForm):
    """Form for creating and editing expense types"""
    
    class Meta:
        model = ExpenseType
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter expense type name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe this expense type'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }


class ExpenseApprovalForm(forms.Form):
    """Form for approving/rejecting expenses"""
    
    APPROVAL_CHOICES = [
        ('approved', 'Approve'),
        ('rejected', 'Reject')
    ]
    
    action = forms.ChoiceField(
        choices=APPROVAL_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add approval/rejection notes (optional)'
        })
    )


class BudgetReportForm(forms.Form):
    """Form for generating budget reports"""
    
    REPORT_TYPE_CHOICES = [
        ('budget_summary', 'Budget Summary'),
        ('expense_analysis', 'Expense Analysis'),
        ('variance_report', 'Variance Report'),
        ('category_spending', 'Category Spending')
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    category = forms.ModelChoiceField(
        queryset=BudgetCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Categories'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('End date must be after start date.')
            
            # Check if date range is not too large (max 1 year)
            if (end_date - start_date).days > 365:
                raise ValidationError('Date range cannot exceed 1 year.')
        
        return cleaned_data


class BudgetFilterForm(forms.Form):
    """Form for filtering budget plans and expenses"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('', 'All Approval Statuses'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name or description'
        })
    )
    category = forms.ModelChoiceField(
        queryset=BudgetCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Categories'
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    approval_status = forms.ChoiceField(
        choices=APPROVAL_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class BudgetSettingsForm(forms.ModelForm):
    """Form for Budget Settings model"""
    
    class Meta:
        model = BudgetSettings
        fields = ['currency_symbol', 'position', 'company_id']
        widgets = {
            'currency_symbol': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter currency symbol (e.g., $, €, ¥)',
                'maxlength': '5'
            }),
            'position': forms.Select(attrs={
                'class': 'form-control'
            }),
            'company_id': forms.Select(attrs={
                'class': 'form-control'
            })
        }