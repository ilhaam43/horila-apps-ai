from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from budget.models import BudgetCategory, BudgetPlan, ExpenseType, Expense
from employee.models import Employee


class BudgetDashboardViewSetTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Add user to Budget Manager group
        budget_group, created = Group.objects.get_or_create(name='Budget Manager')
        self.user.groups.add(budget_group)
        
        # Create Employee instance
        self.employee = Employee.objects.create(
            employee_user_id=self.user,
            employee_first_name='Test',
            employee_last_name='Employee',
            email='test@example.com',
            phone='1234567890'
        )
        
        # Create API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.category = BudgetCategory.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.budget_plan = BudgetPlan.objects.create(
            name='Test Budget Plan',
            description='Test budget plan description',
            category=self.category,
            allocated_amount=Decimal('100000.00'),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status='active'
        )
        
        self.expense_type = ExpenseType.objects.create(
            name='Test Expense Type',
            description='Test expense type description'
        )
        
        # Create test expenses
        self.expense1 = Expense.objects.create(
            title='Test Expense 1',
            description='Test expense 1 description',
            amount=Decimal('5000.00'),
            expense_date=date.today(),
            budget_plan=self.budget_plan,
            expense_type=self.expense_type,
            requested_by=self.employee,
            status='approved'
        )
        
        self.expense2 = Expense.objects.create(
            title='Test Expense 2',
            description='Test expense 2 description',
            amount=Decimal('3000.00'),
            expense_date=date.today(),
            budget_plan=self.budget_plan,
            expense_type=self.expense_type,
            requested_by=self.employee,
            status='paid'
        )
    
    def test_dashboard_list(self):
        """Test dashboard list endpoint"""
        url = '/budget/dashboard/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_budgets', response.data)
        self.assertIn('active_budgets', response.data)
        self.assertIn('total_allocated', response.data)
        self.assertIn('total_spent', response.data)
    
    def test_monthly_expense_donut_current_month(self):
        """Test monthly expense donut chart endpoint for current month"""
        url = '/budget/dashboard/monthly_expense_donut/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('month', response.data)
        self.assertIn('month_name', response.data)
        self.assertIn('total_expenses', response.data)
        self.assertIn('categories', response.data)
        self.assertIn('chart_type', response.data)
        self.assertEqual(response.data['chart_type'], 'donut')
        
        # Check if categories data is properly formatted
        if response.data['categories']:
            category_data = response.data['categories'][0]
            self.assertIn('category_id', category_data)
            self.assertIn('category_name', category_data)
            self.assertIn('amount', category_data)
            self.assertIn('expense_count', category_data)
            self.assertIn('percentage', category_data)
    
    def test_monthly_expense_donut_specific_month(self):
        """Test monthly expense donut chart endpoint for specific month"""
        url = '/budget/dashboard/monthly_expense_donut/'
        current_date = timezone.now().date()
        response = self.client.get(url, {
            'month': current_date.month,
            'year': current_date.year
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('categories', response.data)
        
        # Should have data since we created expenses for today
        self.assertGreater(len(response.data['categories']), 0)
        
        # Check total expenses matches our test data
        expected_total = Decimal('8000.00')  # 5000 + 3000
        self.assertEqual(Decimal(str(response.data['total_expenses'])), expected_total)
    
    def test_monthly_expense_donut_no_data(self):
        """Test monthly expense donut chart endpoint with no data"""
        url = '/budget/dashboard/monthly_expense_donut/'
        # Request data for a future month with no expenses
        future_date = timezone.now().date().replace(year=timezone.now().year + 1)
        response = self.client.get(url, {
            'month': future_date.month,
            'year': future_date.year
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['categories']), 0)
        self.assertEqual(Decimal(str(response.data['total_expenses'])), Decimal('0'))
    
    def test_monthly_expense_donut_invalid_date(self):
        """Test monthly expense donut chart endpoint with invalid date parameters"""
        url = '/budget/dashboard/monthly_expense_donut/'
        response = self.client.get(url, {
            'month': 'invalid',
            'year': 'invalid'
        })
        
        # Should fallback to current month
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        current_month = timezone.now().strftime('%Y-%m')
        self.assertEqual(response.data['month'], current_month)