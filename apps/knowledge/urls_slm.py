from django.urls import path
from . import views_slm

app_name = 'knowledge_slm'

urlpatterns = [
    # SLM Chatbot API endpoints
    path('chat/', views_slm.slm_chat_query, name='slm_chat_query'),
    path('conversations/', views_slm.slm_conversation_list, name='slm_conversation_list'),
    path('conversations/create/', views_slm.slm_conversation_create, name='slm_conversation_create'),
    path('conversations/<uuid:conversation_id>/', views_slm.slm_conversation_detail, name='slm_conversation_detail'),
    path('conversations/<uuid:conversation_id>/delete/', views_slm.slm_conversation_delete, name='slm_conversation_delete'),
    path('status/', views_slm.slm_service_status, name='slm_service_status'),
    path('search/', views_slm.slm_document_search, name='slm_document_search'),
]