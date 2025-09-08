from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ChatbotConversation, ChatbotMessage, ChatbotFeedback,
    KnowledgeDocument, DocumentCategory
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id', 'username', 'email']


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Serializer for DocumentCategory model."""
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'description', 'color']
        read_only_fields = ['id']


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Serializer for KnowledgeDocument model."""
    category = DocumentCategorySerializer(read_only=True)
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'description', 'category', 'author',
            'document_type', 'status', 'visibility', 'priority',
            'created_at', 'updated_at', 'view_count', 'download_count'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'view_count', 'download_count'
        ]


class ChatbotMessageSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotMessage model."""
    referenced_documents = KnowledgeDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatbotMessage
        fields = [
            'id', 'sender', 'content', 'message_type', 'ai_model',
            'confidence_score', 'processing_time', 'is_helpful',
            'feedback_comment', 'referenced_documents', 'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'referenced_documents'
        ]
    
    def to_representation(self, instance):
        """Custom representation for better API response."""
        data = super().to_representation(instance)
        
        # Format timestamps
        if data.get('created_at'):
            data['created_at'] = instance.created_at.isoformat()
        
        # Add human-readable sender
        sender_map = {
            'user': 'User',
            'assistant': 'AI Assistant',
            'system': 'System'
        }
        data['sender_display'] = sender_map.get(data['sender'], data['sender'])
        
        # Format confidence score as percentage
        if data.get('confidence_score'):
            data['confidence_percentage'] = round(data['confidence_score'] * 100, 1)
        
        # Format processing time
        if data.get('processing_time'):
            data['processing_time_ms'] = round(data['processing_time'] * 1000, 2)
        
        return data


class ChatbotConversationSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotConversation model."""
    user = UserSerializer(read_only=True)
    messages = ChatbotMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatbotConversation
        fields = [
            'conversation_id', 'user', 'title', 'status', 'context_summary',
            'message_count', 'created_at', 'last_activity', 'messages',
            'last_message'
        ]
        read_only_fields = [
            'conversation_id', 'created_at', 'last_activity', 'message_count'
        ]
    
    def get_last_message(self, obj):
        """Get the last message in the conversation."""
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return {
                'id': last_message.id,
                'sender': last_message.sender,
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at.isoformat()
            }
        return None
    
    def to_representation(self, instance):
        """Custom representation for better API response."""
        data = super().to_representation(instance)
        
        # Format timestamps
        if data.get('created_at'):
            data['created_at'] = instance.created_at.isoformat()
        if data.get('last_activity'):
            data['last_activity'] = instance.last_activity.isoformat()
        
        # Add conversation title if not set
        if not data.get('title'):
            data['title'] = instance.get_title()
        
        # Add status display
        status_map = {
            'active': 'Active',
            'closed': 'Closed',
            'archived': 'Archived'
        }
        data['status_display'] = status_map.get(data['status'], data['status'])
        
        return data


class ChatbotConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists."""
    user = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatbotConversation
        fields = [
            'conversation_id', 'user', 'title', 'status', 'message_count',
            'created_at', 'last_activity', 'last_message'
        ]
        read_only_fields = [
            'conversation_id', 'created_at', 'last_activity', 'message_count'
        ]
    
    def get_last_message(self, obj):
        """Get the last message preview."""
        last_message = obj.messages.order_by('-created_at').first()
        if last_message:
            return {
                'sender': last_message.sender,
                'content': last_message.content[:50] + '...' if len(last_message.content) > 50 else last_message.content,
                'created_at': last_message.created_at.isoformat()
            }
        return None
    
    def to_representation(self, instance):
        """Custom representation for list view."""
        data = super().to_representation(instance)
        
        # Format timestamps
        if data.get('created_at'):
            data['created_at'] = instance.created_at.isoformat()
        if data.get('last_activity'):
            data['last_activity'] = instance.last_activity.isoformat()
        
        # Add conversation title if not set
        if not data.get('title'):
            data['title'] = instance.get_title()
        
        return data


class ChatbotFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for ChatbotFeedback model."""
    user = UserSerializer(read_only=True)
    message = ChatbotMessageSerializer(read_only=True)
    
    class Meta:
        model = ChatbotFeedback
        fields = [
            'id', 'user', 'message', 'feedback_type', 'rating',
            'comment', 'suggested_improvement', 'missing_information',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """Custom representation for feedback."""
        data = super().to_representation(instance)
        
        # Format timestamps
        if data.get('created_at'):
            data['created_at'] = instance.created_at.isoformat()
        if data.get('updated_at'):
            data['updated_at'] = instance.updated_at.isoformat()
        
        # Add feedback type display
        feedback_type_map = {
            'overall': 'Overall Quality',
            'accuracy': 'Accuracy',
            'relevance': 'Relevance',
            'completeness': 'Completeness',
            'clarity': 'Clarity'
        }
        data['feedback_type_display'] = feedback_type_map.get(
            data['feedback_type'], data['feedback_type']
        )
        
        # Add rating display
        rating_map = {
            1: 'Very Poor',
            2: 'Poor',
            3: 'Fair',
            4: 'Good',
            5: 'Excellent'
        }
        data['rating_display'] = rating_map.get(data['rating'], 'Unknown')
        
        return data


class ChatbotQuerySerializer(serializers.Serializer):
    """Serializer for chatbot query requests."""
    query = serializers.CharField(max_length=2000, required=True)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    context = serializers.JSONField(required=False, default=dict)
    max_results = serializers.IntegerField(min_value=1, max_value=20, default=5)
    include_references = serializers.BooleanField(default=True)
    
    def validate_query(self, value):
        """Validate query content."""
        if not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        return value.strip()


class ChatbotResponseSerializer(serializers.Serializer):
    """Serializer for chatbot responses."""
    success = serializers.BooleanField()
    conversation_id = serializers.UUIDField()
    response = serializers.CharField()
    confidence_score = serializers.FloatField(min_value=0.0, max_value=1.0)
    processing_time = serializers.FloatField(min_value=0.0)
    referenced_documents = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    message_id = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    error = serializers.CharField(required=False)


class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for document search requests."""
    q = serializers.CharField(max_length=500, required=True)
    category = serializers.CharField(max_length=100, required=False)
    max_results = serializers.IntegerField(min_value=1, max_value=50, default=10)
    include_content = serializers.BooleanField(default=False)
    
    def validate_q(self, value):
        """Validate search query."""
        if not value.strip():
            raise serializers.ValidationError("Search query cannot be empty")
        return value.strip()


class ChatbotStatsSerializer(serializers.Serializer):
    """Serializer for chatbot statistics."""
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    user_messages = serializers.IntegerField()
    ai_responses = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    helpful_responses = serializers.IntegerField()
    feedback_count = serializers.IntegerField()
    recent_activity = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )