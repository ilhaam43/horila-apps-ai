from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div
from crispy_forms.bootstrap import FormActions
import json

from .models import (
    OllamaModel,
    OllamaProcessingJob,
    OllamaConfiguration,
    OllamaPromptTemplate
)
from .client import OllamaClient


class OllamaConfigurationForm(forms.ModelForm):
    """Form for Ollama configuration"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep current password"
    )
    
    api_key = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
        help_text="Leave blank to keep current API key"
    )
    
    test_connection = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Test connection after saving"
    )
    
    class Meta:
        model = OllamaConfiguration
        fields = [
            'name', 'description', 'host', 'port', 'use_ssl',
            'api_key', 'username', 'password', 'timeout',
            'max_retries', 'retry_delay', 'max_concurrent_requests',
            'request_queue_size', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'localhost'}),
            'port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '11434'}),
            'use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'timeout': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'max_retries': forms.NumberInput(attrs={'class': 'form-control'}),
            'retry_delay': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'max_concurrent_requests': forms.NumberInput(attrs={'class': 'form-control'}),
            'request_queue_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('is_active', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'description',
            ),
            Fieldset(
                'Connection Settings',
                Row(
                    Column('host', css_class='form-group col-md-8 mb-0'),
                    Column('port', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('use_ssl', css_class='form-group col-md-4 mb-0'),
                    Column('username', css_class='form-group col-md-4 mb-0'),
                    Column('password', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                'api_key',
            ),
            Fieldset(
                'Performance Settings',
                Row(
                    Column('timeout', css_class='form-group col-md-4 mb-0'),
                    Column('max_retries', css_class='form-group col-md-4 mb-0'),
                    Column('retry_delay', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('max_concurrent_requests', css_class='form-group col-md-6 mb-0'),
                    Column('request_queue_size', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'Testing',
                'test_connection',
            ),
            FormActions(
                Submit('submit', 'Save Configuration', css_class='btn btn-primary'),
                HTML('<a href="{% url "ollama_integration:configuration_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )
    
    def clean_port(self):
        """Validate port number"""
        port = self.cleaned_data.get('port')
        if port and (port < 1 or port > 65535):
            raise ValidationError("Port must be between 1 and 65535")
        return port
    
    def clean_timeout(self):
        """Validate timeout"""
        timeout = self.cleaned_data.get('timeout')
        if timeout and timeout <= 0:
            raise ValidationError("Timeout must be positive")
        return timeout
    
    def clean_max_retries(self):
        """Validate max retries"""
        max_retries = self.cleaned_data.get('max_retries')
        if max_retries is not None and max_retries < 0:
            raise ValidationError("Max retries cannot be negative")
        return max_retries
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        test_connection = cleaned_data.get('test_connection')
        
        if test_connection:
            # Test connection with provided settings
            try:
                # Create temporary configuration for testing
                temp_config = OllamaConfiguration(
                    name='temp_test',
                    host=cleaned_data.get('host', 'localhost'),
                    port=cleaned_data.get('port', 11434),
                    use_ssl=cleaned_data.get('use_ssl', False),
                    api_key=cleaned_data.get('api_key', ''),
                    username=cleaned_data.get('username', ''),
                    password=cleaned_data.get('password', ''),
                    timeout=cleaned_data.get('timeout', 30.0)
                )
                
                # Test connection
                client = OllamaClient('temp_test')
                client.config = temp_config
                is_healthy = client.health_check()
                client.close()
                
                if not is_healthy:
                    raise ValidationError("Connection test failed. Please check your settings.")
                    
            except Exception as e:
                raise ValidationError(f"Connection test failed: {str(e)}")
        
        return cleaned_data


class OllamaModelForm(forms.ModelForm):
    """Form for Ollama model"""
    
    test_model = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Test model after saving"
    )
    
    class Meta:
        model = OllamaModel
        fields = [
            'name', 'model_name', 'description', 'task_type',
            'configuration', 'is_active', 'priority', 'temperature',
            'max_tokens', 'top_p', 'top_k', 'system_prompt',
            'custom_parameters'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'llama2:7b'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'configuration': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '2'}),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'top_p': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1'}),
            'top_k': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'system_prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'custom_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active configurations
        self.fields['configuration'].queryset = OllamaConfiguration.objects.filter(is_active=True)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('model_name', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'description',
                Row(
                    Column('task_type', css_class='form-group col-md-6 mb-0'),
                    Column('configuration', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('is_active', css_class='form-group col-md-6 mb-0'),
                    Column('priority', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
            ),
            Fieldset(
                'Model Parameters',
                Row(
                    Column('temperature', css_class='form-group col-md-3 mb-0'),
                    Column('max_tokens', css_class='form-group col-md-3 mb-0'),
                    Column('top_p', css_class='form-group col-md-3 mb-0'),
                    Column('top_k', css_class='form-group col-md-3 mb-0'),
                    css_class='form-row'
                ),
                'system_prompt',
                'custom_parameters',
            ),
            Fieldset(
                'Testing',
                'test_model',
            ),
            FormActions(
                Submit('submit', 'Save Model', css_class='btn btn-primary'),
                HTML('<a href="{% url "ollama_integration:model_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )
    
    def clean_custom_parameters(self):
        """Validate custom parameters JSON"""
        custom_params = self.cleaned_data.get('custom_parameters')
        if custom_params:
            try:
                json.loads(custom_params)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {str(e)}")
        return custom_params
    
    def clean_temperature(self):
        """Validate temperature range"""
        temperature = self.cleaned_data.get('temperature')
        if temperature is not None and (temperature < 0 or temperature > 2):
            raise ValidationError("Temperature must be between 0 and 2")
        return temperature
    
    def clean_top_p(self):
        """Validate top_p range"""
        top_p = self.cleaned_data.get('top_p')
        if top_p is not None and (top_p < 0 or top_p > 1):
            raise ValidationError("top_p must be between 0 and 1")
        return top_p
    
    def clean_top_k(self):
        """Validate top_k"""
        top_k = self.cleaned_data.get('top_k')
        if top_k is not None and top_k <= 0:
            raise ValidationError("top_k must be positive")
        return top_k
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        test_model = cleaned_data.get('test_model')
        
        if test_model:
            configuration = cleaned_data.get('configuration')
            model_name = cleaned_data.get('model_name')
            
            if configuration and model_name:
                try:
                    client = OllamaClient(configuration.name)
                    response = client.generate(
                        model_name,
                        "Hello, this is a test.",
                        temperature=0.1,
                        max_tokens=50
                    )
                    client.close()
                    
                    if not response.success:
                        raise ValidationError(f"Model test failed: {response.error}")
                        
                except Exception as e:
                    raise ValidationError(f"Model test failed: {str(e)}")
        
        return cleaned_data


class ProcessingJobForm(forms.ModelForm):
    """Form for creating processing jobs"""
    
    class Meta:
        model = OllamaProcessingJob
        fields = [
            'name', 'task_type', 'priority', 'prompt',
            'system_prompt', 'input_data'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'system_prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'input_data': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"key": "value"}'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Job Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('task_type', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                'priority',
            ),
            Fieldset(
                'Prompts',
                'prompt',
                'system_prompt',
            ),
            Fieldset(
                'Additional Data',
                'input_data',
            ),
            FormActions(
                Submit('submit', 'Create Job', css_class='btn btn-primary'),
                HTML('<a href="{% url "ollama_integration:job_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )
    
    def clean_input_data(self):
        """Validate input data JSON"""
        input_data = self.cleaned_data.get('input_data')
        if input_data:
            try:
                json.loads(input_data)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {str(e)}")
        return input_data
    
    def clean_prompt(self):
        """Validate prompt is not empty"""
        prompt = self.cleaned_data.get('prompt')
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty")
        return prompt


class OllamaPromptTemplateForm(forms.ModelForm):
    """Form for Ollama prompt templates"""
    
    test_template = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Test template rendering after saving"
    )
    
    class Meta:
        model = OllamaPromptTemplate
        fields = [
            'name', 'description', 'task_type', 'template',
            'system_prompt', 'variables', 'default_parameters',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_type': forms.Select(attrs={'class': 'form-control'}),
            'template': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'system_prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'variables': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '["var1", "var2"]'}),
            'default_parameters': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '{"temperature": 0.7}'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Template Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('task_type', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                'description',
                'is_active',
            ),
            Fieldset(
                'Template Content',
                'template',
                'system_prompt',
            ),
            Fieldset(
                'Configuration',
                'variables',
                'default_parameters',
            ),
            Fieldset(
                'Testing',
                'test_template',
            ),
            FormActions(
                Submit('submit', 'Save Template', css_class='btn btn-primary'),
                HTML('<a href="{% url "ollama_integration:template_list" %}" class="btn btn-secondary">Cancel</a>'),
            )
        )
    
    def clean_variables(self):
        """Validate variables JSON"""
        variables = self.cleaned_data.get('variables')
        if variables:
            try:
                parsed = json.loads(variables)
                if not isinstance(parsed, list):
                    raise ValidationError("Variables must be a JSON list")
                for var in parsed:
                    if not isinstance(var, str) or not var.isidentifier():
                        raise ValidationError(f"Invalid variable name: {var}")
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {str(e)}")
        return variables
    
    def clean_default_parameters(self):
        """Validate default parameters JSON"""
        default_params = self.cleaned_data.get('default_parameters')
        if default_params:
            try:
                json.loads(default_params)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Invalid JSON format: {str(e)}")
        return default_params
    
    def clean_template(self):
        """Validate template syntax"""
        template = self.cleaned_data.get('template')
        if template:
            try:
                from string import Template
                Template(template)
            except Exception as e:
                raise ValidationError(f"Invalid template syntax: {str(e)}")
        return template
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        test_template = cleaned_data.get('test_template')
        
        if test_template:
            template = cleaned_data.get('template')
            variables = cleaned_data.get('variables')
            
            if template and variables:
                try:
                    # Parse variables and create test data
                    var_list = json.loads(variables) if variables else []
                    test_vars = {var: f"test_{var}" for var in var_list}
                    
                    # Test template rendering
                    from string import Template
                    Template(template).substitute(test_vars)
                    
                except Exception as e:
                    raise ValidationError(f"Template test failed: {str(e)}")
        
        return cleaned_data


class QuickGenerationForm(forms.Form):
    """Quick text generation form"""
    
    task_type = forms.ChoiceField(
        choices=OllamaModel.TASK_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    prompt = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        help_text="Enter your prompt here"
    )
    
    system_prompt = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text="Optional system prompt"
    )
    
    temperature = forms.FloatField(
        initial=0.7,
        min_value=0.0,
        max_value=2.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        help_text="Controls randomness (0.0 = deterministic, 2.0 = very random)"
    )
    
    max_tokens = forms.IntegerField(
        initial=2048,
        min_value=1,
        max_value=8192,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Maximum number of tokens to generate"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('task_type', css_class='form-group col-md-6 mb-0'),
                Column('temperature', css_class='form-group col-md-3 mb-0'),
                Column('max_tokens', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'prompt',
            'system_prompt',
            FormActions(
                Submit('submit', 'Generate', css_class='btn btn-primary'),
                HTML('<button type="button" class="btn btn-secondary" onclick="clearForm()">Clear</button>'),
            )
        )
    
    def clean_prompt(self):
        """Validate prompt is not empty"""
        prompt = self.cleaned_data.get('prompt')
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty")
        return prompt


class ModelSearchForm(forms.Form):
    """Form for searching models"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search models...'
        })
    )
    
    task_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Task Types')] + list(OllamaModel.TASK_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Models'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    configuration = forms.ModelChoiceField(
        required=False,
        queryset=OllamaConfiguration.objects.filter(is_active=True),
        empty_label="All Configurations",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.layout = Layout(
            Row(
                Column('search', css_class='form-group col-md-3 mb-0'),
                Column('task_type', css_class='form-group col-md-3 mb-0'),
                Column('is_active', css_class='form-group col-md-3 mb-0'),
                Column('configuration', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            FormActions(
                Submit('submit', 'Search', css_class='btn btn-primary btn-sm'),
                HTML('<a href="?" class="btn btn-secondary btn-sm">Clear</a>'),
            )
        )


class JobFilterForm(forms.Form):
    """Form for filtering processing jobs"""
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + list(OllamaProcessingJob.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    task_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Task Types')] + list(OllamaProcessingJob.TASK_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities')] + list(OllamaProcessingJob.PRIORITY_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    model = forms.ModelChoiceField(
        required=False,
        queryset=OllamaModel.objects.filter(is_active=True),
        empty_label="All Models",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-2 mb-0'),
                Column('task_type', css_class='form-group col-md-2 mb-0'),
                Column('priority', css_class='form-group col-md-2 mb-0'),
                Column('model', css_class='form-group col-md-3 mb-0'),
                Column('date_from', css_class='form-group col-md-1.5 mb-0'),
                Column('date_to', css_class='form-group col-md-1.5 mb-0'),
                css_class='form-row'
            ),
            FormActions(
                Submit('submit', 'Filter', css_class='btn btn-primary btn-sm'),
                HTML('<a href="?" class="btn btn-secondary btn-sm">Clear</a>'),
            )
        )