from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from .hr_administrative_tasks import HRAdministrativeTasksService
from .models import HRQueryLog
import json
import logging

logger = logging.getLogger(__name__)

def is_hr_staff(user):
    """
    Check if user is HR staff or admin
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_passes_test(is_hr_staff)
def run_daily_tasks(request):
    """
    Manually trigger daily HR tasks
    """
    try:
        hr_service = HRAdministrativeTasksService()
        
        # Get options from request
        dry_run = request.data.get('dry_run', False)
        
        if dry_run:
            logger.info(f"Running daily tasks in dry-run mode by user {request.user.username}")
        
        # Execute daily tasks
        results = hr_service.process_daily_tasks()
        
        # Log the execution
        HRQueryLog.objects.create(
            query_type='manual_daily_tasks',
            query_text=f'Manual daily tasks execution (dry_run: {dry_run})',
            response_data=results,
            user=request.user,
            processing_time=0.0
        )
        
        return Response({
            'success': True,
            'message': 'Daily tasks completed successfully',
            'results': results,
            'executed_by': request.user.username,
            'executed_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error running daily tasks: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_passes_test(is_hr_staff)
def run_weekly_tasks(request):
    """
    Manually trigger weekly HR tasks
    """
    try:
        hr_service = HRAdministrativeTasksService()
        
        # Get options from request
        dry_run = request.data.get('dry_run', False)
        email_reports = request.data.get('email_reports', False)
        
        if dry_run:
            logger.info(f"Running weekly tasks in dry-run mode by user {request.user.username}")
        
        # Execute weekly tasks
        results = hr_service.process_weekly_tasks()
        
        # Send email reports if requested and not dry run
        if email_reports and not dry_run:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                
                # Format email content
                email_content = _format_weekly_email_content(results)
                
                # Send to HR team
                hr_emails = getattr(settings, 'HR_TEAM_EMAILS', ['hr@company.com'])
                
                send_mail(
                    subject=f'Weekly HR Report - {results.get("week_start", "")}',
                    message=email_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=hr_emails,
                    fail_silently=False,
                )
                
                results['email_sent'] = True
                results['email_recipients'] = len(hr_emails)
                
            except Exception as email_error:
                logger.error(f"Failed to send email reports: {str(email_error)}")
                results['email_error'] = str(email_error)
        
        # Log the execution
        HRQueryLog.objects.create(
            query_type='manual_weekly_tasks',
            query_text=f'Manual weekly tasks execution (dry_run: {dry_run}, email: {email_reports})',
            response_data=results,
            user=request.user,
            processing_time=0.0
        )
        
        return Response({
            'success': True,
            'message': 'Weekly tasks completed successfully',
            'results': results,
            'executed_by': request.user.username,
            'executed_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error running weekly tasks: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@user_passes_test(is_hr_staff)
def run_monthly_tasks(request):
    """
    Manually trigger monthly HR tasks
    """
    try:
        hr_service = HRAdministrativeTasksService()
        
        # Get options from request
        dry_run = request.data.get('dry_run', False)
        email_reports = request.data.get('email_reports', False)
        generate_pdf = request.data.get('generate_pdf', False)
        
        if dry_run:
            logger.info(f"Running monthly tasks in dry-run mode by user {request.user.username}")
        
        # Execute monthly tasks
        results = hr_service.process_monthly_tasks()
        
        # Generate PDF if requested and not dry run
        if generate_pdf and not dry_run:
            try:
                import os
                from datetime import datetime
                
                # Create reports directory
                reports_dir = os.path.join('media', 'hr_reports')
                os.makedirs(reports_dir, exist_ok=True)
                
                # Generate filename
                month = results.get('month', datetime.now().strftime('%Y-%m'))
                filename = f'hr_monthly_report_{month}.json'
                filepath = os.path.join(reports_dir, filename)
                
                # Save as JSON
                with open(filepath, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                results['pdf_generated'] = True
                results['pdf_path'] = filepath
                
            except Exception as pdf_error:
                logger.error(f"Failed to generate PDF: {str(pdf_error)}")
                results['pdf_error'] = str(pdf_error)
        
        # Send email reports if requested and not dry run
        if email_reports and not dry_run:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                
                # Format email content
                email_content = _format_monthly_email_content(results)
                
                # Send to management and HR team
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
                
                results['email_sent'] = True
                results['email_recipients'] = len(all_recipients)
                
            except Exception as email_error:
                logger.error(f"Failed to send email reports: {str(email_error)}")
                results['email_error'] = str(email_error)
        
        # Log the execution
        HRQueryLog.objects.create(
            query_type='manual_monthly_tasks',
            query_text=f'Manual monthly tasks execution (dry_run: {dry_run}, email: {email_reports}, pdf: {generate_pdf})',
            response_data=results,
            user=request.user,
            processing_time=0.0
        )
        
        return Response({
            'success': True,
            'message': 'Monthly tasks completed successfully',
            'results': results,
            'executed_by': request.user.username,
            'executed_at': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error running monthly tasks: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_passes_test(is_hr_staff)
def get_task_history(request):
    """
    Get history of executed HR tasks
    """
    try:
        # Get query parameters
        task_type = request.GET.get('task_type', None)
        limit = int(request.GET.get('limit', 50))
        
        # Build query
        query = HRQueryLog.objects.filter(
            query_type__in=['daily_tasks', 'weekly_tasks', 'monthly_tasks', 
                          'manual_daily_tasks', 'manual_weekly_tasks', 'manual_monthly_tasks']
        )
        
        if task_type:
            query = query.filter(query_type__icontains=task_type)
        
        # Get recent executions
        recent_executions = query.order_by('-created_at')[:limit]
        
        # Format response
        history = []
        for execution in recent_executions:
            history.append({
                'id': execution.id,
                'task_type': execution.query_type,
                'executed_at': execution.created_at.isoformat(),
                'executed_by': execution.user.username if execution.user else 'System',
                'query_text': execution.query_text,
                'success': execution.response_data.get('errors', []) == [] if execution.response_data else True,
                'tasks_completed': len(execution.response_data.get('tasks_completed', [])) if execution.response_data else 0,
                'errors_count': len(execution.response_data.get('errors', [])) if execution.response_data else 0
            })
        
        return Response({
            'success': True,
            'history': history,
            'total_count': query.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting task history: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@user_passes_test(is_hr_staff)
def get_task_details(request, task_id):
    """
    Get detailed results of a specific task execution
    """
    try:
        execution = HRQueryLog.objects.get(id=task_id)
        
        return Response({
            'success': True,
            'task_details': {
                'id': execution.id,
                'task_type': execution.query_type,
                'executed_at': execution.created_at.isoformat(),
                'executed_by': execution.user.username if execution.user else 'System',
                'query_text': execution.query_text,
                'processing_time': execution.processing_time,
                'full_results': execution.response_data
            }
        }, status=status.HTTP_200_OK)
        
    except HRQueryLog.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Task execution not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Error getting task details: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def _format_weekly_email_content(results):
    """
    Format email content for weekly reports
    """
    content = f"Weekly HR Report\n"
    content += f"Week Period: {results.get('week_start', 'N/A')}\n\n"
    
    for task in results.get('tasks_completed', []):
        task_name = task.get('task', 'Unknown Task')
        content += f"\n{task_name.replace('_', ' ').title()}:\n"
        
        task_result = task.get('result', {})
        if isinstance(task_result, dict) and 'summary' in task_result:
            summary = task_result['summary']
            for key, value in summary.items():
                content += f"  - {key.replace('_', ' ').title()}: {value}\n"
    
    return content

def _format_monthly_email_content(results):
    """
    Format email content for monthly reports
    """
    content = f"Monthly HR Report\n"
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
    
    content += "\n" + "=" * 50 + "\n"
    content += "This is an automated report generated by the HR AI Assistant.\n"
    
    return content