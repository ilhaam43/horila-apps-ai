from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import json
import re

from .models import (
    NLPModel, TextAnalysisJob, NLPConfiguration,
    SentimentAnalysisResult, NamedEntityResult, TextClassificationResult
)


class NLPConfigurationForm(forms.ModelForm):
    """Form for NLP Configuration"""
    
    class Meta:
        model = NLPConfiguration
        fields = [
            'name', 'description', 'max_concurrent_jobs', 'job_timeout',
            'max_text_length', 'auto_load_models', 'model_cache_size',
            'model_unload_timeout', 'max_memory_usage', 'cpu_limit',
            'enable_detailed_logging', 'log_level', 'api_rate_limit',
            'enable_api_key_auth', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama konfigurasi'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Deskripsi konfigurasi'
            }),
            'max_concurrent_jobs': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 50
            }),
            'job_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 30,
                'max': 3600
            }),
            'max_text_length': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 100,
                'max': 100000
            }),
            'model_cache_size': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'model_unload_timeout': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 60,
                'max': 7200
            }),
            'max_memory_usage': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'max': '16.0'
            }),
            'cpu_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0.1',
                'max': '1.0'
            }),
            'log_level': forms.Select(attrs={'class': 'form-control'}),
            'api_rate_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 10,
                'max': 10000
            }),
            'auto_load_models': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_detailed_logging': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_api_key_auth': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('Nama'),
            'description': _('Deskripsi'),
            'max_concurrent_jobs': _('Maksimal Job Bersamaan'),
            'job_timeout': _('Timeout Job (detik)'),
            'max_text_length': _('Panjang Teks Maksimal'),
            'auto_load_models': _('Auto Load Model'),
            'model_cache_size': _('Ukuran Cache Model'),
            'model_unload_timeout': _('Timeout Unload Model (detik)'),
            'max_memory_usage': _('Penggunaan Memori Maksimal (GB)'),
            'cpu_limit': _('Batas CPU (0.1-1.0)'),
            'enable_detailed_logging': _('Aktifkan Logging Detail'),
            'log_level': _('Level Log'),
            'api_rate_limit': _('Batas Rate API (per menit)'),
            'enable_api_key_auth': _('Aktifkan Autentikasi API Key'),
            'is_active': _('Aktif'),
        }
    
    def clean_name(self):
        """Validate configuration name"""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError(_('Nama konfigurasi harus diisi'))
        
        # Check uniqueness
        qs = NLPConfiguration.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(_('Konfigurasi dengan nama ini sudah ada'))
        
        return name
    
    def clean_max_concurrent_jobs(self):
        """Validate max concurrent jobs"""
        value = self.cleaned_data.get('max_concurrent_jobs')
        if value and (value < 1 or value > 50):
            raise ValidationError(_('Maksimal job bersamaan harus antara 1-50'))
        return value
    
    def clean_cpu_limit(self):
        """Validate CPU limit"""
        value = self.cleaned_data.get('cpu_limit')
        if value and (value < 0.1 or value > 1.0):
            raise ValidationError(_('Batas CPU harus antara 0.1-1.0'))
        return value


