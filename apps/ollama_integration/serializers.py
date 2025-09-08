from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    OllamaModel,
    OllamaProcessingJob,
    OllamaConfiguration,
    OllamaModelUsage,
    OllamaPromptTemplate
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class OllamaConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for OllamaConfiguration model"""
    effective_base_url = serializers.ReadOnlyField()
    health_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OllamaConfiguration
        fields = [
            'id', 'name', 'description', 'host', 'port', 'use_ssl',
            'api_key', 'username', 'password', 'timeout', 'max_retries',
            'retry_delay', 'max_concurrent_requests', 'request_queue_size',
            'is_active', 'is_healthy', 'last_health_check',
            'effective_base_url', 'health_status_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_healthy', 'last_health_check', 'effective_base_url',
            'health_status_display', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'api_key': {'write_only': True}
        }
    
    def get_health_status_display(self, obj):
        """Get human-readable health status"""
        if obj.is_healthy:
            return "Healthy"
        elif obj.last_health_check:
            return f"Unhealthy (last checked: {obj.last_health_check.strftime('%Y-%m-%d %H:%M:%S')})"
        else:
            return "Unknown"


class OllamaModelSerializer(serializers.ModelSerializer):
    """Serializer for OllamaModel model"""
    configuration = OllamaConfigurationSerializer(read_only=True)
    configuration_id = serializers.IntegerField(write_only=True)
    effective_model_name = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    performance_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = OllamaModel
        fields = [
            'id', 'name', 'model_name', 'description', 'task_type',
            'task_type_display', 'configuration', 'configuration_id',
            'is_active', 'priority', 'priority_display', 'temperature',
            'max_tokens', 'top_p', 'top_k', 'system_prompt',
            'custom_parameters', 'total_requests', 'successful_requests',
            'failed_requests', 'average_response_time', 'success_rate',
            'effective_model_name', 'performance_metrics',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_requests', 'successful_requests', 'failed_requests',
            'average_response_time', 'success_rate', 'effective_model_name',
            'performance_metrics', 'created_at', 'updated_at'
        ]
    
    def get_performance_metrics(self, obj):
        """Get performance metrics summary"""
        return {
            'total_requests': obj.total_requests,
            'success_rate': obj.success_rate,
            'average_response_time': obj.average_response_time,
            'requests_last_24h': obj.get_requests_last_24h(),
            'avg_tokens_per_request': obj.get_avg_tokens_per_request()
        }
    
    def validate_configuration_id(self, value):
        """Validate configuration exists and is active"""
        try:
            config = OllamaConfiguration.objects.get(id=value)
            if not config.is_active:
                raise serializers.ValidationError("Configuration is not active")
            return value
        except OllamaConfiguration.DoesNotExist:
            raise serializers.ValidationError("Configuration does not exist")
    
    def validate_temperature(self, value):
        """Validate temperature is in valid range"""
        if not 0.0 <= value <= 2.0:
            raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value
    
    def validate_top_p(self, value):
        """Validate top_p is in valid range"""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("top_p must be between 0.0 and 1.0")
        return value
    
    def validate_top_k(self, value):
        """Validate top_k is positive"""
        if value <= 0:
            raise serializers.ValidationError("top_k must be positive")
        return value


class OllamaProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for OllamaProcessingJob model"""
    model = OllamaModelSerializer(read_only=True)
    model_id = serializers.IntegerField(write_only=True)
    created_by = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    processing_time = serializers.ReadOnlyField()
    job_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = OllamaProcessingJob
        fields = [
            'id', 'job_id', 'name', 'model', 'model_id', 'task_type',
            'task_type_display', 'status', 'status_display', 'priority',
            'priority_display', 'prompt', 'system_prompt', 'input_data',
            'output_data', 'tokens_used', 'processing_time', 'error_message',
            'created_by', 'created_at', 'updated_at', 'started_at',
            'completed_at', 'job_summary'
        ]
        read_only_fields = [
            'id', 'job_id', 'status', 'output_data', 'tokens_used',
            'processing_time', 'error_message', 'created_by', 'created_at',
            'updated_at', 'started_at', 'completed_at', 'job_summary'
        ]
    
    def get_job_summary(self, obj):
        """Get job summary information"""
        summary = {
            'job_id': obj.job_id,
            'status': obj.status,
            'created_at': obj.created_at,
            'duration': None,
            'success': obj.status == 'completed'
        }
        
        if obj.processing_time:
            summary['duration'] = f"{obj.processing_time:.2f}s"
        
        if obj.tokens_used:
            summary['tokens_used'] = obj.tokens_used
        
        if obj.error_message:
            summary['error'] = obj.error_message[:100] + "..." if len(obj.error_message) > 100 else obj.error_message
        
        return summary
    
    def validate_model_id(self, value):
        """Validate model exists and is active"""
        try:
            model = OllamaModel.objects.get(id=value)
            if not model.is_active:
                raise serializers.ValidationError("Model is not active")
            return value
        except OllamaModel.DoesNotExist:
            raise serializers.ValidationError("Model does not exist")
    
    def validate_prompt(self, value):
        """Validate prompt is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty")
        return value
    
    def create(self, validated_data):
        """Create job with auto-generated job_id"""
        import time
        user = self.context['request'].user
        validated_data['job_id'] = f"ollama_{int(time.time())}_{user.id}"
        return super().create(validated_data)


class OllamaModelUsageSerializer(serializers.ModelSerializer):
    """Serializer for OllamaModelUsage model"""
    model = OllamaModelSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    processing_time_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OllamaModelUsage
        fields = [
            'id', 'model', 'user', 'tokens_used', 'processing_time',
            'processing_time_display', 'success', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_processing_time_display(self, obj):
        """Get formatted processing time"""
        if obj.processing_time < 1:
            return f"{obj.processing_time * 1000:.0f}ms"
        else:
            return f"{obj.processing_time:.2f}s"


class OllamaPromptTemplateSerializer(serializers.ModelSerializer):
    """Serializer for OllamaPromptTemplate model"""
    created_by = UserSerializer(read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    template_preview = serializers.SerializerMethodField()
    variable_list = serializers.SerializerMethodField()
    
    class Meta:
        model = OllamaPromptTemplate
        fields = [
            'id', 'name', 'description', 'task_type', 'task_type_display',
            'template', 'system_prompt', 'variables', 'default_parameters',
            'is_active', 'usage_count', 'created_by', 'created_at',
            'updated_at', 'template_preview', 'variable_list'
        ]
        read_only_fields = [
            'id', 'usage_count', 'created_by', 'created_at', 'updated_at',
            'template_preview', 'variable_list'
        ]
    
    def get_template_preview(self, obj):
        """Get template preview with sample variables"""
        try:
            sample_vars = {}
            for var in obj.variables:
                sample_vars[var] = f"[{var.upper()}]"
            return obj.render(sample_vars)[:200] + "..." if len(obj.template) > 200 else obj.render(sample_vars)
        except Exception:
            return obj.template[:200] + "..." if len(obj.template) > 200 else obj.template
    
    def get_variable_list(self, obj):
        """Get list of variables with descriptions"""
        return [{
            'name': var,
            'required': True,
            'description': f"Variable: {var}"
        } for var in obj.variables]
    
    def validate_template(self, value):
        """Validate template syntax"""
        try:
            from string import Template
            Template(value)
            return value
        except Exception as e:
            raise serializers.ValidationError(f"Invalid template syntax: {str(e)}")
    
    def validate_variables(self, value):
        """Validate variables list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Variables must be a list")
        
        for var in value:
            if not isinstance(var, str) or not var.isidentifier():
                raise serializers.ValidationError(f"Invalid variable name: {var}")
        
        return value


