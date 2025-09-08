from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
import logging
import json
import numpy as np
from datetime import timedelta, datetime
from typing import Dict, List, Any, Optional

from .models import (
    AIModelRegistry,
    AIPrediction,
    KnowledgeBase,
    DocumentClassification,
    SearchQuery,
    NLPAnalysis,
    WorkflowExecution,
    AIServiceLog,
    AIAnalytics
)
from .budget_ai import BudgetAIService
from .knowledge_ai import KnowledgeAIService
from .indonesian_nlp import IndonesianNLPService
from .rag_n8n_integration import RAGN8NIntegrationService
from .document_classifier import DocumentClassifierService
from .intelligent_search import IntelligentSearchService
from .exceptions import AIServiceError

logger = logging.getLogger(__name__)

# AI Service Initialization Tasks
@shared_task(bind=True, max_retries=3)
def initialize_ai_service(self, service_type: str) -> Dict[str, Any]:
    """Initialize AI service asynchronously."""
    try:
        logger.info(f"Initializing AI service: {service_type}")
        
        service_map = {
            'budget_ai': BudgetAIService,
            'knowledge_ai': KnowledgeAIService,
            'indonesian_nlp': IndonesianNLPService,
            'rag_n8n': RAGN8NIntegrationService,
            'document_classifier': DocumentClassifierService,
            'intelligent_search': IntelligentSearchService
        }
        
        if service_type not in service_map:
            raise ValueError(f"Unknown service type: {service_type}")
        
        service_class = service_map[service_type]
        service = service_class()
        
        # Initialize service
        initialization_result = service.initialize()
        
        logger.info(f"Successfully initialized {service_type}")
        
        return {
            'success': True,
            'service_type': service_type,
            'initialization_result': initialization_result,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Failed to initialize {service_type}: {str(exc)}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying initialization of {service_type} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=exc)
        
        return {
            'success': False,
            'service_type': service_type,
            'error': str(exc),
            'timestamp': timezone.now().isoformat()
        }

