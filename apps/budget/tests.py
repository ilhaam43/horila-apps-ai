from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from .models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense,
    BudgetAlert, FinancialReport, BudgetSettings
)
from employee.models import Employee
from base.models import Company


class BudgetModelTests(TestCase):
    """Test cases for Budget models"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user and company
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            company='Test Company',
            address='Test Address',
            country='Test Country',
            state='Test State',
            city='Test City'
        )
        
        # Create test employee
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='User',
            email='test@example.com',
            badge_id='EMP001'
        )
        
        # Create test budget category
        self.category = BudgetCategory.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        
        # Create test expense type
        self.expense_type = ExpenseType.objects.create(
            name='Test Expense Type',
            description='Test expense type description',
            is_active=True
        )
    
    def test_budget_category_creation(self):
        """Test budget category creation"""
        self.assertEqual(self.category.name, 'Test Category')
        self.assertTrue(self.category.is_active)
        self.assertIsNotNone(self.category.created_at)
    
    def test_budget_plan_creation(self):
        """Test budget plan creation"""
        budget_plan = BudgetPlan.objects.create(
            name='Test Budget Plan',
            description='Test budget plan description',
            category=self.category,
            period_type='monthly',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            allocated_amount=Decimal('10000.00'),
            status='draft',
            created_by=self.employee
        )
        
        self.assertEqual(budget_plan.name, 'Test Budget Plan')
        self.assertEqual(budget_plan.allocated_amount, Decimal('10000.00'))
        self.assertEqual(budget_plan.spent_amount, Decimal('0.00'))
        self.assertEqual(budget_plan.remaining_amount, Decimal('10000.00'))
        self.assertEqual(budget_plan.utilization_percentage, 0)
        self.assertFalse(budget_plan.is_over_budget)
    
    def test_expense_creation(self):
        """Test expense creation"""
        budget_plan = BudgetPlan.objects.create(
            name='Test Budget Plan',
            category=self.category,
            period_type='monthly',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            allocated_amount=Decimal('10000.00'),
            status='active',
            created_by=self.employee
        )
        
        expense = Expense.objects.create(
            title='Test Expense',
            description='Test expense description',
            amount=Decimal('500.00'),
            expense_date=date.today(),
            budget_plan=budget_plan,
            expense_type=self.expense_type,
            requested_by=self.employee,
            status='approved'
        )
        
        self.assertEqual(expense.title, 'Test Expense')
        self.assertEqual(expense.amount, Decimal('500.00'))
        self.assertEqual(expense.status, 'approved')
    
    def test_budget_settings_creation(self):
        """Test budget settings creation"""
        settings = BudgetSettings.objects.create(
            currency_symbol='$',
            position='prefix',
            company_id=self.company
        )
        
        self.assertEqual(settings.currency_symbol, '$')
        self.assertEqual(settings.position, 'prefix')
        self.assertEqual(settings.company_id, self.company)


class BudgetViewTests(TestCase):
    """Test cases for Budget views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.company = Company.objects.create(
            company='Test Company',
            address='Test Address',
            country='Test Country',
            state='Test State',
            city='Test City'
        )
        
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='User',
            email='test@example.com',
            badge_id='EMP001'
        )
        
        self.category = BudgetCategory.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
    
    def test_dashboard_view(self):
        """Test budget dashboard view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('budget:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Budget Control Dashboard')
    
    def test_budget_settings_view(self):
        """Test budget settings view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('budget:budget_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Currency Configuration')
    
    def test_category_list_view(self):
        """Test category list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('budget:category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Budget Categories')
    
    def test_expense_type_list_view(self):
        """Test expense type list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('budget:expense_type_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Expense Types')
    
    def test_report_list_view(self):
        """Test report list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('budget:report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Budget Reports')


class BudgetFilterTests(TestCase):
    """Test cases for Budget filters"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='User',
            email='test@example.com',
            badge_id='EMP001'
        )
        
        # Create test categories
        self.category1 = BudgetCategory.objects.create(
            name='Active Category',
            description='Active category description',
            is_active=True
        )
        
        self.category2 = BudgetCategory.objects.create(
            name='Inactive Category',
            description='Inactive category description',
            is_active=False
        )
        
        # Create test expense types
        self.expense_type1 = ExpenseType.objects.create(
            name='Active Expense Type',
            description='Active expense type description',
            is_active=True
        )
        
        self.expense_type2 = ExpenseType.objects.create(
            name='Inactive Expense Type',
            description='Inactive expense type description',
            is_active=False
        )
    
    def test_category_filter_by_status(self):
        """Test category filtering by status"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test active filter
        response = self.client.get(reverse('budget:category_list') + '?status=active')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Category')
        self.assertNotContains(response, 'Inactive Category')
        
        # Test inactive filter
        response = self.client.get(reverse('budget:category_list') + '?status=inactive')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inactive Category')
        self.assertNotContains(response, 'Active Category')
    
    def test_expense_type_filter_by_status(self):
        """Test expense type filtering by status"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test active filter
        response = self.client.get(reverse('budget:expense_type_list') + '?status=active')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Expense Type')
        self.assertNotContains(response, 'Inactive Expense Type')
        
        # Test inactive filter
        response = self.client.get(reverse('budget:expense_type_list') + '?status=inactive')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inactive Expense Type')
        self.assertNotContains(response, 'Active Expense Type')
    
    def test_category_search_filter(self):
        """Test category search functionality"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('budget:category_list') + '?search=Active')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Category')
    
    def test_expense_type_search_filter(self):
        """Test expense type search functionality"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('budget:expense_type_list') + '?search=Active')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Expense Type')


