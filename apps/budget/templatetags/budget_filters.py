from django import template
from django.utils.safestring import mark_safe
from budget.models import BudgetSettings

register = template.Library()

@register.filter
def currency_format(amount, decimal_places=2):
    """
    Format amount with currency symbol from BudgetSettings
    Supports up to 12-digit amounts (999,999,999,999.99)
    Usage: {{ amount|currency_format }}
    """
    try:
        # Get budget settings
        budget_settings = BudgetSettings.objects.first()
        if not budget_settings:
            # Default settings if none exist
            symbol = '$'
            position = 'postfix'
        else:
            symbol = budget_settings.currency_symbol or '$'
            position = budget_settings.position or 'postfix'
        
        # Format the amount - handle SafeString by converting to float first
        if amount is None:
            amount = 0
        
        # Convert to float to handle SafeString objects
        try:
            amount_float = float(str(amount).replace(',', ''))
        except (ValueError, TypeError):
            amount_float = 0
        
        # Validate 12-digit limit
        if amount_float >= 1000000000000:  # 12 digits
            formatted_amount = "999,999,999,999+"
        else:
            formatted_amount = "{:,.{}f}".format(amount_float, decimal_places)
        
        # Apply currency position
        if position == 'prefix':
            return mark_safe("{}{}".format(symbol, formatted_amount))
        else:
            return mark_safe("{}{}".format(formatted_amount, symbol))
            
    except (ValueError, TypeError):
        return mark_safe("${}".format(amount))

@register.filter
def currency_symbol(request=None):
    """
    Get currency symbol from BudgetSettings
    Usage: {{ request|currency_symbol }}
    """
    try:
        budget_settings = BudgetSettings.objects.first()
        if budget_settings:
            return budget_settings.currency_symbol or '$'
        return '$'
    except:
        return '$'

@register.filter
def currency_position(request=None):
    """
    Get currency position from BudgetSettings
    Usage: {{ request|currency_position }}
    """
    try:
        budget_settings = BudgetSettings.objects.first()
        if budget_settings:
            return budget_settings.position or 'postfix'
        return 'postfix'
    except:
        return 'postfix'