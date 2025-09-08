from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    DocumentCategory, DocumentTag, KnowledgeDocument, DocumentVersion,
    DocumentComment, DocumentAccess, AIAssistant, AIProcessingJob,
    KnowledgeBase, SearchQuery, ChatbotConversation, ChatbotMessage, ChatbotFeedback
)

# Import chatbot serializers
from .chatbot_serializers import (
    ChatbotConversationSerializer, ChatbotMessageSerializer, ChatbotFeedbackSerializer,
    ChatbotConversationListSerializer, ChatbotQuerySerializer, ChatbotResponseSerializer,
    DocumentSearchSerializer, ChatbotStatsSerializer
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Serializer for DocumentCategory model"""
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.ReadOnlyField()
    document_count = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'description', 'color', 'icon', 'parent',
            'parent_name', 'full_path', 'is_active', 'document_count',
            'subcategories', 'created_at', 'updated_at'
        ]
    
    def get_document_count(self, obj):
        return obj.documents.filter(status='published').count()
    
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.filter(is_active=True)
        return DocumentCategorySerializer(subcategories, many=True, context=self.context).data


class DocumentTagSerializer(serializers.ModelSerializer):
    """Serializer for DocumentTag model"""
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentTag
        fields = ['id', 'name', 'color', 'document_count', 'created_at']
    
    def get_document_count(self, obj):
        return obj.documents.filter(status='published').count()


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer for DocumentVersion model"""
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'version_number', 'title', 'content', 'file',
            'change_summary', 'created_by', 'created_at'
        ]


class DocumentCommentSerializer(serializers.ModelSerializer):
    """Serializer for DocumentComment model"""
    created_by = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentComment
        fields = [
            'id', 'content', 'parent', 'created_by', 'created_at',
            'updated_at', 'is_resolved', 'replies'
        ]
    
    def get_replies(self, obj):
        if obj.replies.exists():
            return DocumentCommentSerializer(
                obj.replies.all(), many=True, context=self.context
            ).data
        return []


class KnowledgeDocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists"""
    category = DocumentCategorySerializer(read_only=True)
    tags = DocumentTagSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    is_expired = serializers.ReadOnlyField()
    needs_review = serializers.ReadOnlyField()
    
    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'description', 'document_type', 'document_type_display',
            'category', 'tags', 'status', 'status_display', 'visibility',
            'visibility_display', 'version', 'language', 'view_count',
            'download_count', 'is_expired', 'needs_review', 'created_by',
            'created_at', 'updated_at'
        ]


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Full serializer for KnowledgeDocument model"""
    category = DocumentCategorySerializer(read_only=True)
    tags = DocumentTagSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    updated_by = UserSerializer(read_only=True)
    reviewed_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    
    is_expired = serializers.ReadOnlyField()
    needs_review = serializers.ReadOnlyField()
    
    versions = DocumentVersionSerializer(many=True, read_only=True)
    comments = DocumentCommentSerializer(many=True, read_only=True)
    
    # Write-only fields for creation/update
    category_id = serializers.IntegerField(write_only=True, required=False)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'description', 'content', 'document_type',
            'document_type_display', 'category', 'category_id', 'tags', 'tag_ids',
            'file', 'file_size', 'version', 'language', 'status', 'status_display',
            'visibility', 'visibility_display', 'department', 'allowed_users',
            'view_count', 'download_count', 'ai_confidence_score',
            'ai_suggested_tags', 'ai_extracted_keywords', 'is_expired',
            'needs_review', 'created_by', 'updated_by', 'reviewed_by',
            'approved_by', 'created_at', 'updated_at', 'reviewed_at',
            'approved_at', 'published_at', 'expires_at', 'review_cycle_months',
            'next_review_date', 'versions', 'comments'
        ]
        read_only_fields = [
            'file_size', 'view_count', 'download_count', 'ai_confidence_score',
            'ai_suggested_tags', 'ai_extracted_keywords', 'created_by',
            'updated_by', 'reviewed_by', 'approved_by', 'created_at',
            'updated_at', 'reviewed_at', 'approved_at', 'published_at'
        ]
    
    def create(self, validated_data):
        # Handle category
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id
        
        # Handle tags
        tag_ids = validated_data.pop('tag_ids', [])
        
        # Create document
        document = KnowledgeDocument.objects.create(**validated_data)
        
        # Set tags
        if tag_ids:
            document.tags.set(tag_ids)
        
        return document
    
    def update(self, instance, validated_data):
        # Handle category
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category_id'] = category_id
        
        # Handle tags
        tag_ids = validated_data.pop('tag_ids', None)
        
        # Update document
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags
        if tag_ids is not None:
            instance.tags.set(tag_ids)
        
        return instance


