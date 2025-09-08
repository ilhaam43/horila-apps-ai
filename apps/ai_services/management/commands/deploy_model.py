#!/usr/bin/env python3
"""
Django Management Command for AI Model Deployment
Allows deployment of trained models from command line
"""

import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ai_services.models import AIModelRegistry, ModelTrainingSession
from ai_services.deployment import deployment_manager


class Command(BaseCommand):
    help = 'Deploy trained AI models to production'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['deploy', 'list', 'undeploy', 'status', 'health'],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--training-session-id',
            type=str,
            help='Training session ID to deploy'
        )
        
        parser.add_argument(
            '--deployment-name',
            type=str,
            help='Custom deployment name'
        )
        
        parser.add_argument(
            '--model-name',
            type=str,
            help='Model name to filter by'
        )
        
        parser.add_argument(
            '--service-type',
            choices=['budget_prediction', 'knowledge_search', 'indonesian_nlp'],
            help='Service type to filter by'
        )
        
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action without confirmation'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'deploy':
                self.handle_deploy(options)
            elif action == 'list':
                self.handle_list(options)
            elif action == 'undeploy':
                self.handle_undeploy(options)
            elif action == 'status':
                self.handle_status(options)
            elif action == 'health':
                self.handle_health(options)
        except Exception as e:
            raise CommandError(f'Command failed: {e}')
    
    def handle_deploy(self, options):
        """Handle model deployment"""
        training_session_id = options.get('training_session_id')
        deployment_name = options.get('deployment_name')
        
        if not training_session_id:
            # Show available models for deployment
            self.stdout.write(self.style.WARNING('No training session ID provided.'))
            self.stdout.write('Available models for deployment:')
            self.show_available_models()
            return
        
        try:
            # Get training session info
            session = ModelTrainingSession.objects.get(id=training_session_id)
            
            self.stdout.write(f'Deploying model: {session.model.name}')
            self.stdout.write(f'Service type: {session.model.service_type}')
            self.stdout.write(f'Accuracy: {session.accuracy}')
            self.stdout.write(f'Training completed: {session.completed_at}')
            
            if not options['force']:
                confirm = input('\nProceed with deployment? (y/N): ')
                if confirm.lower() != 'y':
                    self.stdout.write('Deployment cancelled.')
                    return
            
            # Deploy the model
            result = deployment_manager.deploy_model(
                training_session_id=training_session_id,
                deployment_name=deployment_name
            )
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(f'Model deployed successfully: {result["deployment_name"]}')
                )
                self.stdout.write(f'Deployment path: {result["deployment_path"]}')
                
                # Show available endpoints
                endpoints = result.get('endpoints', [])
                if endpoints:
                    self.stdout.write('\nAvailable endpoints:')
                    for endpoint in endpoints:
                        self.stdout.write(f'  {endpoint["method"]} {endpoint["path"]} - {endpoint["description"]}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'Deployment failed: {result["error"]}')
                )
                
        except ModelTrainingSession.DoesNotExist:
            raise CommandError(f'Training session {training_session_id} not found')
    
    def handle_list(self, options):
        """Handle listing deployments"""
        deployments = deployment_manager.list_deployments()
        
        # Apply filters
        model_name = options.get('model_name')
        service_type = options.get('service_type')
        
        if model_name:
            deployments = [d for d in deployments if model_name.lower() in d['model_name'].lower()]
        
        if service_type:
            deployments = [d for d in deployments if d['service_type'] == service_type]
        
        if not deployments:
            self.stdout.write('No deployments found.')
            return
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(deployments, indent=2, default=str))
        else:
            self.show_deployments_table(deployments)
    
    def handle_undeploy(self, options):
        """Handle model undeployment"""
        deployment_name = options.get('deployment_name')
        
        if not deployment_name:
            # Show available deployments
            self.stdout.write(self.style.WARNING('No deployment name provided.'))
            self.stdout.write('Available deployments:')
            deployments = deployment_manager.list_deployments()
            for deployment in deployments:
                self.stdout.write(f'  - {deployment["name"]}')
            return
        
        if not options['force']:
            confirm = input(f'Are you sure you want to undeploy "{deployment_name}"? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Undeployment cancelled.')
                return
        
        result = deployment_manager.undeploy_model(deployment_name)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f'Model undeployed successfully: {deployment_name}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Undeployment failed: {result["error"]}')
            )
    
    def handle_status(self, options):
        """Handle deployment system status"""
        deployments = deployment_manager.list_deployments()
        healthy_count = sum(1 for d in deployments if d['is_healthy'])
        
        self.stdout.write('Deployment System Status:')
        self.stdout.write(f'  Total deployments: {len(deployments)}')
        self.stdout.write(f'  Healthy deployments: {healthy_count}')
        self.stdout.write(f'  Unhealthy deployments: {len(deployments) - healthy_count}')
        self.stdout.write(f'  Deployment directory: {deployment_manager.deployment_dir}')
        
        if options['format'] == 'json':
            status_data = {
                'total_deployments': len(deployments),
                'healthy_deployments': healthy_count,
                'unhealthy_deployments': len(deployments) - healthy_count,
                'deployment_directory': str(deployment_manager.deployment_dir),
                'deployments': deployments
            }
            self.stdout.write(json.dumps(status_data, indent=2, default=str))
    
    def handle_health(self, options):
        """Handle health check for deployments"""
        deployment_name = options.get('deployment_name')
        
        if deployment_name:
            # Check specific deployment
            self.check_deployment_health(deployment_name)
        else:
            # Check all deployments
            deployments = deployment_manager.list_deployments()
            for deployment in deployments:
                self.check_deployment_health(deployment['name'])
    
    def check_deployment_health(self, deployment_name):
        """Check health of a specific deployment"""
        import subprocess
        from pathlib import Path
        
        deployment_path = deployment_manager.deployment_dir / deployment_name
        health_script = deployment_path / 'health_check.py'
        
        if not health_script.exists():
            self.stdout.write(
                self.style.ERROR(f'Health check script not found for {deployment_name}')
            )
            return
        
        try:
            result = subprocess.run(
                ['python3', str(health_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                status = health_data.get('status', 'unknown')
                
                if status == 'healthy':
                    self.stdout.write(
                        self.style.SUCCESS(f'{deployment_name}: {status}')
                    )
                    if 'response_time_ms' in health_data:
                        self.stdout.write(f'  Response time: {health_data["response_time_ms"]}ms')
                else:
                    self.stdout.write(
                        self.style.ERROR(f'{deployment_name}: {status}')
                    )
                    if 'error' in health_data:
                        self.stdout.write(f'  Error: {health_data["error"]}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'{deployment_name}: unhealthy (exit code {result.returncode})')
                )
                if result.stderr:
                    self.stdout.write(f'  Error: {result.stderr}')
                    
        except subprocess.TimeoutExpired:
            self.stdout.write(
                self.style.ERROR(f'{deployment_name}: health check timeout')
            )
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR(f'{deployment_name}: invalid health check response')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'{deployment_name}: health check failed - {e}')
            )
    
    def show_available_models(self):
        """Show available models for deployment"""
        completed_sessions = ModelTrainingSession.objects.filter(
            status='completed'
        ).select_related('model').order_by('-completed_at')[:10]
        
        if not completed_sessions:
            self.stdout.write('No completed training sessions found.')
            return
        
        self.stdout.write('\nRecent completed training sessions:')
        self.stdout.write('-' * 80)
        self.stdout.write(f"{'ID':<36} {'Model Name':<20} {'Service Type':<15} {'Accuracy':<10} {'Completed'}")
        self.stdout.write('-' * 80)
        
        for session in completed_sessions:
            completed_str = session.completed_at.strftime('%Y-%m-%d %H:%M') if session.completed_at else 'N/A'
            accuracy_str = f'{session.accuracy:.3f}' if session.accuracy else 'N/A'
            
            self.stdout.write(
                f'{str(session.id):<36} {session.model.name:<20} {session.model.service_type:<15} {accuracy_str:<10} {completed_str}'
            )
    
    def show_deployments_table(self, deployments):
        """Show deployments in table format"""
        if not deployments:
            return
        
        self.stdout.write('\nDeployed Models:')
        self.stdout.write('-' * 100)
        self.stdout.write(f"{'Name':<25} {'Model':<20} {'Service Type':<15} {'Status':<10} {'Deployed At'}")
        self.stdout.write('-' * 100)
        
        for deployment in deployments:
            status = 'Healthy' if deployment['is_healthy'] else 'Unhealthy'
            deployed_at = deployment['deployed_at'][:16] if deployment['deployed_at'] else 'N/A'
            
            self.stdout.write(
                f'{deployment["name"]:<25} {deployment["model_name"]:<20} {deployment["service_type"]:<15} {status:<10} {deployed_at}'
            )