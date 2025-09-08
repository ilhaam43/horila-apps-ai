from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from . import views

# Create router for API ViewSets
router = DefaultRouter()
router.register(r'categories', views.DocumentCategoryViewSet)
router.register(r'tags', views.DocumentTagViewSet)
router.register(r'documents', views.KnowledgeDocumentViewSet)
router.register(r'ai-assistants', views.AIAssistantViewSet)
router.register(r'knowledge-bases', views.KnowledgeBaseViewSet)

app_name = 'knowledge'

urlpatterns = [
    # Dashboard
    path('', views.knowledge_dashboard, name='dashboard'),
    
    # Document Management
    path('documents/', views.KnowledgeDocumentListView.as_view(), name='document_list'),
    path('documents/create/', views.KnowledgeDocumentCreateView.as_view(), name='document_create'),
    path('documents/bulk-upload/', views.bulk_upload_documents, name='bulk_upload'),
    path('documents/<int:pk>/', views.KnowledgeDocumentDetailView.as_view(), name='document_detail'),
    path('documents/<int:pk>/edit/', views.KnowledgeDocumentUpdateView.as_view(), name='document_edit'),
    path('documents/<int:pk>/delete/', views.KnowledgeDocumentDeleteView.as_view(), name='document_delete'),
    path('documents/<int:pk>/download/', views.download_document, name='document_download'),
    
    # Comments
    path('documents/<int:document_id>/comments/add/', views.add_document_comment, name='add_comment'),
    
    # Categories
    path('categories/', views.DocumentCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.DocumentCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/', views.DocumentCategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', views.DocumentCategoryUpdateView.as_view(), name='category_edit'),
    
    # Search
    path('search/', views.search_documents, name='document_search'),
    
    # AI Assistant
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),
    
    # AI Processing
    path('ai/process-document/<int:document_id>/', views.process_document_ai, name='process_document_ai'),
    path('ai/job-status/<int:job_id>/', views.ai_job_status, name='ai_job_status'),
    
    # API endpoints
    path('api/', include(router.urls)),
    
    # Chatbot
    path('chatbot/', TemplateView.as_view(template_name='knowledge/chatbot.html'), name='chatbot'),
    
    # Chatbot API (Ollama-based)
    path('api/chatbot/query/', views.chatbot_query, name='chatbot_query'),
    path('api/chatbot/conversations/', views.conversation_history, name='conversation_list'),
    path('api/chatbot/conversation/<uuid:conversation_id>/history/', views.conversation_history, name='conversation_detail'),
    path('api/chatbot/conversation/<uuid:conversation_id>/close/', views.close_conversation, name='close_conversation'),
    path('api/chatbot/feedback/', views.submit_feedback, name='submit_feedback'),
    path('api/chatbot/search/', views.chatbot_search_documents, name='chatbot_search'),
    path('api/chatbot/stats/', views.chatbot_stats, name='chatbot_stats'),
    
    # SLM Chatbot API (Small Language Model alternative)
    path('slm/', include('knowledge.urls_slm')),
]