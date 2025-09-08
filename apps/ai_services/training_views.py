from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import os
import json
import mimetypes
from datetime import datetime, timedelta

from .models import TrainingData
from .permissions import (
    admin_manager_required, 
    training_data_upload_required, 
    training_data_manage_required,
    check_training_data_access
)
from .forms import TrainingDataForm, TrainingDataFilterForm
from .utils.model_evaluation import ModelEvaluator, calculate_success_ratio


@admin_manager_required
def training_data_dashboard(request):
    """
    Dashboard utama untuk training data management.
    Hanya dapat diakses oleh admin dan manager.
    """
    # Get filter parameters
    data_type = request.GET.get('data_type', '')
    target_service = request.GET.get('target_service', '')
    processing_status = request.GET.get('processing_status', '')
    search = request.GET.get('search', '')
    
    # Base queryset
    queryset = TrainingData.objects.filter(is_active=True)
    
    # Apply filters
    if data_type:
        queryset = queryset.filter(data_type=data_type)
    if target_service:
        queryset = queryset.filter(target_service=target_service)
    if processing_status:
        queryset = queryset.filter(processing_status=processing_status)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(file_name__icontains=search)
        )
    
    # Order by created_at descending
    queryset = queryset.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(queryset, 20)  # 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    stats = {
        'total': TrainingData.objects.filter(is_active=True).count(),
        'pending': TrainingData.objects.filter(is_active=True, processing_status='pending').count(),
        'processing': TrainingData.objects.filter(is_active=True, processing_status='processing').count(),
        'completed': TrainingData.objects.filter(is_active=True, processing_status='completed').count(),
        'failed': TrainingData.objects.filter(is_active=True, processing_status='failed').count(),
    }
    
    # Recent uploads (last 7 days)
    recent_date = timezone.now() - timedelta(days=7)
    recent_uploads = TrainingData.objects.filter(
        is_active=True, 
        created_at__gte=recent_date
    ).count()
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'recent_uploads': recent_uploads,
        'filter_form': TrainingDataFilterForm(request.GET),
        'current_filters': {
            'data_type': data_type,
            'target_service': target_service,
            'processing_status': processing_status,
            'search': search,
        }
    }
    
    return render(request, 'ai_services/training_data/dashboard.html', context)


@training_data_upload_required
def training_data_upload(request):
    """
    Form untuk upload training data baru.
    Hanya dapat diakses oleh admin dan manager dengan permission upload.
    """
    if request.method == 'POST':
        form = TrainingDataForm(request.POST, request.FILES)
        if form.is_valid():
            training_data = form.save(commit=False)
            training_data.uploaded_by = request.user
            
            # Set file metadata if file is uploaded
            if training_data.file:
                training_data.file_name = training_data.file.name
                training_data.file_size = training_data.file.size
                # Get file extension
                _, ext = os.path.splitext(training_data.file.name)
                training_data.file_type = ext.lower()
            
            training_data.save()
            
            messages.success(request, f'Training data "{training_data.title}" berhasil diupload.')
            return redirect('ai_services:training_data_dashboard')
        else:
            messages.error(request, 'Terjadi kesalahan saat mengupload training data. Periksa form kembali.')
    else:
        form = TrainingDataForm()
    
    context = {
        'form': form,
        'title': 'Upload Training Data Baru'
    }
    
    return render(request, 'ai_services/training_data/upload.html', context)


