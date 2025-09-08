from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_services.hr_administrative_tasks import HRAdministrativeTasksService
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run weekly HR administrative tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without generating actual reports',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
        parser.add_argument(
            '--email-reports',
            action='store_true',
            help='Send reports via email to HR team',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting HR weekly tasks at {timezone.now()}'
            )
        )
        
        try:
            hr_service = HRAdministrativeTasksService()
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('Running in DRY-RUN mode')
                )
            
            # Jalankan tugas mingguan
            results = hr_service.process_weekly_tasks()
            
            if options['verbose']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Weekly tasks results:\n{json.dumps(results, indent=2)}'
                    )
                )
            
            # Ringkasan hasil
            tasks_completed = len(results.get('tasks_completed', []))
            errors = len(results.get('errors', []))
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Weekly tasks completed: {tasks_completed} tasks, {errors} errors'
                )
            )
            
            if errors > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'Errors encountered: {results.get("errors", [])}'
                    )
                )
            
            # Kirim laporan via email jika diminta
            if options['email_reports'] and not options['dry_run']:
                self._send_email_reports(results)
            
            # Log hasil
            self._log_results(results)
            
        except Exception as e:
            logger.error(f'Error running HR weekly tasks: {str(e)}')
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to run weekly tasks: {str(e)}'
                )
            )
            raise
    
    def _send_email_reports(self, results):
        """
        Kirim laporan mingguan via email
        """
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Format email content
            email_content = self._format_email_content(results)
            
            # Kirim ke HR team (bisa dikonfigurasi di settings)
            hr_emails = getattr(settings, 'HR_TEAM_EMAILS', ['hr@company.com'])
            
            send_mail(
                subject=f'Weekly HR Report - {results.get("week_start", "")}',
                message=email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=hr_emails,
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Weekly reports sent to {len(hr_emails)} recipients'
                )
            )
            
        except Exception as e:
            logger.error(f'Failed to send email reports: {str(e)}')
            self.stdout.write(
                self.style.WARNING(
                    f'Failed to send email reports: {str(e)}'
                )
            )
    
    def _format_email_content(self, results):
        """
        Format konten email untuk laporan mingguan
        """
        content = f"Weekly HR Report\n"
        content += f"Week Period: {results.get('week_start', 'N/A')}\n\n"
        
        for task in results.get('tasks_completed', []):
            task_name = task.get('task', 'Unknown Task')
            content += f"\n{task_name.replace('_', ' ').title()}:\n"
            
            task_result = task.get('result', {})
            if isinstance(task_result, dict):
                if 'summary' in task_result:
                    summary = task_result['summary']
                    for key, value in summary.items():
                        content += f"  - {key.replace('_', ' ').title()}: {value}\n"
        
        if results.get('errors'):
            content += f"\nErrors Encountered:\n"
            for error in results.get('errors', []):
                content += f"  - {error}\n"
        
        return content
    
    def _log_results(self, results):
        """
        Log hasil ke database untuk tracking
        """
        try:
            from ai_services.models import HRQueryLog
            
            HRQueryLog.objects.create(
                query_type='weekly_tasks',
                query_text='Automated weekly HR tasks',
                response_data=results,
                user=None,  # System task
                processing_time=0.0
            )
            
        except Exception as e:
            logger.warning(f'Failed to log results: {str(e)}')