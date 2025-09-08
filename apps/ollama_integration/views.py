from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.conf import settings
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import json
import logging
from datetime import timedelta
from typing import Dict, Any

from .models import (
    OllamaModel, 
    OllamaProcessingJob, 
    OllamaConfiguration, 
    OllamaModelUsage, 
    OllamaPromptTemplate
)
from .client import OllamaClient, get_model_manager
from .serializers import (
    OllamaModelSerializer,
    OllamaProcessingJobSerializer,
    OllamaConfigurationSerializer,
    OllamaModelUsageSerializer,
    OllamaPromptTemplateSerializer
)
from .forms import (
    OllamaModelForm,
    OllamaConfigurationForm,
    OllamaPromptTemplateForm,
    ProcessingJobForm
)


logger = logging.getLogger(__name__)


# Dashboard Views
@login_required
def dashboard(request):
    """Ollama integration dashboard"""
    # Get basic statistics
    stats = {
        'total_models': OllamaModel.objects.count(),
        'active_models': OllamaModel.objects.filter(is_active=True).count(),
        'total_jobs': OllamaProcessingJob.objects.count(),
        'pending_jobs': OllamaProcessingJob.objects.filter(status='pending').count(),
        'running_jobs': OllamaProcessingJob.objects.filter(status='processing').count(),
        'completed_jobs': OllamaProcessingJob.objects.filter(status='completed').count(),
        'failed_jobs': OllamaProcessingJob.objects.filter(status='failed').count(),
    }
    
    # Get recent activity
    recent_jobs = OllamaProcessingJob.objects.select_related(
        'model', 'created_by'
    ).order_by('-created_at')[:10]
    
    # Get model performance data
    models_performance = OllamaModel.objects.filter(
        is_active=True
    ).annotate(
        job_count=Count('ollamaprocessingjob')
    ).order_by('-job_count')[:5]
    
    # Get usage statistics for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    usage_stats = OllamaModelUsage.objects.filter(
        created_at__gte=thirty_days_ago
    ).aggregate(
        total_requests=Count('id'),
        total_tokens=Sum('tokens_used'),
        avg_processing_time=Avg('processing_time'),
        success_rate=Avg('success')
    )
    
    # Get configuration health status
    configurations = OllamaConfiguration.objects.filter(is_active=True)
    healthy_configs = configurations.filter(is_healthy=True).count()
    
    context = {
        'stats': stats,
        'recent_jobs': recent_jobs,
        'models_performance': models_performance,
        'usage_stats': usage_stats,
        'configurations_count': configurations.count(),
        'healthy_configs': healthy_configs,
    }
    
    return render(request, 'ollama_integration/dashboard.html', context)


