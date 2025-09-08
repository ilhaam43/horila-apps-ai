from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    AIModelRegistry,
    AIPrediction,
    AIAnalytics,
    KnowledgeBase,
    DocumentClassification,
    SearchQuery,
    NLPAnalysis,
    WorkflowExecution,
    AIServiceLog,
    TrainingData
)

@admin.register(AIModelRegistry)
class AIModelRegistryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'service_type', 'model_type', 'version', 
        'is_active', 'accuracy_score', 'training_date', 'created_at'
    ]
    list_filter = [
        'service_type', 'model_type', 'is_active', 'training_date', 'created_at'
    ]
    search_fields = ['name', 'service_type', 'model_type']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = [
        ('Basic Information', {
            'fields': ('id', 'name', 'service_type', 'model_type', 'version')
        }),
        ('Model Configuration', {
            'fields': ('model_path', 'config', 'is_active')
        }),
        ('Performance Metrics', {
            'fields': ('accuracy_score', 'training_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by')
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(AIPrediction)
class AIPredictionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'model', 'confidence_score', 'processing_time_ms', 
        'is_successful', 'created_at', 'created_by'
    ]
    list_filter = [
        'model__service_type', 'is_successful', 'created_at', 
        'model__name', 'confidence_score'
    ]
    search_fields = ['id', 'model__name', 'error_message']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['model', 'created_by']
    
    fieldsets = [
        ('Prediction Info', {
            'fields': ('id', 'model', 'confidence_score', 'processing_time_ms')
        }),
        ('Data', {
            'fields': ('input_data', 'prediction_result'),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('is_successful', 'error_message')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('model', 'created_by')
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for predictions

@admin.register(AIAnalytics)
class AIAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'service_type', 'metric_name', 'metric_value', 'date', 'created_at'
    ]
    list_filter = ['service_type', 'metric_name', 'date', 'created_at']
    search_fields = ['service_type', 'metric_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    fieldsets = [
        ('Metric Information', {
            'fields': ('service_type', 'metric_name', 'metric_value', 'date')
        }),
        ('Additional Data', {
            'fields': ('metric_data',),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    ]
    
    def changelist_view(self, request, extra_context=None):
        # Add summary statistics
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            
            # Calculate summary stats
            summary = {
                'total_metrics': qs.count(),
                'services_count': qs.values('service_type').distinct().count(),
                'avg_metric_value': qs.aggregate(Avg('metric_value'))['metric_value__avg'] or 0,
                'recent_metrics': qs.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count()
            }
            
            response.context_data['summary'] = summary
        except (AttributeError, KeyError):
            pass
        
        return response

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'content_type', 'category', 'is_active', 
        'view_count', 'last_accessed', 'created_at'
    ]
    list_filter = [
        'content_type', 'category', 'is_active', 'created_at', 'last_accessed'
    ]
    search_fields = ['title', 'content', 'category']
    readonly_fields = ['id', 'view_count', 'last_accessed', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ('id', 'title', 'content_type', 'category')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Classification', {
            'fields': ('tags', 'metadata'),
            'classes': ['collapse']
        }),
        ('AI Data', {
            'fields': ('embedding_vector', 'embedding_model'),
            'classes': ['collapse']
        }),
        ('Status & Analytics', {
            'fields': ('is_active', 'view_count', 'last_accessed')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by')
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(DocumentClassification)
class DocumentClassificationAdmin(admin.ModelAdmin):
    list_display = [
        'document_name', 'predicted_category', 'confidence_score', 
        'classification_method', 'is_successful', 'created_at'
    ]
    list_filter = [
        'predicted_category', 'classification_method', 'is_successful', 
        'file_type', 'created_at'
    ]
    search_fields = ['document_name', 'predicted_category', 'document_path']
    readonly_fields = [
        'id', 'document_hash', 'processing_time_ms', 'created_at'
    ]
    
    fieldsets = [
        ('Document Information', {
            'fields': (
                'id', 'document_name', 'document_path', 'document_hash',
                'file_size', 'file_type', 'extracted_text_length'
            )
        }),
        ('Classification Results', {
            'fields': (
                'predicted_category', 'confidence_score', 'classification_method'
            )
        }),
        ('All Predictions', {
            'fields': ('all_predictions',),
            'classes': ['collapse']
        }),
        ('Processing Info', {
            'fields': ('processing_time_ms', 'is_successful', 'error_message')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for classifications

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = [
        'query_text_short', 'query_type', 'results_count', 
        'processing_time_ms', 'user_satisfaction', 'created_at'
    ]
    list_filter = [
        'query_type', 'results_count', 'user_satisfaction', 'created_at'
    ]
    search_fields = ['query_text']
    readonly_fields = ['id', 'processing_time_ms', 'created_at']
    
    fieldsets = [
        ('Query Information', {
            'fields': ('id', 'query_text', 'query_type')
        }),
        ('Search Parameters', {
            'fields': ('search_models', 'filters', 'limit'),
            'classes': ['collapse']
        }),
        ('Results', {
            'fields': ('results_count', 'results_data', 'processing_time_ms'),
            'classes': ['collapse']
        }),
        ('User Interaction', {
            'fields': ('clicked_results', 'user_satisfaction')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        })
    ]
    
    def query_text_short(self, obj):
        return obj.query_text[:50] + '...' if len(obj.query_text) > 50 else obj.query_text
    query_text_short.short_description = 'Query Text'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for search queries

@admin.register(NLPAnalysis)
class NLPAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'text_short', 'analysis_type', 'sentiment_label', 
        'sentiment_score', 'model_used', 'created_at'
    ]
    list_filter = [
        'analysis_type', 'sentiment_label', 'model_used', 'created_at'
    ]
    search_fields = ['text', 'sentiment_label']
    readonly_fields = [
        'id', 'text_hash', 'processing_time_ms', 'created_at'
    ]
    
    fieldsets = [
        ('Text Information', {
            'fields': ('id', 'text', 'text_hash')
        }),
        ('Analysis Results', {
            'fields': (
                'analysis_type', 'sentiment_label', 'sentiment_score',
                'entities', 'classification_result', 'text_statistics'
            )
        }),
        ('Processing Info', {
            'fields': ('processing_time_ms', 'model_used')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        })
    ]
    
    def text_short(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_short.short_description = 'Text'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for NLP analyses

@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'workflow_name', 'workflow_type', 'n8n_status', 
        'is_successful', 'processing_time_ms', 'created_at'
    ]
    list_filter = [
        'workflow_type', 'n8n_status', 'is_successful', 'created_at'
    ]
    search_fields = ['workflow_name', 'workflow_type', 'n8n_execution_id']
    readonly_fields = [
        'id', 'n8n_execution_id', 'processing_time_ms', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Workflow Information', {
            'fields': (
                'id', 'workflow_type', 'workflow_name', 
                'n8n_workflow_id', 'n8n_execution_id'
            )
        }),
        ('Input Data', {
            'fields': ('input_data', 'rag_query'),
            'classes': ['collapse']
        }),
        ('RAG Results', {
            'fields': ('rag_results',),
            'classes': ['collapse']
        }),
        ('Execution Status', {
            'fields': ('n8n_status', 'is_successful', 'error_message')
        }),
        ('Results', {
            'fields': ('execution_result', 'processing_time_ms'),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by')
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for workflow executions

@admin.register(AIServiceLog)
class AIServiceLogAdmin(admin.ModelAdmin):
    list_display = [
        'service_type', 'operation', 'log_level', 
        'message_short', 'request_id', 'created_at'
    ]
    list_filter = [
        'service_type', 'log_level', 'operation', 'created_at'
    ]
    search_fields = ['service_type', 'operation', 'message', 'request_id']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Log Information', {
            'fields': (
                'id', 'service_type', 'operation', 'log_level', 'message'
            )
        }),
        ('Request Information', {
            'fields': ('request_id', 'user_id', 'ip_address')
        }),
        ('Extra Data', {
            'fields': ('extra_data',),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    ]
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    def has_add_permission(self, request):
        return False  # Logs are created programmatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for logs
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Only superusers can delete logs

# Custom admin site configuration
admin.site.site_header = "Horilla AI Services Administration"
admin.site.site_title = "AI Services Admin"
admin.site.index_title = "Welcome to AI Services Administration"

# Add custom CSS for better JSON field display
class Media:
    css = {
        'all': ('admin/css/ai_services_admin.css',)
    }
    js = ('admin/js/ai_services_admin.js',)

# Register custom admin actions
def export_predictions_csv(modeladmin, request, queryset):
    """Export predictions to CSV."""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ai_predictions.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Model', 'Confidence Score', 'Processing Time (ms)', 
        'Is Successful', 'Created At'
    ])
    
    for prediction in queryset:
        writer.writerow([
            str(prediction.id),
            prediction.model.name,
            prediction.confidence_score,
            prediction.processing_time_ms,
            prediction.is_successful,
            prediction.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

export_predictions_csv.short_description = "Export selected predictions to CSV"

# Add the action to AIPredictionAdmin
AIPredictionAdmin.actions = [export_predictions_csv]

def cleanup_old_logs(modeladmin, request, queryset):
    """Clean up logs older than 30 days."""
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    old_logs = AIServiceLog.objects.filter(created_at__lt=cutoff_date)
    count = old_logs.count()
    old_logs.delete()
    
    modeladmin.message_user(
        request, 
        f"Successfully deleted {count} log entries older than 30 days."
    )

cleanup_old_logs.short_description = "Clean up logs older than 30 days"

# Add the action to AIServiceLogAdmin
AIServiceLogAdmin.actions = [cleanup_old_logs]

@admin.register(TrainingData)
class TrainingDataAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'data_type', 'target_service', 'processing_status', 
        'is_active', 'uploaded_by', 'created_at'
    ]
    list_filter = [
        'data_type', 'target_service', 'processing_status', 
        'is_active', 'is_processed', 'created_at'
    ]
    search_fields = ['title', 'description', 'file_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'file_size', 'file_type']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ('id', 'title', 'description')
        }),
        ('File Upload', {
            'fields': ('file', 'file_name', 'file_size', 'file_type'),
        }),
        ('AI Configuration', {
            'fields': ('data_type', 'target_service')
        }),
        ('Processing', {
            'fields': ('processing_status', 'processing_result', 'error_message', 'processing_time_ms')
        }),
        ('Metadata', {
            'fields': ('metadata', 'tags'),
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ('is_active', 'is_processed')
        }),
        ('Timestamps & Users', {
            'fields': ('created_at', 'updated_at', 'uploaded_by', 'processed_by'),
            'classes': ['collapse']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uploaded_by', 'processed_by')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
            # Set file metadata if file is uploaded
            if obj.file:
                obj.file_name = obj.file.name
                obj.file_size = obj.file.size
                # Get file extension
                import os
                _, ext = os.path.splitext(obj.file.name)
                obj.file_type = ext.lower()
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """Only admin and managers can add training data"""
        if request.user.is_superuser:
            return True
        # Check if user is in admin or manager groups
        user_groups = request.user.groups.values_list('name', flat=True)
        allowed_groups = ['HR_ADMIN', 'MANAGER', 'Budget Manager', 'Finance Team']
        return any(group in allowed_groups for group in user_groups)
    
    def has_change_permission(self, request, obj=None):
        """Only admin and managers can change training data"""
        if request.user.is_superuser:
            return True
        user_groups = request.user.groups.values_list('name', flat=True)
        allowed_groups = ['HR_ADMIN', 'MANAGER', 'Budget Manager', 'Finance Team']
        return any(group in allowed_groups for group in user_groups)
    
    def has_delete_permission(self, request, obj=None):
        """Only admin and managers can delete training data"""
        if request.user.is_superuser:
            return True
        user_groups = request.user.groups.values_list('name', flat=True)
        allowed_groups = ['HR_ADMIN', 'MANAGER', 'Budget Manager']
        return any(group in allowed_groups for group in user_groups)