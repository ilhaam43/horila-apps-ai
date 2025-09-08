from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
import json
import logging

from ollama_integration.models import (
    OllamaConfiguration,
    OllamaModel,
    OllamaPromptTemplate
)
from ollama_integration.client import OllamaClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize Ollama integration with default configurations and models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            default='localhost',
            help='Ollama server host (default: localhost)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=11434,
            help='Ollama server port (default: 11434)'
        )
        parser.add_argument(
            '--ssl',
            action='store_true',
            help='Use SSL connection'
        )
        parser.add_argument(
            '--test-connection',
            action='store_true',
            help='Test connection after setup'
        )
        parser.add_argument(
            '--pull-models',
            action='store_true',
            help='Pull recommended models after setup'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing configurations'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Initializing Ollama Integration...')
        )
        
        try:
            with transaction.atomic():
                # Create default configuration
                config = self.create_default_configuration(
                    host=options['host'],
                    port=options['port'],
                    use_ssl=options['ssl'],
                    force=options['force']
                )
                
                # Test connection if requested
                if options['test_connection']:
                    self.test_connection(config)
                
                # Create default models
                models = self.create_default_models(config, force=options['force'])
                
                # Create default prompt templates
                templates = self.create_default_templates(force=options['force'])
                
                # Pull models if requested
                if options['pull_models']:
                    self.pull_recommended_models(config, models)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully initialized Ollama integration:\n'
                        f'  - Configuration: {config.name}\n'
                        f'  - Models: {len(models)}\n'
                        f'  - Templates: {len(templates)}'
                    )
                )
        
        except Exception as e:
            raise CommandError(f'Failed to initialize Ollama integration: {str(e)}')
    
    def create_default_configuration(self, host, port, use_ssl, force):
        """Create default Ollama configuration"""
        config_name = 'default'
        
        # Check if configuration exists
        if OllamaConfiguration.objects.filter(name=config_name).exists():
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'Configuration "{config_name}" already exists. Use --force to recreate.'
                    )
                )
                return OllamaConfiguration.objects.get(name=config_name)
            else:
                OllamaConfiguration.objects.filter(name=config_name).delete()
                self.stdout.write(
                    self.style.WARNING(f'Deleted existing configuration "{config_name}"')
                )
        
        # Create new configuration
        config = OllamaConfiguration.objects.create(
            name=config_name,
            description='Default Ollama configuration',
            host=host,
            port=port,
            use_ssl=use_ssl,
            timeout=30.0,
            max_retries=3,
            retry_delay=1.0,
            max_concurrent_requests=5,
            request_queue_size=100,
            is_active=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created configuration: {config.name}')
        )
        
        return config
    
    def test_connection(self, config):
        """Test connection to Ollama server"""
        self.stdout.write('Testing connection to Ollama server...')
        
        try:
            client = OllamaClient(config.name)
            is_healthy = client.health_check()
            client.close()
            
            if is_healthy:
                self.stdout.write(
                    self.style.SUCCESS('✓ Connection test successful')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('✗ Connection test failed')
                )
                raise CommandError('Cannot connect to Ollama server')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Connection test failed: {str(e)}')
            )
            raise CommandError(f'Cannot connect to Ollama server: {str(e)}')
    
    def create_default_models(self, config, force):
        """Create default model configurations"""
        default_models = [
            {
                'name': 'Llama 2 7B Chat',
                'model_name': 'llama2:7b-chat',
                'description': 'Llama 2 7B model optimized for chat conversations',
                'task_type': 'chat',
                'priority': 'high',
                'temperature': 0.7,
                'max_tokens': 2048,
                'top_p': 0.9,
                'top_k': 40,
                'system_prompt': 'You are a helpful AI assistant. Provide accurate and helpful responses.'
            },
            {
                'name': 'Llama 2 7B Text',
                'model_name': 'llama2:7b',
                'description': 'Llama 2 7B model for general text generation',
                'task_type': 'text_generation',
                'priority': 'medium',
                'temperature': 0.8,
                'max_tokens': 2048,
                'top_p': 0.9,
                'top_k': 40,
                'system_prompt': 'Generate high-quality, coherent text based on the given prompt.'
            },
            {
                'name': 'Code Llama 7B',
                'model_name': 'codellama:7b',
                'description': 'Code Llama 7B model for code generation and analysis',
                'task_type': 'code_generation',
                'priority': 'high',
                'temperature': 0.3,
                'max_tokens': 4096,
                'top_p': 0.95,
                'top_k': 50,
                'system_prompt': 'You are an expert programmer. Generate clean, efficient, and well-documented code.'
            },
            {
                'name': 'Mistral 7B',
                'model_name': 'mistral:7b',
                'description': 'Mistral 7B model for general purpose tasks',
                'task_type': 'text_generation',
                'priority': 'medium',
                'temperature': 0.7,
                'max_tokens': 2048,
                'top_p': 0.9,
                'top_k': 40,
                'system_prompt': 'You are a knowledgeable assistant. Provide accurate and informative responses.'
            },
            {
                'name': 'Neural Chat 7B',
                'model_name': 'neural-chat:7b',
                'description': 'Neural Chat 7B model optimized for conversational AI',
                'task_type': 'chat',
                'priority': 'medium',
                'temperature': 0.7,
                'max_tokens': 2048,
                'top_p': 0.9,
                'top_k': 40,
                'system_prompt': 'You are a friendly and helpful conversational AI assistant.'
            }
        ]
        
        created_models = []
        
        for model_data in default_models:
            model_name = model_data['name']
            
            # Check if model exists
            if OllamaModel.objects.filter(name=model_name).exists():
                if not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Model "{model_name}" already exists. Use --force to recreate.'
                        )
                    )
                    created_models.append(OllamaModel.objects.get(name=model_name))
                    continue
                else:
                    OllamaModel.objects.filter(name=model_name).delete()
                    self.stdout.write(
                        self.style.WARNING(f'Deleted existing model "{model_name}"')
                    )
            
            # Create new model
            model = OllamaModel.objects.create(
                configuration=config,
                is_active=False,  # Will be activated after pulling
                **model_data
            )
            
            created_models.append(model)
            self.stdout.write(
                self.style.SUCCESS(f'Created model: {model.name}')
            )
        
        return created_models
    
    def create_default_templates(self, force):
        """Create default prompt templates"""
        default_templates = [
            {
                'name': 'Chat Assistant',
                'description': 'Template for general chat assistance',
                'task_type': 'chat',
                'template': 'User: $user_message\n\nPlease provide a helpful and accurate response.',
                'system_prompt': 'You are a helpful AI assistant. Provide clear, accurate, and helpful responses to user questions.',
                'variables': '["user_message"]',
                'default_parameters': '{"temperature": 0.7, "max_tokens": 1024}'
            },
            {
                'name': 'Code Generator',
                'description': 'Template for code generation tasks',
                'task_type': 'code_generation',
                'template': 'Programming Language: $language\nTask: $task\nRequirements: $requirements\n\nGenerate clean, efficient code with comments.',
                'system_prompt': 'You are an expert programmer. Generate high-quality, well-documented code that follows best practices.',
                'variables': '["language", "task", "requirements"]',
                'default_parameters': '{"temperature": 0.3, "max_tokens": 2048}'
            },
            {
                'name': 'Text Summarizer',
                'description': 'Template for text summarization',
                'task_type': 'summarization',
                'template': 'Please summarize the following text in $length style:\n\n$text\n\nSummary:',
                'system_prompt': 'You are an expert at creating concise, accurate summaries that capture the key points of any text.',
                'variables': '["text", "length"]',
                'default_parameters': '{"temperature": 0.5, "max_tokens": 512}'
            },
            {
                'name': 'Question Answerer',
                'description': 'Template for question answering',
                'task_type': 'question_answering',
                'template': 'Context: $context\n\nQuestion: $question\n\nBased on the provided context, please answer the question accurately and concisely.',
                'system_prompt': 'You are an expert at answering questions based on provided context. Only use information from the context to answer.',
                'variables': '["context", "question"]',
                'default_parameters': '{"temperature": 0.3, "max_tokens": 512}'
            },
            {
                'name': 'Creative Writer',
                'description': 'Template for creative writing tasks',
                'task_type': 'text_generation',
                'template': 'Genre: $genre\nTopic: $topic\nStyle: $style\nLength: $length\n\nWrite a creative piece based on the above specifications.',
                'system_prompt': 'You are a creative writer with expertise in various genres and styles. Create engaging, original content.',
                'variables': '["genre", "topic", "style", "length"]',
                'default_parameters': '{"temperature": 0.9, "max_tokens": 2048}'
            }
        ]
        
        created_templates = []
        
        for template_data in default_templates:
            template_name = template_data['name']
            
            # Check if template exists
            if OllamaPromptTemplate.objects.filter(name=template_name).exists():
                if not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Template "{template_name}" already exists. Use --force to recreate.'
                        )
                    )
                    created_templates.append(OllamaPromptTemplate.objects.get(name=template_name))
                    continue
                else:
                    OllamaPromptTemplate.objects.filter(name=template_name).delete()
                    self.stdout.write(
                        self.style.WARNING(f'Deleted existing template "{template_name}"')
                    )
            
            # Create new template
            template = OllamaPromptTemplate.objects.create(
                is_active=True,
                **template_data
            )
            
            created_templates.append(template)
            self.stdout.write(
                self.style.SUCCESS(f'Created template: {template.name}')
            )
        
        return created_templates
    
    def pull_recommended_models(self, config, models):
        """Pull recommended models from Ollama"""
        self.stdout.write('Pulling recommended models...')
        
        # Models to pull (start with smaller ones)
        recommended_models = [
            'llama2:7b-chat',
            'mistral:7b',
            'neural-chat:7b'
        ]
        
        try:
            client = OllamaClient(config.name)
            
            for model_name in recommended_models:
                self.stdout.write(f'Pulling {model_name}...')
                
                try:
                    success = client.pull_model(model_name)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Successfully pulled {model_name}')
                        )
                        
                        # Activate corresponding model configuration
                        model_configs = [m for m in models if m.model_name == model_name]
                        for model_config in model_configs:
                            model_config.is_active = True
                            model_config.save()
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Activated model configuration: {model_config.name}')
                            )
                    
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Failed to pull {model_name}')
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error pulling {model_name}: {str(e)}')
                    )
            
            client.close()
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during model pulling: {str(e)}')
            )
    
    def get_available_models(self, config):
        """Get list of available models from Ollama server"""
        try:
            client = OllamaClient(config.name)
            models = client.list_models()
            client.close()
            return models
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error getting available models: {str(e)}')
            )
            return []