class DocumentAccessSerializer(serializers.ModelSerializer):
    """Serializer for DocumentAccess model"""
    document = KnowledgeDocumentListSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    access_type_display = serializers.CharField(source='get_access_type_display', read_only=True)
    
    class Meta:
        model = DocumentAccess
        fields = [
            'id', 'document', 'user', 'access_type', 'access_type_display',
            'ip_address', 'user_agent', 'accessed_at'
        ]


class AIAssistantSerializer(serializers.ModelSerializer):
    """Serializer for AIAssistant model"""
    assistant_type_display = serializers.CharField(source='get_assistant_type_display', read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = AIAssistant
        fields = [
            'id', 'name', 'assistant_type', 'assistant_type_display',
            'description', 'model_name', 'model_version', 'configuration',
            'is_active', 'accuracy_score', 'total_predictions',
            'successful_predictions', 'success_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'accuracy_score', 'total_predictions', 'successful_predictions',
            'created_at', 'updated_at'
        ]


class AIProcessingJobSerializer(serializers.ModelSerializer):
    """Serializer for AIProcessingJob model"""
    document = KnowledgeDocumentListSerializer(read_only=True)
    assistant = AIAssistantSerializer(read_only=True)
    job_type_display = serializers.CharField(source='get_job_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AIProcessingJob
        fields = [
            'id', 'job_id', 'job_type', 'job_type_display', 'document',
            'assistant', 'status', 'status_display', 'input_data',
            'output_data', 'error_message', 'duration', 'started_at',
            'completed_at', 'created_at'
        ]
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            return duration.total_seconds()
        return None


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """Serializer for KnowledgeBase model"""
    documents = KnowledgeDocumentListSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    document_count = serializers.SerializerMethodField()
    
    # Write-only field for document IDs
    document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'documents', 'document_ids',
            'is_public', 'department', 'document_count', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_document_count(self, obj):
        return obj.documents.count()
    
    def create(self, validated_data):
        document_ids = validated_data.pop('document_ids', [])
        knowledge_base = KnowledgeBase.objects.create(**validated_data)
        
        if document_ids:
            knowledge_base.documents.set(document_ids)
        
        return knowledge_base
    
    def update(self, instance, validated_data):
        document_ids = validated_data.pop('document_ids', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if document_ids is not None:
            instance.documents.set(document_ids)
        
        return instance


class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer for SearchQuery model"""
    user = UserSerializer(read_only=True)
    clicked_document = KnowledgeDocumentListSerializer(read_only=True)
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query', 'user', 'results_count', 'clicked_document',
            'search_filters', 'ip_address', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']


# Analytics Serializers
class DocumentAnalyticsSerializer(serializers.Serializer):
    """Serializer for document analytics data"""
    total_documents = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_downloads = serializers.IntegerField()
    documents_by_category = serializers.DictField()
    documents_by_type = serializers.DictField()
    popular_documents = KnowledgeDocumentListSerializer(many=True)
    recent_documents = KnowledgeDocumentListSerializer(many=True)
    documents_needing_review = serializers.IntegerField()


class SearchAnalyticsSerializer(serializers.Serializer):
    """Serializer for search analytics data"""
    total_searches = serializers.IntegerField()
    unique_searchers = serializers.IntegerField()
    average_results_per_search = serializers.FloatField()
    top_search_terms = serializers.ListField()
    searches_with_no_results = serializers.IntegerField()
    search_trends = serializers.DictField()


class AIAnalyticsSerializer(serializers.Serializer):
    """Serializer for AI analytics data"""
    total_ai_jobs = serializers.IntegerField()
    successful_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    average_processing_time = serializers.FloatField()
    jobs_by_type = serializers.DictField()
    assistant_performance = serializers.DictField()