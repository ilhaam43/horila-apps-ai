from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import json
import mimetypes
import os
from datetime import datetime, timedelta

from .models import (
    DocumentCategory, DocumentTag, KnowledgeDocument, DocumentVersion,
    DocumentComment, DocumentAccess, AIAssistant, AIProcessingJob,
    KnowledgeBase, SearchQuery, ChatbotConversation, ChatbotMessage, ChatbotFeedback
)
from .serializers import (
    DocumentCategorySerializer, DocumentTagSerializer, KnowledgeDocumentSerializer,
    DocumentVersionSerializer, DocumentCommentSerializer, AIAssistantSerializer,
    KnowledgeBaseSerializer, SearchQuerySerializer, ChatbotConversationSerializer,
    ChatbotMessageSerializer, ChatbotFeedbackSerializer
)

# Import chatbot views
from .chatbot_views import (
    chatbot_query, conversation_history, submit_feedback, search_documents as chatbot_search_documents,
    close_conversation, chatbot_stats
)
from .forms import (
    KnowledgeDocumentForm, DocumentCategoryForm, DocumentCommentForm,
    KnowledgeSearchForm, DocumentUploadForm
)
from .utils import (
    process_document_with_ai, extract_text_from_file,
    generate_document_summary, suggest_document_tags
)


# Dashboard Views
@login_required
def knowledge_dashboard(request):
    """Knowledge management dashboard"""
    # Get statistics
    total_documents = KnowledgeDocument.objects.filter(status='published').count()
    total_categories = DocumentCategory.objects.filter(is_active=True).count()
    total_views = KnowledgeDocument.objects.aggregate(total=Sum('view_count'))['total'] or 0
    
    # Recent documents
    recent_documents = KnowledgeDocument.objects.filter(
        status='published'
    ).select_related('category', 'created_by').order_by('-created_at')[:10]
    
    # Popular documents
    popular_documents = KnowledgeDocument.objects.filter(
        status='published'
    ).order_by('-view_count')[:5]
    
    # Documents needing review
    documents_needing_review = KnowledgeDocument.objects.filter(
        next_review_date__lte=timezone.now().date(),
        status='published'
    ).count()
    
    # AI processing statistics
    ai_jobs_today = AIProcessingJob.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    
    context = {
        'total_documents': total_documents,
        'total_categories': total_categories,
        'total_views': total_views,
        'recent_documents': recent_documents,
        'popular_documents': popular_documents,
        'documents_needing_review': documents_needing_review,
        'ai_jobs_today': ai_jobs_today,
    }
    
    return render(request, 'knowledge/dashboard.html', context)


