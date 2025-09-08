"""context_processor.py

This module is used to register context processor for budget app
"""

from budget.models import BudgetSettings
from base.models import Company


def default_currency(request):
    """
    This method will return the currency for budget module
    """
    if BudgetSettings.objects.first() is None:
        settings = BudgetSettings()
        settings.currency_symbol = "$"
        settings.position = "postfix"
        settings.save()
    
    budget_settings = BudgetSettings.objects.first()
    symbol = budget_settings.currency_symbol
    position = budget_settings.position
    
    # Always use current database values, not session
    return {
        "budget_currency": symbol,
        "budget_position": position,
        "budget_settings": budget_settings,
    }


def host(request):
    """
    This method will return the host
    """
    protocol = "https" if request.is_secure() else "http"
    return {"host": request.get_host(), "protocol": protocol}