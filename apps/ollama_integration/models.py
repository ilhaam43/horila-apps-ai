from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class OllamaModel(models.Model):
    """Ollama AI Model Configuration"""
    
    MODEL_TYPES = [
        ('llama2', 'Llama 2'),
        ('llama2:13b', 'Llama 2 13B'),
        ('llama2:70b', 'Llama 2 70B'),
        ('codellama', 'Code Llama'),
        ('codellama:13b', 'Code Llama 13B'),
        ('codellama:34b', 'Code Llama 34B'),
        ('mistral', 'Mistral'),
        ('mixtral', 'Mixtral'),
        ('neural-chat', 'Neural Chat'),
        ('starling-lm', 'Starling LM'),
        ('dolphin-mixtral', 'Dolphin Mixtral'),
        ('phi', 'Phi'),
        ('orca-mini', 'Orca Mini'),
        ('vicuna', 'Vicuna'),
        ('wizard-vicuna-uncensored', 'Wizard Vicuna Uncensored'),
        ('custom', 'Custom Model'),
    ]
    
    TASK_TYPES = [
        ('text_generation', 'Text Generation'),
        ('code_generation', 'Code Generation'),
        ('summarization', 'Text Summarization'),
        ('translation', 'Language Translation'),
        ('question_answering', 'Question Answering'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('classification', 'Text Classification'),
        ('embedding', 'Text Embedding'),
        ('chat', 'Chat/Conversation'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    model_name = models.CharField(max_length=100, choices=MODEL_TYPES)
    custom_model_name = models.CharField(max_length=200, blank=True, null=True,
                                       help_text="Custom model name if 'custom' is selected")
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    
    # Model parameters
    temperature = models.FloatField(default=0.7, validators=[MinValueValidator(0.0), MaxValueValidator(2.0)],
                                  help_text="Controls randomness in generation (0.0-2.0)")
    top_p = models.FloatField(default=0.9, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
                            help_text="Nucleus sampling parameter (0.0-1.0)")
    top_k = models.IntegerField(default=40, validators=[MinValueValidator(1), MaxValueValidator(100)],
                              help_text="Top-k sampling parameter")
    max_tokens = models.IntegerField(default=2048, validators=[MinValueValidator(1), MaxValueValidator(8192)],
                                   help_text="Maximum tokens to generate")
    
    # Configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    priority = models.IntegerField(default=1, help_text="Higher number = higher priority")
    
    # Performance metrics
    average_response_time = models.FloatField(default=0.0, help_text="Average response time in seconds")
    success_rate = models.FloatField(default=100.0, help_text="Success rate percentage")
    total_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'ollama_models'
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['is_active', 'task_type']),
            models.Index(fields=['priority', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_model_name_display()})"
    
    @property
    def effective_model_name(self):
        """Get the effective model name (custom or predefined)"""
        if self.model_name == 'custom' and self.custom_model_name:
            return self.custom_model_name
        return self.model_name
    
    def update_metrics(self, response_time, success=True):
        """Update performance metrics"""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
        
        # Update average response time
        if self.total_requests == 1:
            self.average_response_time = response_time
        else:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) / 
                self.total_requests
            )
        
        # Update success rate
        self.success_rate = ((self.total_requests - self.failed_requests) / self.total_requests) * 100
        
        self.save(update_fields=['total_requests', 'failed_requests', 'average_response_time', 'success_rate'])