class BudgetUtilsTests(TestCase):
    """Test cases for Budget utilities"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='User',
            email='test@example.com',
            badge_id='EMP001'
        )
        
        self.category = BudgetCategory.objects.create(
            name='Test Category',
            description='Test category description',
            is_active=True
        )
        
        self.budget_plan = BudgetPlan.objects.create(
            name='Test Budget Plan',
            category=self.category,
            period_type='monthly',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            allocated_amount=Decimal('10000.00'),
            status='active',
            created_by=self.employee
        )
    
    def test_budget_utilization_calculation(self):
        """Test budget utilization percentage calculation"""
        # Initially no expenses, utilization should be 0
        self.assertEqual(self.budget_plan.utilization_percentage, 0)
        
        # Add expense type
        expense_type = ExpenseType.objects.create(
            name='Test Expense Type',
            description='Test expense type description',
            is_active=True
        )
        
        # Create expense
        Expense.objects.create(
            title='Test Expense',
            amount=Decimal('2000.00'),
            expense_date=date.today(),
            budget_plan=self.budget_plan,
            expense_type=expense_type,
            requested_by=self.employee,
            status='approved'
        )
        
        # Refresh budget plan from database
        self.budget_plan.refresh_from_db()
        
        # Utilization should be 20% (2000/10000 * 100)
        self.assertEqual(self.budget_plan.utilization_percentage, 20)
    
    def test_over_budget_detection(self):
        """Test over budget detection"""
        # Initially not over budget
        self.assertFalse(self.budget_plan.is_over_budget)
        
        # Add expense type
        expense_type = ExpenseType.objects.create(
            name='Test Expense Type',
            description='Test expense type description',
            is_active=True
        )
        
        # Create expense that exceeds budget
        Expense.objects.create(
            title='Large Expense',
            amount=Decimal('12000.00'),
            expense_date=date.today(),
            budget_plan=self.budget_plan,
            expense_type=expense_type,
            requested_by=self.employee,
            status='approved'
        )
        
        # Refresh budget plan from database
        self.budget_plan.refresh_from_db()
        
        # Should be over budget now
        self.assertTrue(self.budget_plan.is_over_budget)