from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Count, Avg, Sum
from django.utils.safestring import mark_safe
import json

from .models import (
    NLPModel, TextAnalysisJob, SentimentAnalysisResult,
    NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics, NLPConfiguration
)
from .client import IndonesianNLPClient


@admin.register(NLPConfiguration)
class NLPConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'max_concurrent_jobs', 'job_timeout', 'max_text_length',
        'model_cache_size', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'is_active']
        }),
        ('Processing Settings', {
            'fields': [
                'max_concurrent_jobs', 'job_timeout', 'max_text_length'
            ]
        }),
        ('Model Management', {
            'fields': [
                'auto_load_models', 'model_cache_size', 'model_unload_timeout'
            ]
        }),
        ('Resource Limits', {
            'fields': ['max_memory_usage', 'cpu_limit']
        }),
        ('Logging & Monitoring', {
            'fields': ['enable_detailed_logging', 'log_level']
        }),
        ('API Settings', {
            'fields': ['api_rate_limit', 'enable_api_key_auth']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    actions = ['activate_configuration', 'deactivate_configuration']
    
    def activate_configuration(self, request, queryset):
        # Deactivate all other configurations first
        NLPConfiguration.objects.all().update(is_active=False)
        # Activate selected configurations
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} configuration(s) activated successfully.',
            messages.SUCCESS
        )
    activate_configuration.short_description = "Activate selected configurations"
    
    def deactivate_configuration(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} configuration(s) deactivated successfully.',
            messages.SUCCESS
        )
    deactivate_configuration.short_description = "Deactivate selected configurations"


@admin.register(NLPModel)
class NLPModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model_type', 'framework', 'is_active', 'is_loaded',
        'accuracy_display', 'last_used', 'usage_count'
    ]
    list_filter = [
        'model_type', 'framework', 'is_active', 'is_loaded', 'created_at'
    ]
    search_fields = ['name', 'description', 'model_path']
    readonly_fields = [
        'is_loaded', 'load_time', 'memory_usage', 'last_used',
        'created_at', 'updated_at', 'usage_count'
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'model_type', 'framework']
        }),
        ('Model Configuration', {
            'fields': ['model_path', 'tokenizer_path', 'config', 'preprocessing_config', 'postprocessing_config']
        }),
        ('Performance Metrics', {
            'fields': ['accuracy', 'precision', 'recall', 'f1_score']
        }),
        ('Status & Usage', {
            'fields': [
                'is_active', 'is_loaded', 'load_time', 'memory_usage',
                'last_used', 'usage_count'
            ]
        }),
        ('Metadata', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    actions = [
        'load_models', 'unload_models', 'test_models',
        'activate_models', 'deactivate_models'
    ]
    
    def accuracy_display(self, obj):
        if obj.accuracy is not None:
            return f"{obj.accuracy:.2%}"
        return "-"
    accuracy_display.short_description = "Accuracy"
    
    def usage_count(self, obj):
        return obj.usage_stats.aggregate(total=Sum('total_requests'))['total'] or 0
    usage_count.short_description = "Total Usage"
    
    def load_models(self, request, queryset):
        client = IndonesianNLPClient()
        loaded_count = 0
        
        for model in queryset:
            if client.load_model(model.name):
                loaded_count += 1
        
        self.message_user(
            request,
            f'{loaded_count} model(s) loaded successfully.',
            messages.SUCCESS
        )
    load_models.short_description = "Load selected models"
    
    def unload_models(self, request, queryset):
        client = IndonesianNLPClient()
        unloaded_count = 0
        
        for model in queryset:
            if client.unload_model(model.name):
                unloaded_count += 1
        
        self.message_user(
            request,
            f'{unloaded_count} model(s) unloaded successfully.',
            messages.SUCCESS
        )
    unload_models.short_description = "Unload selected models"
    
    def test_models(self, request, queryset):
        client = IndonesianNLPClient()
        test_text = "Saya sangat senang dengan layanan ini."
        
        for model in queryset:
            try:
                if model.model_type == 'sentiment':
                    result = client.analyze_sentiment(test_text, model.name)
                    messages.success(
                        request,
                        f"Model {model.name} test successful: {result['sentiment']} ({result['confidence']:.2f})"
                    )
                elif model.model_type == 'ner':
                    entities = client.extract_entities(test_text, model.name)
                    messages.success(
                        request,
                        f"Model {model.name} test successful: {len(entities)} entities found"
                    )
                elif model.model_type == 'classification':
                    result = client.classify_text(test_text, model.name)
                    messages.success(
                        request,
                        f"Model {model.name} test successful: {result['predicted_class']} ({result['confidence']:.2f})"
                    )
            except Exception as e:
                messages.error(
                    request,
                    f"Model {model.name} test failed: {str(e)}"
                )
    test_models.short_description = "Test selected models"
    
    def activate_models(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} model(s) activated successfully.',
            messages.SUCCESS
        )
    activate_models.short_description = "Activate selected models"
    
    def deactivate_models(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} model(s) deactivated successfully.',
            messages.SUCCESS
        )
    deactivate_models.short_description = "Deactivate selected models"


