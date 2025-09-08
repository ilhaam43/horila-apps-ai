import os
import sys
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ...models import NLPConfiguration, NLPModel
from ...client import IndonesianNLPClient
from ...utils import IndonesianTextProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup Indonesian NLP module with default configuration and models'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force setup even if configuration already exists'
        )
        parser.add_argument(
            '--skip-models',
            action='store_true',
            help='Skip model setup and only create configuration'
        )
        parser.add_argument(
            '--models-path',
            type=str,
            default='/models/indonesian_nlp',
            help='Path to store NLP models (default: /models/indonesian_nlp)'
        )
        parser.add_argument(
            '--download-models',
            action='store_true',
            help='Download default models from Hugging Face'
        )
        parser.add_argument(
            '--test-setup',
            action='store_true',
            help='Test the setup after completion'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Indonesian NLP module setup...')
        )
        
        try:
            # Check if setup already exists
            if not options['force'] and self._check_existing_setup():
                self.stdout.write(
                    self.style.WARNING(
                        'Indonesian NLP module is already configured. '
                        'Use --force to override existing configuration.'
                    )
                )
                return
            
            # Create configuration
            self._create_configuration(options)
            
            # Setup models directory
            self._setup_models_directory(options['models_path'])
            
            # Setup models
            if not options['skip_models']:
                self._setup_models(options)
            
            # Download models if requested
            if options['download_models']:
                self._download_default_models(options)
            
            # Test setup if requested
            if options['test_setup']:
                self._test_setup()
            
            self.stdout.write(
                self.style.SUCCESS(
                    'Indonesian NLP module setup completed successfully!'
                )
            )
            
        except Exception as e:
            logger.error(f"Setup failed: {str(e)}")
            raise CommandError(f"Setup failed: {str(e)}")
    
    def _check_existing_setup(self):
        """Check if Indonesian NLP module is already configured"""
        return NLPConfiguration.objects.filter(is_active=True).exists()
    
    def _create_configuration(self, options):
        """Create default NLP configuration"""
        self.stdout.write('Creating NLP configuration...')
        
        with transaction.atomic():
            # Deactivate existing configurations
            NLPConfiguration.objects.filter(is_active=True).update(is_active=False)
            
            # Create new configuration
            config = NLPConfiguration.objects.create(
                name="Default Indonesian NLP Configuration",
                description="Default configuration for Indonesian NLP processing",
                is_active=True,
                max_concurrent_jobs=5,
                default_confidence_threshold=0.7,
                enable_caching=True,
                cache_timeout=3600,
                model_unload_timeout=1800,
                max_text_length=10000,
                enable_preprocessing=True,
                preprocessing_config={
                    'clean_text': True,
                    'normalize_slang': True,
                    'remove_stopwords': False,
                    'stem_text': False
                },
                cpu_limit=80.0,
                memory_limit=4096.0,
                enable_monitoring=True,
                log_level='INFO'
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Configuration created: {config.name}')
            )
    
    def _setup_models_directory(self, models_path):
        """Setup models directory structure"""
        self.stdout.write(f'Setting up models directory: {models_path}')
        
        try:
            # Create main models directory
            os.makedirs(models_path, exist_ok=True)
            
            # Create subdirectories for different model types
            subdirs = ['sentiment', 'ner', 'classification', 'embeddings', 'cache']
            for subdir in subdirs:
                subdir_path = os.path.join(models_path, subdir)
                os.makedirs(subdir_path, exist_ok=True)
                
                # Create .gitkeep file to preserve directory structure
                gitkeep_path = os.path.join(subdir_path, '.gitkeep')
                with open(gitkeep_path, 'w') as f:
                    f.write('')
            
            self.stdout.write(
                self.style.SUCCESS(f'Models directory structure created at {models_path}')
            )
            
        except Exception as e:
            raise CommandError(f"Failed to create models directory: {str(e)}")
    
    def _setup_models(self, options):
        """Setup default NLP models"""
        self.stdout.write('Setting up default NLP models...')
        
        models_path = options['models_path']
        
        # Default models configuration
        default_models = [
            {
                'name': 'indonesian-sentiment-base',
                'model_type': 'sentiment',
                'framework': 'transformers',
                'model_path': os.path.join(models_path, 'sentiment', 'base'),
                'huggingface_model': 'indobenchmark/indobert-base-p1',
                'description': 'Base Indonesian sentiment analysis model using IndoBERT',
                'config': {
                    'task': 'sentiment-analysis',
                    'return_all_scores': True,
                    'function_to_apply': 'softmax'
                }
            },
            {
                'name': 'indonesian-ner-base',
                'model_type': 'ner',
                'framework': 'transformers',
                'model_path': os.path.join(models_path, 'ner', 'base'),
                'huggingface_model': 'indobenchmark/indobert-base-p1',
                'description': 'Base Indonesian named entity recognition model',
                'config': {
                    'task': 'ner',
                    'aggregation_strategy': 'simple'
                }
            },
            {
                'name': 'indonesian-classification-base',
                'model_type': 'classification',
                'framework': 'transformers',
                'model_path': os.path.join(models_path, 'classification', 'base'),
                'huggingface_model': 'indobenchmark/indobert-base-p1',
                'description': 'Base Indonesian text classification model',
                'config': {
                    'task': 'text-classification',
                    'return_all_scores': True
                }
            }
        ]
        
        with transaction.atomic():
            for model_config in default_models:
                # Check if model already exists
                if NLPModel.objects.filter(name=model_config['name']).exists():
                    if not options['force']:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Model {model_config['name']} already exists, skipping..."
                            )
                        )
                        continue
                    else:
                        # Update existing model
                        model = NLPModel.objects.get(name=model_config['name'])
                        for key, value in model_config.items():
                            if key != 'name':
                                setattr(model, key, value)
                        model.save()
                        self.stdout.write(
                            self.style.SUCCESS(f"Updated model: {model_config['name']}")
                        )
                        continue
                
                # Create new model
                model = NLPModel.objects.create(
                    name=model_config['name'],
                    model_type=model_config['model_type'],
                    framework=model_config['framework'],
                    model_path=model_config['model_path'],
                    description=model_config['description'],
                    config=model_config['config'],
                    is_active=True,
                    is_default=True,
                    version='1.0.0',
                    created_at=timezone.now()
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created model: {model.name}")
                )
    
    def _download_default_models(self, options):
        """Download default models from Hugging Face"""
        self.stdout.write('Downloading default models from Hugging Face...')
        
        try:
            from transformers import AutoTokenizer, AutoModel
            
            # Models to download
            models_to_download = [
                'indobenchmark/indobert-base-p1',
                'cahya/bert-base-indonesian-522M',
                'indolem/indobert-base-uncased'
            ]
            
            for model_name in models_to_download:
                try:
                    self.stdout.write(f'Downloading {model_name}...')
                    
                    # Download tokenizer and model
                    tokenizer = AutoTokenizer.from_pretrained(model_name)
                    model = AutoModel.from_pretrained(model_name)
                    
                    # Save to local cache
                    cache_dir = os.path.join(options['models_path'], 'cache', model_name.replace('/', '_'))
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    tokenizer.save_pretrained(cache_dir)
                    model.save_pretrained(cache_dir)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"Downloaded and cached: {model_name}")
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Failed to download {model_name}: {str(e)}"
                        )
                    )
                    
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    'Transformers library not installed. Skipping model download.'
                )
            )
    
    def _test_setup(self):
        """Test the setup by running basic operations"""
        self.stdout.write('Testing Indonesian NLP setup...')
        
        try:
            # Test configuration
            config = NLPConfiguration.get_active_config()
            if not config:
                raise Exception("No active configuration found")
            
            self.stdout.write(
                self.style.SUCCESS(f"✓ Configuration test passed: {config.name}")
            )
            
            # Test text processor
            processor = IndonesianTextProcessor()
            test_text = "Saya sangat senang dengan layanan ini!"
            
            cleaned = processor.clean_text(test_text)
            normalized = processor.normalize_slang(cleaned)
            words = processor.tokenize_words(normalized)
            
            if not words:
                raise Exception("Text processing failed")
            
            self.stdout.write(
                self.style.SUCCESS("✓ Text processor test passed")
            )
            
            # Test client initialization
            client = IndonesianNLPClient()
            frameworks = client.get_available_frameworks()
            
            if not frameworks:
                self.stdout.write(
                    self.style.WARNING("⚠ No NLP frameworks available")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Client test passed. Available frameworks: {', '.join(frameworks)}"
                    )
                )
            
            # Test models
            models = NLPModel.objects.filter(is_active=True)
            if models.exists():
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Models test passed. {models.count()} active models found"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING("⚠ No active models found")
                )
            
            self.stdout.write(
                self.style.SUCCESS("All tests passed! Indonesian NLP module is ready.")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Setup test failed: {str(e)}")
            )
            raise CommandError(f"Setup test failed: {str(e)}")
    
    def _install_dependencies(self):
        """Install required Python dependencies"""
        self.stdout.write('Installing required dependencies...')
        
        dependencies = [
            'transformers>=4.20.0',
            'torch>=1.12.0',
            'nltk>=3.7',
            'Sastrawi>=1.0.1',
            'scikit-learn>=1.1.0',
            'numpy>=1.21.0',
            'pandas>=1.4.0'
        ]
        
        try:
            import subprocess
            
            for dep in dependencies:
                try:
                    self.stdout.write(f'Installing {dep}...')
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Installed: {dep}")
                    )
                except subprocess.CalledProcessError as e:
                    self.stdout.write(
                        self.style.WARNING(f"Failed to install {dep}: {str(e)}")
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Dependency installation failed: {str(e)}")
            )