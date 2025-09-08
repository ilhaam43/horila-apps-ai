from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json
import uuid

class AIModelRegistry(models.Model):
    """
    Registry untuk semua AI models yang digunakan dalam sistem.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    service_type = models.CharField(max_length=50, choices=[
        ('budget_ai', 'Budget AI'),
        ('knowledge_ai', 'Knowledge AI'),
        ('indonesian_nlp', 'Indonesian NLP'),
        ('rag_n8n', 'RAG + N8N Integration'),
        ('document_classifier', 'Document Classifier'),
        ('intelligent_search', 'Intelligent Search'),
    ])
    model_type = models.CharField(max_length=50, choices=[
        ('regression', 'Regression'),
        ('classification', 'Classification'),
        ('clustering', 'Clustering'),
        ('nlp', 'Natural Language Processing'),
        ('embedding', 'Embedding'),
        ('anomaly_detection', 'Anomaly Detection'),
    ])
    version = models.CharField(max_length=20, default='1.0.0')
    model_path = models.CharField(max_length=500)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    accuracy_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    training_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_model_registry_set')
    
    class Meta:
        db_table = 'ai_model_registry'
        ordering = ['-created_at']
        unique_together = ['name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.service_type})"
    
    def get_config(self):
        """Get model configuration as dict."""
        return self.config if isinstance(self.config, dict) else {}
    
    def set_config(self, config_dict):
        """Set model configuration from dict."""
        self.config = config_dict
        self.save(update_fields=['config', 'updated_at'])

class ModelTrainingSession(models.Model):
    """
    Model untuk tracking training session dari AI models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(AIModelRegistry, on_delete=models.CASCADE, related_name='training_sessions')
    
    # Training configuration
    training_data_path = models.CharField(max_length=500, blank=True)
    training_data_size = models.IntegerField(null=True, blank=True)
    validation_data_size = models.IntegerField(null=True, blank=True)
    test_data_size = models.IntegerField(null=True, blank=True)
    
    # Training parameters
    hyperparameters = models.JSONField(default=dict, blank=True)
    training_config = models.JSONField(default=dict, blank=True)
    
    # Training status and results
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('training', 'Training'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    precision = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    recall = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    f1_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    loss = models.FloatField(null=True, blank=True)
    validation_loss = models.FloatField(null=True, blank=True)
    
    # Training time and resources
    training_time_minutes = models.FloatField(null=True, blank=True)
    epochs_completed = models.IntegerField(null=True, blank=True)
    total_epochs = models.IntegerField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Artifacts and outputs
    model_artifacts_path = models.CharField(max_length=500, blank=True)
    logs_path = models.CharField(max_length=500, blank=True)
    
    # Metadata
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='training_sessions')
    
    class Meta:
        db_table = 'model_training_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"Training Session {self.id} - {self.model.name} ({self.status})"
    
    def get_config(self):
        """Get training configuration as dict."""
        return self.training_config if isinstance(self.training_config, dict) else {}
    
    def set_config(self, config_dict):
        """Set training configuration from dict."""
        self.training_config = config_dict
        self.save(update_fields=['training_config', 'updated_at'])
    
    def get_hyperparameters(self):
        """Get hyperparameters as dict."""
        return self.hyperparameters if isinstance(self.hyperparameters, dict) else {}
    
    def set_hyperparameters(self, params_dict):
        """Set hyperparameters from dict."""
        self.hyperparameters = params_dict
        self.save(update_fields=['hyperparameters', 'updated_at'])
    
    def start_training(self):
        """Mark training as started."""
        self.status = 'training'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])
    
    def complete_training(self, accuracy=None, precision=None, recall=None, f1_score=None, loss=None):
        """Mark training as completed with metrics."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if accuracy is not None:
            self.accuracy = accuracy
        if precision is not None:
            self.precision = precision
        if recall is not None:
            self.recall = recall
        if f1_score is not None:
            self.f1_score = f1_score
        if loss is not None:
            self.loss = loss
        self.save()
    
    def fail_training(self, error_message, error_traceback=None):
        """Mark training as failed with error details."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        if error_traceback:
            self.error_traceback = error_traceback
        self.save()
    
    @property
    def duration_minutes(self):
        """Calculate training duration in minutes."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 60
        return None
    
    @property
    def is_completed(self):
        """Check if training is completed successfully."""
        return self.status == 'completed'
    
    @property
    def is_failed(self):
        """Check if training failed."""
        return self.status == 'failed'

class AIPrediction(models.Model):
    """
    Menyimpan hasil prediksi dari semua AI services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(AIModelRegistry, on_delete=models.CASCADE, related_name='predictions')
    
    # Generic relation untuk link ke object apapun
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    input_data = models.JSONField()
    prediction_result = models.JSONField()
    confidence_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    processing_time_ms = models.IntegerField(null=True, blank=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ai_prediction_set')
    
    class Meta:
        db_table = 'ai_predictions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_successful', 'created_at']),
        ]
    
    def __str__(self):
        return f"Prediction {self.id} - {self.model.name}"
    
    def get_input_data(self):
        """Get input data as dict."""
        return self.input_data if isinstance(self.input_data, dict) else {}
    
    def get_prediction_result(self):
        """Get prediction result as dict."""
        return self.prediction_result if isinstance(self.prediction_result, dict) else {}

class AIAnalytics(models.Model):
    """
    Menyimpan analytics dan metrics untuk AI services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=50, choices=[
        ('budget_ai', 'Budget AI'),
        ('knowledge_ai', 'Knowledge AI'),
        ('indonesian_nlp', 'Indonesian NLP'),
        ('rag_n8n', 'RAG + N8N Integration'),
        ('document_classifier', 'Document Classifier'),
        ('intelligent_search', 'Intelligent Search'),
    ])
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    metric_data = models.JSONField(default=dict, blank=True)
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_analytics'
        ordering = ['-date', '-created_at']
        unique_together = ['service_type', 'metric_name', 'date']
        indexes = [
            models.Index(fields=['service_type', 'date']),
            models.Index(fields=['metric_name', 'date']),
        ]
    
    def __str__(self):
        return f"{self.service_type} - {self.metric_name}: {self.metric_value}"

class KnowledgeBase(models.Model):
    """
    Knowledge base untuk Knowledge AI service.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField()
    content_type = models.CharField(max_length=50, choices=[
        ('policy', 'Policy'),
        ('procedure', 'Procedure'),
        ('faq', 'FAQ'),
        ('guide', 'Guide'),
        ('manual', 'Manual'),
        ('other', 'Other'),
    ], default='other')
    category = models.CharField(max_length=100, blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Embedding data
    embedding_vector = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_knowledgebase_created')
    
    class Meta:
        db_table = 'knowledge_base'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['content_type', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_tags(self):
        """Get tags as list."""
        return self.tags if isinstance(self.tags, list) else []
    
    def add_tag(self, tag):
        """Add a tag to the knowledge base entry."""
        tags = self.get_tags()
        if tag not in tags:
            tags.append(tag)
            self.tags = tags
            self.save(update_fields=['tags', 'updated_at'])
    
    def increment_view_count(self):
        """Increment view count and update last accessed time."""
        self.view_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['view_count', 'last_accessed'])

class DocumentClassification(models.Model):
    """
    Menyimpan hasil klasifikasi dokumen.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_name = models.CharField(max_length=255)
    document_path = models.CharField(max_length=500, blank=True)
    document_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hash
    
    # Classification results
    predicted_category = models.CharField(max_length=100)
    confidence_score = models.FloatField(validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    classification_method = models.CharField(max_length=50, choices=[
        ('transformer', 'Transformer'),
        ('embedding', 'Embedding'),
        ('ml_traditional', 'Traditional ML'),
        ('rule_based', 'Rule Based'),
        ('ensemble', 'Ensemble'),
    ])
    all_predictions = models.JSONField(default=dict, blank=True)  # All method results
    
    # Document metadata
    file_size = models.IntegerField(null=True, blank=True)
    file_type = models.CharField(max_length=20, blank=True)
    extracted_text_length = models.IntegerField(null=True, blank=True)
    
    # Processing info
    processing_time_ms = models.IntegerField(null=True, blank=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_document_classification_created')
    
    class Meta:
        db_table = 'document_classifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['predicted_category', 'created_at']),
            models.Index(fields=['classification_method', 'created_at']),
            models.Index(fields=['is_successful', 'created_at']),
            models.Index(fields=['document_hash']),
        ]
    
    def __str__(self):
        return f"{self.document_name} -> {self.predicted_category}"
    
    def get_all_predictions(self):
        """Get all predictions as dict."""
        return self.all_predictions if isinstance(self.all_predictions, dict) else {}

class SearchQuery(models.Model):
    """
    Menyimpan search queries dan analytics.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query_text = models.TextField()
    query_type = models.CharField(max_length=50, choices=[
        ('semantic', 'Semantic Search'),
        ('keyword', 'Keyword Search'),
        ('hybrid', 'Hybrid Search'),
    ])
    
    # Search parameters
    search_models = models.JSONField(default=list, blank=True)  # Models searched
    filters = models.JSONField(default=dict, blank=True)
    limit = models.IntegerField(default=10)
    
    # Results
    results_count = models.IntegerField(default=0)
    results_data = models.JSONField(default=list, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    # User interaction
    clicked_results = models.JSONField(default=list, blank=True)  # Track which results were clicked
    user_satisfaction = models.IntegerField(null=True, blank=True, validators=[
        MinValueValidator(1), MaxValueValidator(5)
    ])  # 1-5 rating
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_searchquery_created')
    
    class Meta:
        db_table = 'search_queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query_type', 'created_at']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['results_count', 'created_at']),
        ]
    
    def __str__(self):
        return f"Search: {self.query_text[:50]}..."
    
    def get_search_models(self):
        """Get search models as list."""
        return self.search_models if isinstance(self.search_models, list) else []
    
    def get_results_data(self):
        """Get results data as list."""
        return self.results_data if isinstance(self.results_data, list) else []
    
    def add_clicked_result(self, result_id):
        """Add a clicked result to tracking."""
        clicked = self.clicked_results if isinstance(self.clicked_results, list) else []
        if result_id not in clicked:
            clicked.append(result_id)
            self.clicked_results = clicked
            self.save(update_fields=['clicked_results'])

