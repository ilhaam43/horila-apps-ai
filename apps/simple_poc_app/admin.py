from django.contrib import admin
from .models import AIModel, PredictionLog, TrainingSession

@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'accuracy', 'is_active', 'created_at')
    list_filter = ('model_type', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'model_type')
        }),
        ('Performance', {
            'fields': ('accuracy', 'file_path')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('model', 'confidence_score', 'processing_time', 'user', 'created_at')
    list_filter = ('model', 'created_at', 'user')
    search_fields = ('model__name',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Prediction Info', {
            'fields': ('model', 'user')
        }),
        ('Data', {
            'fields': ('input_data', 'prediction_result')
        }),
        ('Performance', {
            'fields': ('confidence_score', 'processing_time')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )

@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('model', 'status', 'started_at', 'completed_at')
    list_filter = ('status', 'started_at', 'model')
    search_fields = ('model__name',)
    readonly_fields = ('started_at', 'completed_at')
    
    fieldsets = (
        ('Training Info', {
            'fields': ('model', 'status')
        }),
        ('Configuration', {
            'fields': ('dataset_info', 'training_parameters')
        }),
        ('Results', {
            'fields': ('metrics', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at')
        })
    )