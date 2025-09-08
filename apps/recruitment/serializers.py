from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Candidate, Recruitment, Stage, StageNote, 
    RecruitmentSurvey, SurveyTemplate, Skill
)
from employee.models import Employee
from base.models import JobPosition, Company


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model"""
    
    class Meta:
        model = Skill
        fields = ['id', 'skill', 'company_id']
        read_only_fields = ['id']


class StageSerializer(serializers.ModelSerializer):
    """Serializer for Stage model"""
    
    stage_type_display = serializers.CharField(source='get_stage_type_display', read_only=True)
    
    class Meta:
        model = Stage
        fields = [
            'id', 'stage', 'stage_type', 'stage_type_display', 
            'sequence', 'company_id'
        ]
        read_only_fields = ['id']


class RecruitmentSerializer(serializers.ModelSerializer):
    """Serializer for Recruitment model"""
    
    job_position_title = serializers.CharField(source='job_position_id.job_position', read_only=True)
    managers_names = serializers.SerializerMethodField()
    skills_list = serializers.SerializerMethodField()
    total_candidates = serializers.SerializerMethodField()
    hired_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Recruitment
        fields = [
            'id', 'title', 'description', 'vacancy', 'job_position_id', 'job_position_title',
            'recruitment_managers', 'managers_names', 'skills', 'skills_list',
            'start_date', 'end_date', 'is_event_based', 'is_published', 'is_active',
            'company_id', 'total_candidates', 'hired_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'total_candidates', 'hired_count']
    
    def get_managers_names(self, obj):
        """Get list of manager names"""
        return [manager.get_full_name() for manager in obj.recruitment_managers.all()]
    
    def get_skills_list(self, obj):
        """Get list of required skills"""
        return [skill.skill for skill in obj.skills.all()]
    
    def get_total_candidates(self, obj):
        """Get total number of candidates for this recruitment"""
        return obj.candidate_set.count()
    
    def get_hired_count(self, obj):
        """Get number of hired candidates"""
        return obj.candidate_set.filter(hired=True).count()


class CandidateSerializer(serializers.ModelSerializer):
    """Serializer for Candidate model"""
    
    recruitment_title = serializers.CharField(source='recruitment_id.title', read_only=True)
    stage_name = serializers.CharField(source='stage_id.stage', read_only=True)
    job_position_title = serializers.CharField(source='job_position_id.job_position', read_only=True)
    referral_name = serializers.CharField(source='referral.get_full_name', read_only=True)
    offer_letter_status_display = serializers.CharField(source='get_offer_letter_status_display', read_only=True)
    
    # AI Analysis fields (computed)
    ai_analysis = serializers.SerializerMethodField()
    similarity_score = serializers.SerializerMethodField()
    recommendation = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'name', 'email', 'mobile', 'country', 'state', 'city', 'zip',
            'dob', 'gender', 'experience_months', 'resume', 'portfolio',
            'recruitment_id', 'recruitment_title', 'stage_id', 'stage_name',
            'job_position_id', 'job_position_title', 'referral', 'referral_name',
            'hired', 'canceled', 'is_active', 'joining_date', 'offer_letter_status',
            'offer_letter_status_display', 'start_onboard', 'schedule_date',
            'company_id', 'created_at', 'ai_analysis', 'similarity_score', 'recommendation'
        ]
        read_only_fields = [
            'id', 'created_at', 'ai_analysis', 'similarity_score', 'recommendation'
        ]
    
    def get_ai_analysis(self, obj):
        """Get cached AI analysis result"""
        from django.core.cache import cache
        cached_result = cache.get(f"resume_analysis_{obj.id}")
        return cached_result if cached_result else None
    
    def get_similarity_score(self, obj):
        """Get similarity score from AI analysis"""
        analysis = self.get_ai_analysis(obj)
        return analysis.get('similarity_score') if analysis else None
    
    def get_recommendation(self, obj):
        """Get recommendation from AI analysis"""
        analysis = self.get_ai_analysis(obj)
        return analysis.get('recommendation') if analysis else None


class CandidateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating candidates with validation"""
    
    class Meta:
        model = Candidate
        fields = [
            'name', 'email', 'mobile', 'country', 'state', 'city', 'zip',
            'dob', 'gender', 'experience_months', 'resume', 'portfolio',
            'recruitment_id', 'stage_id', 'job_position_id', 'referral'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness within recruitment"""
        recruitment_id = self.initial_data.get('recruitment_id')
        if recruitment_id:
            existing = Candidate.objects.filter(
                email=value, 
                recruitment_id=recruitment_id
            ).exists()
            if existing:
                raise serializers.ValidationError(
                    "Candidate with this email already exists for this recruitment."
                )
        return value
    
    def validate_mobile(self, value):
        """Validate mobile number format"""
        if value and len(value) < 10:
            raise serializers.ValidationError(
                "Mobile number must be at least 10 digits."
            )
        return value
    
    def validate_resume(self, value):
        """Validate resume file"""
        if value:
            if not value.name.lower().endswith('.pdf'):
                raise serializers.ValidationError(
                    "Resume must be a PDF file."
                )
            if value.size > 5 * 1024 * 1024:  # 5MB limit
                raise serializers.ValidationError(
                    "Resume file size must be less than 5MB."
                )
        return value


class StageNoteSerializer(serializers.ModelSerializer):
    """Serializer for Stage Notes"""
    
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    candidate_name = serializers.CharField(source='candidate_id.name', read_only=True)
    stage_name = serializers.CharField(source='stage_id.stage', read_only=True)
    
    class Meta:
        model = StageNote
        fields = [
            'id', 'candidate_id', 'candidate_name', 'stage_id', 'stage_name',
            'note', 'updated_by', 'updated_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SurveyTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Survey Template"""
    
    class Meta:
        model = SurveyTemplate
        fields = ['id', 'title', 'template_data', 'company_id']
        read_only_fields = ['id']


class RecruitmentSurveySerializer(serializers.ModelSerializer):
    """Serializer for Recruitment Survey"""
    
    template_title = serializers.CharField(source='template_id.title', read_only=True)
    candidate_name = serializers.CharField(source='candidate_id.name', read_only=True)
    
    class Meta:
        model = RecruitmentSurvey
        fields = [
            'id', 'candidate_id', 'candidate_name', 'template_id', 'template_title',
            'answer_data', 'company_id'
        ]
        read_only_fields = ['id']


class CandidateAnalysisSerializer(serializers.Serializer):
    """Serializer for AI analysis results"""
    
    candidate_id = serializers.IntegerField()
    similarity_score = serializers.FloatField()
    recommendation = serializers.CharField()
    skills_match = serializers.ListField(child=serializers.CharField())
    missing_skills = serializers.ListField(child=serializers.CharField())
    experience_analysis = serializers.DictField()
    sentiment_analysis = serializers.DictField()
    extracted_entities = serializers.DictField()
    processed_at = serializers.DateTimeField()
    confidence_score = serializers.FloatField()
    
    class Meta:
        fields = [
            'candidate_id', 'similarity_score', 'recommendation', 'skills_match',
            'missing_skills', 'experience_analysis', 'sentiment_analysis',
            'extracted_entities', 'processed_at', 'confidence_score'
        ]


class WorkflowTriggerSerializer(serializers.Serializer):
    """Serializer for workflow trigger requests"""
    
    candidate_id = serializers.IntegerField()
    workflow_type = serializers.ChoiceField(choices=[
        ('resume_screening', 'Resume Screening'),
        ('interview_scheduling', 'Interview Scheduling'),
        ('candidate_notification', 'Candidate Notification'),
        ('hiring_decision', 'Hiring Decision'),
        ('onboarding_trigger', 'Onboarding Trigger')
    ])
    async_processing = serializers.BooleanField(default=True)
    additional_data = serializers.DictField(required=False)
    
    class Meta:
        fields = ['candidate_id', 'workflow_type', 'async_processing', 'additional_data']


class BatchAnalysisSerializer(serializers.Serializer):
    """Serializer for batch analysis requests"""
    
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=50  # Limit batch size
    )
    job_description = serializers.CharField(required=False, allow_blank=True)
    force_refresh = serializers.BooleanField(default=False)
    
    class Meta:
        fields = ['candidate_ids', 'job_description', 'force_refresh']


class ServiceHealthSerializer(serializers.Serializer):
    """Serializer for service health check results"""
    
    n8n = serializers.DictField()
    ollama = serializers.DictField()
    chroma_db = serializers.DictField()
    overall_health = serializers.BooleanField()
    
    class Meta:
        fields = ['n8n', 'ollama', 'chroma_db', 'overall_health']


class TaskStatusSerializer(serializers.Serializer):
    """Serializer for Celery task status"""
    
    task_id = serializers.CharField()
    status = serializers.CharField()
    ready = serializers.BooleanField()
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False)
    
    class Meta:
        fields = ['task_id', 'status', 'ready', 'result', 'error']


class RecruitmentAnalyticsSerializer(serializers.Serializer):
    """Serializer for recruitment analytics"""
    
    statistics = serializers.DictField()
    stage_distribution = serializers.ListField(child=serializers.DictField())
    recent_ai_analyses = serializers.ListField(child=serializers.DictField())
    
    class Meta:
        fields = ['statistics', 'stage_distribution', 'recent_ai_analyses']