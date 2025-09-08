import os
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
try:
    import pandas as pd
except ImportError:
    pd = None
from .models import BudgetPlan, Expense, BudgetAlert, FinancialReport


def generate_financial_report(report_instance):
    """Generate financial report based on report type"""
    report_type = report_instance.report_type
    start_date = report_instance.start_date
    end_date = report_instance.end_date
    parameters = report_instance.parameters or {}
    
    # Get format from parameters, default to PDF
    report_format = parameters.get('format', 'pdf')
    
    # Create reports directory if it doesn't exist
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports', 'budget')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Generate filename based on format
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_extension = 'xlsx' if report_format == 'excel' else 'pdf'
    filename = f"{report_type}_{timestamp}.{file_extension}"
    file_path = os.path.join(reports_dir, filename)
    
    if report_type == 'budget_summary':
        return generate_budget_summary_report(file_path, start_date, end_date, parameters)
    elif report_type == 'expense_analysis':
        return generate_expense_analysis_report(file_path, start_date, end_date, parameters)
    elif report_type == 'variance_report':
        return generate_variance_report(file_path, start_date, end_date, parameters)
    elif report_type == 'cash_flow':
        return generate_cash_flow_report(file_path, start_date, end_date, parameters)
    elif report_type == 'department_wise':
        return generate_department_wise_report(file_path, start_date, end_date, parameters)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


