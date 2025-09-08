from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
import os

from .models import TrainingData


class TrainingDataForm(forms.ModelForm):
    """
    Form untuk upload dan edit training data.
    """
    
    class Meta:
        model = TrainingData
        fields = [
            'title', 'description', 'file', 'data_type', 
            'target_service', 'tags'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Masukkan judul training data',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Deskripsi detail tentang training data ini'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.txt,.pdf,.docx,.csv,.json,.xlsx'
            }),
            'data_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'target_service': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tag1, Tag2, Tag3 (pisahkan dengan koma)'
            }),

        }
        labels = {
            'title': 'Judul Training Data',
            'description': 'Deskripsi',
            'file': 'File Training Data',
            'data_type': 'Tipe Data',
            'target_service': 'Target Service AI',
            'tags': 'Tags',

        }
        help_texts = {
            'title': 'Berikan judul yang deskriptif untuk training data ini.',
            'description': 'Jelaskan isi dan tujuan dari training data ini.',
            'file': 'Upload file dalam format: TXT, PDF, DOCX, CSV, JSON, atau XLSX (maksimal 50MB).',
            'data_type': 'Pilih jenis data training yang sesuai.',
            'target_service': 'Pilih service AI yang akan menggunakan data ini.',
            'tags': 'Tambahkan tags untuk memudahkan pencarian (opsional).',

        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required
        self.fields['title'].required = True
        self.fields['description'].required = True
        self.fields['data_type'].required = True
        self.fields['target_service'].required = True
        
        # Add file validation
        self.fields['file'].validators.append(
            FileExtensionValidator(
                allowed_extensions=['txt', 'pdf', 'docx', 'csv', 'json', 'xlsx'],
                message='Format file tidak didukung. Gunakan: TXT, PDF, DOCX, CSV, JSON, atau XLSX.'
            )
        )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (50MB limit)
            if file.size > 50 * 1024 * 1024:  # 50MB in bytes
                raise ValidationError('Ukuran file terlalu besar. Maksimal 50MB.')
            
            # Check file extension
            allowed_extensions = ['.txt', '.pdf', '.docx', '.csv', '.json', '.xlsx']
            file_extension = os.path.splitext(file.name)[1].lower()
            
            if file_extension not in allowed_extensions:
                raise ValidationError(
                    f'Format file tidak didukung: {file_extension}. '
                    f'Gunakan salah satu dari: {", ".join(allowed_extensions)}'
                )
        
        return file
    
    def clean_title(self):
        title = self.cleaned_data.get('title')
        
        if title:
            # Check for duplicate titles (excluding current instance if editing)
            queryset = TrainingData.objects.filter(title__iexact=title, is_active=True)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError('Training data dengan judul ini sudah ada.')
        
        return title
    
    def clean_tags(self):
        tags = self.cleaned_data.get('tags')
        
        if tags:
            # Clean and validate tags
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            
            # Limit number of tags
            if len(tag_list) > 10:
                raise ValidationError('Maksimal 10 tags diperbolehkan.')
            
            # Validate individual tag length
            for tag in tag_list:
                if len(tag) > 50:
                    raise ValidationError(f'Tag "{tag}" terlalu panjang. Maksimal 50 karakter per tag.')
            
            # Return cleaned tags as comma-separated string
            return ', '.join(tag_list)
        
        return tags


class TrainingDataFilterForm(forms.Form):
    """
    Form untuk filter training data di dashboard.
    """
    
    DATA_TYPE_CHOICES = [
        ('knowledge_base', 'Knowledge Base'),
        ('nlp_training', 'NLP Training'),
        ('classification', 'Classification'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('embedding', 'Embedding'),
        ('other', 'Other'),
    ]
    
    TARGET_SERVICE_CHOICES = [
        ('budget_ai', 'Budget AI'),
        ('knowledge_ai', 'Knowledge AI'),
        ('indonesian_nlp', 'Indonesian NLP'),
        ('rag_n8n', 'RAG + N8N Integration'),
        ('document_classifier', 'Document Classifier'),
        ('intelligent_search', 'Intelligent Search'),
    ]
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    data_type = forms.ChoiceField(
        choices=[('', 'Semua Tipe')] + DATA_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    target_service = forms.ChoiceField(
        choices=[('', 'Semua Service')] + TARGET_SERVICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    processing_status = forms.ChoiceField(
        choices=[('', 'Semua Status')] + PROCESSING_STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': 'Cari berdasarkan judul, deskripsi, atau nama file...'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        }),
        label='Dari Tanggal'
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control form-control-sm',
            'type': 'date'
        }),
        label='Sampai Tanggal'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('Tanggal "dari" tidak boleh lebih besar dari tanggal "sampai".')
        
        return cleaned_data


class TrainingDataBulkActionForm(forms.Form):
    """
    Form untuk bulk actions pada training data.
    """
    
    ACTION_CHOICES = [
        ('', 'Pilih Aksi'),
        ('delete', 'Hapus Terpilih'),
        ('process', 'Proses Terpilih'),
        ('export', 'Export Data Terpilih')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    selected_items = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    def clean_selected_items(self):
        selected_items = self.cleaned_data.get('selected_items')
        
        if selected_items:
            try:
                # Convert comma-separated string to list of integers
                item_ids = [int(id.strip()) for id in selected_items.split(',') if id.strip()]
                
                if not item_ids:
                    raise ValidationError('Tidak ada item yang dipilih.')
                
                # Validate that all IDs exist and are active
                existing_count = TrainingData.objects.filter(
                    id__in=item_ids, 
                    is_active=True
                ).count()
                
                if existing_count != len(item_ids):
                    raise ValidationError('Beberapa item yang dipilih tidak valid atau sudah dihapus.')
                
                return item_ids
                
            except ValueError:
                raise ValidationError('Format ID item tidak valid.')
        
        raise ValidationError('Tidak ada item yang dipilih.')


class TrainingDataSearchForm(forms.Form):
    """
    Advanced search form untuk training data.
    """
    
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan kata kunci pencarian...'
        }),
        label='Kata Kunci'
    )
    
    search_in = forms.MultipleChoiceField(
        choices=[
            ('title', 'Judul'),
            ('description', 'Deskripsi'),
            ('file_name', 'Nama File'),
            ('tags', 'Tags'),
            ('notes', 'Catatan')
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Cari di'
    )
    
    uploaded_by = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username atau nama lengkap'
        }),
        label='Diupload oleh'
    )
    
    file_type = forms.ChoiceField(
        choices=[
            ('', 'Semua Format'),
            ('.txt', 'Text (.txt)'),
            ('.pdf', 'PDF (.pdf)'),
            ('.docx', 'Word (.docx)'),
            ('.csv', 'CSV (.csv)'),
            ('.json', 'JSON (.json)'),
            ('.xlsx', 'Excel (.xlsx)')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Format File'
    )
    
    min_file_size = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'KB'
        }),
        label='Ukuran File Min (KB)'
    )
    
    max_file_size = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'KB'
        }),
        label='Ukuran File Max (KB)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_size = cleaned_data.get('min_file_size')
        max_size = cleaned_data.get('max_file_size')
        
        if min_size and max_size and min_size > max_size:
            raise ValidationError('Ukuran file minimum tidak boleh lebih besar dari maksimum.')
        
        return cleaned_data