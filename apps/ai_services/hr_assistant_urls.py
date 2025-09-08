"""HR Assistant URL Configuration"""

from django.urls import path
from . import hr_assistant_views

app_name = 'hr_assistant'

urlpatterns = [
    # Main HR Assistant chat endpoint
    path('chat/', hr_assistant_views.HRAssistantChatView.as_view(), name='chat'),
    
    # HR insights endpoint
    path('insights/', hr_assistant_views.HRInsightsView.as_view(), name='insights'),
    
    # Quick query endpoint
    path('quick-query/', hr_assistant_views.hr_assistant_quick_query, name='quick_query'),
    
    # Status endpoint
    path('status/', hr_assistant_views.hr_assistant_status, name='status'),
    
    # Feedback endpoint
    path('feedback/', hr_assistant_views.hr_assistant_feedback, name='feedback'),
]