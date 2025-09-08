#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import models
from employee.models import Employee
from budget.models import BudgetCategory, BudgetPlan, ExpenseType, Expense

def create_test_data():
    print("Creating test data for budget filtering...")
    
    # Get or create admin user
    try:
        admin_user = User.objects.get(username='admin')
        admin_employee = admin_user.employee_get
        print(f"Using existing admin user: {admin_user.username}")
    except User.DoesNotExist:
        print("Admin user not found. Please run create_budget_user.py first.")
        return
    
    # Create Budget Categories
    categories_data = [
        {'name': 'Operations', 'description': 'Operational expenses'},
        {'name': 'Marketing', 'description': 'Marketing and advertising'},
        {'name': 'IT & Technology', 'description': 'Technology infrastructure'},
        {'name': 'Human Resources', 'description': 'HR related expenses'},
        {'name': 'Facilities', 'description': 'Office and facility costs'},
    ]
    
    categories = []
    for cat_data in categories_data:
        category, created = BudgetCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'is_active': True
            }
        )
        categories.append(category)
        if created:
            print(f"Created category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")
    
    # Create Expense Types
    expense_types_data = [
        {'name': 'Office Supplies', 'description': 'General office supplies'},
        {'name': 'Software License', 'description': 'Software licensing costs'},
        {'name': 'Travel', 'description': 'Business travel expenses'},
        {'name': 'Training', 'description': 'Employee training and development'},
        {'name': 'Equipment', 'description': 'Office equipment and hardware'},
    ]
    
    expense_types = []
    for exp_type_data in expense_types_data:
        expense_type, created = ExpenseType.objects.get_or_create(
            name=exp_type_data['name'],
            defaults={
                'description': exp_type_data['description'],
                'is_active': True
            }
        )
        expense_types.append(expense_type)
        if created:
            print(f"Created expense type: {expense_type.name}")
        else:
            print(f"Expense type already exists: {expense_type.name}")
    
    # Create Budget Plans
    today = datetime.now().date()
    plans_data = [
        {
            'name': 'Q2 2024 Facilities Budget',
            'category': categories[4],  # Facilities
            'allocated_amount': Decimal('45000.00'),
            'start_date': today - timedelta(days=60),
            'end_date': today + timedelta(days=30),
            'status': 'active'
        },
        {
            'name': '2024 Annual Training Budget',
            'category': categories[3],  # Human Resources
            'allocated_amount': Decimal('120000.00'),
            'start_date': today - timedelta(days=30),
            'end_date': today + timedelta(days=335),
            'status': 'active'
        },
        {
            'name': 'February 2024 HR Budget',
            'category': categories[3],  # Human Resources
            'allocated_amount': Decimal('18000.00'),
            'start_date': today - timedelta(days=90),
            'end_date': today - timedelta(days=60),
            'status': 'completed'
        },
        {
            'name': 'January 2024 IT Budget',
            'category': categories[2],  # IT & Technology
            'allocated_amount': Decimal('25000.00'),
            'start_date': today - timedelta(days=120),
            'end_date': today - timedelta(days=90),
            'status': 'completed'
        },
        {
            'name': 'Q1 2024 Marketing Budget',
            'category': categories[1],  # Marketing
            'allocated_amount': Decimal('75000.00'),
            'start_date': today - timedelta(days=150),
            'end_date': today - timedelta(days=60),
            'status': 'completed'
        },
        {
            'name': 'Q1 2024 Operations Budget',
            'category': categories[0],  # Operations
            'allocated_amount': Decimal('85000.00'),
            'start_date': today - timedelta(days=150),
            'end_date': today - timedelta(days=60),
            'status': 'completed'
        },
    ]
    
    plans = []
    for plan_data in plans_data:
        plan, created = BudgetPlan.objects.get_or_create(
            name=plan_data['name'],
            defaults={
                'category': plan_data['category'],
                'allocated_amount': plan_data['allocated_amount'],
                'start_date': plan_data['start_date'],
                'end_date': plan_data['end_date'],
                'status': plan_data['status'],
                'created_by': admin_employee,
                'approved_by': admin_employee,
                'description': f"Test budget plan for {plan_data['category'].name}"
            }
        )
        plans.append(plan)
        if created:
            print(f"Created budget plan: {plan.name}")
        else:
            print(f"Budget plan already exists: {plan.name}")
    
    # Create Expenses
    expenses_data = [
        {
            'description': 'Office supplies for Q2',
            'budget_plan': plans[0],  # Facilities
            'expense_type': expense_types[0],  # Office Supplies
            'amount': Decimal('1500.00'),
            'status': 'approved',
            'expense_date': today - timedelta(days=10)
        },
        {
            'description': 'Adobe Creative Suite License',
            'budget_plan': plans[1],  # Training
            'expense_type': expense_types[1],  # Software License
            'amount': Decimal('2800.00'),
            'status': 'paid',
            'expense_date': today - timedelta(days=15)
        },
        {
            'description': 'Business trip to client meeting',
            'budget_plan': plans[5],  # Operations
            'expense_type': expense_types[2],  # Travel
            'amount': Decimal('3200.00'),
            'status': 'approved',
            'expense_date': today - timedelta(days=20)
        },
        {
            'description': 'Employee training workshop',
            'budget_plan': plans[1],  # Training
            'expense_type': expense_types[3],  # Training
            'amount': Decimal('4500.00'),
            'status': 'pending',
            'expense_date': today - timedelta(days=5)
        },
        {
            'description': 'New laptops for development team',
            'budget_plan': plans[3],  # IT Budget
            'expense_type': expense_types[4],  # Equipment
            'amount': Decimal('12000.00'),
            'status': 'rejected',
            'expense_date': today - timedelta(days=30)
        },
        {
            'description': 'Marketing campaign materials',
            'budget_plan': plans[4],  # Marketing
            'expense_type': expense_types[0],  # Office Supplies
            'amount': Decimal('5500.00'),
            'status': 'paid',
            'expense_date': today - timedelta(days=45)
        },
    ]
    
    for exp_data in expenses_data:
        expense, created = Expense.objects.get_or_create(
            description=exp_data['description'],
            budget_plan=exp_data['budget_plan'],
            defaults={
                'expense_type': exp_data['expense_type'],
                'amount': exp_data['amount'],
                'status': exp_data['status'],
                'expense_date': exp_data['expense_date'],
                'requested_by': admin_employee,
                'approved_by': admin_employee if exp_data['status'] in ['approved', 'paid'] else None,
                'vendor_name': 'Test Vendor',
                'receipt_number': f'RCP-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            }
        )
        if created:
            print(f"Created expense: {expense.description}")
        else:
            print(f"Expense already exists: {expense.description}")
    
    # Update spent amounts for budget plans
    for plan in plans:
        total_spent = Expense.objects.filter(
            budget_plan=plan,
            status__in=['approved', 'paid']
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        plan.spent_amount = total_spent
        plan.save()
        print(f"Updated spent amount for {plan.name}: ${total_spent}")
    
    print("\nTest data creation completed!")
    print(f"Created {len(categories)} categories")
    print(f"Created {len(expense_types)} expense types")
    print(f"Created {len(plans)} budget plans")
    print(f"Created {len(expenses_data)} expenses")

if __name__ == '__main__':
    create_test_data()