@admin_manager_required
def training_data_detail(request, training_data_id):
    """
    Detail view untuk training data.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    context = {
        'training_data': training_data,
        'can_edit': check_training_data_access(request.user),
        'can_delete': request.user.is_superuser or request.user.groups.filter(
            name__in=['HR_ADMIN', 'Budget Manager', 'IT Manager']
        ).exists()
    }
    
    return render(request, 'ai_services/training_data/detail.html', context)


@training_data_manage_required
def training_data_edit(request, training_data_id):
    """
    Edit training data.
    Hanya dapat diakses oleh admin dan manager senior.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    if request.method == 'POST':
        form = TrainingDataForm(request.POST, request.FILES, instance=training_data)
        if form.is_valid():
            updated_training_data = form.save(commit=False)
            
            # Update file metadata if new file is uploaded
            if 'file' in request.FILES:
                updated_training_data.file_name = updated_training_data.file.name
                updated_training_data.file_size = updated_training_data.file.size
                _, ext = os.path.splitext(updated_training_data.file.name)
                updated_training_data.file_type = ext.lower()
            
            updated_training_data.save()
            
            messages.success(request, f'Training data "{updated_training_data.title}" berhasil diupdate.')
            return redirect('ai_services:training_data_detail', training_data_id=training_data.id)
        else:
            messages.error(request, 'Terjadi kesalahan saat mengupdate training data.')
    else:
        form = TrainingDataForm(instance=training_data)
    
    context = {
        'form': form,
        'training_data': training_data,
        'title': f'Edit Training Data: {training_data.title}'
    }
    
    return render(request, 'ai_services/training_data/edit.html', context)


@training_data_manage_required
@require_http_methods(["POST"])
def training_data_delete(request, training_data_id):
    """
    Soft delete training data.
    Hanya dapat diakses oleh admin senior.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    # Soft delete
    training_data.is_active = False
    training_data.save(update_fields=['is_active', 'updated_at'])
    
    messages.success(request, f'Training data "{training_data.title}" berhasil dihapus.')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'Training data berhasil dihapus.'})
    
    return redirect('ai_services:training_data_dashboard')


@admin_manager_required
def training_data_download(request, training_data_id):
    """
    Download file training data.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    if not training_data.file:
        messages.error(request, 'File tidak tersedia untuk training data ini.')
        return redirect('ai_services:training_data_detail', training_data_id=training_data.id)
    
    try:
        file_path = training_data.file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
                response['Content-Disposition'] = f'attachment; filename="{training_data.file_name}"'
                return response
        else:
            messages.error(request, 'File tidak ditemukan di server.')
    except Exception as e:
        messages.error(request, f'Terjadi kesalahan saat mengunduh file: {str(e)}')
    
    return redirect('ai_services:training_data_detail', training_data_id=training_data.id)


@admin_manager_required
@require_http_methods(["POST"])
def training_data_process(request, training_data_id):
    """
    Trigger processing untuk training data.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    if training_data.processing_status == 'processing':
        return JsonResponse({
            'success': False, 
            'message': 'Training data sedang dalam proses.'
        })
    
    # Update status to processing
    training_data.processing_status = 'processing'
    training_data.processed_by = request.user
    training_data.save(update_fields=['processing_status', 'processed_by', 'updated_at'])
    
    # TODO: Trigger actual AI processing here
    # This would typically involve:
    # 1. Reading the uploaded file
    # 2. Processing based on data_type and target_service
    # 3. Updating the model or knowledge base
    # 4. Setting processing_status to 'completed' or 'failed'
    
    messages.success(request, f'Processing dimulai untuk training data "{training_data.title}".')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'message': 'Processing dimulai.',
            'status': 'processing'
        })
    
    return redirect('ai_services:training_data_detail', training_data_id=training_data.id)


@admin_manager_required
def training_data_api_stats(request):
    """
    API endpoint untuk statistik training data (untuk dashboard charts).
    """
    # Data untuk chart berdasarkan data_type
    data_type_stats = {}
    for choice in TrainingData._meta.get_field('data_type').choices:
        data_type_stats[choice[1]] = TrainingData.objects.filter(
            is_active=True, 
            data_type=choice[0]
        ).count()
    
    # Data untuk chart berdasarkan processing_status
    status_stats = {}
    for choice in TrainingData._meta.get_field('processing_status').choices:
        status_stats[choice[1]] = TrainingData.objects.filter(
            is_active=True, 
            processing_status=choice[0]
        ).count()
    
    # Upload trend (last 30 days)
    upload_trend = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        count = TrainingData.objects.filter(
            is_active=True,
            created_at__date=date
        ).count()
        upload_trend.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    upload_trend.reverse()  # Oldest first
    
    return JsonResponse({
        'data_type_stats': data_type_stats,
        'status_stats': status_stats,
        'upload_trend': upload_trend
    })


@admin_manager_required
def training_data_evaluation(request, training_data_id):
    """
    View untuk menampilkan evaluasi model dan metrik performa.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    # Get evaluation summary
    evaluation_summary = training_data.get_evaluation_summary()
    success_ratio = calculate_success_ratio(training_data)
    
    context = {
        'training_data': training_data,
        'evaluation_summary': evaluation_summary,
        'success_ratio': success_ratio,
        'has_metrics': any([
            training_data.accuracy_score,
            training_data.precision_score,
            training_data.recall_score,
            training_data.f1_score
        ])
    }
    
    return render(request, 'ai_services/training_data/evaluation.html', context)