# Specialized serializers for specific use cases
class OllamaModelSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for model summaries"""
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    
    class Meta:
        model = OllamaModel
        fields = [
            'id', 'name', 'model_name', 'task_type', 'task_type_display',
            'is_active', 'success_rate', 'average_response_time'
        ]


class ProcessingJobCreateSerializer(serializers.Serializer):
    """Serializer for creating processing jobs via API"""
    task_type = serializers.ChoiceField(choices=OllamaProcessingJob.TASK_TYPE_CHOICES)
    prompt = serializers.CharField(max_length=10000)
    name = serializers.CharField(max_length=200, required=False)
    system_prompt = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=OllamaProcessingJob.PRIORITY_CHOICES,
        default='normal'
    )
    input_data = serializers.JSONField(required=False, default=dict)
    
    def validate_prompt(self, value):
        """Validate prompt is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty")
        return value


class TextGenerationSerializer(serializers.Serializer):
    """Serializer for text generation API"""
    prompt = serializers.CharField(max_length=10000)
    task_type = serializers.ChoiceField(choices=OllamaModel.TASK_TYPE_CHOICES)
    system_prompt = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    temperature = serializers.FloatField(min_value=0.0, max_value=2.0, default=0.7)
    max_tokens = serializers.IntegerField(min_value=1, max_value=8192, default=2048)
    top_p = serializers.FloatField(min_value=0.0, max_value=1.0, default=0.9)
    top_k = serializers.IntegerField(min_value=1, default=40)
    stream = serializers.BooleanField(default=False)
    
    def validate_prompt(self, value):
        """Validate prompt is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty")
        return value


class ChatCompletionSerializer(serializers.Serializer):
    """Serializer for chat completion API"""
    messages = serializers.ListField(
        child=serializers.DictField(),
        min_length=1
    )
    task_type = serializers.ChoiceField(choices=OllamaModel.TASK_TYPE_CHOICES)
    temperature = serializers.FloatField(min_value=0.0, max_value=2.0, default=0.7)
    max_tokens = serializers.IntegerField(min_value=1, max_value=8192, default=2048)
    stream = serializers.BooleanField(default=False)
    
    def validate_messages(self, value):
        """Validate messages format"""
        for i, message in enumerate(value):
            if not isinstance(message, dict):
                raise serializers.ValidationError(f"Message {i} must be a dictionary")
            
            if 'role' not in message or 'content' not in message:
                raise serializers.ValidationError(f"Message {i} must have 'role' and 'content' fields")
            
            if message['role'] not in ['system', 'user', 'assistant']:
                raise serializers.ValidationError(f"Message {i} has invalid role: {message['role']}")
            
            if not message['content'].strip():
                raise serializers.ValidationError(f"Message {i} content cannot be empty")
        
        return value


class EmbeddingGenerationSerializer(serializers.Serializer):
    """Serializer for embedding generation API"""
    text = serializers.CharField(max_length=10000)
    
    def validate_text(self, value):
        """Validate text is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Text cannot be empty")
        return value


