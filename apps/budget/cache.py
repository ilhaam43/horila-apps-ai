from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BudgetPlan, Expense, BudgetCategory, ExpenseType, FinancialReport


class BudgetCacheManager:
    """Cache manager for budget module"""
    
    @staticmethod
    def clear_dashboard_cache(user_id=None):
        """Clear dashboard cache for specific user or all users"""
        if user_id:
            cache.delete(f'budget_dashboard_{user_id}')
        else:
            # Clear all dashboard caches (use pattern matching if available)
            cache.delete_many(['budget_dashboard_*'])
    
    @staticmethod
    def clear_monthly_spending_cache():
        """Clear monthly spending cache"""
        cache.delete('budget_monthly_spending')
    
    @staticmethod
    def clear_budget_stats_cache():
        """Clear budget statistics cache"""
        cache.delete('budget_stats')
    
    @staticmethod
    def get_or_set_budget_stats(callback, timeout=900):
        """Get budget stats from cache or set if not exists"""
        cache_key = 'budget_stats'
        stats = cache.get(cache_key)
        if stats is None:
            stats = callback()
            cache.set(cache_key, stats, timeout)
        return stats


# Signal handlers to clear cache when data changes
@receiver([post_save, post_delete], sender=BudgetPlan)
def clear_budget_cache_on_plan_change(sender, **kwargs):
    """Clear relevant caches when budget plan changes"""
    BudgetCacheManager.clear_dashboard_cache()
    BudgetCacheManager.clear_budget_stats_cache()


@receiver([post_save, post_delete], sender=Expense)
def clear_budget_cache_on_expense_change(sender, **kwargs):
    """Clear relevant caches when expense changes"""
    BudgetCacheManager.clear_dashboard_cache()
    BudgetCacheManager.clear_monthly_spending_cache()
    BudgetCacheManager.clear_budget_stats_cache()


@receiver([post_save, post_delete], sender=BudgetCategory)
def clear_budget_cache_on_category_change(sender, **kwargs):
    """Clear relevant caches when budget category changes"""
    BudgetCacheManager.clear_dashboard_cache()


@receiver([post_save, post_delete], sender=ExpenseType)
def clear_budget_cache_on_expense_type_change(sender, **kwargs):
    """Clear relevant caches when expense type changes"""
    BudgetCacheManager.clear_dashboard_cache()


@receiver([post_save, post_delete], sender=FinancialReport)
def clear_budget_cache_on_report_change(sender, **kwargs):
    """Clear relevant caches when financial report changes"""
    BudgetCacheManager.clear_dashboard_cache()