# Document Views
class KnowledgeDocumentListView(LoginRequiredMixin, ListView):
    """List all knowledge documents"""
    model = KnowledgeDocument
    template_name = 'knowledge/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = KnowledgeDocument.objects.filter(
            status='published'
        ).select_related('category', 'created_by')
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by document type
        doc_type = self.request.GET.get('type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)
        
        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(content__icontains=search_query)
            )
            
            # Log search query
            SearchQuery.objects.create(
                query=search_query,
                user=self.request.user,
                results_count=queryset.count()
            )
        
        return queryset.order_by('-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.filter(is_active=True)
        context['document_types'] = KnowledgeDocument.DOCUMENT_TYPES
        context['search_form'] = KnowledgeSearchForm(self.request.GET)
        return context


class KnowledgeDocumentDetailView(LoginRequiredMixin, DetailView):
    """Detail view for knowledge document"""
    model = KnowledgeDocument
    template_name = 'knowledge/document_detail.html'
    context_object_name = 'document'
    
    def get_object(self):
        obj = super().get_object()
        
        # Check access permissions
        if obj.visibility == 'department' and obj.department != self.request.user.employee.department:
            if not obj.allowed_users.filter(id=self.request.user.id).exists():
                raise Http404("Document not found")
        elif obj.visibility == 'restricted':
            if not obj.allowed_users.filter(id=self.request.user.id).exists():
                raise Http404("Document not found")
        
        # Increment view count
        obj.increment_view_count()
        
        # Log access
        DocumentAccess.objects.create(
            document=obj,
            user=self.request.user,
            access_type='view',
            ip_address=self.get_client_ip()
        )
        
        return obj
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.filter(parent=None).order_by('created_at')
        context['comment_form'] = DocumentCommentForm()
        context['versions'] = self.object.versions.order_by('-created_at')[:5]
        context['related_documents'] = KnowledgeDocument.objects.filter(
            category=self.object.category,
            status='published'
        ).exclude(id=self.object.id)[:5]
        return context


class KnowledgeDocumentCreateView(LoginRequiredMixin, CreateView):
    """Create new knowledge document"""
    model = KnowledgeDocument
    form_class = KnowledgeDocumentForm
    template_name = 'knowledge/document_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        
        # Process with AI if file is uploaded
        if form.instance.file:
            process_document_with_ai.delay(form.instance.id)
        
        messages.success(self.request, 'Document created successfully!')
        return response


class KnowledgeDocumentUpdateView(LoginRequiredMixin, UpdateView):
    """Update knowledge document"""
    model = KnowledgeDocument
    form_class = KnowledgeDocumentForm
    template_name = 'knowledge/document_form.html'
    
    def form_valid(self, form):
        # Create version history
        if form.has_changed():
            DocumentVersion.objects.create(
                document=self.object,
                version_number=self.object.version,
                title=self.object.title,
                content=self.object.content,
                change_summary=form.cleaned_data.get('change_summary', 'Updated'),
                created_by=self.request.user
            )
        
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        
        messages.success(self.request, 'Document updated successfully!')
        return response


class KnowledgeDocumentDeleteView(LoginRequiredMixin, DeleteView):
    """Delete knowledge document"""
    model = KnowledgeDocument
    template_name = 'knowledge/document_confirm_delete.html'
    context_object_name = 'document'
    
    def get_success_url(self):
        messages.success(self.request, 'Document deleted successfully!')
        return reverse('knowledge:document_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Check permissions
        if self.object.created_by != request.user and not request.user.has_perm('knowledge.delete_knowledgedocument'):
            messages.error(request, 'You do not have permission to delete this document.')
            return redirect('knowledge:document_detail', pk=self.object.pk)
        
        return super().delete(request, *args, **kwargs)


# AJAX Views
@login_required
@require_http_methods(["POST"])
def add_document_comment(request, document_id):
    """Add comment to document via AJAX"""
    document = get_object_or_404(KnowledgeDocument, id=document_id)
    form = DocumentCommentForm(request.POST)
    
    if form.is_valid():
        comment = form.save(commit=False)
        comment.document = document
        comment.created_by = request.user
        
        parent_id = request.POST.get('parent_id')
        if parent_id:
            comment.parent_id = parent_id
        
        comment.save()
        
        # Log access
        DocumentAccess.objects.create(
            document=document,
            user=request.user,
            access_type='comment'
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'created_by': comment.created_by.get_full_name() or comment.created_by.username,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
    
    return JsonResponse({'success': False, 'errors': form.errors})


@login_required
def download_document(request, document_id):
    """Download document file"""
    document = get_object_or_404(KnowledgeDocument, id=document_id)
    
    # Check permissions
    if document.visibility == 'department' and document.department != request.user.employee.department:
        if not document.allowed_users.filter(id=request.user.id).exists():
            raise Http404("Document not found")
    elif document.visibility == 'restricted':
        if not document.allowed_users.filter(id=request.user.id).exists():
            raise Http404("Document not found")
    
    if not document.file:
        raise Http404("File not found")
    
    # Increment download count
    document.increment_download_count()
    
    # Log access
    DocumentAccess.objects.create(
        document=document,
        user=request.user,
        access_type='download'
    )
    
    # Serve file
    file_path = document.file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    
    raise Http404("File not found")


@login_required
def search_documents(request):
    """Advanced document search"""
    form = KnowledgeSearchForm(request.GET)
    documents = []
    
    if form.is_valid():
        query = form.cleaned_data.get('query')
        category = form.cleaned_data.get('category')
        document_type = form.cleaned_data.get('document_type')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        
        documents = KnowledgeDocument.objects.filter(status='published')
        
        if query:
            documents = documents.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(content__icontains=query) |
                Q(ai_extracted_keywords__icontains=query)
            )
        
        if category:
            documents = documents.filter(category=category)
        
        if document_type:
            documents = documents.filter(document_type=document_type)
        
        if date_from:
            documents = documents.filter(created_at__gte=date_from)
        
        if date_to:
            documents = documents.filter(created_at__lte=date_to)
        
        documents = documents.select_related('category', 'created_by').order_by('-updated_at')
        
        # Log search
        if query:
            SearchQuery.objects.create(
                query=query,
                user=request.user,
                results_count=documents.count(),
                search_filters={
                    'category': category.id if category else None,
                    'document_type': document_type,
                    'date_from': date_from.isoformat() if date_from else None,
                    'date_to': date_to.isoformat() if date_to else None,
                }
            )
    
    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'form': form,
        'documents': page_obj,
        'total_results': documents.count() if documents else 0
    }
    
    return render(request, 'knowledge/search_results.html', context)


# AI Processing Views
@login_required
@require_http_methods(["POST"])
def process_document_ai(request, document_id):
    """Trigger AI processing for document"""
    document = get_object_or_404(KnowledgeDocument, id=document_id)
    
    # Check if user can edit document
    if document.created_by != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        # Trigger AI processing
        job = process_document_with_ai.delay(document.id)
        
        return JsonResponse({
            'success': True,
            'job_id': str(job.id),
            'message': 'AI processing started'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def ai_job_status(request, job_id):
    """Check AI job status"""
    try:
        job = AIProcessingJob.objects.get(job_id=job_id)
        return JsonResponse({
            'status': job.status,
            'output_data': job.output_data,
            'error_message': job.error_message
        })
    except AIProcessingJob.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)


# Category Views
class DocumentCategoryListView(LoginRequiredMixin, ListView):
    """List all document categories"""
    model = DocumentCategory
    template_name = 'knowledge/categories.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = DocumentCategory.objects.filter(is_active=True)
        
        # Search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add statistics for each category
        for category in context['categories']:
            category.document_count = category.documents.filter(status='published').count()
            category.total_views = category.documents.aggregate(
                total=Sum('view_count')
            )['total'] or 0
            category.contributors_count = category.documents.values('created_by').distinct().count()
        
        return context


class DocumentCategoryDetailView(LoginRequiredMixin, DetailView):
    """Detail view for document category"""
    model = DocumentCategory
    template_name = 'knowledge/category_detail.html'
    context_object_name = 'category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get documents in this category
        documents = KnowledgeDocument.objects.filter(
            category=self.object,
            status='published'
        ).select_related('created_by').order_by('-updated_at')
        
        context['documents'] = documents
        context['document_count'] = documents.count()
        
        return context


class DocumentCategoryCreateView(LoginRequiredMixin, CreateView):
    """Create new document category"""
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'knowledge/category_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Category created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('knowledge:categories')


class DocumentCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Update document category"""
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'knowledge/category_form.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Category updated successfully!')
        return response
    
    def get_success_url(self):
        return reverse('knowledge:category_detail', kwargs={'pk': self.object.pk})


@login_required
def bulk_upload_documents(request):
    """Bulk upload documents"""
    if request.method == 'POST':
        # Handle bulk upload logic here
        files = request.FILES.getlist('documents')
        category_id = request.POST.get('category')
        
        if files:
            uploaded_count = 0
            for file in files:
                try:
                    # Create document for each file
                    document = KnowledgeDocument.objects.create(
                        title=file.name,
                        description=f'Bulk uploaded: {file.name}',
                        document_type='file',
                        file=file,
                        created_by=request.user,
                        status='draft'
                    )
                    
                    if category_id:
                        try:
                            category = DocumentCategory.objects.get(id=category_id)
                            document.category = category
                            document.save()
                        except DocumentCategory.DoesNotExist:
                            pass
                    
                    uploaded_count += 1
                except Exception as e:
                    messages.error(request, f'Error uploading {file.name}: {str(e)}')
            
            if uploaded_count > 0:
                messages.success(request, f'Successfully uploaded {uploaded_count} documents.')
            
            return redirect('knowledge:document_list')
        else:
            messages.error(request, 'Please select files to upload.')
    
    categories = DocumentCategory.objects.filter(is_active=True)
    context = {
        'categories': categories,
    }
    return render(request, 'knowledge/bulk_upload.html', context)


@login_required
def ai_assistant_view(request):
    """AI Assistant interface"""
    # Get available AI assistants
    assistants = AIAssistant.objects.filter(is_active=True)
    
    # Get recent AI processing jobs
    recent_jobs = AIProcessingJob.objects.all().order_by('-created_at')[:10]
    
    # Get AI statistics
    total_jobs = AIProcessingJob.objects.count()
    successful_jobs = AIProcessingJob.objects.filter(
        status='completed'
    ).count()
    
    context = {
        'assistants': assistants,
        'recent_jobs': recent_jobs,
        'total_jobs': total_jobs,
        'successful_jobs': successful_jobs,
        'success_rate': (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0,
    }
    
    return render(request, 'knowledge/ai_assistant.html', context)


# API ViewSets
class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """API ViewSet for Document Categories"""
    queryset = DocumentCategory.objects.filter(is_active=True)
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['parent', 'is_active']


class DocumentTagViewSet(viewsets.ModelViewSet):
    """API ViewSet for Document Tags"""
    queryset = DocumentTag.objects.all()
    serializer_class = DocumentTagSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """API ViewSet for Knowledge Documents"""
    queryset = KnowledgeDocument.objects.filter(status='published')
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'content']
    filterset_fields = ['category', 'document_type', 'status', 'visibility']
    ordering_fields = ['created_at', 'updated_at', 'view_count']
    ordering = ['-updated_at']
    
    @action(detail=True, methods=['post'])
    def increment_view(self, request, pk=None):
        """Increment document view count"""
        document = self.get_object()
        document.increment_view_count()
        return Response({'view_count': document.view_count})
    
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """Get related documents"""
        document = self.get_object()
        related = KnowledgeDocument.objects.filter(
            category=document.category,
            status='published'
        ).exclude(id=document.id)[:5]
        
        serializer = self.get_serializer(related, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular documents"""
        popular_docs = self.get_queryset().order_by('-view_count')[:10]
        serializer = self.get_serializer(popular_docs, many=True)
        return Response(serializer.data)


class AIAssistantViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for AI Assistants"""
    queryset = AIAssistant.objects.filter(is_active=True)
    serializer_class = AIAssistantSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def process_document(self, request, pk=None):
        """Process document with AI assistant"""
        assistant = self.get_object()
        document_id = request.data.get('document_id')
        
        if not document_id:
            return Response(
                {'error': 'document_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = KnowledgeDocument.objects.get(id=document_id)
            job = process_document_with_ai.delay(document.id, assistant.id)
            
            return Response({
                'job_id': str(job.id),
                'message': 'Processing started'
            })
        except KnowledgeDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    """API ViewSet for Knowledge Bases"""
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['is_public', 'department']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)