class ModelTestSerializer(serializers.Serializer):
    """Serializer for model testing"""
    prompt = serializers.CharField(
        max_length=1000,
        default="Hello, this is a test message. Please respond briefly."
    )
    
    def validate_prompt(self, value):
        """Validate prompt is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Prompt cannot be empty")
        return value


class TemplateRenderSerializer(serializers.Serializer):
    """Serializer for template rendering"""
    variables = serializers.DictField(
        child=serializers.CharField(max_length=1000),
        required=False,
        default=dict
    )
    
    def validate_variables(self, value):
        """Validate variables are strings"""
        for key, val in value.items():
            if not isinstance(key, str) or not isinstance(val, str):
                raise serializers.ValidationError("All variables must be strings")
        return value


# Statistics and Analytics Serializers
class ModelUsageStatsSerializer(serializers.Serializer):
    """Serializer for model usage statistics"""
    model_id = serializers.IntegerField()
    model_name = serializers.CharField()
    total_requests = serializers.IntegerField()
    successful_requests = serializers.IntegerField()
    failed_requests = serializers.IntegerField()
    success_rate = serializers.FloatField()
    total_tokens = serializers.IntegerField()
    average_processing_time = serializers.FloatField()
    last_used = serializers.DateTimeField()


class SystemHealthSerializer(serializers.Serializer):
    """Serializer for system health status"""
    healthy = serializers.BooleanField()
    configurations = serializers.ListField(
        child=serializers.DictField()
    )
    timestamp = serializers.DateTimeField()
    total_models = serializers.IntegerField(required=False)
    active_models = serializers.IntegerField(required=False)
    pending_jobs = serializers.IntegerField(required=False)