class NLPAnalysis(models.Model):
    """
    Menyimpan hasil analisis NLP Indonesia.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    text_hash = models.CharField(max_length=64, blank=True)  # SHA-256 hash untuk caching
    
    # Analysis results
    sentiment_label = models.CharField(max_length=20, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(-1.0), MaxValueValidator(1.0)
    ])
    entities = models.JSONField(default=list, blank=True)  # Named entities
    classification_result = models.JSONField(default=dict, blank=True)
    text_statistics = models.JSONField(default=dict, blank=True)
    
    # Processing info
    analysis_type = models.CharField(max_length=50, choices=[
        ('sentiment', 'Sentiment Analysis'),
        ('ner', 'Named Entity Recognition'),
        ('classification', 'Text Classification'),
        ('full', 'Full Analysis'),
    ])
    processing_time_ms = models.IntegerField(null=True, blank=True)
    model_used = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_nlp_analysis_created')
    
    class Meta:
        db_table = 'nlp_analyses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['text_hash']),
            models.Index(fields=['sentiment_label', 'created_at']),
            models.Index(fields=['analysis_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"NLP Analysis: {self.text[:50]}..."
    
    def get_entities(self):
        """Get entities as list."""
        return self.entities if isinstance(self.entities, list) else []
    
    def get_classification_result(self):
        """Get classification result as dict."""
        return self.classification_result if isinstance(self.classification_result, dict) else {}
    
    def get_text_statistics(self):
        """Get text statistics as dict."""
        return self.text_statistics if isinstance(self.text_statistics, dict) else {}

class WorkflowExecution(models.Model):
    """
    Menyimpan eksekusi workflow RAG + N8N.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_type = models.CharField(max_length=100)
    workflow_name = models.CharField(max_length=200)
    
    # Input data
    input_data = models.JSONField()
    rag_query = models.TextField(blank=True)
    rag_results = models.JSONField(default=list, blank=True)
    
    # N8N execution
    n8n_workflow_id = models.CharField(max_length=100, blank=True)
    n8n_execution_id = models.CharField(max_length=100, blank=True)
    n8n_status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    
    # Results
    execution_result = models.JSONField(default=dict, blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    is_successful = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_workflow_execution_created')
    
    class Meta:
        db_table = 'workflow_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['workflow_type', 'created_at']),
            models.Index(fields=['n8n_status', 'created_at']),
            models.Index(fields=['is_successful', 'created_at']),
            models.Index(fields=['n8n_execution_id']),
        ]
    
    def __str__(self):
        return f"Workflow: {self.workflow_name} ({self.n8n_status})"
    
    def get_input_data(self):
        """Get input data as dict."""
        return self.input_data if isinstance(self.input_data, dict) else {}
    
    def get_rag_results(self):
        """Get RAG results as list."""
        return self.rag_results if isinstance(self.rag_results, list) else []
    
    def get_execution_result(self):
        """Get execution result as dict."""
        return self.execution_result if isinstance(self.execution_result, dict) else {}