@admin_manager_required
def training_data_metrics_api(request, training_data_id):
    """
    API endpoint untuk mendapatkan metrik evaluasi training data.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    evaluation_summary = training_data.get_evaluation_summary()
    
    return JsonResponse({
        'training_data_id': str(training_data.id),
        'title': training_data.title,
        'processing_status': training_data.processing_status,
        'evaluation_metrics': evaluation_summary,
        'success_ratio': training_data.get_success_ratio(),
        'last_updated': training_data.updated_at.isoformat() if training_data.updated_at else None
    })


@admin_manager_required
@require_http_methods(["POST"])
def training_data_update_metrics(request, training_data_id):
    """
    API endpoint untuk mengupdate metrik evaluasi training data.
    """
    training_data = get_object_or_404(TrainingData, id=training_data_id, is_active=True)
    
    try:
        data = json.loads(request.body)
        
        # Extract metrics from request
        accuracy = data.get('accuracy')
        precision = data.get('precision')
        recall = data.get('recall')
        f1_score = data.get('f1_score')
        additional_metrics = data.get('additional_metrics', {})
        validation_loss = data.get('validation_loss')
        epochs = data.get('epochs')
        model_size = data.get('model_size')
        
        # Update metrics
        training_data.set_evaluation_metrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1_score,
            additional_metrics=additional_metrics,
            validation_loss=validation_loss,
            epochs=epochs,
            model_size=model_size
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Metrik evaluasi berhasil diupdate',
            'evaluation_summary': training_data.get_evaluation_summary()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@admin_manager_required
def training_data_performance_dashboard(request):
    """
    Dashboard untuk menampilkan performa semua training data.
    """
    # Get all training data with metrics
    training_data_list = TrainingData.objects.filter(
        is_active=True,
        processing_status='completed'
    ).exclude(
        accuracy_score__isnull=True,
        precision_score__isnull=True,
        recall_score__isnull=True,
        f1_score__isnull=True
    ).order_by('-accuracy_score')
    
    # Calculate average metrics
    total_count = training_data_list.count()
    if total_count > 0:
        avg_metrics = {
            'accuracy': sum(td.accuracy_score or 0 for td in training_data_list) / total_count,
            'precision': sum(td.precision_score or 0 for td in training_data_list) / total_count,
            'recall': sum(td.recall_score or 0 for td in training_data_list) / total_count,
            'f1_score': sum(td.f1_score or 0 for td in training_data_list) / total_count,
        }
    else:
        avg_metrics = {
            'accuracy': 0,
            'precision': 0,
            'recall': 0,
            'f1_score': 0,
        }
    
    # Performance by service type
    service_performance = {}
    for choice in TrainingData._meta.get_field('target_service').choices:
        service_data = training_data_list.filter(target_service=choice[0])
        if service_data.exists():
            service_performance[choice[1]] = {
                'count': service_data.count(),
                'avg_accuracy': sum(td.accuracy_score or 0 for td in service_data) / service_data.count(),
                'best_accuracy': max(td.accuracy_score or 0 for td in service_data),
            }
    
    context = {
        'training_data_list': training_data_list[:20],  # Top 20
        'total_count': total_count,
        'avg_metrics': avg_metrics,
        'service_performance': service_performance,
    }
    
    return render(request, 'ai_services/training_data/performance_dashboard.html', context)