# Model Management Views
class OllamaModelListView(LoginRequiredMixin, ListView):
    """List all Ollama models"""
    model = OllamaModel
    template_name = 'ollama_integration/model_list.html'
    context_object_name = 'models'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = OllamaModel.objects.select_related('configuration')
        
        # Filter by task type
        task_type = self.request.GET.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by active status
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Search by name or description
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(model_name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task_types'] = OllamaModel.TASK_TYPE_CHOICES
        context['current_filters'] = {
            'task_type': self.request.GET.get('task_type', ''),
            'is_active': self.request.GET.get('is_active', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context


class OllamaModelDetailView(LoginRequiredMixin, DetailView):
    """Detail view for Ollama model"""
    model = OllamaModel
    template_name = 'ollama_integration/model_detail.html'
    context_object_name = 'model'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        model = self.get_object()
        
        # Get recent jobs for this model
        recent_jobs = OllamaProcessingJob.objects.filter(
            model=model
        ).select_related('created_by').order_by('-created_at')[:10]
        
        # Get usage statistics
        thirty_days_ago = timezone.now() - timedelta(days=30)
        usage_stats = OllamaModelUsage.objects.filter(
            model=model,
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_requests=Count('id'),
            total_tokens=Sum('tokens_used'),
            avg_processing_time=Avg('processing_time'),
            success_rate=Avg('success')
        )
        
        context.update({
            'recent_jobs': recent_jobs,
            'usage_stats': usage_stats,
        })
        
        return context


class OllamaModelCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Create new Ollama model"""
    model = OllamaModel
    form_class = OllamaModelForm
    template_name = 'ollama_integration/model_form.html'
    success_url = reverse_lazy('ollama_integration:model_list')
    permission_required = 'ollama_integration.add_ollamamodel'
    
    def form_valid(self, form):
        messages.success(self.request, 'Model created successfully!')
        return super().form_valid(form)


class OllamaModelUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Update Ollama model"""
    model = OllamaModel
    form_class = OllamaModelForm
    template_name = 'ollama_integration/model_form.html'
    success_url = reverse_lazy('ollama_integration:model_list')
    permission_required = 'ollama_integration.change_ollamamodel'
    
    def form_valid(self, form):
        messages.success(self.request, 'Model updated successfully!')
        return super().form_valid(form)


# Processing Job Views
class ProcessingJobListView(LoginRequiredMixin, ListView):
    """List processing jobs"""
    model = OllamaProcessingJob
    template_name = 'ollama_integration/job_list.html'
    context_object_name = 'jobs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = OllamaProcessingJob.objects.select_related(
            'model', 'created_by'
        )
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by task type
        task_type = self.request.GET.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        
        # Filter by user (if not superuser)
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = OllamaProcessingJob.STATUS_CHOICES
        context['task_type_choices'] = OllamaProcessingJob.TASK_TYPE_CHOICES
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'task_type': self.request.GET.get('task_type', ''),
        }
        return context


class ProcessingJobDetailView(LoginRequiredMixin, DetailView):
    """Detail view for processing job"""
    model = OllamaProcessingJob
    template_name = 'ollama_integration/job_detail.html'
    context_object_name = 'job'
    
    def get_queryset(self):
        queryset = OllamaProcessingJob.objects.select_related(
            'model', 'created_by'
        )
        
        # Non-superusers can only see their own jobs
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset


@login_required
@require_POST
def create_processing_job(request):
    """Create a new processing job"""
    form = ProcessingJobForm(request.POST)
    
    if form.is_valid():
        try:
            model_manager = get_model_manager()
            
            # Get the best model for the task
            task_type = form.cleaned_data['task_type']
            model = model_manager.get_best_model_for_task(task_type)
            
            if not model:
                return JsonResponse({
                    'success': False,
                    'error': f'No available model for task type: {task_type}'
                })
            
            # Create the job
            job = model_manager.create_processing_job(
                model=model,
                task_type=task_type,
                prompt=form.cleaned_data['prompt'],
                user=request.user,
                name=form.cleaned_data.get('name'),
                priority=form.cleaned_data.get('priority', 'normal'),
                system_prompt=form.cleaned_data.get('system_prompt')
            )
            
            return JsonResponse({
                'success': True,
                'job_id': job.job_id,
                'redirect_url': reverse_lazy('ollama_integration:job_detail', kwargs={'pk': job.pk})
            })
            
        except Exception as e:
            logger.error(f"Failed to create processing job: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    })


# API Views
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_text(request):
    """Generate text using Ollama model"""
    try:
        data = request.data
        
        # Validate required fields
        required_fields = ['prompt', 'task_type']
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        model_manager = get_model_manager()
        
        # Process with best available model
        response = model_manager.process_with_best_model(
            task_type=data['task_type'],
            prompt=data['prompt'],
            user=request.user,
            system_prompt=data.get('system_prompt'),
            temperature=data.get('temperature', 0.7),
            max_tokens=data.get('max_tokens', 2048)
        )
        
        if response.success:
            return Response({
                'success': True,
                'content': response.content,
                'model': response.model,
                'tokens_used': response.tokens_used,
                'processing_time': response.processing_time,
                'metadata': response.metadata
            })
        else:
            return Response(
                {
                    'success': False,
                    'error': response.error
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_streaming(request):
    """Generate streaming text using Ollama model"""
    try:
        data = request.data
        
        # Validate required fields
        required_fields = ['prompt', 'model_name']
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        client = OllamaClient()
        
        def generate():
            try:
                for chunk in client.generate(
                    model_name=data['model_name'],
                    prompt=data['prompt'],
                    system_prompt=data.get('system_prompt'),
                    temperature=data.get('temperature', 0.7),
                    max_tokens=data.get('max_tokens', 2048),
                    stream=True
                ):
                    if chunk.success:
                        yield f"data: {json.dumps({'content': chunk.content, 'done': False})}\n\n"
                    else:
                        yield f"data: {json.dumps({'error': chunk.error, 'done': True})}\n\n"
                        break
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
            finally:
                client.close()
        
        response = StreamingHttpResponse(
            generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        
        return response
    
    except Exception as e:
        logger.error(f"Streaming generation failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_completion(request):
    """Chat completion using Ollama model"""
    try:
        data = request.data
        
        # Validate required fields
        if 'messages' not in data or 'task_type' not in data:
            return Response(
                {'error': 'Missing required fields: messages, task_type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        model_manager = get_model_manager()
        model = model_manager.get_best_model_for_task(data['task_type'])
        
        if not model:
            return Response(
                {'error': f'No available model for task type: {data["task_type"]}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        client = OllamaClient(model.configuration.name)
        
        response = client.chat(
            model_name=model.effective_model_name,
            messages=data['messages'],
            temperature=data.get('temperature', model.temperature),
            max_tokens=data.get('max_tokens', model.max_tokens),
            stream=data.get('stream', False)
        )
        
        client.close()
        
        if response.success:
            # Record usage
            OllamaModelUsage.record_usage(
                model=model,
                user=request.user,
                tokens_used=response.tokens_used,
                processing_time=response.processing_time,
                success=True
            )
            
            return Response({
                'success': True,
                'content': response.content,
                'model': response.model,
                'tokens_used': response.tokens_used,
                'processing_time': response.processing_time
            })
        else:
            return Response(
                {
                    'success': False,
                    'error': response.error
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Chat completion failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_embeddings(request):
    """Generate embeddings using Ollama model"""
    try:
        data = request.data
        
        if 'text' not in data:
            return Response(
                {'error': 'Missing required field: text'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get embedding model
        model = OllamaModel.objects.filter(
            task_type='embedding',
            is_active=True
        ).first()
        
        if not model:
            return Response(
                {'error': 'No embedding model available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        client = OllamaClient(model.configuration.name)
        
        response = client.embed(
            model_name=model.effective_model_name,
            text=data['text']
        )
        
        client.close()
        
        if response.success:
            return Response({
                'success': True,
                'embeddings': response.metadata.get('embeddings', []),
                'model': response.model,
                'processing_time': response.processing_time
            })
        else:
            return Response(
                {
                    'success': False,
                    'error': response.error
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Health Check Views
@api_view(['GET'])
def health_check(request):
    """Check health of Ollama configurations"""
    try:
        configurations = OllamaConfiguration.objects.filter(is_active=True)
        results = []
        
        for config in configurations:
            try:
                client = OllamaClient(config.name)
                is_healthy = client.health_check()
                client.close()
                
                results.append({
                    'name': config.name,
                    'healthy': is_healthy,
                    'url': config.effective_base_url
                })
            except Exception as e:
                results.append({
                    'name': config.name,
                    'healthy': False,
                    'error': str(e),
                    'url': config.effective_base_url
                })
        
        overall_healthy = all(result['healthy'] for result in results)
        
        return Response({
            'healthy': overall_healthy,
            'configurations': results,
            'timestamp': timezone.now().isoformat()
        })
    
    except Exception as e:
        return Response(
            {
                'healthy': False,
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_available_models(request):
    """List available models on Ollama servers"""
    try:
        configurations = OllamaConfiguration.objects.filter(
            is_active=True,
            is_healthy=True
        )
        
        all_models = []
        
        for config in configurations:
            try:
                client = OllamaClient(config.name)
                models = client.list_models()
                client.close()
                
                for model in models:
                    model['configuration'] = config.name
                    all_models.append(model)
                    
            except Exception as e:
                logger.error(f"Failed to list models for {config.name}: {e}")
                continue
        
        return Response({
            'success': True,
            'models': all_models,
            'count': len(all_models)
        })
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ViewSets for REST API
class OllamaModelViewSet(viewsets.ModelViewSet):
    """ViewSet for Ollama models"""
    queryset = OllamaModel.objects.all()
    serializer_class = OllamaModelSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['task_type', 'is_active', 'configuration']
    search_fields = ['name', 'model_name', 'description']
    ordering_fields = ['name', 'created_at', 'priority', 'success_rate']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test a specific model"""
        model = self.get_object()
        test_prompt = request.data.get('prompt', 'Hello, this is a test.')
        
        try:
            client = OllamaClient(model.configuration.name)
            response = client.generate(
                model.effective_model_name,
                test_prompt,
                temperature=0.1,
                max_tokens=100
            )
            client.close()
            
            return Response({
                'success': response.success,
                'content': response.content,
                'processing_time': response.processing_time,
                'error': response.error
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reset_metrics(self, request, pk=None):
        """Reset model performance metrics"""
        model = self.get_object()
        model.reset_metrics()
        return Response({'success': True, 'message': 'Metrics reset successfully'})


class OllamaProcessingJobViewSet(viewsets.ModelViewSet):
    """ViewSet for processing jobs"""
    serializer_class = OllamaProcessingJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'task_type', 'priority', 'model']
    search_fields = ['name', 'job_id']
    ordering_fields = ['created_at', 'priority', 'processing_time']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter jobs based on user permissions"""
        queryset = OllamaProcessingJob.objects.select_related('model', 'created_by')
        
        # Non-superusers can only see their own jobs
        if not self.request.user.is_superuser:
            queryset = queryset.filter(created_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by when creating job"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a job"""
        job = self.get_object()
        
        if job.status != 'pending':
            return Response(
                {'error': 'Job is not in pending status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            model_manager = get_model_manager()
            response = model_manager.process_job(job)
            
            return Response({
                'success': response.success,
                'content': response.content,
                'processing_time': response.processing_time,
                'tokens_used': response.tokens_used,
                'error': response.error
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OllamaConfigurationViewSet(viewsets.ModelViewSet):
    """ViewSet for Ollama configurations"""
    queryset = OllamaConfiguration.objects.all()
    serializer_class = OllamaConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_active', 'is_healthy']
    search_fields = ['name', 'description', 'host']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to Ollama server"""
        config = self.get_object()
        
        try:
            client = OllamaClient(config.name)
            is_healthy = client.health_check()
            client.close()
            
            return Response({
                'healthy': is_healthy,
                'url': config.effective_base_url,
                'timestamp': timezone.now().isoformat()
            })
        except Exception as e:
            return Response(
                {'healthy': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OllamaPromptTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for prompt templates"""
    queryset = OllamaPromptTemplate.objects.all()
    serializer_class = OllamaPromptTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['task_type', 'is_active', 'created_by']
    search_fields = ['name', 'description', 'template']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        """Set created_by when creating template"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """Render template with provided variables"""
        template = self.get_object()
        variables = request.data.get('variables', {})
        
        try:
            rendered = template.render(variables)
            return Response({
                'success': True,
                'rendered': rendered
            })
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class OllamaModelUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for model usage statistics (read-only)"""
    queryset = OllamaModelUsage.objects.all()
    serializer_class = OllamaModelUsageSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['model', 'user', 'success']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter usage based on user permissions"""
        queryset = OllamaModelUsage.objects.select_related('model', 'user')
        
        # Non-superusers can only see their own usage
        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset