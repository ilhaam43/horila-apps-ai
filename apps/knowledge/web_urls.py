from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'knowledge_web'

urlpatterns = [
    # Knowledge Management Dashboard
    path('', views.knowledge_dashboard, name='dashboard'),
    
    # Document Management Web Interface
    path('documents/', views.KnowledgeDocumentListView.as_view(), name='document_list'),
    path('documents/create/', views.KnowledgeDocumentCreateView.as_view(), name='document_create'),
    path('documents/bulk-upload/', views.bulk_upload_documents, name='bulk_upload'),
    path('documents/<int:pk>/', views.KnowledgeDocumentDetailView.as_view(), name='document_detail'),
    path('documents/<int:pk>/edit/', views.KnowledgeDocumentUpdateView.as_view(), name='document_edit'),
    path('documents/<int:pk>/download/', views.download_document, name='document_download'),
    
    # Comments
    path('documents/<int:document_id>/comments/add/', views.add_document_comment, name='add_comment'),
    
    # Categories
    path('categories/', views.DocumentCategoryListView.as_view(), name='categories'),
    path('categories/create/', views.DocumentCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/', views.DocumentCategoryDetailView.as_view(), name='category_detail'),
    path('categories/<int:pk>/edit/', views.DocumentCategoryUpdateView.as_view(), name='category_edit'),
    
    # Search Interface
    path('search/', views.search_documents, name='document_search'),
    
    # AI Assistant Interface
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),
    
    # AI Processing Interface
    path('ai/process-document/<int:document_id>/', views.process_document_ai, name='process_document_ai'),
    path('ai/job-status/<int:job_id>/', views.ai_job_status, name='ai_job_status'),
    
    # Chatbot Interface
    path('chatbot/', TemplateView.as_view(template_name='knowledge/chatbot.html'), name='chatbot'),
]