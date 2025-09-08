from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
from crispy_forms.bootstrap import FormActions
from employee.models import Department
from .models import (
    DocumentCategory, DocumentTag, KnowledgeDocument, DocumentVersion,
    DocumentComment, KnowledgeBase
)


class KnowledgeDocumentForm(forms.ModelForm):
    """Form for creating and editing knowledge documents"""
    
    tags = forms.ModelMultipleChoiceField(
        queryset=DocumentTag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select relevant tags for this document"
    )
    
    allowed_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select users who can access this document (for restricted visibility)"
    )
    
    change_summary = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text="Describe the changes made (for version history)"
    )
    
    class Meta:
        model = KnowledgeDocument
        fields = [
            'title', 'description', 'content', 'document_type', 'category',
            'tags', 'file', 'version', 'language', 'status', 'visibility',
            'department', 'allowed_users', 'expires_at', 'review_cycle_months',
            'next_review_date'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'content': forms.Textarea(attrs={'rows': 15, 'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'language': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'review_cycle_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'next_review_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter categories to active ones
        self.fields['category'].queryset = DocumentCategory.objects.filter(is_active=True)
        
        # Filter departments
        self.fields['department'].queryset = Department.objects.all()
        self.fields['department'].empty_label = "All Departments"
        
        # Set up crispy forms
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Document Information',
                Row(
                    Column('title', css_class='form-group col-md-8 mb-0'),
                    Column('version', css_class='form-group col-md-4 mb-0'),
                ),
                'description',
                Row(
                    Column('document_type', css_class='form-group col-md-6 mb-0'),
                    Column('category', css_class='form-group col-md-6 mb-0'),
                ),
                'tags',
                'content',
                'file',
            ),
            Fieldset(
                'Access Control',
                Row(
                    Column('status', css_class='form-group col-md-4 mb-0'),
                    Column('visibility', css_class='form-group col-md-4 mb-0'),
                    Column('language', css_class='form-group col-md-4 mb-0'),
                ),
                'department',
                'allowed_users',
            ),
            Fieldset(
                'Review & Expiry',
                Row(
                    Column('review_cycle_months', css_class='form-group col-md-4 mb-0'),
                    Column('next_review_date', css_class='form-group col-md-4 mb-0'),
                    Column('expires_at', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            'change_summary',
            FormActions(
                Submit('submit', 'Save Document', css_class='btn btn-primary'),
                HTML('<a href="{% url "knowledge:document_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )
    
    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise ValidationError("Expiry date must be in the future.")
        return expires_at
    
    def clean_next_review_date(self):
        next_review_date = self.cleaned_data.get('next_review_date')
        if next_review_date and next_review_date <= timezone.now().date():
            raise ValidationError("Next review date must be in the future.")
        return next_review_date
    
    def clean(self):
        cleaned_data = super().clean()
        visibility = cleaned_data.get('visibility')
        department = cleaned_data.get('department')
        allowed_users = cleaned_data.get('allowed_users')
        
        if visibility == 'department' and not department:
            raise ValidationError({
                'department': 'Department is required for department-only visibility.'
            })
        
        if visibility == 'restricted' and not allowed_users:
            raise ValidationError({
                'allowed_users': 'At least one user must be selected for restricted visibility.'
            })
        
        return cleaned_data


class DocumentCategoryForm(forms.ModelForm):
    """Form for creating and editing document categories"""
    
    class Meta:
        model = DocumentCategory
        fields = ['name', 'description', 'color', 'icon', 'parent', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., fas fa-folder'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Exclude self from parent choices to prevent circular references
        if self.instance.pk:
            self.fields['parent'].queryset = DocumentCategory.objects.exclude(
                pk=self.instance.pk
            ).filter(is_active=True)
        else:
            self.fields['parent'].queryset = DocumentCategory.objects.filter(is_active=True)
        
        self.fields['parent'].empty_label = "No Parent (Top Level)"
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-8 mb-0'),
                Column('is_active', css_class='form-group col-md-4 mb-0'),
            ),
            'description',
            Row(
                Column('color', css_class='form-group col-md-6 mb-0'),
                Column('icon', css_class='form-group col-md-6 mb-0'),
            ),
            'parent',
            FormActions(
                Submit('submit', 'Save Category', css_class='btn btn-primary'),
                HTML('<a href="{% url "knowledge:category_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )


class DocumentTagForm(forms.ModelForm):
    """Form for creating and editing document tags"""
    
    class Meta:
        model = DocumentTag
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-8 mb-0'),
                Column('color', css_class='form-group col-md-4 mb-0'),
            ),
            FormActions(
                Submit('submit', 'Save Tag', css_class='btn btn-primary'),
                HTML('<a href="{% url "knowledge:tag_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )


class DocumentCommentForm(forms.ModelForm):
    """Form for adding comments to documents"""
    
    class Meta:
        model = DocumentComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Add your comment...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            'content',
            FormActions(
                Submit('submit', 'Add Comment', css_class='btn btn-primary btn-sm'),
            )
        )


class KnowledgeSearchForm(forms.Form):
    """Advanced search form for knowledge documents"""
    
    query = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search documents...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    document_type = forms.ChoiceField(
        choices=[('', 'All Types')] + KnowledgeDocument.DOCUMENT_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Status')] + KnowledgeDocument.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    visibility = forms.ChoiceField(
        choices=[('', 'All Visibility')] + KnowledgeDocument.VISIBILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    tags = forms.ModelMultipleChoiceField(
        queryset=DocumentTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'GET'
        self.helper.layout = Layout(
            Row(
                Column('query', css_class='form-group col-md-12 mb-0'),
            ),
            Row(
                Column('category', css_class='form-group col-md-4 mb-0'),
                Column('document_type', css_class='form-group col-md-4 mb-0'),
                Column('status', css_class='form-group col-md-4 mb-0'),
            ),
            Row(
                Column('visibility', css_class='form-group col-md-4 mb-0'),
                Column('date_from', css_class='form-group col-md-4 mb-0'),
                Column('date_to', css_class='form-group col-md-4 mb-0'),
            ),
            'tags',
            FormActions(
                Submit('submit', 'Search', css_class='btn btn-primary'),
                HTML('<a href="{% url "knowledge:search" %}" class="btn btn-secondary">Clear</a>'),
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError("Start date must be before end date.")
        
        return cleaned_data


class DocumentUploadForm(forms.Form):
    """Form for bulk document upload"""
    
    files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        }),
        help_text="Select files to upload"
    )
    
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    document_type = forms.ChoiceField(
        choices=KnowledgeDocument.DOCUMENT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=KnowledgeDocument.STATUS_CHOICES,
        initial='draft',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    visibility = forms.ChoiceField(
        choices=KnowledgeDocument.VISIBILITY_CHOICES,
        initial='public',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    auto_process_ai = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Automatically process uploaded documents with AI",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'files',
            Row(
                Column('category', css_class='form-group col-md-6 mb-0'),
                Column('document_type', css_class='form-group col-md-6 mb-0'),
            ),
            Row(
                Column('status', css_class='form-group col-md-6 mb-0'),
                Column('visibility', css_class='form-group col-md-6 mb-0'),
            ),
            'auto_process_ai',
            FormActions(
                Submit('submit', 'Upload Documents', css_class='btn btn-primary'),
            )
        )


class KnowledgeBaseForm(forms.ModelForm):
    """Form for creating and editing knowledge bases"""
    
    documents = forms.ModelMultipleChoiceField(
        queryset=KnowledgeDocument.objects.filter(status='published'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select documents to include in this knowledge base"
    )
    
    class Meta:
        model = KnowledgeBase
        fields = ['name', 'description', 'is_public', 'department', 'documents']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['department'].queryset = Department.objects.all()
        self.fields['department'].empty_label = "All Departments"
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            'description',
            Row(
                Column('is_public', css_class='form-group col-md-6 mb-0'),
                Column('department', css_class='form-group col-md-6 mb-0'),
            ),
            'documents',
            FormActions(
                Submit('submit', 'Save Knowledge Base', css_class='btn btn-primary'),
                HTML('<a href="{% url "knowledge:knowledgebase_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )


class DocumentReviewForm(forms.ModelForm):
    """Form for reviewing documents"""
    
    review_comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        required=False,
        help_text="Add review comments"
    )
    
    class Meta:
        model = KnowledgeDocument
        fields = ['status', 'next_review_date']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'next_review_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit status choices for review
        self.fields['status'].choices = [
            ('review', 'Under Review'),
            ('approved', 'Approved'),
            ('published', 'Published'),
            ('archived', 'Archived'),
        ]
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'status',
            'next_review_date',
            'review_comments',
            FormActions(
                Submit('submit', 'Update Review', css_class='btn btn-primary'),
            )
        )