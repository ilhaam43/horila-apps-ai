from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date
from budget.forms import BudgetPlanForm, ExpenseForm
from budget.models import BudgetCategory, BudgetPlan, ExpenseType
from employee.models import Employee
from django.contrib.auth.models import User
from dynamic_fields.forms import _thread_locals


class TwelveDigitValidationTest(TestCase):
    """Test cases for 12-digit validation in budget forms"""
    
    def setUp(self):
        """Set up test data"""
        # Create request factory
        self.factory = RequestFactory()
        
        # Create test user and employee
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Add user to Budget Manager group
        from django.contrib.auth.models import Group
        budget_manager_group, created = Group.objects.get_or_create(name='Budget Manager')
        self.user.groups.add(budget_manager_group)
        
        # Create test employee
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='User'
        )
        
        # Setup request for thread locals
        request = self.factory.get('/')
        request.user = self.user
        # Add session to request
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        _thread_locals.request = request
        
        # Create test category
        self.category = BudgetCategory.objects.create(
            name='Test Category',
            description='Test category for validation'
        )
        
        # Create test expense type
        self.expense_type = ExpenseType.objects.create(
            name='Test Expense Type',
            description='Test expense type for validation'
        )
        
        # Create test budget plan
        self.budget_plan = BudgetPlan.objects.create(
            name='Test Budget Plan',
            category=self.category,
            period_type='monthly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            allocated_amount=Decimal('100000.00'),
            status='active',
            created_by=self.employee
        )
    
    def test_budget_plan_form_valid_12_digit_amount(self):
        """Test BudgetPlanForm accepts valid 12-digit amounts"""
        form_data = {
            'name': 'Test Budget',
            'description': 'Test description',
            'category': self.category.id,
            'period_type': 'monthly',
            'allocated_amount': '999999999999.99',  # Max 12 digits
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'status': 'draft'
        }
        form = BudgetPlanForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_budget_plan_form_invalid_over_12_digit_amount(self):
        """Test BudgetPlanForm rejects amounts over 12 digits"""
        form_data = {
            'name': 'Test Budget',
            'description': 'Test description',
            'category': self.category.id,
            'period_type': 'monthly',
            'allocated_amount': '1000000000000.00',  # Over 12 digits
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'status': 'draft'
        }
        form = BudgetPlanForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('allocated_amount', form.errors)
        self.assertIn('12 digits maximum', str(form.errors['allocated_amount']))
    
    def test_budget_plan_form_invalid_zero_amount(self):
        """Test BudgetPlanForm rejects zero amounts"""
        form_data = {
            'name': 'Test Budget',
            'description': 'Test description',
            'category': self.category.id,
            'period_type': 'monthly',
            'allocated_amount': '0.00',
            'start_date': '2024-01-01',
            'end_date': '2024-01-31',
            'status': 'draft'
        }
        form = BudgetPlanForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('allocated_amount', form.errors)
    
    def test_expense_form_valid_12_digit_amount(self):
        """Test ExpenseForm accepts valid 12-digit amounts"""
        form_data = {
            'title': 'Test Expense',
            'description': 'Test expense description',
            'budget_plan': str(self.budget_plan.id),
            'expense_type': self.expense_type.id,
            'amount': '999999999999.99',  # Max 12 digits
            'expense_date': '2024-01-15',
            'receipt_number': 'REC001',
            'vendor_name': 'Test Vendor'
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
    
    def test_expense_form_invalid_over_12_digit_amount(self):
        """Test ExpenseForm rejects amounts over 12 digits"""
        form_data = {
            'title': 'Test Expense',
            'description': 'Test expense description',
            'budget_plan': str(self.budget_plan.id),
            'expense_type': self.expense_type.id,
            'amount': '1000000000000.00',  # Over 12 digits
            'expense_date': '2024-01-15',
            'receipt_number': 'REC001',
            'vendor_name': 'Test Vendor'
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
        self.assertIn('12 digits maximum', str(form.errors['amount']))
    
    def test_expense_form_invalid_zero_amount(self):
        """Test ExpenseForm rejects zero amounts"""
        form_data = {
            'title': 'Test Expense',
            'description': 'Test expense description',
            'budget_plan': str(self.budget_plan.id),
            'expense_type': self.expense_type.id,
            'amount': '0.00',
            'expense_date': '2024-01-15',
            'receipt_number': 'REC001',
            'vendor_name': 'Test Vendor'
        }
        form = ExpenseForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_model_supports_12_digit_amounts(self):
        """Test that models can store 12-digit amounts"""
        # Test BudgetPlan model
        budget_plan = BudgetPlan.objects.create(
            name='12 Digit Test Budget',
            category=self.category,
            period_type='yearly',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            allocated_amount=Decimal('999999999999.99'),
            created_by=self.employee
        )
        self.assertEqual(budget_plan.allocated_amount, Decimal('999999999999.99'))
        
        # Test that the budget plan can be saved and retrieved
        saved_plan = BudgetPlan.objects.get(id=budget_plan.id)
        self.assertEqual(saved_plan.allocated_amount, Decimal('999999999999.99'))