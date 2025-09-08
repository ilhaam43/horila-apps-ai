from django.urls import path
from . import chatbot_views

app_name = 'chatbot'

urlpatterns = [
    # Main chatbot API endpoint
    path('chat/', chatbot_views.ChatbotAPIView.as_view(), name='chat_api'),
    
    # Session management
    path('session/<str:session_id>/end/', chatbot_views.end_chat_session, name='end_session'),
    
    # Quick queries without session
    path('quick-query/', chatbot_views.quick_hr_query, name='quick_query'),
    
    # Status and information endpoints
    path('status/', chatbot_views.hr_assistant_status, name='status'),
    path('summary/', chatbot_views.user_hr_summary, name='user_summary'),
]