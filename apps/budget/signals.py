from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal
from .models import Expense, BudgetPlan, BudgetAlert
from .utils import send_budget_alert, check_budget_thresholds


@receiver(post_save, sender=Expense)
def update_budget_spent_amount(sender, instance, created, **kwargs):
    """Update budget plan spent amount when expense is saved"""
    if instance.status in ['approved', 'paid']:
        budget_plan = instance.budget_plan
        
        # Recalculate spent amount from all approved/paid expenses
        total_spent = budget_plan.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        budget_plan.spent_amount = total_spent
        budget_plan.save()
        
        # Check for budget alerts
        check_budget_alerts(budget_plan)


@receiver(post_delete, sender=Expense)
def update_budget_on_expense_delete(sender, instance, **kwargs):
    """Update budget plan when expense is deleted"""
    if instance.status in ['approved', 'paid']:
        budget_plan = instance.budget_plan
        
        # Recalculate spent amount
        total_spent = budget_plan.expenses.filter(
            status__in=['approved', 'paid']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        budget_plan.spent_amount = total_spent
        budget_plan.save()


@receiver(pre_save, sender=Expense)
def track_expense_status_change(sender, instance, **kwargs):
    """Track expense status changes for budget updates"""
    if instance.pk:
        try:
            old_instance = Expense.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Expense.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Expense)
def handle_expense_status_change(sender, instance, created, **kwargs):
    """Handle expense status changes and update budget accordingly"""
    if not created and hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status
        
        # If status changed from/to approved or paid, update budget
        if (old_status in ['approved', 'paid'] and new_status not in ['approved', 'paid']) or \
           (old_status not in ['approved', 'paid'] and new_status in ['approved', 'paid']):
            
            budget_plan = instance.budget_plan
            total_spent = budget_plan.expenses.filter(
                status__in=['approved', 'paid']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            budget_plan.spent_amount = total_spent
            budget_plan.save()
            
            # Check for budget alerts
            check_budget_alerts(budget_plan)


@receiver(post_save, sender=BudgetPlan)
def create_default_budget_alerts(sender, instance, created, **kwargs):
    """Create default budget alerts when a new budget plan is created"""
    if created:
        # Create default threshold alerts
        default_thresholds = [75, 90, 100]
        
        for threshold in default_thresholds:
            BudgetAlert.objects.create(
                budget_plan=instance,
                alert_type='threshold',
                threshold_percentage=threshold,
                message=f'Budget {instance.name} has reached {threshold}% utilization.',
                is_active=True
            )


@receiver(post_save, sender=BudgetPlan)
def check_budget_expiry_alerts(sender, instance, **kwargs):
    """Check and create budget expiry alerts"""
    from django.utils import timezone
    from datetime import timedelta
    
    # Check if budget is expiring soon (7 days before end date)
    days_until_expiry = (instance.end_date - timezone.now().date()).days
    
    if days_until_expiry <= 7 and days_until_expiry > 0:
        # Check if expiry alert already exists
        expiry_alert, created = BudgetAlert.objects.get_or_create(
            budget_plan=instance,
            alert_type='expiry',
            defaults={
                'message': f'Budget {instance.name} will expire in {days_until_expiry} days.',
                'is_active': True
            }
        )
        
        if created and not expiry_alert.is_sent:
            send_budget_alert(expiry_alert)


def check_budget_alerts(budget_plan):
    """Check and trigger budget alerts for a specific budget plan"""
    utilization = budget_plan.utilization_percentage
    
    # Check threshold alerts
    threshold_alerts = BudgetAlert.objects.filter(
        budget_plan=budget_plan,
        alert_type='threshold',
        is_active=True,
        is_sent=False,
        threshold_percentage__lte=utilization
    )
    
    for alert in threshold_alerts:
        send_budget_alert(alert)
    
    # Check over budget alert
    if budget_plan.is_over_budget:
        over_budget_alert, created = BudgetAlert.objects.get_or_create(
            budget_plan=budget_plan,
            alert_type='overbudget',
            defaults={
                'message': f'Budget {budget_plan.name} has exceeded its allocated amount by ${budget_plan.spent_amount - budget_plan.allocated_amount:,.2f}.',
                'is_active': True
            }
        )
        
        if created or not over_budget_alert.is_sent:
            send_budget_alert(over_budget_alert)


@receiver(post_save, sender=BudgetPlan)
def handle_budget_approval(sender, instance, **kwargs):
    """Handle budget plan approval notifications"""
    if instance.status == 'approved' and instance.approved_by:
        # Create approval notification alert
        approval_alert, created = BudgetAlert.objects.get_or_create(
            budget_plan=instance,
            alert_type='approval',
            defaults={
                'message': f'Budget {instance.name} has been approved by {instance.approved_by.get_full_name()}.',
                'is_active': True
            }
        )
        
        if created:
            # Add budget creator to recipients
            approval_alert.sent_to.add(instance.created_by)
            send_budget_alert(approval_alert)