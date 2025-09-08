from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta

from .models import (
    OllamaModel, 
    OllamaProcessingJob, 
    OllamaConfiguration, 
    OllamaModelUsage, 
    OllamaPromptTemplate
)
from .client import OllamaClient


@admin.register(OllamaConfiguration)
class OllamaConfigurationAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'host', 'port', 'is_active', 'is_healthy', 
        'max_concurrent_requests', 'created_at', 'health_status'
    ]
    list_filter = ['is_active', 'is_healthy', 'created_at']
    search_fields = ['name', 'description', 'host']
    readonly_fields = ['created_at', 'updated_at', 'last_health_check', 'health_status']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Connection Settings', {
            'fields': ('host', 'port', 'use_ssl', 'api_key', 'username', 'password')
        }),
        ('Performance Settings', {
            'fields': (
                'timeout', 'max_retries', 'retry_delay', 
                'max_concurrent_requests', 'request_queue_size'
            )
        }),
        ('Health Status', {
            'fields': ('is_healthy', 'last_health_check', 'health_status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['test_connection', 'activate_configurations', 'deactivate_configurations']
    
    def test_connection(self, request, queryset):
        """Test connection to Ollama servers"""
        results = []
        for config in queryset:
            try:
                client = OllamaClient(config.name)
                is_healthy = client.health_check()
                client.close()
                
                if is_healthy:
                    results.append(f"{config.name}: Connection successful")
                else:
                    results.append(f"{config.name}: Connection failed")
            except Exception as e:
                results.append(f"{config.name}: Error - {str(e)}")
        
        self.message_user(request, "\n".join(results))
    test_connection.short_description = "Test connection to selected configurations"
    
    def activate_configurations(self, request, queryset):
        """Activate selected configurations"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} configurations activated.")
    activate_configurations.short_description = "Activate selected configurations"
    
    def deactivate_configurations(self, request, queryset):
        """Deactivate selected configurations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} configurations deactivated.")
    deactivate_configurations.short_description = "Deactivate selected configurations"


@admin.register(OllamaModel)
class OllamaModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model_name', 'task_type', 'is_active', 'priority',
        'success_rate_display', 'avg_response_time_display', 'total_requests',
        'created_at'
    ]
    list_filter = [
        'task_type', 'is_active', 'priority', 'created_at',
        'configuration__name'
    ]
    search_fields = ['name', 'model_name', 'description']
    readonly_fields = [
        'created_at', 'updated_at', 'total_requests', 'successful_requests',
        'failed_requests', 'average_response_time', 'success_rate_display',
        'avg_response_time_display', 'model_stats'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'model_name', 'description', 'task_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('configuration', 'priority')
        }),
        ('Model Parameters', {
            'fields': (
                'temperature', 'max_tokens', 'top_p', 'top_k',
                'system_prompt', 'custom_parameters'
            )
        }),
        ('Performance Metrics', {
            'fields': (
                'total_requests', 'successful_requests', 'failed_requests',
                'average_response_time', 'success_rate_display', 'avg_response_time_display'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('model_stats',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['test_models', 'activate_models', 'deactivate_models', 'reset_metrics']
    
    def success_rate_display(self, obj):
        """Display success rate with color coding"""
        rate = obj.success_rate
        if rate >= 0.9:
            color = 'green'
        elif rate >= 0.7:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1%}</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def avg_response_time_display(self, obj):
        """Display average response time with formatting"""
        time_ms = obj.average_response_time * 1000
        if time_ms < 1000:
            return f"{time_ms:.0f}ms"
        else:
            return f"{obj.average_response_time:.1f}s"
    avg_response_time_display.short_description = 'Avg Response Time'
    
    def model_stats(self, obj):
        """Display detailed model statistics"""
        if obj.total_requests == 0:
            return "No usage data available"
        
        # Get recent usage (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_usage = OllamaModelUsage.objects.filter(
            model=obj,
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_tokens=Sum('tokens_used'),
            avg_time=Avg('processing_time'),
            total_requests=Count('id')
        )
        
        stats_html = f"""
        <div style="font-family: monospace; font-size: 12px;">
            <strong>All Time:</strong><br>
            • Total Requests: {obj.total_requests:,}<br>
            • Success Rate: {obj.success_rate:.1%}<br>
            • Avg Response: {obj.average_response_time:.2f}s<br><br>
            
            <strong>Last 30 Days:</strong><br>
            • Requests: {recent_usage['total_requests'] or 0:,}<br>
            • Tokens Used: {recent_usage['total_tokens'] or 0:,}<br>
            • Avg Time: {(recent_usage['avg_time'] or 0):.2f}s<br>
        </div>
        """
        
        return mark_safe(stats_html)
    model_stats.short_description = 'Detailed Statistics'
    
    def test_models(self, request, queryset):
        """Test selected models"""
        results = []
        test_prompt = "Hello, this is a test message. Please respond briefly."
        
        for model in queryset:
            try:
                client = OllamaClient(model.configuration.name)
                response = client.generate(
                    model.effective_model_name,
                    test_prompt,
                    temperature=0.1,
                    max_tokens=50
                )
                client.close()
                
                if response.success:
                    results.append(f"{model.name}: Test successful ({response.processing_time:.2f}s)")
                else:
                    results.append(f"{model.name}: Test failed - {response.error}")
            except Exception as e:
                results.append(f"{model.name}: Error - {str(e)}")
        
        self.message_user(request, "\n".join(results))
    test_models.short_description = "Test selected models"
    
    def activate_models(self, request, queryset):
        """Activate selected models"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} models activated.")
    activate_models.short_description = "Activate selected models"
    
    def deactivate_models(self, request, queryset):
        """Deactivate selected models"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} models deactivated.")
    deactivate_models.short_description = "Deactivate selected models"
    
    def reset_metrics(self, request, queryset):
        """Reset performance metrics for selected models"""
        for model in queryset:
            model.reset_metrics()
        self.message_user(request, f"Metrics reset for {queryset.count()} models.")
    reset_metrics.short_description = "Reset performance metrics"


@admin.register(OllamaProcessingJob)
class OllamaProcessingJobAdmin(admin.ModelAdmin):
    list_display = [
        'job_id', 'name', 'model', 'task_type', 'status', 'priority',
        'created_by', 'processing_time_display', 'created_at'
    ]
    list_filter = [
        'status', 'task_type', 'priority', 'created_at',
        'model__name', 'created_by'
    ]
    search_fields = ['job_id', 'name', 'prompt']
    readonly_fields = [
        'job_id', 'created_at', 'updated_at', 'started_at', 'completed_at',
        'processing_time_display', 'job_details'
    ]
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'name', 'status', 'priority', 'created_by')
        }),
        ('Processing Details', {
            'fields': ('model', 'task_type', 'prompt', 'system_prompt')
        }),
        ('Input/Output Data', {
            'fields': ('input_data', 'output_data'),
            'classes': ('collapse',)
        }),
        ('Timing Information', {
            'fields': (
                'created_at', 'started_at', 'completed_at', 'processing_time_display'
            ),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Job Details', {
            'fields': ('job_details',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['retry_failed_jobs', 'cancel_pending_jobs']
    
    def processing_time_display(self, obj):
        """Display processing time with formatting"""
        if obj.processing_time:
            return f"{obj.processing_time:.2f}s"
        return "-"
    processing_time_display.short_description = 'Processing Time'
    
    def job_details(self, obj):
        """Display detailed job information"""
        details_html = f"""
        <div style="font-family: monospace; font-size: 12px;">
            <strong>Job ID:</strong> {obj.job_id}<br>
            <strong>Status:</strong> <span style="color: {'green' if obj.status == 'completed' else 'red' if obj.status == 'failed' else 'orange'}">{obj.get_status_display()}</span><br>
            <strong>Model:</strong> {obj.model.name}<br>
            <strong>Task Type:</strong> {obj.get_task_type_display()}<br>
            <strong>Priority:</strong> {obj.get_priority_display()}<br><br>
            
            <strong>Timing:</strong><br>
            • Created: {obj.created_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
        """
        
        if obj.started_at:
            details_html += f"• Started: {obj.started_at.strftime('%Y-%m-%d %H:%M:%S')}<br>"
        
        if obj.completed_at:
            details_html += f"• Completed: {obj.completed_at.strftime('%Y-%m-%d %H:%M:%S')}<br>"
        
        if obj.processing_time:
            details_html += f"• Duration: {obj.processing_time:.2f}s<br>"
        
        if obj.tokens_used:
            details_html += f"<br><strong>Tokens Used:</strong> {obj.tokens_used:,}<br>"
        
        if obj.error_message:
            details_html += f"<br><strong>Error:</strong><br><span style='color: red;'>{obj.error_message}</span><br>"
        
        details_html += "</div>"
        
        return mark_safe(details_html)
    job_details.short_description = 'Job Details'
    
    def retry_failed_jobs(self, request, queryset):
        """Retry failed jobs"""
        failed_jobs = queryset.filter(status='failed')
        count = 0
        
        for job in failed_jobs:
            job.status = 'pending'
            job.error_message = ""
            job.started_at = None
            job.completed_at = None
            job.save()
            count += 1
        
        self.message_user(request, f"{count} failed jobs reset to pending.")
    retry_failed_jobs.short_description = "Retry failed jobs"
    
    def cancel_pending_jobs(self, request, queryset):
        """Cancel pending jobs"""
        pending_jobs = queryset.filter(status='pending')
        updated = pending_jobs.update(status='cancelled')
        self.message_user(request, f"{updated} pending jobs cancelled.")
    cancel_pending_jobs.short_description = "Cancel pending jobs"


@admin.register(OllamaModelUsage)
class OllamaModelUsageAdmin(admin.ModelAdmin):
    list_display = [
        'model', 'user', 'tokens_used', 'processing_time_display',
        'success', 'created_at'
    ]
    list_filter = [
        'success', 'created_at', 'model__name', 'user'
    ]
    search_fields = ['model__name', 'user__username']
    readonly_fields = ['created_at', 'processing_time_display']
    
    fieldsets = (
        ('Usage Information', {
            'fields': ('model', 'user', 'tokens_used', 'processing_time', 'success')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def processing_time_display(self, obj):
        """Display processing time with formatting"""
        return f"{obj.processing_time:.3f}s"
    processing_time_display.short_description = 'Processing Time'
    
    def has_add_permission(self, request):
        """Disable manual addition of usage records"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of usage records"""
        return False


@admin.register(OllamaPromptTemplate)
class OllamaPromptTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'task_type', 'is_active', 'usage_count',
        'created_by', 'created_at'
    ]
    list_filter = ['task_type', 'is_active', 'created_at', 'created_by']
    search_fields = ['name', 'description', 'template']
    readonly_fields = ['created_at', 'updated_at', 'usage_count']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'task_type', 'is_active')
        }),
        ('Template Content', {
            'fields': ('template', 'system_prompt', 'variables')
        }),
        ('Parameters', {
            'fields': ('default_parameters',),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('usage_count',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['activate_templates', 'deactivate_templates', 'test_templates']
    
    def activate_templates(self, request, queryset):
        """Activate selected templates"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} templates activated.")
    activate_templates.short_description = "Activate selected templates"
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} templates deactivated.")
    deactivate_templates.short_description = "Deactivate selected templates"
    
    def test_templates(self, request, queryset):
        """Test template rendering"""
        results = []
        test_variables = {'text': 'sample text', 'user': 'test user'}
        
        for template in queryset:
            try:
                rendered = template.render(test_variables)
                results.append(f"{template.name}: Template rendered successfully")
            except Exception as e:
                results.append(f"{template.name}: Rendering failed - {str(e)}")
        
        self.message_user(request, "\n".join(results))
    test_templates.short_description = "Test template rendering"
    
    def save_model(self, request, obj, form, change):
        """Set created_by when saving"""
        if not change:  # Only set on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Custom admin site configuration
class OllamaAdminSite(admin.AdminSite):
    site_header = "Ollama AI Integration Administration"
    site_title = "Ollama Admin"
    index_title = "Welcome to Ollama AI Integration Administration"
    
    def index(self, request, extra_context=None):
        """Custom admin index with Ollama statistics"""
        extra_context = extra_context or {}
        
        # Get basic statistics
        stats = {
            'total_models': OllamaModel.objects.count(),
            'active_models': OllamaModel.objects.filter(is_active=True).count(),
            'total_jobs': OllamaProcessingJob.objects.count(),
            'pending_jobs': OllamaProcessingJob.objects.filter(status='pending').count(),
            'total_configurations': OllamaConfiguration.objects.count(),
            'healthy_configurations': OllamaConfiguration.objects.filter(is_healthy=True).count(),
        }
        
        # Get recent usage statistics
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_usage = OllamaModelUsage.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(
            total_requests=Count('id'),
            total_tokens=Sum('tokens_used'),
            avg_processing_time=Avg('processing_time')
        )
        
        stats.update({
            'recent_requests': recent_usage['total_requests'] or 0,
            'recent_tokens': recent_usage['total_tokens'] or 0,
            'avg_processing_time': recent_usage['avg_processing_time'] or 0,
        })
        
        extra_context['ollama_stats'] = stats
        
        return super().index(request, extra_context)


# Register with custom admin site if needed
# ollama_admin_site = OllamaAdminSite(name='ollama_admin')
# ollama_admin_site.register(OllamaConfiguration, OllamaConfigurationAdmin)
# ollama_admin_site.register(OllamaModel, OllamaModelAdmin)
# ollama_admin_site.register(OllamaProcessingJob, OllamaProcessingJobAdmin)
# ollama_admin_site.register(OllamaModelUsage, OllamaModelUsageAdmin)
# ollama_admin_site.register(OllamaPromptTemplate, OllamaPromptTemplateAdmin)