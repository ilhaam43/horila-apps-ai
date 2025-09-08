from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json


class NLPModel(models.Model):
    """Model to store NLP model configurations"""
    
    MODEL_TYPES = [
        ('sentiment', 'Sentiment Analysis'),
        ('emotion', 'Emotion Detection'),
        ('ner', 'Named Entity Recognition'),
        ('classification', 'Text Classification'),
        ('summarization', 'Text Summarization'),
        ('keyword_extraction', 'Keyword Extraction'),
        ('topic_modeling', 'Topic Modeling'),
        ('language_detection', 'Language Detection'),
    ]
    
    FRAMEWORKS = [
        ('transformers', 'Hugging Face Transformers'),
        ('spacy', 'spaCy'),
        ('nltk', 'NLTK'),
        ('scikit_learn', 'Scikit-learn'),
        ('tensorflow', 'TensorFlow'),
        ('pytorch', 'PyTorch'),
        ('custom', 'Custom Implementation'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    framework = models.CharField(max_length=50, choices=FRAMEWORKS)
    model_path = models.CharField(max_length=500, help_text="Path to model files or HuggingFace model name")
    tokenizer_path = models.CharField(max_length=500, blank=True, help_text="Path to tokenizer files")
    
    # Model configuration
    config = models.JSONField(default=dict, help_text="Model-specific configuration parameters")
    preprocessing_config = models.JSONField(default=dict, help_text="Text preprocessing configuration")
    postprocessing_config = models.JSONField(default=dict, help_text="Output postprocessing configuration")
    
    # Performance metrics
    accuracy = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    precision = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    recall = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    f1_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Status and metadata
    is_active = models.BooleanField(default=True)
    is_loaded = models.BooleanField(default=False, help_text="Whether model is currently loaded in memory")
    load_time = models.FloatField(null=True, blank=True, help_text="Model loading time in seconds")
    memory_usage = models.BigIntegerField(null=True, blank=True, help_text="Memory usage in bytes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_type', 'is_active']),
            models.Index(fields=['framework']),
            models.Index(fields=['is_loaded']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.model_type})"
    
    def save(self, *args, **kwargs):
        if self.pk:
            # Update last_used when model is accessed
            old_instance = NLPModel.objects.get(pk=self.pk)
            if old_instance.is_loaded != self.is_loaded and self.is_loaded:
                self.last_used = timezone.now()
        super().save(*args, **kwargs)


class TextAnalysisJob(models.Model):
    """Model to store text analysis jobs and results"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Job identification
    job_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    
    # Input data
    input_text = models.TextField()
    input_language = models.CharField(max_length=10, default='id', help_text="ISO language code")
    
    # Model and processing
    model = models.ForeignKey(NLPModel, on_delete=models.CASCADE)
    parameters = models.JSONField(default=dict, help_text="Processing parameters")
    analysis_type = models.CharField(max_length=50, choices=NLPModel.MODEL_TYPES, default='sentiment', help_text="Type of analysis to perform")
    
    # Job status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Results
    result = models.JSONField(null=True, blank=True, help_text="Analysis results")
    confidence_score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    processing_time = models.FloatField(null=True, blank=True, help_text="Processing time in seconds")
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['model', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['job_id']),
        ]
    
    def __str__(self):
        return f"Job {self.job_id} - {self.analysis_type} ({self.status})"
    
    @property
    def duration(self):
        """Calculate job duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class SentimentAnalysisResult(models.Model):
    """Detailed sentiment analysis results"""
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
        ('mixed', 'Mixed'),
    ]
    
    job = models.OneToOneField(TextAnalysisJob, on_delete=models.CASCADE, related_name='sentiment_result')
    
    # Overall sentiment
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Detailed scores
    positive_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    negative_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    neutral_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Additional analysis
    subjectivity = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    emotion_scores = models.JSONField(default=dict, help_text="Emotion detection scores")
    keywords = models.JSONField(default=list, help_text="Extracted keywords")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Sentiment: {self.sentiment} ({self.confidence:.2f})"


class NamedEntityResult(models.Model):
    """Named Entity Recognition results"""
    
    ENTITY_TYPES = [
        ('PERSON', 'Person'),
        ('ORG', 'Organization'),
        ('GPE', 'Geopolitical Entity'),
        ('LOC', 'Location'),
        ('DATE', 'Date'),
        ('TIME', 'Time'),
        ('MONEY', 'Money'),
        ('PERCENT', 'Percentage'),
        ('MISC', 'Miscellaneous'),
    ]
    
    job = models.ForeignKey(TextAnalysisJob, on_delete=models.CASCADE, related_name='ner_results')
    
    # Entity information
    text = models.CharField(max_length=500)
    label = models.CharField(max_length=50, choices=ENTITY_TYPES)
    start_pos = models.IntegerField()
    end_pos = models.IntegerField()
    confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    
    # Additional metadata
    normalized_text = models.CharField(max_length=500, blank=True)
    context = models.TextField(blank=True, help_text="Surrounding context")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_pos']
        indexes = [
            models.Index(fields=['job', 'label']),
            models.Index(fields=['start_pos', 'end_pos']),
        ]
    
    def __str__(self):
        return f"{self.text} ({self.label})"


class TextClassificationResult(models.Model):
    """Text classification results"""
    
    job = models.OneToOneField(TextAnalysisJob, on_delete=models.CASCADE, related_name='classification_result')
    
    # Classification results
    predicted_class = models.CharField(max_length=100)
    confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(1)])
    class_probabilities = models.JSONField(default=dict, help_text="Probabilities for all classes")
    
    # Feature analysis
    top_features = models.JSONField(default=list, help_text="Most important features for classification")
    feature_weights = models.JSONField(default=dict, help_text="Feature importance weights")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Class: {self.predicted_class} ({self.confidence:.2f})"