# HR Administrative Tasks
@shared_task(bind=True, max_retries=3)
def run_hr_daily_tasks(self):
    """
    Celery task untuk menjalankan tugas harian HR
    """
    try:
        from .hr_administrative_tasks import HRAdministrativeTasksService
        from .models import HRQueryLog
        
        logger.info("Starting automated HR daily tasks")
        
        hr_service = HRAdministrativeTasksService()
        results = hr_service.process_daily_tasks()
        
        # Log hasil ke database
        HRQueryLog.objects.create(
            query_type='automated_daily_tasks',
            query_text='Automated daily HR tasks via Celery',
            response_data=results,
            user=None,  # System task
            processing_time=0.0
        )
        
        logger.info(f"Daily tasks completed successfully: {len(results.get('tasks_completed', []))} tasks")
        
        # Return summary untuk monitoring
        return {
            'success': True,
            'tasks_completed': len(results.get('tasks_completed', [])),
            'errors': len(results.get('errors', [])),
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in daily tasks: {str(exc)}")
        
        # Retry jika masih ada kesempatan
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying daily tasks (attempt {self.request.retries + 1})")
            raise self.retry(countdown=300, exc=exc)  # Retry after 5 minutes
        
        # Log error ke database
        try:
            from .models import HRQueryLog
            HRQueryLog.objects.create(
                query_type='automated_daily_tasks_error',
                query_text=f'Failed automated daily HR tasks: {str(exc)}',
                response_data={'error': str(exc)},
                user=None,
                processing_time=0.0
            )
        except:
            pass
        
        return {
            'success': False,
            'error': str(exc),
            'executed_at': timezone.now().isoformat()
        }

@shared_task(bind=True, max_retries=3)
def run_hr_weekly_tasks(self):
    """
    Celery task untuk menjalankan tugas mingguan HR
    """
    try:
        from .hr_administrative_tasks import HRAdministrativeTasksService
        from .models import HRQueryLog
        
        logger.info("Starting automated HR weekly tasks")
        
        hr_service = HRAdministrativeTasksService()
        results = hr_service.process_weekly_tasks()
        
        # Log hasil ke database
        HRQueryLog.objects.create(
            query_type='automated_weekly_tasks',
            query_text='Automated weekly HR tasks via Celery',
            response_data=results,
            user=None,  # System task
            processing_time=0.0
        )
        
        logger.info(f"Weekly tasks completed successfully: {len(results.get('tasks_completed', []))} tasks")
        
        # Kirim email report otomatis
        try:
            from django.core.mail import send_mail
            
            if hasattr(settings, 'HR_TEAM_EMAILS') and settings.HR_TEAM_EMAILS:
                email_content = _format_weekly_email_content(results)
                
                send_mail(
                    subject=f'Automated Weekly HR Report - {results.get("week_start", "")}',
                    message=email_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=settings.HR_TEAM_EMAILS,
                    fail_silently=True,
                )
                
                logger.info(f"Weekly report email sent to {len(settings.HR_TEAM_EMAILS)} recipients")
                
        except Exception as email_error:
            logger.warning(f"Failed to send weekly report email: {str(email_error)}")
        
        return {
            'success': True,
            'tasks_completed': len(results.get('tasks_completed', [])),
            'errors': len(results.get('errors', [])),
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in weekly tasks: {str(exc)}")
        
        # Retry jika masih ada kesempatan
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying weekly tasks (attempt {self.request.retries + 1})")
            raise self.retry(countdown=600, exc=exc)  # Retry after 10 minutes
        
        # Log error ke database
        try:
            from .models import HRQueryLog
            HRQueryLog.objects.create(
                query_type='automated_weekly_tasks_error',
                query_text=f'Failed automated weekly HR tasks: {str(exc)}',
                response_data={'error': str(exc)},
                user=None,
                processing_time=0.0
            )
        except:
            pass
        
        return {
            'success': False,
            'error': str(exc),
            'executed_at': timezone.now().isoformat()
        }

@shared_task(bind=True, max_retries=3)
def run_hr_monthly_tasks(self):
    """
    Celery task untuk menjalankan tugas bulanan HR
    """
    try:
        from .hr_administrative_tasks import HRAdministrativeTasksService
        from .models import HRQueryLog
        
        logger.info("Starting automated HR monthly tasks")
        
        hr_service = HRAdministrativeTasksService()
        results = hr_service.process_monthly_tasks()
        
        # Log hasil ke database
        HRQueryLog.objects.create(
            query_type='automated_monthly_tasks',
            query_text='Automated monthly HR tasks via Celery',
            response_data=results,
            user=None,  # System task
            processing_time=0.0
        )
        
        logger.info(f"Monthly tasks completed successfully: {len(results.get('tasks_completed', []))} tasks")
        
        # Generate dan simpan laporan PDF
        try:
            import os
            
            reports_dir = os.path.join('media', 'hr_reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            month = results.get('month', datetime.now().strftime('%Y-%m'))
            filename = f'automated_hr_monthly_report_{month}.json'
            filepath = os.path.join(reports_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Monthly report saved to {filepath}")
            
        except Exception as file_error:
            logger.warning(f"Failed to save monthly report file: {str(file_error)}")
        
        # Kirim email report ke management
        try:
            from django.core.mail import send_mail
            
            management_emails = getattr(settings, 'MANAGEMENT_TEAM_EMAILS', [])
            hr_emails = getattr(settings, 'HR_TEAM_EMAILS', [])
            all_recipients = list(set(management_emails + hr_emails))
            
            if all_recipients:
                email_content = _format_monthly_email_content(results)
                
                send_mail(
                    subject=f'Automated Monthly HR Report - {results.get("month", "")}',
                    message=email_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=all_recipients,
                    fail_silently=True,
                )
                
                logger.info(f"Monthly report email sent to {len(all_recipients)} recipients")
                
        except Exception as email_error:
            logger.warning(f"Failed to send monthly report email: {str(email_error)}")
        
        return {
            'success': True,
            'tasks_completed': len(results.get('tasks_completed', [])),
            'errors': len(results.get('errors', [])),
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in monthly tasks: {str(exc)}")
        
        # Retry jika masih ada kesempatan
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying monthly tasks (attempt {self.request.retries + 1})")
            raise self.retry(countdown=1800, exc=exc)  # Retry after 30 minutes
        
        # Log error ke database
        try:
            from .models import HRQueryLog
            HRQueryLog.objects.create(
                query_type='automated_monthly_tasks_error',
                query_text=f'Failed automated monthly HR tasks: {str(exc)}',
                response_data={'error': str(exc)},
                user=None,
                processing_time=0.0
            )
        except:
            pass
        
        return {
            'success': False,
            'error': str(exc),
            'executed_at': timezone.now().isoformat()
        }

@shared_task
def cleanup_old_hr_logs():
    """
    Cleanup log HR yang sudah lama (lebih dari 6 bulan)
    """
    try:
        from .models import HRQueryLog
        
        six_months_ago = timezone.now() - timedelta(days=180)
        
        # Hapus log yang lebih dari 6 bulan
        deleted_count = HRQueryLog.objects.filter(
            created_at__lt=six_months_ago
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old HR logs")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'executed_at': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error in cleanup task: {str(exc)}")
        return {
            'success': False,
            'error': str(exc),
            'executed_at': timezone.now().isoformat()
        }

def _format_weekly_email_content(results):
    """
    Format email content untuk laporan mingguan
    """
    content = f"Automated Weekly HR Report\n"
    content += f"Week Period: {results.get('week_start', 'N/A')}\n\n"
    
    for task in results.get('tasks_completed', []):
        task_name = task.get('task', 'Unknown Task')
        content += f"\n{task_name.replace('_', ' ').title()}:\n"
        
        task_result = task.get('result', {})
        if isinstance(task_result, dict) and 'summary' in task_result:
            summary = task_result['summary']
            for key, value in summary.items():
                content += f"  - {key.replace('_', ' ').title()}: {value}\n"
    
    if results.get('errors'):
        content += f"\nErrors Encountered:\n"
        for error in results.get('errors', []):
            content += f"  - {error}\n"
    
    content += "\n" + "=" * 50 + "\n"
    content += "This is an automated report generated by the HR AI Assistant.\n"
    
    return content

def _format_monthly_email_content(results):
    """
    Format email content untuk laporan bulanan
    """
    content = f"Automated Monthly HR Report\n"
    content += f"Report Month: {results.get('month', 'N/A')}\n\n"
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
            
            # Attendance metrics
            att_metrics = task_result.get('attendance_metrics', {})
            content += f"  - Attendance Rate: {att_metrics.get('attendance_rate', 'N/A')}%\n"
            
            # Performance metrics
            perf_metrics = task_result.get('performance_metrics', {})
            content += f"  - Average Objective Progress: {perf_metrics.get('average_objective_progress', 'N/A')}%\n"
    
    if results.get('errors'):
        content += f"\nErrors Encountered:\n"
        for error in results.get('errors', []):
            content += f"  - {error}\n"
    
    content += "\n" + "=" * 50 + "\n"
    content += "This is an automated report generated by the HR AI Assistant.\n"
    content += f"Generated at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return content