def generate_budget_summary_report(file_path, start_date, end_date, parameters):
    """Generate budget summary report"""
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph("Budget Summary Report", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Get budget data
    budgets = BudgetPlan.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('category')
    
    # Summary table
    summary_data = [['Budget Name', 'Category', 'Allocated', 'Spent', 'Remaining', 'Utilization %']]
    
    total_allocated = Decimal('0')
    total_spent = Decimal('0')
    
    for budget in budgets:
        total_allocated += budget.allocated_amount
        total_spent += budget.spent_amount
        
        summary_data.append([
            budget.name,
            budget.category.name,
            f"IDR{budget.allocated_amount:,.2f}",
            f"IDR{budget.spent_amount:,.2f}",
            f"IDR{budget.remaining_amount:,.2f}",
            f"{budget.utilization_percentage:.1f}%"
        ])
    
    # Add totals row
    summary_data.append([
        'TOTAL',
        '',
        f"IDR{total_allocated:,.2f}",
        f"IDR{total_spent:,.2f}",
        f"IDR{total_allocated - total_spent:,.2f}",
        f"{(total_spent / total_allocated * 100) if total_allocated > 0 else 0:.1f}%"
    ])
    
    # Create table
    table = Table(summary_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    # Generate report
    doc.build(story)
    
    return os.path.join('reports', 'budget', os.path.basename(file_path))


def generate_expense_analysis_report(file_path, start_date, end_date, parameters):
    """Generate expense analysis report"""
    # Get format from parameters
    report_format = parameters.get('format', 'pdf')
    
    # Get expense data
    expenses = Expense.objects.filter(
        expense_date__range=[start_date, end_date],
        status__in=['approved', 'paid']
    ).select_related('expense_type', 'budget_plan')
    
    # Expense by type analysis
    expense_by_type = expenses.values('expense_type__name').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    if report_format == 'excel' and pd is not None:
        # Generate Excel report
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Expense by type sheet
            type_data = []
            for item in expense_by_type:
                avg_amount = item['total_amount'] / item['count'] if item['count'] > 0 else 0
                type_data.append({
                    'Expense Type': item['expense_type__name'],
                    'Total Amount (IDR)': float(item['total_amount']),
                    'Count': item['count'],
                    'Average (IDR)': float(avg_amount)
                })
            
            type_df = pd.DataFrame(type_data)
            type_df.to_excel(writer, sheet_name='Expenses by Type', index=False)
            
            # Individual expenses sheet
            expense_data = []
            for expense in expenses:
                expense_data.append({
                    'Date': expense.expense_date,
                    'Title': expense.title,
                    'Type': expense.expense_type.name,
                    'Budget Plan': expense.budget_plan.name,
                    'Amount (IDR)': float(expense.amount),
                    'Status': expense.status,
                    'Vendor': expense.vendor_name or 'N/A'
                })
            
            expense_df = pd.DataFrame(expense_data)
            expense_df.to_excel(writer, sheet_name='Individual Expenses', index=False)
            
            # Summary sheet
            total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0
            summary_data = [{
                'Metric': 'Total Expenses',
                'Value (IDR)': float(total_expenses)
            }, {
                'Metric': 'Number of Expenses',
                'Value (IDR)': expenses.count()
            }, {
                'Metric': 'Average Expense',
                'Value (IDR)': float(total_expenses / expenses.count()) if expenses.count() > 0 else 0
            }]
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    else:
        # Generate PDF report (original implementation)
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        story.append(Paragraph("Expense Analysis Report", title_style))
        story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Create expense type table
        type_data = [['Expense Type', 'Total Amount', 'Count', 'Average']]
        
        for item in expense_by_type:
            avg_amount = item['total_amount'] / item['count'] if item['count'] > 0 else 0
            type_data.append([
                item['expense_type__name'],
                f"IDR{item['total_amount']:,.2f}",
                str(item['count']),
                f"IDR{avg_amount:,.2f}"
            ])
        
        story.append(Paragraph("Expenses by Type", styles['Heading2']))
        
        type_table = Table(type_data)
        type_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(type_table)
        story.append(Spacer(1, 20))
        
        # Generate report
        doc.build(story)
    
    return os.path.join('reports', 'budget', os.path.basename(file_path))


def generate_variance_report(file_path, start_date, end_date, parameters):
    """Generate budget variance report"""
    doc = SimpleDocTemplate(file_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph("Budget Variance Report", title_style))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Get budget data with variance analysis
    budgets = BudgetPlan.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date
    ).select_related('category')
    
    # Variance table
    variance_data = [['Budget', 'Allocated', 'Actual', 'Variance', 'Variance %', 'Status']]
    
    for budget in budgets:
        variance = budget.allocated_amount - budget.spent_amount
        variance_pct = (variance / budget.allocated_amount * 100) if budget.allocated_amount > 0 else 0
        
        status = 'Over Budget' if variance < 0 else 'Under Budget' if variance > 0 else 'On Budget'
        
        variance_data.append([
            budget.name,
            f"IDR{budget.allocated_amount:,.2f}",
            f"IDR{budget.spent_amount:,.2f}",
            f"IDR{variance:,.2f}",
            f"{variance_pct:.1f}%",
            status
        ])
    
    variance_table = Table(variance_data)
    variance_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(variance_table)
    
    # Generate report
    doc.build(story)
    
    return os.path.join('reports', 'budget', os.path.basename(file_path))


def generate_cash_flow_report(file_path, start_date, end_date, parameters):
    """Generate cash flow report"""
    # Implementation for cash flow report
    # This would include monthly/weekly cash flow analysis
    pass


def generate_department_wise_report(file_path, start_date, end_date, parameters):
    """Generate department-wise budget report"""
    # Implementation for department-wise report
    # This would analyze budget usage by department
    pass


def send_budget_alert(alert_instance):
    """Send budget alert notifications"""
    try:
        # Get recipients
        recipients = []
        
        # Add budget creator and approver
        if alert_instance.budget_plan.created_by:
            recipients.append(alert_instance.budget_plan.created_by.employee_work_info.email)
        
        if alert_instance.budget_plan.approved_by:
            recipients.append(alert_instance.budget_plan.approved_by.employee_work_info.email)
        
        # Add users from sent_to field
        for employee in alert_instance.sent_to.all():
            if hasattr(employee, 'employee_work_info') and employee.employee_work_info.email:
                recipients.append(employee.employee_work_info.email)
        
        # Remove duplicates
        recipients = list(set(recipients))
        
        if not recipients:
            return False
        
        # Prepare email content
        subject = f"Budget Alert: {alert_instance.budget_plan.name}"
        
        context = {
            'alert': alert_instance,
            'budget_plan': alert_instance.budget_plan,
            'utilization': alert_instance.budget_plan.utilization_percentage,
            'remaining_amount': alert_instance.budget_plan.remaining_amount
        }
        
        # Render email template
        html_message = render_to_string('budget/emails/budget_alert.html', context)
        plain_message = render_to_string('budget/emails/budget_alert.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False
        )
        
        # Mark alert as sent
        alert_instance.is_sent = True
        alert_instance.sent_at = timezone.now()
        alert_instance.save()
        
        return True
        
    except Exception as e:
        print(f"Error sending budget alert: {str(e)}")
        return False


def check_budget_thresholds():
    """Check all active budgets for threshold alerts"""
    active_budgets = BudgetPlan.objects.filter(status='active')
    
    for budget in active_budgets:
        # Check for existing threshold alerts
        threshold_alerts = BudgetAlert.objects.filter(
            budget_plan=budget,
            alert_type='threshold',
            is_active=True
        )
        
        utilization = budget.utilization_percentage
        
        for alert in threshold_alerts:
            if (alert.threshold_percentage and 
                utilization >= alert.threshold_percentage and 
                not alert.is_sent):
                send_budget_alert(alert)
        
        # Check for over budget
        if budget.is_over_budget:
            over_budget_alert, created = BudgetAlert.objects.get_or_create(
                budget_plan=budget,
                alert_type='overbudget',
                defaults={
                    'message': f'Budget {budget.name} has exceeded its allocated amount.',
                    'is_active': True
                }
            )
            
            if created or not over_budget_alert.is_sent:
                send_budget_alert(over_budget_alert)


def export_budget_data_csv(queryset, fields=None):
    """Export budget data to CSV format"""
    if fields is None:
        fields = ['name', 'category__name', 'allocated_amount', 'spent_amount', 'status']
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="budget_data.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    header = [field.replace('__', '_').replace('_', ' ').title() for field in fields]
    writer.writerow(header)
    
    # Write data
    for obj in queryset:
        row = []
        for field in fields:
            value = obj
            for attr in field.split('__'):
                value = getattr(value, attr, '')
            row.append(str(value))
        writer.writerow(row)
    
    return response


def calculate_budget_metrics(budget_plan):
    """Calculate various metrics for a budget plan"""
    metrics = {
        'utilization_rate': budget_plan.utilization_percentage,
        'burn_rate': 0,  # Amount spent per day
        'projected_completion': None,
        'days_remaining': 0,
        'average_expense': 0,
        'expense_frequency': 0
    }
    
    # Calculate days remaining
    today = timezone.now().date()
    if budget_plan.end_date > today:
        metrics['days_remaining'] = (budget_plan.end_date - today).days
    
    # Calculate burn rate and projections
    total_days = (budget_plan.end_date - budget_plan.start_date).days
    if total_days > 0:
        metrics['burn_rate'] = float(budget_plan.spent_amount) / total_days
        
        if metrics['burn_rate'] > 0:
            remaining_budget = budget_plan.remaining_amount
            days_to_completion = remaining_budget / metrics['burn_rate']
            metrics['projected_completion'] = today + timedelta(days=int(days_to_completion))
    
    # Calculate expense metrics
    expenses = budget_plan.expenses.filter(status__in=['approved', 'paid'])
    expense_count = expenses.count()
    
    if expense_count > 0:
        metrics['average_expense'] = budget_plan.spent_amount / expense_count
        metrics['expense_frequency'] = expense_count / total_days if total_days > 0 else 0
    
    return metrics