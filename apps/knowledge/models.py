from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from employee.models import Department
import uuid
import os


class DocumentCategory(models.Model):
    """Categories for organizing knowledge documents"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code')
    icon = models.CharField(max_length=50, default='fas fa-folder', help_text='FontAwesome icon class')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Document Category'
        verbose_name_plural = 'Document Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def full_path(self):
        """Get full category path"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class DocumentTag(models.Model):
    """Tags for document classification"""
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6c757d')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Document Tag'
        verbose_name_plural = 'Document Tags'
        ordering = ['name']
    
    def __str__(self):
        return self.name


def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('knowledge', 'documents', str(instance.created_by.id), filename)


class KnowledgeDocument(models.Model):
    """Main knowledge document model"""
    
    DOCUMENT_TYPES = [
        ('policy', 'Policy'),
        ('procedure', 'Procedure'),
        ('manual', 'Manual'),
        ('guide', 'Guide'),
        ('template', 'Template'),
        ('form', 'Form'),
        ('presentation', 'Presentation'),
        ('training', 'Training Material'),
        ('other', 'Other')
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('department', 'Department Only'),
        ('restricted', 'Restricted Access')
    ]
    
    title = models.CharField(max_length=200, default='Document Version')
    description = models.TextField(default='No description provided')
    content = models.TextField(blank=True, help_text='Rich text content')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='other')
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='documents')
    tags = models.ManyToManyField(DocumentTag, blank=True, related_name='documents')
    
    # File attachment
    file = models.FileField(
        upload_to=document_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
            'txt', 'md', 'html', 'zip', 'rar'
        ])]
    )
    file_size = models.PositiveIntegerField(null=True, blank=True)
    
    # Metadata
    version = models.CharField(max_length=20, default='1.0')
    language = models.CharField(max_length=10, default='en')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    # Access control
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_documents')
    
    # Tracking
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    
    # AI Classification
    ai_confidence_score = models.FloatField(null=True, blank=True, help_text='AI classification confidence')
    ai_suggested_tags = models.JSONField(default=list, blank=True)
    ai_extracted_keywords = models.JSONField(default=list, blank=True)
    
    # Timestamps and users
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_documents')
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_documents')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_documents')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Expiry and review cycle
    expires_at = models.DateTimeField(null=True, blank=True)
    review_cycle_months = models.PositiveIntegerField(default=12, help_text='Review cycle in months')
    next_review_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Knowledge Document'
        verbose_name_plural = 'Knowledge Documents'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', 'visibility']),
            models.Index(fields=['category', 'document_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def needs_review(self):
        """Check if document needs review"""
        if self.next_review_date:
            return timezone.now().date() >= self.next_review_date
        return False
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class DocumentVersion(models.Model):
    """Version history for documents"""
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20)
    title = models.CharField(max_length=200, default='Document Version')
    content = models.TextField()
    file = models.FileField(upload_to='knowledge/versions/', null=True, blank=True)
    change_summary = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Document Version'
        verbose_name_plural = 'Document Versions'
        ordering = ['-created_at']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentComment(models.Model):
    """Comments and feedback on documents"""
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Document Comment'
        verbose_name_plural = 'Document Comments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.document.title} by {self.created_by.username}"


class DocumentAccess(models.Model):
    """Track document access for analytics"""
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='access_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    access_type = models.CharField(max_length=20, choices=[
        ('view', 'View'),
        ('download', 'Download'),
        ('edit', 'Edit'),
        ('comment', 'Comment')
    ])
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accessed_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = 'Document Access'
        verbose_name_plural = 'Document Access Logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['document', 'access_type']),
            models.Index(fields=['user', 'accessed_at']),
        ]


class AIAssistant(models.Model):
    """AI Assistant for knowledge management"""
    
    ASSISTANT_TYPES = [
        ('document_classifier', 'Document Classifier'),
        ('content_analyzer', 'Content Analyzer'),
        ('search_assistant', 'Search Assistant'),
        ('recommendation_engine', 'Recommendation Engine')
    ]
    
    name = models.CharField(max_length=100)
    assistant_type = models.CharField(max_length=30, choices=ASSISTANT_TYPES, default='document_classifier')
    description = models.TextField()
    model_name = models.CharField(max_length=100, help_text='AI model identifier')
    model_version = models.CharField(max_length=20, default='1.0')
    configuration = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    
    # Performance metrics
    accuracy_score = models.FloatField(null=True, blank=True)
    total_predictions = models.PositiveIntegerField(default=0)
    successful_predictions = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'AI Assistant'
        verbose_name_plural = 'AI Assistants'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_assistant_type_display()})"
    
    @property
    def success_rate(self):
        """Calculate success rate percentage"""
        if self.total_predictions > 0:
            return (self.successful_predictions / self.total_predictions) * 100
        return 0