class AIServiceLog(models.Model):
    """
    Logging untuk semua AI services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_type = models.CharField(max_length=50)
    operation = models.CharField(max_length=100)
    log_level = models.CharField(max_length=20, choices=[
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ])
    message = models.TextField()
    extra_data = models.JSONField(default=dict, blank=True)
    
    # Request info
    request_id = models.CharField(max_length=100, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ai_service_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_type', 'created_at']),
            models.Index(fields=['log_level', 'created_at']),
            models.Index(fields=['request_id']),
        ]
    
    def __str__(self):
        return f"{self.service_type} - {self.log_level}: {self.message[:50]}..."
    
    def get_extra_data(self):
        """Get extra data as dict."""
        return self.extra_data if isinstance(self.extra_data, dict) else {}

class ChatSession(models.Model):
    """
    Model untuk menyimpan sesi chat HR Assistant
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, default='HR Chat Session')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class ChatMessage(models.Model):
    """
    Model untuk menyimpan pesan dalam sesi chat
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    is_user_message = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['is_user_message']),
        ]
    
    def __str__(self):
        message_type = "User" if self.is_user_message else "Bot"
        return f"{message_type}: {self.message[:50]}... - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class HRQueryLog(models.Model):
    """
    Model untuk logging query HR Assistant
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hr_query_logs')
    query = models.TextField()
    query_type = models.CharField(max_length=100)
    response_data = models.JSONField(default=dict)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    processing_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'hr_query_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['query_type']),
            models.Index(fields=['success']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.query_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class TrainingData(models.Model):
    """
    Model untuk menyimpan training data yang dapat diupload oleh admin dan manager.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # File upload
    file = models.FileField(upload_to='training_data/', null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(null=True, blank=True)  # in bytes
    file_type = models.CharField(max_length=50, blank=True)
    
    # Training data type
    data_type = models.CharField(max_length=50, choices=[
        ('knowledge_base', 'Knowledge Base'),
        ('nlp_training', 'NLP Training'),
        ('classification', 'Classification'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('embedding', 'Embedding'),
        ('other', 'Other'),
    ], default='knowledge_base')
    
    # AI Service target
    target_service = models.CharField(max_length=50, choices=[
        ('budget_ai', 'Budget AI'),
        ('knowledge_ai', 'Knowledge AI'),
        ('indonesian_nlp', 'Indonesian NLP'),
        ('rag_n8n', 'RAG + N8N Integration'),
        ('document_classifier', 'Document Classifier'),
        ('intelligent_search', 'Intelligent Search'),
    ], default='knowledge_ai')
    
    # Processing status
    processing_status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Processing results
    processing_result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    processing_time_ms = models.IntegerField(null=True, blank=True)
    
    # Model evaluation metrics
    accuracy_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    precision_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    recall_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    f1_score = models.FloatField(null=True, blank=True, validators=[
        MinValueValidator(0.0), MaxValueValidator(1.0)
    ])
    evaluation_metrics = models.JSONField(default=dict, blank=True)  # Additional metrics
    train_test_split_ratio = models.FloatField(default=0.8, validators=[
        MinValueValidator(0.1), MaxValueValidator(0.9)
    ])
    validation_loss = models.FloatField(null=True, blank=True)
    training_epochs = models.IntegerField(null=True, blank=True)
    model_size_mb = models.FloatField(null=True, blank=True)
    
    # Status flags
    is_active = models.BooleanField(default=True)
    is_processed = models.BooleanField(default=False)
    
    # Timestamps and user tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='training_data_uploads')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_data_processed')
    
    class Meta:
        db_table = 'training_data'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['data_type', 'created_at']),
            models.Index(fields=['target_service', 'created_at']),
            models.Index(fields=['processing_status', 'created_at']),
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['is_active', 'is_processed']),
        ]
        permissions = [
            ('can_upload_training_data', 'Can upload training data'),
            ('can_manage_training_data', 'Can manage training data'),
            ('can_process_training_data', 'Can process training data'),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.data_type} ({self.processing_status})"
    
    @property
    def tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []
    
    @property
    def file_name(self):
        """Get the filename from file field"""
        if self.file:
            return self.file.name.split('/')[-1]
        return None
    
    @property
    def file_type(self):
        """Get file extension"""
        if self.file:
            return self.file.name.split('.')[-1].lower()
        return None
    
    @property
    def file_size(self):
        """Get file size in bytes"""
        if self.file:
            try:
                return self.file.size
            except:
                return 0
        return 0
    
    def get_metadata(self):
        """Get metadata as dict."""
        return self.metadata if isinstance(self.metadata, dict) else {}
    
    def get_tags(self):
        """Get tags as list."""
        return self.tags if isinstance(self.tags, list) else []
    
    def add_tag(self, tag):
        """Add a tag to the training data."""
        tags = self.get_tags()
        if tag not in tags:
            tags.append(tag)
            self.tags = tags
            self.save(update_fields=['tags', 'updated_at'])
    
    def get_processing_result(self):
        """Get processing result as dict."""
        return self.processing_result if isinstance(self.processing_result, dict) else {}
    
    def mark_as_processed(self, result=None, processed_by=None):
        """Mark training data as processed."""
        self.is_processed = True
        self.processing_status = 'completed'
        if result:
            self.processing_result = result
        if processed_by:
            self.processed_by = processed_by
        self.save(update_fields=['is_processed', 'processing_status', 'processing_result', 'processed_by', 'updated_at'])
    
    def mark_as_failed(self, error_message, processed_by=None):
        """Mark training data as failed."""
        self.processing_status = 'failed'
        self.error_message = error_message
        if processed_by:
            self.processed_by = processed_by
        self.save(update_fields=['processing_status', 'error_message', 'processed_by', 'updated_at'])
    
    def set_evaluation_metrics(self, accuracy=None, precision=None, recall=None, f1=None, 
                              additional_metrics=None, validation_loss=None, epochs=None, model_size=None):
        """Set evaluation metrics for the training data."""
        if accuracy is not None:
            self.accuracy_score = accuracy
        if precision is not None:
            self.precision_score = precision
        if recall is not None:
            self.recall_score = recall
        if f1 is not None:
            self.f1_score = f1
        if additional_metrics:
            self.evaluation_metrics = additional_metrics
        if validation_loss is not None:
            self.validation_loss = validation_loss
        if epochs is not None:
            self.training_epochs = epochs
        if model_size is not None:
            self.model_size_mb = model_size
        
        self.save(update_fields=[
            'accuracy_score', 'precision_score', 'recall_score', 'f1_score',
            'evaluation_metrics', 'validation_loss', 'training_epochs', 'model_size_mb', 'updated_at'
        ])
    
    def get_success_ratio(self):
        """Calculate success ratio based on accuracy score."""
        if self.accuracy_score is not None:
            return self.accuracy_score
        return None
    
    def get_evaluation_summary(self):
        """Get comprehensive evaluation summary."""
        return {
            'accuracy': self.accuracy_score,
            'precision': self.precision_score,
            'recall': self.recall_score,
            'f1_score': self.f1_score,
            'validation_loss': self.validation_loss,
            'training_epochs': self.training_epochs,
            'model_size_mb': self.model_size_mb,
            'train_test_split': self.train_test_split_ratio,
            'additional_metrics': self.evaluation_metrics,
            'success_ratio': self.get_success_ratio()
        }