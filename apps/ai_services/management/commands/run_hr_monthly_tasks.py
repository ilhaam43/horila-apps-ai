from django.core.management.base import BaseCommand
from django.utils import timezone
from ai_services.hr_administrative_tasks import HRAdministrativeTasksService
import json
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run monthly HR administrative tasks'
    
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
            help='Send comprehensive reports via email to management',
        )
        parser.add_argument(
            '--generate-pdf',
            action='store_true',
            help='Generate PDF reports for archival',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting HR monthly tasks at {timezone.now()}'
            )
        )
        
        try:
            hr_service = HRAdministrativeTasksService()
            
            if options['dry_run']:
                self.stdout.write(
                    self.style.WARNING('Running in DRY-RUN mode')
                )
            
            # Jalankan tugas bulanan
            results = hr_service.process_monthly_tasks()
            
            if options['verbose']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Monthly tasks results:\n{json.dumps(results, indent=2)}'
                    )
                )
            
            # Ringkasan hasil
            tasks_completed = len(results.get('tasks_completed', []))
            errors = len(results.get('errors', []))
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Monthly tasks completed: {tasks_completed} tasks, {errors} errors'
                )
            )
            
            if errors > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f'Errors encountered: {results.get("errors", [])}'
                    )
                )
            
            # Generate PDF jika diminta
            if options['generate_pdf'] and not options['dry_run']:
                pdf_path = self._generate_pdf_report(results)
                if pdf_path:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'PDF report generated: {pdf_path}'
                        )
                    )
            
            # Kirim laporan via email jika diminta
            if options['email_reports'] and not options['dry_run']:
                self._send_email_reports(results)
            
            # Log hasil
            self._log_results(results)
            
        except Exception as e:
            logger.error(f'Error running HR monthly tasks: {str(e)}')
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to run monthly tasks: {str(e)}'
                )
            )
            raise
    
    def _generate_pdf_report(self, results):
        """
        Generate PDF report untuk arsip
        """
        try:
            import os
            from datetime import datetime
            
            # Buat direktori reports jika belum ada
            reports_dir = os.path.join('media', 'hr_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate filename
            month = results.get('month', datetime.now().strftime('%Y-%m'))
            filename = f'hr_monthly_report_{month}.json'
            filepath = os.path.join(reports_dir, filename)
            
            # Simpan sebagai JSON untuk sementara (bisa diubah ke PDF nanti)
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            return filepath
            
        except Exception as e:
            logger.error(f'Failed to generate PDF report: {str(e)}')
            return None
    
    def _send_email_reports(self, results):
        """
        Kirim laporan bulanan via email ke management
        """
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Format email content
            email_content = self._format_email_content(results)
            
            # Kirim ke management team (bisa dikonfigurasi di settings)
            management_emails = getattr(settings, 'MANAGEMENT_TEAM_EMAILS', ['management@company.com'])
            hr_emails = getattr(settings, 'HR_TEAM_EMAILS', ['hr@company.com'])
            
            all_recipients = list(set(management_emails + hr_emails))
            
            send_mail(
                subject=f'Monthly HR Report - {results.get("month", "")}',
                message=email_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=all_recipients,
                fail_silently=False,
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Monthly reports sent to {len(all_recipients)} recipients'
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
        Format konten email untuk laporan bulanan
        """
        content = f"Monthly HR Report\n"
        content += f"Report Month: {results.get('month', 'N/A')}\n\n"
        
        # Executive Summary
        content += "EXECUTIVE SUMMARY\n"
        content += "=" * 50 + "\n\n"
        
        for task in results.get('tasks_completed', []):
            task_name = task.get('task', 'Unknown Task')
            task_result = task.get('result', {})
            
            if task_name == 'monthly_hr_report' and isinstance(task_result, dict):
                content += "HR Metrics Overview:\n"
                
                # Employee metrics
                emp_metrics = task_result.get('employee_metrics', {})
                content += f"  - Total Active Employees: {emp_metrics.get('total_active_employees', 'N/A')}\n"
                content += f"  - New Hires: {emp_metrics.get('new_hires', 'N/A')}\n"
                
                # Leave metrics
                leave_metrics = task_result.get('leave_metrics', {})
                content += f"  - Leave Requests: {leave_metrics.get('total_requests', 'N/A')}\n"
                content += f"  - Leave Approval Rate: {leave_metrics.get('approved_requests', 0) / max(leave_metrics.get('total_requests', 1), 1) * 100:.1f}%\n"
                
                # Attendance metrics
                att_metrics = task_result.get('attendance_metrics', {})
                content += f"  - Attendance Rate: {att_metrics.get('attendance_rate', 'N/A')}%\n"
                
                # Performance metrics
                perf_metrics = task_result.get('performance_metrics', {})
                content += f"  - Average Objective Progress: {perf_metrics.get('average_objective_progress', 'N/A')}%\n"
                
            elif task_name == 'turnover_analysis' and isinstance(task_result, dict):
                content += "\nTurnover Analysis:\n"
                summary = task_result.get('summary', {})
                content += f"  - Turnover Rate: {summary.get('turnover_rate', 'N/A')}%\n"
                content += f"  - Net Growth: {summary.get('net_growth', 'N/A')} employees\n"
                
            elif task_name == 'policy_review' and isinstance(task_result, dict):
                content += "\nPolicy Recommendations:\n"
                recommendations = task_result.get('recommendations', [])
                for rec in recommendations[:3]:  # Top 3 recommendations
                    content += f"  - {rec.get('category', 'N/A')}: {rec.get('recommendation', 'N/A')}\n"
        
        if results.get('errors'):
            content += f"\nErrors Encountered:\n"
            for error in results.get('errors', []):
                content += f"  - {error}\n"
        
        content += "\n" + "=" * 50 + "\n"
        content += "This is an automated report generated by the HR AI Assistant.\n"
        content += f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return content
    
    def _log_results(self, results):
        """
        Log hasil ke database untuk tracking
        """
        try:
            from ai_services.models import HRQueryLog
            
            HRQueryLog.objects.create(
                query_type='monthly_tasks',
                query_text='Automated monthly HR tasks',
                response_data=results,
                user=None,  # System task
                processing_time=0.0
            )
            
        except Exception as e:
            logger.warning(f'Failed to log results: {str(e)}')