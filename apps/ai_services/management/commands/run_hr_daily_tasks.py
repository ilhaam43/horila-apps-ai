from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_services.hr_administrative_tasks import HRAdministrativeTasksService
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run daily HR administrative tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without sending actual notifications',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting HR daily tasks at {timezone.now()}'
            )
        )
        
        try:
            hr_service = HRAdministrativeTasksService()
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('Running in DRY-RUN mode')
                )
            
            # Jalankan tugas harian
            results = hr_service.process_daily_tasks()
            
            if options['verbose']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Daily tasks results:\n{json.dumps(results, indent=2)}'
                    )
                )
            
            # Ringkasan hasil
            tasks_completed = len(results.get('tasks_completed', []))
            errors = len(results.get('errors', []))
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Daily tasks completed: {tasks_completed} tasks, {errors} errors'
                )
            )
            
            if errors > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'Errors encountered: {results.get("errors", [])}'
                    )
                )
            
            # Log hasil ke database atau file jika diperlukan
            self._log_results(results)
            
        except Exception as e:
            logger.error(f'Error running HR daily tasks: {str(e)}')
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to run daily tasks: {str(e)}'
                )
            )
            raise
    
    def _log_results(self, results):
        """
        Log hasil ke database untuk tracking
        """
        try:
            from ai_services.models import HRQueryLog
            
            HRQueryLog.objects.create(
                query_type='daily_tasks',
                query_text='Automated daily HR tasks',
                response_data=results,
                user=None,  # System task
                processing_time=0.0
            )
            
        except Exception as e:
            logger.warning(f'Failed to log results: {str(e)}')