class NLPModelForm(forms.ModelForm):
    """Form for NLP Model"""
    
    config_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '{"param1": "value1", "param2": "value2"}'
        }),
        required=False,
        label=_('Konfigurasi (JSON)'),
        help_text=_('Konfigurasi model dalam format JSON')
    )
    
    preprocessing_config_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '{"lowercase": true, "remove_punctuation": false}'
        }),
        required=False,
        label=_('Konfigurasi Preprocessing (JSON)'),
        help_text=_('Konfigurasi preprocessing dalam format JSON')
    )
    
    postprocessing_config_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '{"threshold": 0.5, "normalize": true}'
        }),
        required=False,
        label=_('Konfigurasi Postprocessing (JSON)'),
        help_text=_('Konfigurasi postprocessing dalam format JSON')
    )
    
    class Meta:
        model = NLPModel
        fields = [
            'name', 'description', 'model_type', 'framework',
            'model_path', 'tokenizer_path', 'accuracy', 'precision',
            'recall', 'f1_score', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama model'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Deskripsi model'
            }),
            'model_type': forms.Select(attrs={'class': 'form-control'}),
            'framework': forms.Select(attrs={'class': 'form-control'}),
            'model_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Path ke model file'
            }),
            'tokenizer_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Path ke tokenizer (opsional)'
            }),
            'accuracy': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            }),
            'precision': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            }),
            'recall': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            }),
            'f1_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': _('Nama Model'),
            'description': _('Deskripsi'),
            'model_type': _('Tipe Model'),
            'framework': _('Framework'),
            'model_path': _('Path Model'),
            'tokenizer_path': _('Path Tokenizer'),
            'accuracy': _('Akurasi'),
            'precision': _('Presisi'),
            'recall': _('Recall'),
            'f1_score': _('F1 Score'),
            'is_active': _('Aktif'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate JSON fields from model instance
        if self.instance and self.instance.pk:
            if self.instance.config:
                self.fields['config_json'].initial = json.dumps(
                    self.instance.config, indent=2, ensure_ascii=False
                )
            if self.instance.preprocessing_config:
                self.fields['preprocessing_config_json'].initial = json.dumps(
                    self.instance.preprocessing_config, indent=2, ensure_ascii=False
                )
            if self.instance.postprocessing_config:
                self.fields['postprocessing_config_json'].initial = json.dumps(
                    self.instance.postprocessing_config, indent=2, ensure_ascii=False
                )
    
    def clean_name(self):
        """Validate model name"""
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError(_('Nama model harus diisi'))
        
        # Check uniqueness
        qs = NLPModel.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(_('Model dengan nama ini sudah ada'))
        
        return name
    
    def clean_config_json(self):
        """Validate and parse config JSON"""
        config_json = self.cleaned_data.get('config_json')
        if config_json:
            try:
                return json.loads(config_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_(f'Format JSON tidak valid: {str(e)}'))
        return {}
    
    def clean_preprocessing_config_json(self):
        """Validate and parse preprocessing config JSON"""
        config_json = self.cleaned_data.get('preprocessing_config_json')
        if config_json:
            try:
                return json.loads(config_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_(f'Format JSON tidak valid: {str(e)}'))
        return {}
    
    def clean_postprocessing_config_json(self):
        """Validate and parse postprocessing config JSON"""
        config_json = self.cleaned_data.get('postprocessing_config_json')
        if config_json:
            try:
                return json.loads(config_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_(f'Format JSON tidak valid: {str(e)}'))
        return {}
    
    def save(self, commit=True):
        """Save model with JSON configs"""
        instance = super().save(commit=False)
        
        # Set JSON configs
        instance.config = self.cleaned_data.get('config_json', {})
        instance.preprocessing_config = self.cleaned_data.get('preprocessing_config_json', {})
        instance.postprocessing_config = self.cleaned_data.get('postprocessing_config_json', {})
        
        if commit:
            instance.save()
        return instance


class TextAnalysisJobForm(forms.ModelForm):
    """Form for Text Analysis Job"""
    
    parameters_json = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': '{"threshold": 0.5, "max_entities": 10}'
        }),
        required=False,
        label=_('Parameter (JSON)'),
        help_text=_('Parameter analisis dalam format JSON')
    )
    
    class Meta:
        model = TextAnalysisJob
        fields = [
            'name', 'description', 'input_text', 'input_language',
            'model', 'priority', 'max_retries'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nama job analisis'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Deskripsi job'
            }),
            'input_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Masukkan teks yang akan dianalisis...'
            }),
            'input_language': forms.Select(attrs={'class': 'form-control'}),
            'model': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'max_retries': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 5
            }),
        }
        labels = {
            'name': _('Nama Job'),
            'description': _('Deskripsi'),
            'input_text': _('Teks Input'),
            'input_language': _('Bahasa Input'),
            'model': _('Model'),
            'priority': _('Prioritas'),
            'max_retries': _('Maksimal Retry'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active models only
        self.fields['model'].queryset = NLPModel.objects.filter(is_active=True)
        
        # Populate parameters JSON field
        if self.instance and self.instance.pk and self.instance.parameters:
            self.fields['parameters_json'].initial = json.dumps(
                self.instance.parameters, indent=2, ensure_ascii=False
            )
    
    def clean_input_text(self):
        """Validate input text"""
        text = self.cleaned_data.get('input_text')
        if not text or not text.strip():
            raise ValidationError(_('Teks input harus diisi'))
        
        # Check text length
        config = NLPConfiguration.get_active_config()
        max_length = config.max_text_length if config else 10000
        
        if len(text) > max_length:
            raise ValidationError(
                _(f'Teks terlalu panjang. Maksimal {max_length} karakter')
            )
        
        return text.strip()
    
    def clean_parameters_json(self):
        """Validate and parse parameters JSON"""
        params_json = self.cleaned_data.get('parameters_json')
        if params_json:
            try:
                return json.loads(params_json)
            except json.JSONDecodeError as e:
                raise ValidationError(_(f'Format JSON tidak valid: {str(e)}'))
        return {}
    
    def save(self, commit=True):
        """Save job with JSON parameters"""
        instance = super().save(commit=False)
        
        # Set parameters
        instance.parameters = self.cleaned_data.get('parameters_json', {})
        
        # Generate job_id if not exists
        if not instance.job_id:
            import uuid
            instance.job_id = str(uuid.uuid4())
        
        if commit:
            instance.save()
        return instance


class QuickAnalysisForm(forms.Form):
    """Form for quick text analysis"""
    
    text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Masukkan teks yang akan dianalisis...'
        }),
        label=_('Teks'),
        max_length=10000
    )
    
    analysis_type = forms.ChoiceField(
        choices=[
            ('sentiment', _('Analisis Sentimen')),
            ('ner', _('Pengenalan Entitas Bernama')),
            ('classification', _('Klasifikasi Teks')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Jenis Analisis')
    )
    
    model = forms.ModelChoiceField(
        queryset=NLPModel.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Model'),
        required=False,
        empty_label=_('Pilih model otomatis')
    )
    
    def clean_text(self):
        """Validate text input"""
        text = self.cleaned_data.get('text')
        if not text or not text.strip():
            raise ValidationError(_('Teks harus diisi'))
        return text.strip()
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        analysis_type = cleaned_data.get('analysis_type')
        model = cleaned_data.get('model')
        
        if model and analysis_type:
            if model.model_type != analysis_type:
                raise ValidationError(
                    _(f'Model {model.name} tidak cocok untuk analisis {analysis_type}')
                )
        
        return cleaned_data


class BatchAnalysisForm(forms.Form):
    """Form for batch text analysis"""
    
    texts = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Masukkan teks, satu per baris...'
        }),
        label=_('Teks (satu per baris)'),
        help_text=_('Masukkan maksimal 100 teks, satu per baris')
    )
    
    analysis_type = forms.ChoiceField(
        choices=[
            ('sentiment', _('Analisis Sentimen')),
            ('ner', _('Pengenalan Entitas Bernama')),
            ('classification', _('Klasifikasi Teks')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Jenis Analisis')
    )
    
    model = forms.ModelChoiceField(
        queryset=NLPModel.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Model'),
        required=False,
        empty_label=_('Pilih model otomatis')
    )
    
    def clean_texts(self):
        """Validate and parse texts"""
        texts_raw = self.cleaned_data.get('texts')
        if not texts_raw:
            raise ValidationError(_('Teks harus diisi'))
        
        # Split by lines and clean
        texts = [line.strip() for line in texts_raw.split('\n') if line.strip()]
        
        if not texts:
            raise ValidationError(_('Minimal satu teks harus diisi'))
        
        if len(texts) > 100:
            raise ValidationError(_('Maksimal 100 teks dapat diproses sekaligus'))
        
        # Check individual text length
        config = NLPConfiguration.get_active_config()
        max_length = config.max_text_length if config else 10000
        
        for i, text in enumerate(texts, 1):
            if len(text) > max_length:
                raise ValidationError(
                    _(f'Teks baris {i} terlalu panjang. Maksimal {max_length} karakter')
                )
        
        return texts
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        analysis_type = cleaned_data.get('analysis_type')
        model = cleaned_data.get('model')
        
        if model and analysis_type:
            if model.model_type != analysis_type:
                raise ValidationError(
                    _(f'Model {model.name} tidak cocok untuk analisis {analysis_type}')
                )
        
        return cleaned_data


class ModelTestForm(forms.Form):
    """Form for testing NLP models"""
    
    test_text = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Saya sangat senang dengan layanan ini.'
        }),
        label=_('Teks Uji'),
        initial='Saya sangat senang dengan layanan ini.',
        max_length=1000
    )
    
    def clean_test_text(self):
        """Validate test text"""
        text = self.cleaned_data.get('test_text')
        if not text or not text.strip():
            raise ValidationError(_('Teks uji harus diisi'))
        return text.strip()


class ModelSearchForm(forms.Form):
    """Form for searching models"""
    
    query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari model...'
        }),
        label=_('Pencarian'),
        required=False
    )
    
    model_type = forms.ChoiceField(
        choices=[
            ('', _('Semua Tipe')),
            ('sentiment', _('Analisis Sentimen')),
            ('ner', _('Pengenalan Entitas')),
            ('classification', _('Klasifikasi Teks')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Tipe Model'),
        required=False
    )
    
    framework = forms.ChoiceField(
        choices=[
            ('', _('Semua Framework')),
            ('tensorflow', _('TensorFlow')),
            ('pytorch', _('PyTorch')),
            ('transformers', _('Transformers')),
            ('scikit-learn', _('Scikit-learn')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Framework'),
        required=False
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', _('Semua Status')),
            ('true', _('Aktif')),
            ('false', _('Tidak Aktif'))
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Status'),
        required=False
    )
    
    is_loaded = forms.ChoiceField(
        choices=[
            ('', _('Semua')),
            ('true', _('Dimuat')),
            ('false', _('Tidak Dimuat'))
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Status Muat'),
        required=False
    )


class JobSearchForm(forms.Form):
    """Form for searching analysis jobs"""
    
    query = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari job...'
        }),
        label=_('Pencarian'),
        required=False
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('Semua Status')),
            ('pending', _('Menunggu')),
            ('processing', _('Diproses')),
            ('completed', _('Selesai')),
            ('failed', _('Gagal')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Status'),
        required=False
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('', _('Semua Prioritas')),
            ('low', _('Rendah')),
            ('normal', _('Normal')),
            ('high', _('Tinggi')),
            ('urgent', _('Mendesak')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Prioritas'),
        required=False
    )
    
    model = forms.ModelChoiceField(
        queryset=NLPModel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Model'),
        required=False,
        empty_label=_('Semua Model')
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('Dari Tanggal'),
        required=False
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('Sampai Tanggal'),
        required=False
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_('Tanggal mulai tidak boleh lebih besar dari tanggal akhir'))
        
        return cleaned_data


class ConfigurationImportForm(forms.Form):
    """Form for importing configuration"""
    
    config_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.json'
        }),
        label=_('File Konfigurasi'),
        help_text=_('Upload file JSON berisi konfigurasi')
    )
    
    overwrite_existing = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Timpa Konfigurasi yang Ada'),
        required=False,
        help_text=_('Centang untuk menimpa konfigurasi dengan nama yang sama')
    )
    
    def clean_config_file(self):
        """Validate configuration file"""
        file = self.cleaned_data.get('config_file')
        if not file:
            return file
        
        # Check file extension
        if not file.name.endswith('.json'):
            raise ValidationError(_('File harus berformat JSON'))
        
        # Check file size (max 1MB)
        if file.size > 1024 * 1024:
            raise ValidationError(_('Ukuran file maksimal 1MB'))
        
        # Validate JSON content
        try:
            file.seek(0)
            content = file.read().decode('utf-8')
            json.loads(content)
            file.seek(0)  # Reset file pointer
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValidationError(_(f'File JSON tidak valid: {str(e)}'))
        
        return file


class UsageStatsFilterForm(forms.Form):
    """Form for filtering usage statistics"""
    
    model = forms.ModelChoiceField(
        queryset=NLPModel.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Model'),
        required=False,
        empty_label=_('Semua Model')
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('Dari Tanggal'),
        required=False
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label=_('Sampai Tanggal'),
        required=False
    )
    
    group_by = forms.ChoiceField(
        choices=[
            ('date', _('Per Hari')),
            ('hour', _('Per Jam')),
            ('model', _('Per Model')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label=_('Kelompokkan Berdasarkan'),
        initial='date'
    )
    
    def clean(self):
        """Validate date range"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_('Tanggal mulai tidak boleh lebih besar dari tanggal akhir'))
        
        return cleaned_data