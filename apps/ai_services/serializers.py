from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    AIModelRegistry,
    AIPrediction,
    AIAnalytics,
    KnowledgeBase,
    DocumentClassification,
    SearchQuery,
    NLPAnalysis,
    WorkflowExecution,
    AIServiceLog
)

class UserSerializer(serializers.ModelSerializer):
    """Serializer untuk User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']

class AIModelRegistrySerializer(serializers.ModelSerializer):
    """Serializer untuk AIModelRegistry."""
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AIModelRegistry
        fields = [
            'id', 'name', 'service_type', 'model_type', 'version',
            'model_path', 'config', 'is_active', 'accuracy_score',
            'training_date', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_accuracy_score(self, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Accuracy score must be between 0.0 and 1.0")
        return value

class AIPredictionSerializer(serializers.ModelSerializer):
    """Serializer untuk AIPrediction."""
    model = AIModelRegistrySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = AIPrediction
        fields = [
            'id', 'model', 'content_type', 'object_id', 'input_data',
            'prediction_result', 'confidence_score', 'processing_time_ms',
            'is_successful', 'error_message', 'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_confidence_score(self, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value

class AIAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer untuk AIAnalytics."""
    
    class Meta:
        model = AIAnalytics
        fields = [
            'id', 'service_type', 'metric_name', 'metric_value',
            'metric_data', 'date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """Serializer untuk KnowledgeBase."""
    created_by = UserSerializer(read_only=True)
    tags_display = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'title', 'content', 'content_type', 'category',
            'tags', 'tags_display', 'metadata', 'is_active',
            'view_count', 'last_accessed', 'created_at', 'updated_at',
            'created_by'
        ]
        read_only_fields = [
            'id', 'view_count', 'last_accessed', 'created_at', 'updated_at'
        ]
    
    def get_tags_display(self, obj):
        """Get tags as comma-separated string."""
        tags = obj.get_tags()
        return ', '.join(tags) if tags else ''
    
    def validate_tags(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list")
        return value

class KnowledgeBaseCreateSerializer(serializers.ModelSerializer):
    """Serializer untuk membuat KnowledgeBase baru."""
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'title', 'content', 'content_type', 'category', 'tags', 'metadata'
        ]
    
    def create(self, validated_data):
        # Set created_by dari request user
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

class DocumentClassificationSerializer(serializers.ModelSerializer):
    """Serializer untuk DocumentClassification."""
    created_by = UserSerializer(read_only=True)
    all_predictions_display = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentClassification
        fields = [
            'id', 'document_name', 'document_path', 'document_hash',
            'predicted_category', 'confidence_score', 'classification_method',
            'all_predictions', 'all_predictions_display', 'file_size',
            'file_type', 'extracted_text_length', 'processing_time_ms',
            'is_successful', 'error_message', 'created_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'document_hash', 'processing_time_ms', 'created_at'
        ]
    
    def get_all_predictions_display(self, obj):
        """Get formatted display of all predictions."""
        predictions = obj.get_all_predictions()
        if not predictions:
            return {}
        
        formatted = {}
        for method, result in predictions.items():
            if isinstance(result, dict) and 'category' in result and 'confidence' in result:
                formatted[method] = f"{result['category']} ({result['confidence']:.2f})"
            else:
                formatted[method] = str(result)
        
        return formatted
    
    def validate_confidence_score(self, value):
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value

class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer untuk SearchQuery."""
    created_by = UserSerializer(read_only=True)
    search_models_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query_text', 'query_type', 'search_models',
            'search_models_display', 'filters', 'limit', 'results_count',
            'results_data', 'processing_time_ms', 'clicked_results',
            'user_satisfaction', 'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'processing_time_ms', 'created_at']
    
    def get_search_models_display(self, obj):
        """Get search models as comma-separated string."""
        models = obj.get_search_models()
        return ', '.join(models) if models else ''
    
    def validate_user_satisfaction(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("User satisfaction must be between 1 and 5")
        return value
    
    def validate_search_models(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Search models must be a list")
        return value

class SearchQueryCreateSerializer(serializers.ModelSerializer):
    """Serializer untuk membuat SearchQuery baru."""
    
    class Meta:
        model = SearchQuery
        fields = [
            'query_text', 'query_type', 'search_models', 'filters', 'limit'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

class NLPAnalysisSerializer(serializers.ModelSerializer):
    """Serializer untuk NLPAnalysis."""
    created_by = UserSerializer(read_only=True)
    entities_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NLPAnalysis
        fields = [
            'id', 'text', 'text_hash', 'sentiment_label', 'sentiment_score',
            'entities', 'entities_display', 'classification_result',
            'text_statistics', 'analysis_type', 'processing_time_ms',
            'model_used', 'created_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'text_hash', 'processing_time_ms', 'created_at'
        ]
    
    def get_entities_display(self, obj):
        """Get entities as formatted string."""
        entities = obj.get_entities()
        if not entities:
            return ''
        
        formatted = []
        for entity in entities:
            if isinstance(entity, dict) and 'text' in entity and 'label' in entity:
                formatted.append(f"{entity['text']} ({entity['label']})")
            else:
                formatted.append(str(entity))
        
        return ', '.join(formatted)
    
    def validate_sentiment_score(self, value):
        if value is not None and (value < -1.0 or value > 1.0):
            raise serializers.ValidationError("Sentiment score must be between -1.0 and 1.0")
        return value
    
    def validate_entities(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Entities must be a list")
        return value

class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer untuk WorkflowExecution."""
    created_by = UserSerializer(read_only=True)
    rag_results_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow_type', 'workflow_name', 'input_data',
            'rag_query', 'rag_results', 'rag_results_count',
            'n8n_workflow_id', 'n8n_execution_id', 'n8n_status',
            'execution_result', 'processing_time_ms', 'is_successful',
            'error_message', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = [
            'id', 'n8n_execution_id', 'processing_time_ms',
            'created_at', 'updated_at'
        ]
    
    def get_rag_results_count(self, obj):
        """Get count of RAG results."""
        results = obj.get_rag_results()
        return len(results) if results else 0
    
    def validate_input_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Input data must be a dictionary")
        return value