class AIProcessingJob(models.Model):
    """Track AI processing jobs"""
    
    JOB_TYPES = [
        ('classify_document', 'Classify Document'),
        ('extract_keywords', 'Extract Keywords'),
        ('generate_summary', 'Generate Summary'),
        ('suggest_tags', 'Suggest Tags'),
        ('analyze_sentiment', 'Analyze Sentiment')
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]
    
    job_id = models.UUIDField(default=uuid.uuid4, unique=True)
    job_type = models.CharField(max_length=30, choices=JOB_TYPES)
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='ai_jobs')
    assistant = models.ForeignKey(AIAssistant, on_delete=models.CASCADE, related_name='jobs')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'AI Processing Job'
        verbose_name_plural = 'AI Processing Jobs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_job_type_display()} - {self.document.title}"


class KnowledgeBase(models.Model):
    """Knowledge base collections"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    documents = models.ManyToManyField(KnowledgeDocument, related_name='knowledge_bases')
    is_public = models.BooleanField(default=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Knowledge Base'
        verbose_name_plural = 'Knowledge Bases'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class SearchQuery(models.Model):
    """Model for tracking search queries"""
    query = models.CharField(max_length=500)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    clicked_document = models.ForeignKey(KnowledgeDocument, on_delete=models.SET_NULL, null=True, blank=True)
    search_filters = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"Search: {self.query[:50]}"


class ChatbotConversation(models.Model):
    """Model for chatbot conversations"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('archived', 'Archived')
    ]
    
    conversation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatbot_conversations')
    title = models.CharField(max_length=200, blank=True, help_text='Auto-generated from first message')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Context and metadata
    context_documents = models.ManyToManyField(KnowledgeDocument, blank=True, related_name='chatbot_contexts')
    session_metadata = models.JSONField(default=dict, help_text='Session info, user agent, etc.')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Chatbot Conversation'
        verbose_name_plural = 'Chatbot Conversations'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"Conversation {self.conversation_id} - {self.user.username}"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    def get_title(self):
        """Get conversation title from first user message"""
        if self.title:
            return self.title
        first_message = self.messages.filter(sender='user').first()
        if first_message:
            return first_message.content[:50] + ('...' if len(first_message.content) > 50 else '')
        return f"Conversation {self.conversation_id}"


class ChatbotMessage(models.Model):
    """Model for individual chatbot messages"""
    
    SENDER_CHOICES = [
        ('user', 'User'),
        ('assistant', 'AI Assistant'),
        ('system', 'System')
    ]
    
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('document_reference', 'Document Reference'),
        ('search_results', 'Search Results'),
        ('error', 'Error Message'),
        ('system_info', 'System Information')
    ]
    
    conversation = models.ForeignKey(ChatbotConversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    message_type = models.CharField(max_length=30, choices=MESSAGE_TYPES, default='text')
    content = models.TextField()
    
    # AI-specific fields
    ai_model = models.CharField(max_length=100, blank=True, help_text='AI model used for response')
    confidence_score = models.FloatField(null=True, blank=True, help_text='AI confidence in response')
    processing_time = models.FloatField(null=True, blank=True, help_text='Response generation time in seconds')
    
    # Document references
    referenced_documents = models.ManyToManyField(KnowledgeDocument, blank=True, related_name='chatbot_references')
    document_snippets = models.JSONField(default=list, help_text='Relevant document excerpts used')
    
    # Metadata
    metadata = models.JSONField(default=dict, help_text='Additional message metadata')
    
    # User feedback
    is_helpful = models.BooleanField(null=True, blank=True)
    feedback_comment = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Chatbot Message'
        verbose_name_plural = 'Chatbot Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'message_type']),
        ]
    
    def __str__(self):
        return f"{self.sender}: {self.content[:50]}..."
    
    @property
    def has_document_references(self):
        return self.referenced_documents.exists()
    
    def add_document_reference(self, document, snippet=None):
        """Add a document reference with optional snippet"""
        self.referenced_documents.add(document)
        if snippet:
            snippets = self.document_snippets or []
            snippets.append({
                'document_id': document.id,
                'document_title': document.title,
                'snippet': snippet,
                'added_at': timezone.now().isoformat()
            })
            self.document_snippets = snippets
            self.save()


class ChatbotFeedback(models.Model):
    """Model for collecting chatbot feedback"""
    
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent')
    ]
    
    FEEDBACK_TYPES = [
        ('accuracy', 'Answer Accuracy'),
        ('relevance', 'Answer Relevance'),
        ('completeness', 'Answer Completeness'),
        ('clarity', 'Answer Clarity'),
        ('speed', 'Response Speed'),
        ('overall', 'Overall Experience')
    ]
    
    message = models.ForeignKey(ChatbotMessage, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES, default='overall')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    
    # Improvement suggestions
    suggested_improvement = models.TextField(blank=True)
    missing_information = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Chatbot Feedback'
        verbose_name_plural = 'Chatbot Feedback'
        ordering = ['-created_at']
        unique_together = ['message', 'user', 'feedback_type']
    
    def __str__(self):
        return f"Feedback for {self.message.id}: {self.rating}/5"