@admin.register(TextAnalysisJob)
class TextAnalysisJobAdmin(admin.ModelAdmin):
    list_display = [
        'job_id', 'model', 'status', 'priority', 'progress',
        'confidence_display', 'processing_time_display', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'model__model_type', 'model__name', 'created_at'
    ]
    search_fields = ['job_id', 'name', 'input_text']
    readonly_fields = [
        'job_id', 'result_display', 'processing_time', 'duration',
        'created_at', 'started_at', 'completed_at'
    ]
    
    fieldsets = [
        ('Job Information', {
            'fields': ['job_id', 'name', 'description', 'model']
        }),
        ('Input Data', {
            'fields': ['input_text', 'input_language', 'parameters']
        }),
        ('Job Status', {
            'fields': ['status', 'priority', 'progress', 'retry_count', 'max_retries']
        }),
        ('Results', {
            'fields': ['result_display', 'confidence_score', 'processing_time', 'duration']
        }),
        ('Error Handling', {
            'fields': ['error_message']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'started_at', 'completed_at'],
            'classes': ['collapse']
        }),
        ('User Information', {
            'fields': ['created_by'],
            'classes': ['collapse']
        })
    ]
    
    actions = ['retry_failed_jobs', 'cancel_pending_jobs', 'delete_old_jobs']
    
    def confidence_display(self, obj):
        if obj.confidence_score is not None:
            return f"{obj.confidence_score:.2%}"
        return "-"
    confidence_display.short_description = "Confidence"
    
    def processing_time_display(self, obj):
        if obj.processing_time is not None:
            return f"{obj.processing_time:.2f}s"
        return "-"
    processing_time_display.short_description = "Processing Time"
    
    def result_display(self, obj):
        if obj.result:
            formatted_result = json.dumps(obj.result, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 200px; overflow-y: auto;">{}</pre>', formatted_result)
        return "-"
    result_display.short_description = "Result"
    
    def retry_failed_jobs(self, request, queryset):
        failed_jobs = queryset.filter(status='failed')
        updated = failed_jobs.update(
            status='pending',
            error_message='',
            started_at=None,
            completed_at=None
        )
        self.message_user(
            request,
            f'{updated} failed job(s) queued for retry.',
            messages.SUCCESS
        )
    retry_failed_jobs.short_description = "Retry failed jobs"
    
    def cancel_pending_jobs(self, request, queryset):
        pending_jobs = queryset.filter(status__in=['pending', 'processing'])
        updated = pending_jobs.update(status='cancelled')
        self.message_user(
            request,
            f'{updated} job(s) cancelled.',
            messages.SUCCESS
        )
    cancel_pending_jobs.short_description = "Cancel pending/processing jobs"
    
    def delete_old_jobs(self, request, queryset):
        # Delete jobs older than 30 days
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        old_jobs = queryset.filter(created_at__lt=cutoff_date)
        count = old_jobs.count()
        old_jobs.delete()
        self.message_user(
            request,
            f'{count} old job(s) deleted.',
            messages.SUCCESS
        )
    delete_old_jobs.short_description = "Delete jobs older than 30 days"


class NamedEntityResultInline(admin.TabularInline):
    model = NamedEntityResult
    extra = 0
    readonly_fields = ['text', 'label', 'start_pos', 'end_pos', 'confidence', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SentimentAnalysisResult)
class SentimentAnalysisResultAdmin(admin.ModelAdmin):
    list_display = [
        'job', 'sentiment', 'confidence_display', 'positive_score_display',
        'negative_score_display', 'neutral_score_display', 'created_at'
    ]
    list_filter = ['sentiment', 'created_at']
    search_fields = ['job__job_id', 'job__input_text']
    readonly_fields = [
        'job', 'sentiment', 'confidence', 'positive_score',
        'negative_score', 'neutral_score', 'subjectivity',
        'emotion_scores_display', 'keywords_display', 'created_at'
    ]
    
    def confidence_display(self, obj):
        return f"{obj.confidence:.2%}"
    confidence_display.short_description = "Confidence"
    
    def positive_score_display(self, obj):
        return f"{obj.positive_score:.2%}"
    positive_score_display.short_description = "Positive"
    
    def negative_score_display(self, obj):
        return f"{obj.negative_score:.2%}"
    negative_score_display.short_description = "Negative"
    
    def neutral_score_display(self, obj):
        return f"{obj.neutral_score:.2%}"
    neutral_score_display.short_description = "Neutral"
    
    def emotion_scores_display(self, obj):
        if obj.emotion_scores:
            formatted_scores = json.dumps(obj.emotion_scores, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_scores)
        return "-"
    emotion_scores_display.short_description = "Emotion Scores"
    
    def keywords_display(self, obj):
        if obj.keywords:
            return ", ".join(obj.keywords)
        return "-"
    keywords_display.short_description = "Keywords"


@admin.register(NamedEntityResult)
class NamedEntityResultAdmin(admin.ModelAdmin):
    list_display = [
        'job', 'text', 'label', 'confidence_display',
        'position_display', 'created_at'
    ]
    list_filter = ['label', 'created_at']
    search_fields = ['job__job_id', 'text', 'normalized_text']
    readonly_fields = [
        'job', 'text', 'label', 'start_pos', 'end_pos',
        'confidence', 'normalized_text', 'context', 'created_at'
    ]
    
    def confidence_display(self, obj):
        return f"{obj.confidence:.2%}"
    confidence_display.short_description = "Confidence"
    
    def position_display(self, obj):
        return f"{obj.start_pos}-{obj.end_pos}"
    position_display.short_description = "Position"


@admin.register(TextClassificationResult)
class TextClassificationResultAdmin(admin.ModelAdmin):
    list_display = [
        'job', 'predicted_class', 'confidence_display', 'created_at'
    ]
    list_filter = ['predicted_class', 'created_at']
    search_fields = ['job__job_id', 'predicted_class']
    readonly_fields = [
        'job', 'predicted_class', 'confidence', 'class_probabilities_display',
        'top_features_display', 'feature_weights_display', 'created_at'
    ]
    
    def confidence_display(self, obj):
        return f"{obj.confidence:.2%}"
    confidence_display.short_description = "Confidence"
    
    def class_probabilities_display(self, obj):
        if obj.class_probabilities:
            formatted_probs = json.dumps(obj.class_probabilities, indent=2, ensure_ascii=False)
            return format_html('<pre>{}</pre>', formatted_probs)
        return "-"
    class_probabilities_display.short_description = "Class Probabilities"
    
    def top_features_display(self, obj):
        if obj.top_features:
            return ", ".join(str(f) for f in obj.top_features[:10])  # Show top 10
        return "-"
    top_features_display.short_description = "Top Features"
    
    def feature_weights_display(self, obj):
        if obj.feature_weights:
            # Show top 5 feature weights
            sorted_weights = sorted(obj.feature_weights.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            formatted_weights = "\n".join([f"{k}: {v:.4f}" for k, v in sorted_weights])
            return format_html('<pre>{}</pre>', formatted_weights)
        return "-"
    feature_weights_display.short_description = "Feature Weights (Top 5)"


@admin.register(ModelUsageStatistics)
class ModelUsageStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        'model', 'date', 'hour', 'total_requests', 'success_rate_display',
        'avg_processing_time_display', 'peak_memory_display'
    ]
    list_filter = ['model', 'date']
    search_fields = ['model__name']
    readonly_fields = [
        'model', 'total_requests', 'successful_requests', 'failed_requests',
        'avg_processing_time', 'min_processing_time', 'max_processing_time',
        'total_cpu_time', 'peak_memory_usage', 'date', 'hour',
        'success_rate_display', 'created_at', 'updated_at'
    ]
    
    date_hierarchy = 'date'
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.2%}"
    success_rate_display.short_description = "Success Rate"
    
    def avg_processing_time_display(self, obj):
        return f"{obj.avg_processing_time:.3f}s"
    avg_processing_time_display.short_description = "Avg Time"
    
    def peak_memory_display(self, obj):
        if obj.peak_memory_usage:
            return f"{obj.peak_memory_usage / 1024 / 1024:.1f} MB"
        return "-"
    peak_memory_display.short_description = "Peak Memory"
    
    actions = ['export_statistics']
    
    def export_statistics(self, request, queryset):
        # This would implement CSV export functionality
        self.message_user(
            request,
            "Statistics export functionality would be implemented here.",
            messages.INFO
        )
    export_statistics.short_description = "Export statistics to CSV"
    
    def changelist_view(self, request, extra_context=None):
        # Add summary statistics to the changelist view
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            summary = qs.aggregate(
                total_requests=Sum('total_requests'),
                total_successful=Sum('successful_requests'),
                total_failed=Sum('failed_requests'),
                avg_time=Avg('avg_processing_time')
            )
            
            response.context_data['summary'] = {
                'total_requests': summary['total_requests'] or 0,
                'total_successful': summary['total_successful'] or 0,
                'total_failed': summary['total_failed'] or 0,
                'overall_success_rate': (
                    summary['total_successful'] / summary['total_requests'] * 100
                    if summary['total_requests'] else 0
                ),
                'avg_processing_time': summary['avg_time'] or 0
            }
        except (AttributeError, KeyError):
            pass
        
        return response


# Custom admin site configuration
admin.site.site_header = "Indonesian NLP Administration"
admin.site.site_title = "Indonesian NLP Admin"
admin.site.index_title = "Welcome to Indonesian NLP Administration"