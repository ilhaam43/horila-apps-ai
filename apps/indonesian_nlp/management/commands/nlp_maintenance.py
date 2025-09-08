import os
import sys
import json
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Avg, Sum

from ...models import (
    NLPConfiguration, NLPModel, TextAnalysisJob,
    SentimentAnalysisResult, NamedEntityResult,
    TextClassificationResult, ModelUsageStatistics
)
from ...client import IndonesianNLPClient
from ...utils import ModelPerformanceTracker, CacheManager
from ...tasks import cleanup_old_jobs, health_check_models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Maintenance and monitoring tools for Indonesian NLP module'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Status command
        status_parser = subparsers.add_parser('status', help='Show system status')
        status_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status information'
        )
        
        # Cleanup command
        cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old data')
        cleanup_parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete jobs older than N days (default: 30)'
        )
        cleanup_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        
        # Health check command
        health_parser = subparsers.add_parser('health', help='Run health checks')
        health_parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix detected issues'
        )
        
        # Statistics command
        stats_parser = subparsers.add_parser('stats', help='Show usage statistics')
        stats_parser.add_argument(
            '--period',
            choices=['day', 'week', 'month', 'year'],
            default='week',
            help='Statistics period (default: week)'
        )
        stats_parser.add_argument(
            '--export',
            type=str,
            help='Export statistics to JSON file'
        )
        
        # Cache management
        cache_parser = subparsers.add_parser('cache', help='Manage cache')
        cache_parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all cache'
        )
        cache_parser.add_argument(
            '--size',
            action='store_true',
            help='Show cache size information'
        )
        
        # Model management
        model_parser = subparsers.add_parser('models', help='Manage models')
        model_parser.add_argument(
            '--list',
            action='store_true',
            help='List all models'
        )
        model_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate model files'
        )
        model_parser.add_argument(
            '--optimize',
            action='store_true',
            help='Optimize model performance'
        )
        
        # Configuration management
        config_parser = subparsers.add_parser('config', help='Manage configuration')
        config_parser.add_argument(
            '--show',
            action='store_true',
            help='Show current configuration'
        )
        config_parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate configuration'
        )
        config_parser.add_argument(
            '--backup',
            type=str,
            help='Backup configuration to file'
        )
        config_parser.add_argument(
            '--restore',
            type=str,
            help='Restore configuration from file'
        )
    
    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'nlp_maintenance')
            return
        
        try:
            if action == 'status':
                self._show_status(options)
            elif action == 'cleanup':
                self._cleanup_data(options)
            elif action == 'health':
                self._health_check(options)
            elif action == 'stats':
                self._show_statistics(options)
            elif action == 'cache':
                self._manage_cache(options)
            elif action == 'models':
                self._manage_models(options)
            elif action == 'config':
                self._manage_config(options)
            else:
                raise CommandError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.error(f"Maintenance command failed: {str(e)}")
            raise CommandError(f"Command failed: {str(e)}")
    
    def _show_status(self, options):
        """Show system status"""
        self.stdout.write(self.style.SUCCESS('Indonesian NLP Module Status'))
        self.stdout.write('=' * 50)
        
        # Configuration status
        config = NLPConfiguration.get_active_config()
        if config:
            self.stdout.write(f"Configuration: {config.name} (Active)")
            self.stdout.write(f"Max Concurrent Jobs: {config.max_concurrent_jobs}")
            self.stdout.write(f"Cache Enabled: {config.enable_caching}")
        else:
            self.stdout.write(self.style.ERROR("No active configuration found"))
        
        # Models status
        active_models = NLPModel.objects.filter(is_active=True)
        self.stdout.write(f"\nActive Models: {active_models.count()}")
        
        for model in active_models:
            status = "Loaded" if model.is_loaded else "Not Loaded"
            self.stdout.write(f"  - {model.name} ({model.model_type}): {status}")
        
        # Jobs status
        total_jobs = TextAnalysisJob.objects.count()
        pending_jobs = TextAnalysisJob.objects.filter(status='pending').count()
        running_jobs = TextAnalysisJob.objects.filter(status='running').count()
        completed_jobs = TextAnalysisJob.objects.filter(status='completed').count()
        failed_jobs = TextAnalysisJob.objects.filter(status='failed').count()
        
        self.stdout.write(f"\nJobs Status:")
        self.stdout.write(f"  Total: {total_jobs}")
        self.stdout.write(f"  Pending: {pending_jobs}")
        self.stdout.write(f"  Running: {running_jobs}")
        self.stdout.write(f"  Completed: {completed_jobs}")
        self.stdout.write(f"  Failed: {failed_jobs}")
        
        if options['detailed']:
            self._show_detailed_status()
    
    def _show_detailed_status(self):
        """Show detailed system status"""
        self.stdout.write("\nDetailed Status:")
        self.stdout.write('-' * 30)
        
        # Recent activity
        recent_jobs = TextAnalysisJob.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        self.stdout.write(f"Jobs in last 24h: {recent_jobs}")
        
        # Performance metrics
        avg_processing_time = TextAnalysisJob.objects.filter(
            status='completed',
            processing_time__isnull=False
        ).aggregate(avg_time=Avg('processing_time'))['avg_time']
        
        if avg_processing_time:
            self.stdout.write(f"Avg Processing Time: {avg_processing_time:.2f}s")
        
        # Error rate
        total_completed = TextAnalysisJob.objects.filter(
            status__in=['completed', 'failed']
        ).count()
        
        if total_completed > 0:
            error_rate = (failed_jobs / total_completed) * 100
            self.stdout.write(f"Error Rate: {error_rate:.2f}%")
        
        # Memory usage (if available)
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            self.stdout.write(f"Memory Usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        except ImportError:
            pass
    
    def _cleanup_data(self, options):
        """Cleanup old data"""
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f"Cleaning up data older than {days} days...")
        
        # Find old jobs
        old_jobs = TextAnalysisJob.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed']
        )
        
        job_count = old_jobs.count()
        
        if dry_run:
            self.stdout.write(f"Would delete {job_count} old jobs")
            
            # Show breakdown by status
            for status in ['completed', 'failed']:
                count = old_jobs.filter(status=status).count()
                self.stdout.write(f"  {status}: {count} jobs")
        else:
            if job_count > 0:
                with transaction.atomic():
                    # Delete related results first
                    SentimentAnalysisResult.objects.filter(
                        job__in=old_jobs
                    ).delete()
                    
                    NamedEntityResult.objects.filter(
                        job__in=old_jobs
                    ).delete()
                    
                    TextClassificationResult.objects.filter(
                        job__in=old_jobs
                    ).delete()
                    
                    # Delete jobs
                    deleted_count = old_jobs.delete()[0]
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"Deleted {deleted_count} old jobs")
                    )
            else:
                self.stdout.write("No old jobs to delete")
        
        # Cleanup old statistics
        old_stats = ModelUsageStatistics.objects.filter(
            date__lt=cutoff_date.date()
        )
        
        stats_count = old_stats.count()
        
        if dry_run:
            self.stdout.write(f"Would delete {stats_count} old statistics records")
        else:
            if stats_count > 0:
                deleted_stats = old_stats.delete()[0]
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {deleted_stats} old statistics")
                )
    
    def _health_check(self, options):
        """Run health checks"""
        self.stdout.write("Running health checks...")
        
        issues = []
        
        # Check configuration
        config = NLPConfiguration.get_active_config()
        if not config:
            issues.append("No active configuration found")
        
        # Check models
        active_models = NLPModel.objects.filter(is_active=True)
        if not active_models.exists():
            issues.append("No active models found")
        
        # Check model files
        for model in active_models:
            if not os.path.exists(model.model_path):
                issues.append(f"Model file not found: {model.model_path}")
        
        # Check for stuck jobs
        stuck_jobs = TextAnalysisJob.objects.filter(
            status='running',
            created_at__lt=timezone.now() - timedelta(hours=1)
        )
        
        if stuck_jobs.exists():
            issues.append(f"{stuck_jobs.count()} jobs appear to be stuck")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_percent = (free / total) * 100
            
            if free_percent < 10:
                issues.append(f"Low disk space: {free_percent:.1f}% free")
        except Exception:
            pass
        
        # Report results
        if issues:
            self.stdout.write(self.style.ERROR(f"Found {len(issues)} issues:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
            
            if options['fix']:
                self._fix_issues(issues)
        else:
            self.stdout.write(self.style.SUCCESS("All health checks passed"))
    
    def _fix_issues(self, issues):
        """Attempt to fix detected issues"""
        self.stdout.write("Attempting to fix issues...")
        
        # Fix stuck jobs
        stuck_jobs = TextAnalysisJob.objects.filter(
            status='running',
            created_at__lt=timezone.now() - timedelta(hours=1)
        )
        
        if stuck_jobs.exists():
            stuck_jobs.update(
                status='failed',
                error_message='Job timed out during health check',
                completed_at=timezone.now()
            )
            self.stdout.write(
                self.style.SUCCESS(f"Reset {stuck_jobs.count()} stuck jobs")
            )
    
    def _show_statistics(self, options):
        """Show usage statistics"""
        period = options['period']
        export_file = options.get('export')
        
        # Calculate date range
        now = timezone.now()
        if period == 'day':
            start_date = now - timedelta(days=1)
        elif period == 'week':
            start_date = now - timedelta(weeks=1)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:  # year
            start_date = now - timedelta(days=365)
        
        self.stdout.write(f"Statistics for the last {period}:")
        self.stdout.write('=' * 40)
        
        # Job statistics
        jobs_in_period = TextAnalysisJob.objects.filter(
            created_at__gte=start_date
        )
        
        total_jobs = jobs_in_period.count()
        completed_jobs = jobs_in_period.filter(status='completed').count()
        failed_jobs = jobs_in_period.filter(status='failed').count()
        
        self.stdout.write(f"Total Jobs: {total_jobs}")
        self.stdout.write(f"Completed: {completed_jobs}")
        self.stdout.write(f"Failed: {failed_jobs}")
        
        if total_jobs > 0:
            success_rate = (completed_jobs / total_jobs) * 100
            self.stdout.write(f"Success Rate: {success_rate:.2f}%")
        
        # Model usage
        model_usage = jobs_in_period.values('model__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        if model_usage:
            self.stdout.write("\nModel Usage:")
            for usage in model_usage:
                model_name = usage['model__name'] or 'Unknown'
                self.stdout.write(f"  {model_name}: {usage['count']} jobs")
        
        # Analysis type breakdown
        analysis_types = jobs_in_period.values('analysis_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        if analysis_types:
            self.stdout.write("\nAnalysis Types:")
            for analysis in analysis_types:
                self.stdout.write(
                    f"  {analysis['analysis_type']}: {analysis['count']} jobs"
                )
        
        # Export statistics if requested
        if export_file:
            stats_data = {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': now.isoformat(),
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': success_rate if total_jobs > 0 else 0,
                'model_usage': list(model_usage),
                'analysis_types': list(analysis_types)
            }
            
            with open(export_file, 'w') as f:
                json.dump(stats_data, f, indent=2, default=str)
            
            self.stdout.write(
                self.style.SUCCESS(f"Statistics exported to {export_file}")
            )
    
    def _manage_cache(self, options):
        """Manage cache"""
        cache_manager = CacheManager()
        
        if options.get('clear'):
            cache_manager.clear_all()
            self.stdout.write(self.style.SUCCESS("Cache cleared"))
        
        if options.get('size'):
            # This would require implementing cache size calculation
            self.stdout.write("Cache size information not implemented yet")
    
    def _manage_models(self, options):
        """Manage models"""
        if options.get('list'):
            models = NLPModel.objects.all()
            
            self.stdout.write("Available Models:")
            self.stdout.write('=' * 40)
            
            for model in models:
                status = "Active" if model.is_active else "Inactive"
                loaded = "Loaded" if model.is_loaded else "Not Loaded"
                
                self.stdout.write(
                    f"{model.name} ({model.model_type}) - {status}, {loaded}"
                )
                self.stdout.write(f"  Path: {model.model_path}")
                self.stdout.write(f"  Version: {model.version}")
                self.stdout.write("")
        
        if options.get('validate'):
            self._validate_models()
        
        if options.get('optimize'):
            self._optimize_models()
    
    def _validate_models(self):
        """Validate model files and configuration"""
        self.stdout.write("Validating models...")
        
        models = NLPModel.objects.filter(is_active=True)
        
        for model in models:
            # Check if model file exists
            if not os.path.exists(model.model_path):
                self.stdout.write(
                    self.style.ERROR(f"Model file not found: {model.model_path}")
                )
                continue
            
            # Check model configuration
            try:
                if model.config:
                    # Validate JSON configuration
                    json.loads(json.dumps(model.config))
                
                self.stdout.write(
                    self.style.SUCCESS(f"✓ {model.name} validation passed")
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ {model.name} validation failed: {str(e)}")
                )
    
    def _optimize_models(self):
        """Optimize model performance"""
        self.stdout.write("Optimizing models...")
        
        # This could include:
        # - Model quantization
        # - Cache optimization
        # - Memory management
        
        self.stdout.write("Model optimization not implemented yet")
    
    def _manage_config(self, options):
        """Manage configuration"""
        if options.get('show'):
            config = NLPConfiguration.get_active_config()
            if config:
                self.stdout.write(f"Active Configuration: {config.name}")
                self.stdout.write(f"Description: {config.description}")
                self.stdout.write(f"Max Concurrent Jobs: {config.max_concurrent_jobs}")
                self.stdout.write(f"Cache Enabled: {config.enable_caching}")
                self.stdout.write(f"CPU Limit: {config.cpu_limit}%")
                self.stdout.write(f"Memory Limit: {config.memory_limit} MB")
            else:
                self.stdout.write(self.style.ERROR("No active configuration found"))
        
        if options.get('backup'):
            self._backup_config(options['backup'])
        
        if options.get('restore'):
            self._restore_config(options['restore'])
    
    def _backup_config(self, backup_file):
        """Backup configuration to file"""
        config = NLPConfiguration.get_active_config()
        if not config:
            raise CommandError("No active configuration to backup")
        
        config_data = {
            'name': config.name,
            'description': config.description,
            'max_concurrent_jobs': config.max_concurrent_jobs,
            'default_confidence_threshold': config.default_confidence_threshold,
            'enable_caching': config.enable_caching,
            'cache_timeout': config.cache_timeout,
            'model_unload_timeout': config.model_unload_timeout,
            'max_text_length': config.max_text_length,
            'enable_preprocessing': config.enable_preprocessing,
            'preprocessing_config': config.preprocessing_config,
            'cpu_limit': config.cpu_limit,
            'memory_limit': config.memory_limit,
            'enable_monitoring': config.enable_monitoring,
            'log_level': config.log_level,
            'backup_date': timezone.now().isoformat()
        }
        
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        self.stdout.write(
            self.style.SUCCESS(f"Configuration backed up to {backup_file}")
        )
    
    def _restore_config(self, restore_file):
        """Restore configuration from file"""
        if not os.path.exists(restore_file):
            raise CommandError(f"Backup file not found: {restore_file}")
        
        with open(restore_file, 'r') as f:
            config_data = json.load(f)
        
        # Deactivate current configuration
        NLPConfiguration.objects.filter(is_active=True).update(is_active=False)
        
        # Create new configuration from backup
        config = NLPConfiguration.objects.create(
            name=config_data['name'] + ' (Restored)',
            description=config_data['description'],
            is_active=True,
            max_concurrent_jobs=config_data['max_concurrent_jobs'],
            default_confidence_threshold=config_data['default_confidence_threshold'],
            enable_caching=config_data['enable_caching'],
            cache_timeout=config_data['cache_timeout'],
            model_unload_timeout=config_data['model_unload_timeout'],
            max_text_length=config_data['max_text_length'],
            enable_preprocessing=config_data['enable_preprocessing'],
            preprocessing_config=config_data['preprocessing_config'],
            cpu_limit=config_data['cpu_limit'],
            memory_limit=config_data['memory_limit'],
            enable_monitoring=config_data['enable_monitoring'],
            log_level=config_data['log_level']
        )
        
        self.stdout.write(
            self.style.SUCCESS(f"Configuration restored: {config.name}")
        )