class OllamaProcessingJob(models.Model):
    """Ollama AI Processing Job"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Job identification
    job_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Job configuration
    model = models.ForeignKey(OllamaModel, on_delete=models.CASCADE, related_name='jobs')
    task_type = models.CharField(max_length=50)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Input/Output
    input_data = models.JSONField(help_text="Input data for processing")
    output_data = models.JSONField(null=True, blank=True, help_text="Processing results")
    
    # Processing details
    prompt = models.TextField(help_text="Prompt sent to the model")
    system_prompt = models.TextField(blank=True, help_text="System prompt for context")
    
    # Status and progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    error_message = models.TextField(blank=True)
    
    # Performance metrics
    processing_time = models.FloatField(null=True, blank=True, help_text="Processing time in seconds")
    tokens_used = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # User tracking
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ollama_jobs')
    
    # Related objects (generic foreign key for flexibility)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'ollama_processing_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['model', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def start_processing(self):
        """Mark job as started"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def complete_processing(self, output_data, tokens_used=0):
        """Mark job as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.output_data = output_data
        self.tokens_used = tokens_used
        self.progress = 100
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
        
        self.save(update_fields=[
            'status', 'completed_at', 'output_data', 'tokens_used', 
            'progress', 'processing_time'
        ])
    
    def fail_processing(self, error_message):
        """Mark job as failed"""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        
        if self.started_at:
            self.processing_time = (self.completed_at - self.started_at).total_seconds()
        
        self.save(update_fields=[
            'status', 'completed_at', 'error_message', 'processing_time'
        ])


class OllamaConfiguration(models.Model):
    """Ollama Server Configuration"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Server settings
    host = models.CharField(max_length=255, default='localhost')
    port = models.IntegerField(default=11434)
    base_url = models.URLField(blank=True, help_text="Full base URL (overrides host/port)")
    
    # Authentication
    api_key = models.CharField(max_length=500, blank=True)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)
    
    # Connection settings
    timeout = models.IntegerField(default=30, help_text="Request timeout in seconds")
    max_retries = models.IntegerField(default=3)
    retry_delay = models.FloatField(default=1.0, help_text="Delay between retries in seconds")
    
    # Performance settings
    max_concurrent_requests = models.IntegerField(default=5)
    request_queue_size = models.IntegerField(default=100)
    
    # Health monitoring
    is_active = models.BooleanField(default=True)
    is_healthy = models.BooleanField(default=True)
    last_health_check = models.DateTimeField(null=True, blank=True)
    health_check_interval = models.IntegerField(default=300, help_text="Health check interval in seconds")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'ollama_configurations'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def effective_base_url(self):
        """Get the effective base URL"""
        if self.base_url:
            return self.base_url.rstrip('/')
        return f"http://{self.host}:{self.port}"
    
    def update_health_status(self, is_healthy):
        """Update health status"""
        self.is_healthy = is_healthy
        self.last_health_check = timezone.now()
        self.save(update_fields=['is_healthy', 'last_health_check'])


class OllamaModelUsage(models.Model):
    """Track Ollama model usage statistics"""
    
    model = models.ForeignKey(OllamaModel, on_delete=models.CASCADE, related_name='usage_stats')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ollama_usage')
    
    # Usage metrics
    date = models.DateField(default=timezone.now)
    request_count = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    total_processing_time = models.FloatField(default=0.0)
    
    # Success/failure tracking
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)
    
    # Cost tracking (if applicable)
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ollama_model_usage'
        unique_together = ['model', 'user', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['model', 'date']),
            models.Index(fields=['user', 'date']),
        ]
    
    def __str__(self):
        return f"{self.model.name} - {self.user.username} - {self.date}"
    
    @classmethod
    def record_usage(cls, model, user, tokens_used, processing_time, success=True):
        """Record model usage"""
        usage, created = cls.objects.get_or_create(
            model=model,
            user=user,
            date=timezone.now().date(),
            defaults={
                'request_count': 0,
                'total_tokens': 0,
                'total_processing_time': 0.0,
                'successful_requests': 0,
                'failed_requests': 0,
            }
        )
        
        usage.request_count += 1
        usage.total_tokens += tokens_used
        usage.total_processing_time += processing_time
        
        if success:
            usage.successful_requests += 1
        else:
            usage.failed_requests += 1
        
        usage.save()
        return usage


class OllamaPromptTemplate(models.Model):
    """Reusable prompt templates for Ollama"""
    
    TEMPLATE_TYPES = [
        ('system', 'System Prompt'),
        ('user', 'User Prompt'),
        ('assistant', 'Assistant Prompt'),
        ('function', 'Function Call'),
        ('summarization', 'Summarization'),
        ('translation', 'Translation'),
        ('classification', 'Classification'),
        ('qa', 'Question Answering'),
        ('code', 'Code Generation'),
        ('analysis', 'Text Analysis'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    
    # Template content
    template = models.TextField(help_text="Template with placeholders like {variable}")
    system_prompt = models.TextField(blank=True, help_text="System prompt to use with this template")
    
    # Template metadata
    variables = models.JSONField(default=list, help_text="List of required variables")
    example_input = models.JSONField(default=dict, help_text="Example input data")
    example_output = models.TextField(blank=True, help_text="Example expected output")
    
    # Usage settings
    recommended_models = models.ManyToManyField(OllamaModel, blank=True, 
                                              help_text="Recommended models for this template")
    default_temperature = models.FloatField(default=0.7)
    default_max_tokens = models.IntegerField(default=1024)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False, help_text="Available to all users")
    
    # Usage tracking
    usage_count = models.IntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ollama_templates')
    
    class Meta:
        db_table = 'ollama_prompt_templates'
        ordering = ['name']
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
            models.Index(fields=['is_public', 'is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def render_template(self, **kwargs):
        """Render template with provided variables"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}")
    
    def increment_usage(self):
        """Increment usage counter"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])