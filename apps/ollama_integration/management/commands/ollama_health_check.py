from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Q
import json
import time
from datetime import timedelta
from tabulate import tabulate

from ollama_integration.models import (
    OllamaConfiguration,
    OllamaModel,
    OllamaProcessingJob,
    OllamaModelUsage
)
from ollama_integration.client import OllamaClient


class Command(BaseCommand):
    help = 'Perform health checks and monitoring for Ollama integration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['check', 'monitor', 'stats', 'cleanup', 'benchmark'],
            help='Action to perform'
        )
        parser.add_argument(
            '--config',
            type=str,
            help='Configuration name to check (default: all active configurations)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Monitoring interval in seconds (default: 30)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=300,
            help='Monitoring duration in seconds (default: 300)'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days for statistics (default: 7)'
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='Clean up jobs older than N days (default: 30)'
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Specific model for benchmark'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'check':
                self.health_check(options['config'], options['format'])
            elif action == 'monitor':
                self.monitor(options['config'], options['interval'], options['duration'])
            elif action == 'stats':
                self.show_statistics(options['config'], options['days'], options['format'])
            elif action == 'cleanup':
                self.cleanup_old_jobs(options['cleanup_days'])
            elif action == 'benchmark':
                self.benchmark_models(options['config'], options['model'])
        
        except KeyboardInterrupt:
            self.stdout.write('\nOperation cancelled by user')
        except Exception as e:
            raise CommandError(f'Failed to {action}: {str(e)}')
    
    def health_check(self, config_name, output_format):
        """Perform comprehensive health check"""
        self.stdout.write('Performing Ollama health check...')
        
        # Get configurations to check
        if config_name:
            try:
                configs = [OllamaConfiguration.objects.get(name=config_name)]
            except OllamaConfiguration.DoesNotExist:
                raise CommandError(f'Configuration "{config_name}" not found')
        else:
            configs = OllamaConfiguration.objects.filter(is_active=True)
        
        if not configs:
            self.stdout.write(self.style.WARNING('No active configurations found'))
            return
        
        results = []
        
        for config in configs:
            result = self.check_configuration(config)
            results.append(result)
        
        if output_format == 'json':
            self.stdout.write(json.dumps(results, indent=2, default=str))
        else:
            self.display_health_results(results)
    
    def check_configuration(self, config):
        """Check a single configuration"""
        result = {
            'configuration': config.name,
            'url': f'{"https" if config.use_ssl else "http"}://{config.host}:{config.port}',
            'status': 'unknown',
            'response_time': None,
            'models': [],
            'jobs': {},
            'errors': []
        }
        
        try:
            # Test connection and measure response time
            start_time = time.time()
            client = OllamaClient(config.name)
            is_healthy = client.health_check()
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            result['status'] = 'healthy' if is_healthy else 'unhealthy'
            result['response_time'] = round(response_time, 2)
            
            if is_healthy:
                # Check models
                try:
                    server_models = client.list_models()
                    db_models = OllamaModel.objects.filter(configuration=config)
                    
                    for db_model in db_models:
                        model_info = {
                            'name': db_model.name,
                            'model_name': db_model.model_name,
                            'is_active': db_model.is_active,
                            'available_on_server': any(
                                m.get('name') == db_model.model_name for m in server_models
                            ),
                            'last_used': None
                        }
                        
                        # Get last usage
                        last_job = OllamaProcessingJob.objects.filter(
                            configuration=config,
                            model=db_model,
                            status='completed'
                        ).order_by('-completed_at').first()
                        
                        if last_job:
                            model_info['last_used'] = last_job.completed_at
                        
                        result['models'].append(model_info)
                
                except Exception as e:
                    result['errors'].append(f'Error checking models: {str(e)}')
                
                # Check job statistics
                try:
                    now = timezone.now()
                    last_24h = now - timedelta(hours=24)
                    
                    result['jobs'] = {
                        'total': OllamaProcessingJob.objects.filter(configuration=config).count(),
                        'pending': OllamaProcessingJob.objects.filter(
                            configuration=config, status='pending'
                        ).count(),
                        'running': OllamaProcessingJob.objects.filter(
                            configuration=config, status='running'
                        ).count(),
                        'completed_24h': OllamaProcessingJob.objects.filter(
                            configuration=config,
                            status='completed',
                            completed_at__gte=last_24h
                        ).count(),
                        'failed_24h': OllamaProcessingJob.objects.filter(
                            configuration=config,
                            status='failed',
                            created_at__gte=last_24h
                        ).count()
                    }
                
                except Exception as e:
                    result['errors'].append(f'Error checking jobs: {str(e)}')
            
            client.close()
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f'Connection error: {str(e)}')
        
        return result
    
    def display_health_results(self, results):
        """Display health check results in table format"""
        # Configuration status table
        config_headers = ['Configuration', 'Status', 'Response Time (ms)', 'URL', 'Errors']
        config_rows = []
        
        for result in results:
            status_color = self.style.SUCCESS if result['status'] == 'healthy' else self.style.ERROR
            config_rows.append([
                result['configuration'],
                status_color(result['status']),
                result['response_time'] or 'N/A',
                result['url'],
                len(result['errors'])
            ])
        
        self.stdout.write('\n' + self.style.SUCCESS('Configuration Health:'))
        self.stdout.write(tabulate(config_rows, headers=config_headers, tablefmt='grid'))
        
        # Model status for each configuration
        for result in results:
            if result['models']:
                self.stdout.write(f'\n' + self.style.SUCCESS(f'Models for {result["configuration"]}:'))
                
                model_headers = ['Name', 'Model Name', 'Active', 'On Server', 'Last Used']
                model_rows = []
                
                for model in result['models']:
                    last_used = model['last_used'].strftime('%Y-%m-%d %H:%M') if model['last_used'] else 'Never'
                    model_rows.append([
                        model['name'],
                        model['model_name'],
                        '✓' if model['is_active'] else '✗',
                        '✓' if model['available_on_server'] else '✗',
                        last_used
                    ])
                
                self.stdout.write(tabulate(model_rows, headers=model_headers, tablefmt='grid'))
        
        # Job statistics
        for result in results:
            if result['jobs']:
                self.stdout.write(f'\n' + self.style.SUCCESS(f'Job Statistics for {result["configuration"]}:'))
                
                job_data = [
                    ['Total Jobs', result['jobs']['total']],
                    ['Pending Jobs', result['jobs']['pending']],
                    ['Running Jobs', result['jobs']['running']],
                    ['Completed (24h)', result['jobs']['completed_24h']],
                    ['Failed (24h)', result['jobs']['failed_24h']]
                ]
                
                self.stdout.write(tabulate(job_data, headers=['Metric', 'Count'], tablefmt='grid'))
        
        # Errors
        for result in results:
            if result['errors']:
                self.stdout.write(f'\n' + self.style.ERROR(f'Errors for {result["configuration"]}:'))
                for error in result['errors']:
                    self.stdout.write(f'  • {error}')
    
    def monitor(self, config_name, interval, duration):
        """Monitor Ollama services continuously"""
        self.stdout.write(f'Starting monitoring (interval: {interval}s, duration: {duration}s)...')
        
        # Get configurations to monitor
        if config_name:
            try:
                configs = [OllamaConfiguration.objects.get(name=config_name)]
            except OllamaConfiguration.DoesNotExist:
                raise CommandError(f'Configuration "{config_name}" not found')
        else:
            configs = OllamaConfiguration.objects.filter(is_active=True)
        
        if not configs:
            raise CommandError('No configurations to monitor')
        
        start_time = time.time()
        check_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                check_count += 1
                self.stdout.write(f'\n--- Check #{check_count} at {timezone.now().strftime("%H:%M:%S")} ---')
                
                for config in configs:
                    try:
                        client = OllamaClient(config.name)
                        start_check = time.time()
                        is_healthy = client.health_check()
                        response_time = (time.time() - start_check) * 1000
                        
                        status = '✓' if is_healthy else '✗'
                        color = self.style.SUCCESS if is_healthy else self.style.ERROR
                        
                        self.stdout.write(
                            f'{config.name}: {color(status)} ({response_time:.1f}ms)'
                        )
                        
                        client.close()
                    
                    except Exception as e:
                        self.stdout.write(
                            f'{config.name}: {self.style.ERROR("✗")} Error: {str(e)}'
                        )
                
                if (time.time() - start_time) < duration:
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            self.stdout.write('\nMonitoring stopped by user')
        
        self.stdout.write(f'\nMonitoring completed. Total checks: {check_count}')
    
    def show_statistics(self, config_name, days, output_format):
        """Show usage statistics"""
        self.stdout.write(f'Showing statistics for the last {days} days...')
        
        # Get configurations
        if config_name:
            try:
                configs = [OllamaConfiguration.objects.get(name=config_name)]
            except OllamaConfiguration.DoesNotExist:
                raise CommandError(f'Configuration "{config_name}" not found')
        else:
            configs = OllamaConfiguration.objects.filter(is_active=True)
        
        cutoff_date = timezone.now() - timedelta(days=days)
        stats = []
        
        for config in configs:
            config_stats = self.calculate_config_stats(config, cutoff_date)
            stats.append(config_stats)
        
        if output_format == 'json':
            self.stdout.write(json.dumps(stats, indent=2, default=str))
        else:
            self.display_statistics(stats)
    
    def calculate_config_stats(self, config, cutoff_date):
        """Calculate statistics for a configuration"""
        jobs = OllamaProcessingJob.objects.filter(
            configuration=config,
            created_at__gte=cutoff_date
        )
        
        completed_jobs = jobs.filter(status='completed')
        failed_jobs = jobs.filter(status='failed')
        
        # Calculate average processing time
        avg_processing_time = completed_jobs.aggregate(
            avg_time=Avg('processing_time')
        )['avg_time'] or 0
        
        # Model usage statistics
        model_stats = jobs.values('model__name').annotate(
            job_count=Count('id')
        ).order_by('-job_count')
        
        # Task type statistics
        task_stats = jobs.values('task_type').annotate(
            job_count=Count('id')
        ).order_by('-job_count')
        
        return {
            'configuration': config.name,
            'total_jobs': jobs.count(),
            'completed_jobs': completed_jobs.count(),
            'failed_jobs': failed_jobs.count(),
            'success_rate': (completed_jobs.count() / jobs.count() * 100) if jobs.count() > 0 else 0,
            'avg_processing_time': round(avg_processing_time, 2) if avg_processing_time else 0,
            'model_usage': list(model_stats),
            'task_usage': list(task_stats)
        }
    
    def display_statistics(self, stats):
        """Display statistics in table format"""
        # Overall statistics
        headers = ['Configuration', 'Total Jobs', 'Completed', 'Failed', 'Success Rate', 'Avg Time (s)']
        rows = []
        
        for stat in stats:
            rows.append([
                stat['configuration'],
                stat['total_jobs'],
                stat['completed_jobs'],
                stat['failed_jobs'],
                f"{stat['success_rate']:.1f}%",
                stat['avg_processing_time']
            ])
        
        self.stdout.write('\n' + self.style.SUCCESS('Overall Statistics:'))
        self.stdout.write(tabulate(rows, headers=headers, tablefmt='grid'))
        
        # Model usage for each configuration
        for stat in stats:
            if stat['model_usage']:
                self.stdout.write(f'\n' + self.style.SUCCESS(f'Model Usage for {stat["configuration"]}:'))
                
                model_rows = []
                for model in stat['model_usage'][:10]:  # Top 10 models
                    model_rows.append([
                        model['model__name'] or 'Unknown',
                        model['job_count']
                    ])
                
                self.stdout.write(tabulate(
                    model_rows,
                    headers=['Model', 'Jobs'],
                    tablefmt='grid'
                ))
    
    def cleanup_old_jobs(self, days):
        """Clean up old processing jobs"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'Cleaning up jobs older than {days} days ({cutoff_date})...')
        
        # Count jobs to be deleted
        old_jobs = OllamaProcessingJob.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed', 'cancelled']
        )
        
        job_count = old_jobs.count()
        
        if job_count == 0:
            self.stdout.write('No old jobs to clean up')
            return
        
        self.stdout.write(f'Found {job_count} old jobs to delete')
        
        # Confirm deletion
        confirm = input(f'Are you sure you want to delete {job_count} old jobs? [y/N]: ')
        if confirm.lower() != 'y':
            self.stdout.write('Cleanup cancelled')
            return
        
        # Delete jobs
        deleted_count, _ = old_jobs.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_count} old jobs')
        )
    
    def benchmark_models(self, config_name, model_name):
        """Benchmark model performance"""
        self.stdout.write('Running model benchmarks...')
        
        # Get configuration
        if config_name:
            try:
                config = OllamaConfiguration.objects.get(name=config_name)
            except OllamaConfiguration.DoesNotExist:
                raise CommandError(f'Configuration "{config_name}" not found')
        else:
            config = OllamaConfiguration.objects.filter(is_active=True).first()
            if not config:
                raise CommandError('No active configuration found')
        
        # Get models to benchmark
        if model_name:
            models = OllamaModel.objects.filter(
                configuration=config,
                model_name=model_name,
                is_active=True
            )
        else:
            models = OllamaModel.objects.filter(
                configuration=config,
                is_active=True
            )[:5]  # Limit to 5 models
        
        if not models:
            raise CommandError('No models found for benchmarking')
        
        # Benchmark prompts
        test_prompts = [
            "Hello, how are you?",
            "Explain quantum computing in simple terms.",
            "Write a short poem about technology.",
            "What is the capital of France?",
            "Solve this math problem: 15 * 23 + 7"
        ]
        
        results = []
        
        try:
            client = OllamaClient(config.name)
            
            for model in models:
                self.stdout.write(f'Benchmarking {model.name}...')
                
                model_results = {
                    'model': model.name,
                    'model_name': model.model_name,
                    'tests': []
                }
                
                for i, prompt in enumerate(test_prompts, 1):
                    self.stdout.write(f'  Test {i}/{len(test_prompts)}')
                    
                    try:
                        start_time = time.time()
                        response = client.generate(
                            model=model.model_name,
                            prompt=prompt,
                            max_tokens=100,
                            temperature=0.7
                        )
                        end_time = time.time()
                        
                        if response and response.get('response'):
                            model_results['tests'].append({
                                'prompt': prompt,
                                'response_time': round((end_time - start_time) * 1000, 2),
                                'response_length': len(response['response']),
                                'success': True
                            })
                        else:
                            model_results['tests'].append({
                                'prompt': prompt,
                                'response_time': None,
                                'response_length': 0,
                                'success': False
                            })
                    
                    except Exception as e:
                        model_results['tests'].append({
                            'prompt': prompt,
                            'response_time': None,
                            'response_length': 0,
                            'success': False,
                            'error': str(e)
                        })
                
                results.append(model_results)
            
            client.close()
        
        except Exception as e:
            raise CommandError(f'Benchmark failed: {str(e)}')
        
        # Display results
        self.display_benchmark_results(results)
    
    def display_benchmark_results(self, results):
        """Display benchmark results"""
        self.stdout.write('\n' + self.style.SUCCESS('Benchmark Results:'))
        
        # Summary table
        headers = ['Model', 'Avg Response Time (ms)', 'Success Rate', 'Avg Response Length']
        rows = []
        
        for result in results:
            successful_tests = [t for t in result['tests'] if t['success']]
            
            if successful_tests:
                avg_time = sum(t['response_time'] for t in successful_tests) / len(successful_tests)
                avg_length = sum(t['response_length'] for t in successful_tests) / len(successful_tests)
            else:
                avg_time = 0
                avg_length = 0
            
            success_rate = len(successful_tests) / len(result['tests']) * 100
            
            rows.append([
                result['model'],
                round(avg_time, 2),
                f"{success_rate:.1f}%",
                round(avg_length, 1)
            ])
        
        self.stdout.write(tabulate(rows, headers=headers, tablefmt='grid'))
        
        # Detailed results
        for result in results:
            self.stdout.write(f'\n' + self.style.SUCCESS(f'Detailed Results for {result["model"]}:'))
            
            detail_headers = ['Test', 'Response Time (ms)', 'Length', 'Status']
            detail_rows = []
            
            for i, test in enumerate(result['tests'], 1):
                status = '✓' if test['success'] else '✗'
                detail_rows.append([
                    f'Test {i}',
                    test['response_time'] or 'N/A',
                    test['response_length'],
                    status
                ])
            
            self.stdout.write(tabulate(detail_rows, headers=detail_headers, tablefmt='grid'))