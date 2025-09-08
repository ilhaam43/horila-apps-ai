from django.urls import path
from . import hr_admin_views

urlpatterns = [
    # Manual task execution endpoints
    path('tasks/daily/', hr_admin_views.run_daily_tasks, name='run_daily_tasks'),
    path('tasks/weekly/', hr_admin_views.run_weekly_tasks, name='run_weekly_tasks'),
    path('tasks/monthly/', hr_admin_views.run_monthly_tasks, name='run_monthly_tasks'),
    
    # Task history and monitoring endpoints
    path('tasks/history/', hr_admin_views.get_task_history, name='get_task_history'),
    path('tasks/details/<int:task_id>/', hr_admin_views.get_task_details, name='get_task_details'),
]