class AIServiceLogSerializer(serializers.ModelSerializer):
    """Serializer untuk AIServiceLog."""
    
    class Meta:
        model = AIServiceLog
        fields = [
            'id', 'service_type', 'operation', 'log_level', 'message',
            'extra_data', 'request_id', 'user_id', 'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_extra_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Extra data must be a dictionary")
        return value

# Input/Output Serializers untuk API endpoints

class BudgetPredictionInputSerializer(serializers.Serializer):
    """Input serializer untuk budget prediction."""
    budget_data = serializers.DictField()
    prediction_type = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'yearly'],
        default='monthly'
    )
    include_anomaly_detection = serializers.BooleanField(default=True)
    
    def validate_budget_data(self, value):
        required_fields = ['amount', 'category', 'department']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        return value

class KnowledgeQueryInputSerializer(serializers.Serializer):
    """Input serializer untuk knowledge query."""
    query = serializers.CharField(max_length=1000)
    max_results = serializers.IntegerField(default=5, min_value=1, max_value=20)
    include_metadata = serializers.BooleanField(default=True)
    confidence_threshold = serializers.FloatField(
        default=0.5, 
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

class IndonesianNLPInputSerializer(serializers.Serializer):
    """Input serializer untuk Indonesian NLP analysis."""
    text = serializers.CharField(max_length=10000)
    analysis_types = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['sentiment', 'ner', 'classification', 'statistics']
        ),
        default=['sentiment']
    )
    include_confidence = serializers.BooleanField(default=True)

class DocumentClassificationInputSerializer(serializers.Serializer):
    """Input serializer untuk document classification."""
    document = serializers.DictField()
    methods = serializers.ListField(
        child=serializers.ChoiceField(
            choices=['transformer', 'embedding', 'ml_traditional', 'rule_based', 'all']
        ),
        default=['all']
    )
    confidence_threshold = serializers.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    def validate_document(self, value):
        if 'content' not in value and 'file_path' not in value:
            raise serializers.ValidationError(
                "Document must contain either 'content' or 'file_path'"
            )
        return value

class IntelligentSearchInputSerializer(serializers.Serializer):
    """Input serializer untuk intelligent search."""
    query = serializers.CharField(max_length=1000)
    search_type = serializers.ChoiceField(
        choices=['semantic', 'keyword', 'hybrid'],
        default='hybrid'
    )
    models = serializers.ListField(
        child=serializers.CharField(),
        default=[]
    )
    filters = serializers.DictField(default=dict)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)
    include_scores = serializers.BooleanField(default=True)

class RAGN8NInputSerializer(serializers.Serializer):
    """Input serializer untuk RAG + N8N integration."""
    workflow_type = serializers.ChoiceField(
        choices=['candidate_screening', 'interview_scheduling', 'onboarding', 'performance_review']
    )
    query = serializers.CharField(max_length=1000)
    context_data = serializers.DictField(default=dict)
    n8n_params = serializers.DictField(default=dict)
    max_rag_results = serializers.IntegerField(default=5, min_value=1, max_value=10)

# Response Serializers

class AIResponseSerializer(serializers.Serializer):
    """Generic AI response serializer."""
    success = serializers.BooleanField()
    service = serializers.CharField()
    result = serializers.DictField()
    timestamp = serializers.DateTimeField()
    error = serializers.CharField(required=False)
    error_type = serializers.CharField(required=False)

class BatchAIRequestSerializer(serializers.Serializer):
    """Serializer untuk batch AI requests."""
    requests = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate_requests(self, value):
        if not value:
            raise serializers.ValidationError("At least one request is required")
        
        for i, request in enumerate(value):
            if 'service_type' not in request:
                raise serializers.ValidationError(
                    f"Request {i}: 'service_type' is required"
                )
            if 'input_data' not in request:
                raise serializers.ValidationError(
                    f"Request {i}: 'input_data' is required"
                )
        
        return value

class BatchAIResponseSerializer(serializers.Serializer):
    """Serializer untuk batch AI response."""
    success = serializers.BooleanField()
    results = serializers.ListField(
        child=serializers.DictField()
    )
    total_processed = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    error = serializers.CharField(required=False)

class AIServiceStatusSerializer(serializers.Serializer):
    """Serializer untuk AI service status."""
    success = serializers.BooleanField()
    services = serializers.DictField()
    timestamp = serializers.DateTimeField()
    error = serializers.CharField(required=False)

class HealthCheckSerializer(serializers.Serializer):
    """Serializer untuk health check response."""
    status = serializers.ChoiceField(choices=['healthy', 'degraded', 'unhealthy'])
    timestamp = serializers.DateTimeField()
    services = serializers.DictField()
    error = serializers.CharField(required=False)