from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    DocumentCategory, DocumentTag, KnowledgeDocument, DocumentVersion,
    DocumentComment, DocumentAccess, AIAssistant, AIProcessingJob,
    KnowledgeBase, SearchQuery
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'color_display', 'is_active', 'document_count', 'created_at']
    list_filter = ['is_active', 'created_at', 'parent']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    prepopulated_fields = {'name': ('name',)}
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'
    
    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Documents'


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color_display', 'document_count', 'created_at']
    search_fields = ['name']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'
    
    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Documents'


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ['created_at', 'created_by']
    fields = ['version_number', 'change_summary', 'created_by', 'created_at']


class DocumentCommentInline(admin.TabularInline):
    model = DocumentComment
    extra = 0
    readonly_fields = ['created_at', 'created_by']
    fields = ['content', 'is_resolved', 'created_by', 'created_at']


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'document_type', 'status', 'visibility',
        'view_count', 'download_count', 'created_by', 'created_at'
    ]
    list_filter = [
        'document_type', 'status', 'visibility', 'category',
        'created_at', 'department', 'language'
    ]
    search_fields = ['title', 'description', 'content']
    list_editable = ['status', 'visibility']
    readonly_fields = [
        'view_count', 'download_count', 'file_size',
        'ai_confidence_score', 'created_at', 'updated_at'
    ]
    filter_horizontal = ['tags', 'allowed_users']
    inlines = [DocumentVersionInline, DocumentCommentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'content', 'document_type')
        }),
        ('Classification', {
            'fields': ('category', 'tags', 'language')
        }),
        ('File Attachment', {
            'fields': ('file', 'file_size'),
            'classes': ('collapse',)
        }),
        ('Access Control', {
            'fields': ('status', 'visibility', 'department', 'allowed_users')
        }),
        ('Versioning', {
            'fields': ('version', 'review_cycle_months', 'next_review_date', 'expires_at')
        }),
        ('AI Analysis', {
            'fields': ('ai_confidence_score', 'ai_suggested_tags', 'ai_extracted_keywords'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'download_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new document
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'created_by', 'created_at']
    list_filter = ['created_at', 'document__category']
    search_fields = ['document__title', 'version_number', 'change_summary']
    readonly_fields = ['created_at']


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    list_display = ['document', 'created_by', 'is_resolved', 'created_at']
    list_filter = ['is_resolved', 'created_at']
    search_fields = ['document__title', 'content', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DocumentAccess)
class DocumentAccessAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'access_type', 'ip_address', 'accessed_at']
    list_filter = ['access_type', 'accessed_at']
    search_fields = ['document__title', 'user__username', 'ip_address']
    readonly_fields = ['accessed_at']
    date_hierarchy = 'accessed_at'


@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'assistant_type', 'model_name', 'is_active',
        'success_rate_display', 'total_predictions', 'created_at'
    ]
    list_filter = ['assistant_type', 'is_active', 'created_at']
    search_fields = ['name', 'model_name', 'description']
    list_editable = ['is_active']
    readonly_fields = [
        'total_predictions', 'successful_predictions',
        'accuracy_score', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'assistant_type', 'description', 'is_active')
        }),
        ('Model Configuration', {
            'fields': ('model_name', 'model_version', 'configuration')
        }),
        ('Performance Metrics', {
            'fields': (
                'accuracy_score', 'total_predictions',
                'successful_predictions'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        color = 'green' if rate >= 80 else 'orange' if rate >= 60 else 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'


@admin.register(AIProcessingJob)
class AIProcessingJobAdmin(admin.ModelAdmin):
    list_display = [
        'job_id', 'job_type', 'document', 'assistant',
        'status', 'created_at', 'completed_at'
    ]
    list_filter = ['job_type', 'status', 'created_at', 'assistant']
    search_fields = ['job_id', 'document__title', 'assistant__name']
    readonly_fields = [
        'job_id', 'started_at', 'completed_at', 'created_at'
    ]
    
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'job_type', 'document', 'assistant', 'status')
        }),
        ('Data', {
            'fields': ('input_data', 'output_data', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_public', 'department', 'document_count', 'created_by', 'created_at']
    list_filter = ['is_public', 'department', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['documents']
    readonly_fields = ['created_at', 'updated_at']
    
    def document_count(self, obj):
        return obj.documents.count()
    document_count.short_description = 'Documents'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = [
        'query_display', 'user', 'results_count',
        'clicked_document', 'created_at'
    ]
    list_filter = ['created_at', 'results_count']
    search_fields = ['query', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def query_display(self, obj):
        return obj.query[:50] + '...' if len(obj.query) > 50 else obj.query
    query_display.short_description = 'Query'
    
    def has_add_permission(self, request):
        return False  # Search queries are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Read-only for analysis


# Custom admin site configuration
admin.site.site_header = 'Knowledge Management System'
admin.site.site_title = 'Knowledge Admin'
admin.site.index_title = 'Knowledge Management Administration'