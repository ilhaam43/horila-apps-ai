from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random

from budget.models import (
    BudgetCategory, BudgetPlan, ExpenseType, Expense, 
    BudgetAlert, FinancialReport
)
from employee.models import Employee


class Command(BaseCommand):
    help = 'Load dummy data for budget module'

    def handle(self, *args, **options):
        self.stdout.write('Loading budget dummy data...')
        
        # Get active employees
        employees = Employee.objects.filter(is_active=True)[:10]
        if not employees.exists():
            self.stdout.write(
                self.style.ERROR('No active employees found. Please create employees first.')
            )
            return
        
        # Create Budget Categories
        self.create_budget_categories()
        
        # Create Expense Types
        self.create_expense_types()
        
        # Create Budget Plans
        self.create_budget_plans(employees)
        
        # Create Expenses
        self.create_expenses(employees)
        
        # Create Budget Alerts
        self.create_budget_alerts(employees)
        
        # Create Financial Reports
        self.create_financial_reports(employees)
        
        self.stdout.write(
            self.style.SUCCESS('Successfully loaded budget dummy data!')
        )
    
    def create_budget_categories(self):
        categories_data = [
            {'name': 'Operations', 'description': 'Day-to-day operational expenses'},
            {'name': 'Marketing', 'description': 'Marketing and advertising expenses'},
            {'name': 'IT & Technology', 'description': 'Technology infrastructure and software'},
            {'name': 'Human Resources', 'description': 'HR related expenses'},
            {'name': 'Travel & Entertainment', 'description': 'Business travel and entertainment'},
            {'name': 'Office Supplies', 'description': 'Office equipment and supplies'},
            {'name': 'Training & Development', 'description': 'Employee training and development'},
            {'name': 'Facilities', 'description': 'Office rent and utilities'},
        ]
        
        for cat_data in categories_data:
            category, created = BudgetCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')
    
    def create_expense_types(self):
        expense_types_data = [
            {'name': 'Software License', 'description': 'Software licensing fees'},
            {'name': 'Office Rent', 'description': 'Monthly office rent'},
            {'name': 'Utilities', 'description': 'Electricity, water, internet'},
            {'name': 'Marketing Campaign', 'description': 'Advertising and promotion'},
            {'name': 'Training Course', 'description': 'Employee training programs'},
            {'name': 'Business Travel', 'description': 'Travel expenses for business'},
            {'name': 'Office Equipment', 'description': 'Computers, furniture, etc.'},
            {'name': 'Consulting Services', 'description': 'External consulting fees'},
            {'name': 'Maintenance', 'description': 'Equipment and facility maintenance'},
            {'name': 'Supplies', 'description': 'General office supplies'},
        ]
        
        for exp_data in expense_types_data:
            expense_type, created = ExpenseType.objects.get_or_create(
                name=exp_data['name'],
                defaults={'description': exp_data['description']}
            )
            if created:
                self.stdout.write(f'Created expense type: {expense_type.name}')
    
    def create_budget_plans(self, employees):
        categories = BudgetCategory.objects.all()
        current_date = date.today()
        
        budget_plans_data = [
            {
                'name': 'Q1 2024 Operations Budget',
                'period_type': 'quarterly',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 3, 31),
                'allocated_amount': Decimal('150000.00'),
                'spent_amount': Decimal('89500.00'),
                'status': 'active'
            },
            {
                'name': 'Q1 2024 Marketing Budget',
                'period_type': 'quarterly', 
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 3, 31),
                'allocated_amount': Decimal('75000.00'),
                'spent_amount': Decimal('52300.00'),
                'status': 'active'
            },
            {
                'name': 'January 2024 IT Budget',
                'period_type': 'monthly',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 1, 31),
                'allocated_amount': Decimal('25000.00'),
                'spent_amount': Decimal('23800.00'),
                'status': 'completed'
            },
            {
                'name': 'February 2024 HR Budget',
                'period_type': 'monthly',
                'start_date': date(2024, 2, 1),
                'end_date': date(2024, 2, 29),
                'allocated_amount': Decimal('18000.00'),
                'spent_amount': Decimal('15600.00'),
                'status': 'completed'
            },
            {
                'name': '2024 Annual Training Budget',
                'period_type': 'yearly',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 12, 31),
                'allocated_amount': Decimal('120000.00'),
                'spent_amount': Decimal('35000.00'),
                'status': 'active'
            },
            {
                'name': 'Q2 2024 Facilities Budget',
                'period_type': 'quarterly',
                'start_date': date(2024, 4, 1),
                'end_date': date(2024, 6, 30),
                'allocated_amount': Decimal('45000.00'),
                'spent_amount': Decimal('12000.00'),
                'status': 'approved'
            }
        ]
        
        for i, plan_data in enumerate(budget_plans_data):
            category = categories[i % len(categories)]
            employee = employees[i % len(employees)]
            
            budget_plan, created = BudgetPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'category': category,
                    'period_type': plan_data['period_type'],
                    'start_date': plan_data['start_date'],
                    'end_date': plan_data['end_date'],
                    'allocated_amount': plan_data['allocated_amount'],
                    'spent_amount': plan_data['spent_amount'],
                    'status': plan_data['status'],
                    'created_by': employee,
                    'approved_by': employee if plan_data['status'] in ['approved', 'active'] else None,
                    'approved_at': timezone.now() if plan_data['status'] in ['approved', 'active'] else None,
                }
            )
            if created:
                self.stdout.write(f'Created budget plan: {budget_plan.name}')
    
    def create_expenses(self, employees):
        budget_plans = BudgetPlan.objects.all()
        expense_types = ExpenseType.objects.all()
        
        expenses_data = [
            {
                'title': 'Microsoft Office 365 License',
                'description': 'Annual subscription for Microsoft Office 365 for 50 users',
                'amount': Decimal('15000.00'),
                'expense_date': date(2024, 1, 15),
                'receipt_number': 'RCP-2024-001',
                'vendor_name': 'Microsoft Corporation',
                'status': 'approved',
                'priority': 'high'
            },
            {
                'title': 'Office Rent - January 2024',
                'description': 'Monthly office rent payment for headquarters',
                'amount': Decimal('25000.00'),
                'expense_date': date(2024, 1, 1),
                'receipt_number': 'RCP-2024-002',
                'vendor_name': 'Property Management Co.',
                'status': 'paid',
                'priority': 'high'
            },
            {
                'title': 'Google Ads Campaign',
                'description': 'Digital marketing campaign for Q1 product launch',
                'amount': Decimal('12500.00'),
                'expense_date': date(2024, 1, 20),
                'receipt_number': 'RCP-2024-003',
                'vendor_name': 'Google LLC',
                'status': 'approved',
                'priority': 'medium'
            },
            {
                'title': 'Employee Training Workshop',
                'description': 'Leadership development workshop for managers',
                'amount': Decimal('8500.00'),
                'expense_date': date(2024, 2, 5),
                'receipt_number': 'RCP-2024-004',
                'vendor_name': 'Training Solutions Inc.',
                'status': 'approved',
                'priority': 'medium'
            },
            {
                'title': 'Business Travel - Client Meeting',
                'description': 'Flight and accommodation for client presentation',
                'amount': Decimal('3200.00'),
                'expense_date': date(2024, 2, 12),
                'receipt_number': 'RCP-2024-005',
                'vendor_name': 'Travel Agency Ltd.',
                'status': 'pending',
                'priority': 'medium'
            },
            {
                'title': 'New Laptops for Development Team',
                'description': 'Purchase of 5 high-performance laptops',
                'amount': Decimal('18000.00'),
                'expense_date': date(2024, 2, 18),
                'receipt_number': 'RCP-2024-006',
                'vendor_name': 'Tech Equipment Store',
                'status': 'pending',
                'priority': 'high'
            },
            {
                'title': 'IT Consulting Services',
                'description': 'Security audit and system optimization',
                'amount': Decimal('7500.00'),
                'expense_date': date(2024, 2, 25),
                'receipt_number': 'RCP-2024-007',
                'vendor_name': 'CyberSec Consultants',
                'status': 'rejected',
                'priority': 'low'
            },
            {
                'title': 'Office Supplies - Stationery',
                'description': 'Monthly office supplies and stationery',
                'amount': Decimal('850.00'),
                'expense_date': date(2024, 3, 1),
                'receipt_number': 'RCP-2024-008',
                'vendor_name': 'Office Depot',
                'status': 'approved',
                'priority': 'low'
            },
            {
                'title': 'Server Maintenance',
                'description': 'Quarterly server maintenance and updates',
                'amount': Decimal('4200.00'),
                'expense_date': date(2024, 3, 10),
                'receipt_number': 'RCP-2024-009',
                'vendor_name': 'Server Solutions Ltd.',
                'status': 'paid',
                'priority': 'medium'
            },
            {
                'title': 'Conference Registration',
                'description': 'Registration for annual tech conference',
                'amount': Decimal('2800.00'),
                'expense_date': date(2024, 3, 15),
                'receipt_number': 'RCP-2024-010',
                'vendor_name': 'TechConf Organizers',
                'status': 'pending',
                'priority': 'low'
            }
        ]
        
        for i, exp_data in enumerate(expenses_data):
            budget_plan = budget_plans[i % len(budget_plans)]
            expense_type = expense_types[i % len(expense_types)]
            employee = employees[i % len(employees)]
            approver = employees[(i + 1) % len(employees)]
            
            expense, created = Expense.objects.get_or_create(
                title=exp_data['title'],
                budget_plan=budget_plan,
                defaults={
                    'expense_type': expense_type,
                    'description': exp_data['description'],
                    'amount': exp_data['amount'],
                    'expense_date': exp_data['expense_date'],
                    'receipt_number': exp_data['receipt_number'],
                    'vendor_name': exp_data['vendor_name'],
                    'status': exp_data['status'],
                    'priority': exp_data['priority'],
                    'requested_by': employee,
                    'approved_by': approver if exp_data['status'] in ['approved', 'paid'] else None,
                    'approved_at': timezone.now() if exp_data['status'] in ['approved', 'paid'] else None,
                    'paid_at': timezone.now() if exp_data['status'] == 'paid' else None,
                }
            )
            if created:
                self.stdout.write(f'Created expense: {expense.title}')
    
    def create_budget_alerts(self, employees):
        budget_plans = BudgetPlan.objects.all()[:3]
        
        alerts_data = [
            {
                'alert_type': 'threshold',
                'threshold_percentage': Decimal('80.00'),
                'message': 'Budget utilization has reached 80% threshold',
                'is_active': True,
                'is_sent': False
            },
            {
                'alert_type': 'overbudget',
                'threshold_percentage': None,
                'message': 'Budget has exceeded allocated amount',
                'is_active': True,
                'is_sent': True
            },
            {
                'alert_type': 'expiry',
                'threshold_percentage': None,
                'message': 'Budget period is expiring in 7 days',
                'is_active': True,
                'is_sent': False
            }
        ]
        
        for i, alert_data in enumerate(alerts_data):
            if i < len(budget_plans):
                budget_plan = budget_plans[i]
                
                # Check if alert already exists
                existing_alert = BudgetAlert.objects.filter(
                    budget_plan=budget_plan,
                    alert_type=alert_data['alert_type']
                ).first()
                
                if not existing_alert:
                    alert = BudgetAlert.objects.create(
                        budget_plan=budget_plan,
                        alert_type=alert_data['alert_type'],
                        threshold_percentage=alert_data['threshold_percentage'],
                        message=alert_data['message'],
                        is_active=alert_data['is_active'],
                        is_sent=alert_data['is_sent'],
                        sent_at=timezone.now() if alert_data['is_sent'] else None,
                    )
                    # Add some employees to sent_to field
                    alert.sent_to.add(*employees[:3])
                    self.stdout.write(f'Created budget alert: {alert.alert_type} for {budget_plan.name}')
                else:
                    self.stdout.write(f'Budget alert already exists: {existing_alert.alert_type} for {budget_plan.name}')
    
    def create_financial_reports(self, employees):
        reports_data = [
            {
                'name': 'Q1 2024 Budget Summary Report',
                'report_type': 'budget_summary',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 3, 31),
                'file_path': '/reports/budget_summary_q1_2024.pdf',
                'parameters': {
                    'include_charts': True,
                    'department_breakdown': True,
                    'variance_analysis': True
                }
            },
            {
                'name': 'February 2024 Expense Analysis',
                'report_type': 'expense_analysis',
                'start_date': date(2024, 2, 1),
                'end_date': date(2024, 2, 29),
                'file_path': '/reports/expense_analysis_feb_2024.pdf',
                'parameters': {
                    'category_wise': True,
                    'trend_analysis': True,
                    'top_expenses': 10
                }
            },
            {
                'name': 'Q1 2024 Variance Report',
                'report_type': 'variance_report',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 3, 31),
                'file_path': '/reports/variance_report_q1_2024.pdf',
                'parameters': {
                    'variance_threshold': 10,
                    'include_explanations': True,
                    'forecast_next_period': True
                }
            },
            {
                'name': 'March 2024 Cash Flow Report',
                'report_type': 'cash_flow',
                'start_date': date(2024, 3, 1),
                'end_date': date(2024, 3, 31),
                'file_path': '/reports/cash_flow_mar_2024.pdf',
                'parameters': {
                    'weekly_breakdown': True,
                    'payment_status': True,
                    'pending_approvals': True
                }
            },
            {
                'name': 'Department Wise Budget Report - Q1 2024',
                'report_type': 'department_wise',
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 3, 31),
                'file_path': '/reports/department_budget_q1_2024.pdf',
                'parameters': {
                    'comparison_with_previous': True,
                    'efficiency_metrics': True,
                    'recommendations': True
                }
            }
        ]
        
        for i, report_data in enumerate(reports_data):
            employee = employees[i % len(employees)]
            
            report, created = FinancialReport.objects.get_or_create(
                name=report_data['name'],
                defaults={
                    'report_type': report_data['report_type'],
                    'start_date': report_data['start_date'],
                    'end_date': report_data['end_date'],
                    'generated_by': employee,
                    'file_path': report_data['file_path'],
                    'parameters': report_data['parameters'],
                }
            )
            if created:
                self.stdout.write(f'Created financial report: {report.name}')