class ModelUsageStatistics(models.Model):
    """Track model usage statistics"""
    
    model = models.ForeignKey(NLPModel, on_delete=models.CASCADE, related_name='usage_stats')
    
    # Usage metrics
    total_requests = models.BigIntegerField(default=0)
    successful_requests = models.BigIntegerField(default=0)
    failed_requests = models.BigIntegerField(default=0)
    
    # Performance metrics
    avg_processing_time = models.FloatField(default=0.0)
    min_processing_time = models.FloatField(null=True, blank=True)
    max_processing_time = models.FloatField(null=True, blank=True)
    
    # Resource usage
    total_cpu_time = models.FloatField(default=0.0)
    peak_memory_usage = models.BigIntegerField(default=0)
    
    # Time period
    date = models.DateField()
    hour = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['model', 'date', 'hour']
        ordering = ['-date', '-hour']
        indexes = [
            models.Index(fields=['model', 'date']),
            models.Index(fields=['date', 'hour']),
        ]
    
    def __str__(self):
        return f"{self.model.name} - {self.date} {self.hour}:00"
    
    @property
    def success_rate(self):
        """Calculate success rate"""
        if self.total_requests > 0:
            return self.successful_requests / self.total_requests
        return 0.0


class NLPConfiguration(models.Model):
    """Global NLP configuration settings"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Processing settings
    max_concurrent_jobs = models.IntegerField(default=5, validators=[MinValueValidator(1)])
    job_timeout = models.IntegerField(default=300, help_text="Job timeout in seconds")
    max_text_length = models.IntegerField(default=10000, help_text="Maximum text length for processing")
    
    # Model management
    auto_load_models = models.BooleanField(default=True)
    model_cache_size = models.IntegerField(default=3, help_text="Number of models to keep in memory")
    model_unload_timeout = models.IntegerField(default=1800, help_text="Unload unused models after N seconds")
    
    # Resource limits
    max_memory_usage = models.BigIntegerField(default=2147483648, help_text="Maximum memory usage in bytes (2GB default)")
    cpu_limit = models.FloatField(default=0.8, help_text="CPU usage limit (0.0-1.0)")
    
    # Logging and monitoring
    enable_detailed_logging = models.BooleanField(default=True)
    log_level = models.CharField(max_length=20, default='INFO', choices=[
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ])
    
    # Caching settings
    enable_caching = models.BooleanField(default=True, help_text="Enable result caching")
    
    # API and security settings
    api_rate_limit = models.IntegerField(default=100, help_text="API requests per minute")
    enable_api_key_auth = models.BooleanField(default=False)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_active_config(cls):
        """Get the active configuration"""
        return cls.objects.filter(is_active=True).first()