from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from typing import List, Dict
import json

from .models import (
    NLPModel, TextAnalysisJob, SentimentAnalysisResult,
    NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics, NLPConfiguration
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class NLPConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for NLP Configuration"""
    
    class Meta:
        model = NLPConfiguration
        fields = [
            'id', 'name', 'description', 'max_concurrent_jobs', 'job_timeout',
            'max_text_length', 'auto_load_models', 'model_cache_size',
            'model_unload_timeout', 'max_memory_usage', 'cpu_limit',
            'enable_detailed_logging', 'log_level', 'api_rate_limit',
            'enable_api_key_auth', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_max_concurrent_jobs(self, value):
        if value < 1 or value > 50:
            raise serializers.ValidationError("Max concurrent jobs must be between 1 and 50")
        return value
    
    def validate_job_timeout(self, value):
        if value < 30 or value > 3600:
            raise serializers.ValidationError("Job timeout must be between 30 and 3600 seconds")
        return value
    
    def validate_cpu_limit(self, value):
        if value < 0.1 or value > 1.0:
            raise serializers.ValidationError("CPU limit must be between 0.1 and 1.0")
        return value


class NLPModelSerializer(serializers.ModelSerializer):
    """Serializer for NLP Model"""
    
    created_by = UserSerializer(read_only=True)
    usage_count = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    avg_processing_time = serializers.SerializerMethodField()
    
    class Meta:
        model = NLPModel
        fields = [
            'id', 'name', 'description', 'model_type', 'framework',
            'model_path', 'tokenizer_path', 'config', 'preprocessing_config',
            'postprocessing_config', 'accuracy', 'precision', 'recall', 'f1_score',
            'is_active', 'is_loaded', 'load_time', 'memory_usage', 'last_used',
            'created_at', 'updated_at', 'created_by', 'usage_count',
            'success_rate', 'avg_processing_time'
        ]
        read_only_fields = [
            'id', 'is_loaded', 'load_time', 'memory_usage', 'last_used',
            'created_at', 'updated_at', 'usage_count', 'success_rate',
            'avg_processing_time'
        ]
    
    def get_usage_count(self, obj):
        """Get total usage count for the model"""
        return obj.usage_stats.aggregate(
            total=models.Sum('total_requests')
        )['total'] or 0
    
    def get_success_rate(self, obj):
        """Get success rate for the model"""
        stats = obj.usage_stats.aggregate(
            total=models.Sum('total_requests'),
            successful=models.Sum('successful_requests')
        )
        if stats['total'] and stats['total'] > 0:
            return stats['successful'] / stats['total']
        return 0.0
    
    def get_avg_processing_time(self, obj):
        """Get average processing time for the model"""
        return obj.usage_stats.aggregate(
            avg_time=models.Avg('avg_processing_time')
        )['avg_time'] or 0.0
    
    def validate_name(self, value):
        """Validate model name uniqueness"""
        if self.instance:
            # Update case - exclude current instance
            if NLPModel.objects.exclude(pk=self.instance.pk).filter(name=value).exists():
                raise serializers.ValidationError("Model with this name already exists")
        else:
            # Create case
            if NLPModel.objects.filter(name=value).exists():
                raise serializers.ValidationError("Model with this name already exists")
        return value
    
    def validate_config(self, value):
        """Validate config is valid JSON"""
        if isinstance(value, str):
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Config must be valid JSON")
        return value


class SentimentAnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for Sentiment Analysis Result"""
    
    class Meta:
        model = SentimentAnalysisResult
        fields = [
            'id', 'sentiment', 'confidence', 'positive_score',
            'negative_score', 'neutral_score', 'subjectivity',
            'emotion_scores', 'keywords', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NamedEntityResultSerializer(serializers.ModelSerializer):
    """Serializer for Named Entity Result"""
    
    class Meta:
        model = NamedEntityResult
        fields = [
            'id', 'text', 'label', 'start_pos', 'end_pos',
            'confidence', 'normalized_text', 'context', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TextClassificationResultSerializer(serializers.ModelSerializer):
    """Serializer for Text Classification Result"""
    
    class Meta:
        model = TextClassificationResult
        fields = [
            'id', 'predicted_class', 'confidence', 'class_probabilities',
            'top_features', 'feature_weights', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TextAnalysisJobSerializer(serializers.ModelSerializer):
    """Serializer for Text Analysis Job"""
    
    model = NLPModelSerializer(read_only=True)
    model_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    
    # Related results
    sentiment_result = SentimentAnalysisResultSerializer(read_only=True)
    ner_results = NamedEntityResultSerializer(many=True, read_only=True)
    classification_result = TextClassificationResultSerializer(read_only=True)
    
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = TextAnalysisJob
        fields = [
            'id', 'job_id', 'name', 'description', 'input_text', 'input_language',
            'model', 'model_id', 'parameters', 'status', 'priority', 'progress',
            'result', 'confidence_score', 'processing_time', 'error_message',
            'retry_count', 'max_retries', 'created_at', 'started_at',
            'completed_at', 'created_by', 'sentiment_result', 'ner_results',
            'classification_result', 'duration'
        ]
        read_only_fields = [
            'id', 'job_id', 'result', 'confidence_score', 'processing_time',
            'error_message', 'retry_count', 'created_at', 'started_at',
            'completed_at', 'duration'
        ]
    
    def get_duration(self, obj):
        """Get job duration in seconds"""
        return obj.duration
    
    def validate_model_id(self, value):
        """Validate model exists and is active"""
        try:
            model = NLPModel.objects.get(id=value)
            if not model.is_active:
                raise serializers.ValidationError("Selected model is not active")
            return value
        except NLPModel.DoesNotExist:
            raise serializers.ValidationError("Model does not exist")
    
    def validate_input_text(self, value):
        """Validate input text length"""
        config = NLPConfiguration.get_active_config()
        max_length = config.max_text_length if config else 10000
        
        if len(value) > max_length:
            raise serializers.ValidationError(
                f"Input text exceeds maximum length of {max_length} characters"
            )
        return value
    
    def create(self, validated_data):
        """Create job with auto-generated job_id"""
        import uuid
        validated_data['job_id'] = str(uuid.uuid4())
        return super().create(validated_data)


class ModelUsageStatisticsSerializer(serializers.ModelSerializer):
    """Serializer for Model Usage Statistics"""
    
    model = NLPModelSerializer(read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ModelUsageStatistics
        fields = [
            'id', 'model', 'total_requests', 'successful_requests',
            'failed_requests', 'avg_processing_time', 'min_processing_time',
            'max_processing_time', 'total_cpu_time', 'peak_memory_usage',
            'date', 'hour', 'success_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'success_rate', 'created_at', 'updated_at']
    
    def get_success_rate(self, obj):
        """Get success rate"""
        return obj.success_rate


# Specialized serializers for API endpoints
class QuickAnalysisSerializer(serializers.Serializer):
    """Serializer for quick analysis requests"""
    
    text = serializers.CharField(max_length=10000)
    model_name = serializers.CharField(max_length=200, required=False)
    
    def validate_text(self, value):
        """Validate text is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Text cannot be empty")
        return value.strip()
    
    def validate_model_name(self, value):
        """Validate model exists and is active"""
        if value:
            try:
                model = NLPModel.objects.get(name=value, is_active=True)
                return value
            except NLPModel.DoesNotExist:
                raise serializers.ValidationError("Model does not exist or is not active")
        return value


class BatchAnalysisSerializer(serializers.Serializer):
    """Serializer for batch analysis requests"""
    
    texts = serializers.ListField(
        child=serializers.CharField(max_length=10000),
        min_length=1,
        max_length=100
    )
    analysis_type = serializers.ChoiceField(
        choices=['sentiment', 'ner', 'classification']
    )
    model_name = serializers.CharField(max_length=200, required=False)
    
    def validate_texts(self, value):
        """Validate all texts are not empty"""
        cleaned_texts = []
        for text in value:
            if not text.strip():
                raise serializers.ValidationError("All texts must be non-empty")
            cleaned_texts.append(text.strip())
        return cleaned_texts
    
    def validate_model_name(self, value):
        """Validate model exists and is active"""
        if value:
            try:
                model = NLPModel.objects.get(name=value, is_active=True)
                return value
            except NLPModel.DoesNotExist:
                raise serializers.ValidationError("Model does not exist or is not active")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        analysis_type = data.get('analysis_type')
        model_name = data.get('model_name')
        
        if model_name:
            # Validate model type matches analysis type
            try:
                model = NLPModel.objects.get(name=model_name, is_active=True)
                if model.model_type != analysis_type:
                    raise serializers.ValidationError(
                        f"Model {model_name} is of type {model.model_type}, "
                        f"but analysis type {analysis_type} was requested"
                    )
            except NLPModel.DoesNotExist:
                pass  # Already validated in validate_model_name
        
        return data


class ModelTestSerializer(serializers.Serializer):
    """Serializer for model testing requests"""
    
    text = serializers.CharField(
        max_length=1000,
        required=False,
        default="Saya sangat senang dengan layanan ini."
    )
    
    def validate_text(self, value):
        """Validate text is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Test text cannot be empty")
        return value.strip()


class JobCreateSerializer(serializers.Serializer):
    """Serializer for creating analysis jobs"""
    
    input_text = serializers.CharField(max_length=10000)
    model_name = serializers.CharField(max_length=200)
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False)
    priority = serializers.ChoiceField(
        choices=TextAnalysisJob.PRIORITY_CHOICES,
        default='medium'
    )
    parameters = serializers.JSONField(required=False, default=dict)
    
    def validate_input_text(self, value):
        """Validate input text"""
        if not value.strip():
            raise serializers.ValidationError("Input text cannot be empty")
        return value.strip()
    
    def validate_model_name(self, value):
        """Validate model exists and is active"""
        try:
            model = NLPModel.objects.get(name=value, is_active=True)
            return value
        except NLPModel.DoesNotExist:
            raise serializers.ValidationError("Model does not exist or is not active")


class ModelSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for model summaries"""
    
    usage_count = serializers.SerializerMethodField()
    
    class Meta:
        model = NLPModel
        fields = [
            'id', 'name', 'model_type', 'framework', 'is_active',
            'is_loaded', 'accuracy', 'last_used', 'usage_count'
        ]
    
    def get_usage_count(self, obj):
        """Get total usage count"""
        return getattr(obj, '_usage_count', 0)


class JobSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for job summaries"""
    
    model_name = serializers.CharField(source='model.name', read_only=True)
    model_type = serializers.CharField(source='model.model_type', read_only=True)
    
    class Meta:
        model = TextAnalysisJob
        fields = [
            'id', 'job_id', 'name', 'status', 'priority', 'progress',
            'confidence_score', 'processing_time', 'created_at',
            'model_name', 'model_type'
        ]


class SystemStatusSerializer(serializers.Serializer):
    """Serializer for system status information"""
    
    timestamp = serializers.DateTimeField()
    models = serializers.DictField()
    jobs = serializers.DictField()
    today_usage = serializers.DictField()
    configuration = serializers.DictField()


class AnalysisResultSerializer(serializers.Serializer):
    """Generic serializer for analysis results"""
    
    text = serializers.CharField()
    analysis_type = serializers.CharField()
    result = serializers.JSONField()
    processing_time = serializers.FloatField(required=False)
    model_name = serializers.CharField(required=False)


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses"""
    
    error = serializers.CharField()
    details = serializers.JSONField(required=False)
    timestamp = serializers.DateTimeField(default=timezone.now)


class PaginatedResponseSerializer(serializers.Serializer):
    """Serializer for paginated responses"""
    
    count = serializers.IntegerField()
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = serializers.ListField()


class ModelPerformanceSerializer(serializers.Serializer):
    """Serializer for model performance metrics"""
    
    model_name = serializers.CharField()
    model_type = serializers.CharField()
    total_jobs = serializers.IntegerField()
    successful_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_confidence = serializers.FloatField()
    avg_processing_time = serializers.FloatField()
    last_used = serializers.DateTimeField()


class UsageStatsSummarySerializer(serializers.Serializer):
    """Serializer for usage statistics summary"""
    
    date = serializers.DateField()
    total_requests = serializers.IntegerField()
    successful_requests = serializers.IntegerField()
    failed_requests = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_processing_time = serializers.FloatField()
    unique_models_used = serializers.IntegerField()