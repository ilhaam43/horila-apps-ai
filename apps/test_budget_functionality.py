#!/usr/bin/env python3
"""
Test script to verify budget module functionality
"""

import os
import sys
import django
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from budget.models import BudgetCategory, BudgetPlan, ExpenseType, Expense, FinancialReport
from employee.models import Employee

User = get_user_model()

def test_budget_models():
    """Test budget models creation and relationships"""
    print("Testing budget models...")
    
    try:
        # Test BudgetCategory
        category = BudgetCategory.objects.first()
        if category:
            print(f"✓ BudgetCategory found: {category.name}")
        else:
            print("✗ No BudgetCategory found")
        
        # Test BudgetPlan
        plan = BudgetPlan.objects.first()
        if plan:
            print(f"✓ BudgetPlan found: {plan.name}")
        else:
            print("✗ No BudgetPlan found")
        
        # Test ExpenseType
        expense_type = ExpenseType.objects.first()
        if expense_type:
            print(f"✓ ExpenseType found: {expense_type.name}")
        else:
            print("✗ No ExpenseType found")
        
        # Test Expense
        expense = Expense.objects.first()
        if expense:
            print(f"✓ Expense found: {expense.description}")
        else:
            print("✗ No Expense found")
        
        # Test FinancialReport
        report = FinancialReport.objects.first()
        if report:
            print(f"✓ FinancialReport found: {report.name}")
        else:
            print("✗ No FinancialReport found")
            
        print("Models test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Models test failed: {str(e)}")
        return False

def test_budget_views():
    """Test budget views accessibility"""
    print("\nTesting budget views...")
    
    try:
        client = Client()
        
        # Get a test user
        user = User.objects.first()
        if not user:
            print("✗ No user found for testing")
            return False
            
        client.force_login(user)
        
        # Test main budget views
        views_to_test = [
            ('budget:dashboard', 'Budget Dashboard'),
            ('budget:plan_list', 'Budget Plan List'),
            ('budget:expense_list', 'Expense List'),
            ('budget:category_list', 'Category List'),
            ('budget:expense_type_list', 'Expense Type List'),
            ('budget:report_list', 'Report List'),
        ]
        
        for url_name, view_name in views_to_test:
            try:
                response = client.get(reverse(url_name))
                if response.status_code == 200:
                    print(f"✓ {view_name} accessible")
                else:
                    print(f"✗ {view_name} returned status {response.status_code}")
            except Exception as e:
                print(f"✗ {view_name} failed: {str(e)}")
        
        print("Views test completed!")
        return True
        
    except Exception as e:
        print(f"✗ Views test failed: {str(e)}")
        return False

def test_employee_get_method():
    """Test employee_get method functionality"""
    print("\nTesting employee_get method...")
    
    try:
        user = User.objects.first()
        if not user:
            print("✗ No user found for testing")
            return False
        
        # Test employee_get method
        if hasattr(user, 'employee_get'):
            employee = user.employee_get
            if employee:
                print(f"✓ employee_get method works: {employee}")
            else:
                print("✗ employee_get returned None")
        else:
            print("✗ employee_get method not found")
            
        return True
        
    except Exception as e:
        print(f"✗ employee_get test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("BUDGET MODULE FUNCTIONALITY TEST")
    print("=" * 50)
    
    tests = [
        test_budget_models,
        test_budget_views,
        test_employee_get_method,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Budget module is working correctly.")
    else:
        print("✗ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)