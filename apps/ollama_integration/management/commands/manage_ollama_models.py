from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import json
import logging
from tabulate import tabulate

from ollama_integration.models import (
    OllamaConfiguration,
    OllamaModel,
    OllamaProcessingJob
)
from ollama_integration.client import OllamaClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage Ollama models (list, pull, remove, test)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'pull', 'remove', 'test', 'status', 'sync'],
            help='Action to perform'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Model name for pull/remove/test actions'
        )
        parser.add_argument(
            '--config',
            type=str,
            default='default',
            help='Configuration name to use (default: default)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Apply action to all models'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action without confirmation'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format for list action'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        try:
            # Get configuration
            config = self.get_configuration(options['config'])
            
            # Execute action
            if action == 'list':
                self.list_models(config, options['format'])
            elif action == 'pull':
                self.pull_model(config, options['model'], options['force'])
            elif action == 'remove':
                self.remove_model(config, options['model'], options['all'], options['force'])
            elif action == 'test':
                self.test_model(config, options['model'], options['all'])
            elif action == 'status':
                self.show_status(config)
            elif action == 'sync':
                self.sync_models(config)
        
        except Exception as e:
            raise CommandError(f'Failed to {action} models: {str(e)}')
    
    def get_configuration(self, config_name):
        """Get Ollama configuration"""
        try:
            config = OllamaConfiguration.objects.get(name=config_name)
            if not config.is_active:
                self.stdout.write(
                    self.style.WARNING(f'Configuration "{config_name}" is not active')
                )
            return config
        except OllamaConfiguration.DoesNotExist:
            raise CommandError(f'Configuration "{config_name}" not found')
    
    def list_models(self, config, output_format):
        """List available models"""
        self.stdout.write(f'Listing models for configuration: {config.name}')
        
        try:
            client = OllamaClient(config.name)
            
            # Get models from Ollama server
            server_models = client.list_models()
            
            # Get models from database
            db_models = OllamaModel.objects.filter(configuration=config)
            
            client.close()
            
            if output_format == 'json':
                self.output_json(server_models, db_models)
            elif output_format == 'csv':
                self.output_csv(server_models, db_models)
            else:
                self.output_table(server_models, db_models)
        
        except Exception as e:
            raise CommandError(f'Failed to list models: {str(e)}')
    
    def output_table(self, server_models, db_models):
        """Output models in table format"""
        # Server models
        if server_models:
            self.stdout.write('\n' + self.style.SUCCESS('Models on Ollama Server:'))
            
            headers = ['Name', 'Size', 'Modified', 'Digest']
            rows = []
            
            for model in server_models:
                rows.append([
                    model.get('name', 'N/A'),
                    self.format_size(model.get('size', 0)),
                    model.get('modified_at', 'N/A'),
                    model.get('digest', 'N/A')[:12] + '...' if model.get('digest') else 'N/A'
                ])
            
            self.stdout.write(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            self.stdout.write(self.style.WARNING('No models found on Ollama server'))
        
        # Database models
        if db_models.exists():
            self.stdout.write('\n' + self.style.SUCCESS('Model Configurations in Database:'))
            
            headers = ['Name', 'Model Name', 'Task Type', 'Priority', 'Active', 'Created']
            rows = []
            
            for model in db_models:
                rows.append([
                    model.name,
                    model.model_name,
                    model.task_type,
                    model.priority,
                    '✓' if model.is_active else '✗',
                    model.created_at.strftime('%Y-%m-%d %H:%M')
                ])
            
            self.stdout.write(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            self.stdout.write(self.style.WARNING('No model configurations found in database'))
    
    def output_json(self, server_models, db_models):
        """Output models in JSON format"""
        data = {
            'server_models': server_models,
            'database_models': [
                {
                    'id': model.id,
                    'name': model.name,
                    'model_name': model.model_name,
                    'task_type': model.task_type,
                    'priority': model.priority,
                    'is_active': model.is_active,
                    'created_at': model.created_at.isoformat()
                }
                for model in db_models
            ]
        }
        
        self.stdout.write(json.dumps(data, indent=2))
    
    def output_csv(self, server_models, db_models):
        """Output models in CSV format"""
        import csv
        import io
        
        # Server models CSV
        if server_models:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Type', 'Name', 'Size', 'Modified', 'Digest'])
            
            for model in server_models:
                writer.writerow([
                    'server',
                    model.get('name', 'N/A'),
                    model.get('size', 0),
                    model.get('modified_at', 'N/A'),
                    model.get('digest', 'N/A')
                ])
            
            # Database models CSV
            for model in db_models:
                writer.writerow([
                    'database',
                    model.name,
                    model.model_name,
                    model.task_type,
                    model.priority,
                    model.is_active
                ])
            
            self.stdout.write(output.getvalue())
    
    def pull_model(self, config, model_name, force):
        """Pull a model from Ollama"""
        if not model_name:
            raise CommandError('Model name is required for pull action')
        
        self.stdout.write(f'Pulling model: {model_name}')
        
        if not force:
            confirm = input(f'Are you sure you want to pull "{model_name}"? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('Pull cancelled')
                return
        
        try:
            client = OllamaClient(config.name)
            
            # Check if model already exists
            existing_models = client.list_models()
            model_exists = any(m.get('name') == model_name for m in existing_models)
            
            if model_exists and not force:
                self.stdout.write(
                    self.style.WARNING(f'Model "{model_name}" already exists. Use --force to re-pull.')
                )
                client.close()
                return
            
            # Pull model
            self.stdout.write(f'Pulling {model_name}... (this may take a while)')
            success = client.pull_model(model_name)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully pulled {model_name}')
                )
                
                # Activate corresponding database model if exists
                try:
                    db_model = OllamaModel.objects.get(
                        configuration=config,
                        model_name=model_name
                    )
                    db_model.is_active = True
                    db_model.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Activated database model: {db_model.name}')
                    )
                except OllamaModel.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f'No database configuration found for {model_name}. '
                            'Consider creating one for better management.'
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to pull {model_name}')
                )
            
            client.close()
        
        except Exception as e:
            raise CommandError(f'Error pulling model: {str(e)}')
    
    def remove_model(self, config, model_name, remove_all, force):
        """Remove a model from Ollama"""
        if not model_name and not remove_all:
            raise CommandError('Model name is required for remove action (or use --all)')
        
        try:
            client = OllamaClient(config.name)
            models_to_remove = []
            
            if remove_all:
                server_models = client.list_models()
                models_to_remove = [m.get('name') for m in server_models]
            else:
                models_to_remove = [model_name]
            
            if not models_to_remove:
                self.stdout.write('No models to remove')
                client.close()
                return
            
            self.stdout.write(f'Models to remove: {", ".join(models_to_remove)}')
            
            if not force:
                confirm = input('Are you sure you want to remove these models? [y/N]: ')
                if confirm.lower() != 'y':
                    self.stdout.write('Remove cancelled')
                    client.close()
                    return
            
            for model in models_to_remove:
                try:
                    success = client.remove_model(model)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Removed {model}')
                        )
                        
                        # Deactivate corresponding database model
                        try:
                            db_model = OllamaModel.objects.get(
                                configuration=config,
                                model_name=model
                            )
                            db_model.is_active = False
                            db_model.save()
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ Deactivated database model: {db_model.name}')
                            )
                        except OllamaModel.DoesNotExist:
                            pass
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'✗ Failed to remove {model}')
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error removing {model}: {str(e)}')
                    )
            
            client.close()
        
        except Exception as e:
            raise CommandError(f'Error removing models: {str(e)}')
    
    def test_model(self, config, model_name, test_all):
        """Test a model"""
        try:
            client = OllamaClient(config.name)
            models_to_test = []
            
            if test_all:
                server_models = client.list_models()
                models_to_test = [m.get('name') for m in server_models]
            elif model_name:
                models_to_test = [model_name]
            else:
                raise CommandError('Model name is required for test action (or use --all)')
            
            if not models_to_test:
                self.stdout.write('No models to test')
                client.close()
                return
            
            test_prompt = "Hello, this is a test. Please respond with a brief greeting."
            
            for model in models_to_test:
                self.stdout.write(f'Testing {model}...')
                
                try:
                    response = client.generate(
                        model=model,
                        prompt=test_prompt,
                        max_tokens=50,
                        temperature=0.7
                    )
                    
                    if response and response.get('response'):
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {model} - Response: {response["response"][:100]}...')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'✗ {model} - No response received')
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ {model} - Error: {str(e)}')
                    )
            
            client.close()
        
        except Exception as e:
            raise CommandError(f'Error testing models: {str(e)}')
    
    def show_status(self, config):
        """Show overall status"""
        self.stdout.write(f'Status for configuration: {config.name}')
        
        try:
            client = OllamaClient(config.name)
            
            # Health check
            is_healthy = client.health_check()
            health_status = '✓ Healthy' if is_healthy else '✗ Unhealthy'
            
            # Model counts
            server_models = client.list_models() if is_healthy else []
            db_models = OllamaModel.objects.filter(configuration=config)
            active_models = db_models.filter(is_active=True)
            
            # Job statistics
            total_jobs = OllamaProcessingJob.objects.filter(configuration=config).count()
            pending_jobs = OllamaProcessingJob.objects.filter(
                configuration=config,
                status='pending'
            ).count()
            running_jobs = OllamaProcessingJob.objects.filter(
                configuration=config,
                status='running'
            ).count()
            
            client.close()
            
            # Display status
            status_data = [
                ['Configuration', config.name],
                ['Server Health', health_status],
                ['Server URL', f'{"https" if config.use_ssl else "http"}://{config.host}:{config.port}'],
                ['Models on Server', len(server_models)],
                ['Database Models', db_models.count()],
                ['Active Models', active_models.count()],
                ['Total Jobs', total_jobs],
                ['Pending Jobs', pending_jobs],
                ['Running Jobs', running_jobs]
            ]
            
            self.stdout.write(tabulate(status_data, headers=['Metric', 'Value'], tablefmt='grid'))
        
        except Exception as e:
            raise CommandError(f'Error getting status: {str(e)}')
    
    def sync_models(self, config):
        """Sync database models with server models"""
        self.stdout.write(f'Syncing models for configuration: {config.name}')
        
        try:
            client = OllamaClient(config.name)
            server_models = client.list_models()
            db_models = OllamaModel.objects.filter(configuration=config)
            
            server_model_names = {m.get('name') for m in server_models}
            db_model_names = {m.model_name for m in db_models}
            
            # Activate models that exist on server
            activated = 0
            for db_model in db_models:
                if db_model.model_name in server_model_names and not db_model.is_active:
                    db_model.is_active = True
                    db_model.save()
                    activated += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Activated: {db_model.name}')
                    )
            
            # Deactivate models that don't exist on server
            deactivated = 0
            for db_model in db_models:
                if db_model.model_name not in server_model_names and db_model.is_active:
                    db_model.is_active = False
                    db_model.save()
                    deactivated += 1
                    self.stdout.write(
                        self.style.WARNING(f'✗ Deactivated: {db_model.name}')
                    )
            
            # Report missing configurations
            missing_configs = server_model_names - db_model_names
            if missing_configs:
                self.stdout.write(
                    self.style.WARNING(
                        f'Models on server without database configuration: {", ".join(missing_configs)}'
                    )
                )
            
            client.close()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sync completed: {activated} activated, {deactivated} deactivated'
                )
            )
        
        except Exception as e:
            raise CommandError(f'Error syncing models: {str(e)}')
    
    def format_size(self, size_bytes):
        """Format size in human readable format"""
        if size_bytes == 0:
            return '0 B'
        
        size_names = ['B', 'KB', 'MB', 'GB', 'TB']
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f'{s} {size_names[i]}'