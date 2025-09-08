from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, Sum
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class HRAdministrativeTasksService:
    """
    Service untuk menangani tugas-tugas administratif HR otomatis
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.reminder_service = ReminderService()
        self.report_service = ReportService()
    
    def process_daily_tasks(self) -> Dict[str, Any]:
        """
        Proses tugas harian otomatis
        """
        results = {
            'date': datetime.now().date().isoformat(),
            'tasks_completed': [],
            'errors': []
        }
        
        try:
            # 1. Cek dan kirim reminder cuti yang akan berakhir
            leave_reminders = self.reminder_service.send_leave_expiry_reminders()
            results['tasks_completed'].append({
                'task': 'leave_expiry_reminders',
                'result': leave_reminders
            })
            
            # 2. Cek dan kirim reminder evaluasi kinerja
            performance_reminders = self.reminder_service.send_performance_review_reminders()
            results['tasks_completed'].append({
                'task': 'performance_review_reminders',
                'result': performance_reminders
            })
            
            # 3. Cek kontrak yang akan berakhir
            contract_reminders = self.reminder_service.send_contract_expiry_reminders()
            results['tasks_completed'].append({
                'task': 'contract_expiry_reminders',
                'result': contract_reminders
            })
            
            # 4. Generate notifikasi untuk birthday karyawan
            birthday_notifications = self.notification_service.send_birthday_notifications()
            results['tasks_completed'].append({
                'task': 'birthday_notifications',
                'result': birthday_notifications
            })
            
            # 5. Cek dan proses permintaan cuti yang tertunda lama
            pending_leave_alerts = self.notification_service.send_pending_leave_alerts()
            results['tasks_completed'].append({
                'task': 'pending_leave_alerts',
                'result': pending_leave_alerts
            })
            
        except Exception as e:
            logger.error(f"Error in daily tasks: {str(e)}")
            results['errors'].append(str(e))
        
        return results
    
    def process_weekly_tasks(self) -> Dict[str, Any]:
        """
        Proses tugas mingguan otomatis
        """
        results = {
            'week_start': (datetime.now() - timedelta(days=datetime.now().weekday())).date().isoformat(),
            'tasks_completed': [],
            'errors': []
        }
        
        try:
            # 1. Generate laporan kehadiran mingguan
            attendance_report = self.report_service.generate_weekly_attendance_report()
            results['tasks_completed'].append({
                'task': 'weekly_attendance_report',
                'result': attendance_report
            })
            
            # 2. Generate laporan cuti mingguan
            leave_report = self.report_service.generate_weekly_leave_report()
            results['tasks_completed'].append({
                'task': 'weekly_leave_report',
                'result': leave_report
            })
            
            # 3. Analisis produktivitas tim
            productivity_analysis = self.report_service.generate_team_productivity_analysis()
            results['tasks_completed'].append({
                'task': 'team_productivity_analysis',
                'result': productivity_analysis
            })
            
        except Exception as e:
            logger.error(f"Error in weekly tasks: {str(e)}")
            results['errors'].append(str(e))
        
        return results
    
    def process_monthly_tasks(self) -> Dict[str, Any]:
        """
        Proses tugas bulanan otomatis
        """
        results = {
            'month': datetime.now().strftime('%Y-%m'),
            'tasks_completed': [],
            'errors': []
        }
        
        try:
            # 1. Generate laporan HR komprehensif
            hr_report = self.report_service.generate_monthly_hr_report()
            results['tasks_completed'].append({
                'task': 'monthly_hr_report',
                'result': hr_report
            })
            
            # 2. Analisis turnover dan retention
            turnover_analysis = self.report_service.generate_turnover_analysis()
            results['tasks_completed'].append({
                'task': 'turnover_analysis',
                'result': turnover_analysis
            })
            
            # 3. Review dan update kebijakan otomatis
            policy_review = self.process_policy_review()
            results['tasks_completed'].append({
                'task': 'policy_review',
                'result': policy_review
            })
            
        except Exception as e:
            logger.error(f"Error in monthly tasks: {str(e)}")
            results['errors'].append(str(e))
        
        return results
    
    def process_policy_review(self) -> Dict[str, Any]:
        """
        Review kebijakan HR dan berikan rekomendasi
        """
        try:
            recommendations = []
            
            # Analisis data cuti untuk rekomendasi kebijakan
            from leave.models import LeaveRequest, LeaveType
            
            # Cek tingkat penggunaan cuti
            current_year = datetime.now().year
            leave_usage = LeaveRequest.objects.filter(
                created_at__year=current_year,
                status='approved'
            ).count()
            
            if leave_usage > 0:
                # Analisis pola cuti
                leave_types_usage = LeaveRequest.objects.filter(
                    created_at__year=current_year,
                    status='approved'
                ).values('leave_type__name').annotate(
                    count=Count('id')
                ).order_by('-count')
                
                recommendations.append({
                    'category': 'leave_policy',
                    'recommendation': f'Tipe cuti yang paling banyak digunakan: {leave_types_usage[0]["leave_type__name"] if leave_types_usage else "N/A"}',
                    'data': list(leave_types_usage)
                })
            
            # Analisis kinerja untuk rekomendasi training
            from pms.models import EmployeeObjective
            
            low_performance = EmployeeObjective.objects.filter(
                created_at__year=current_year,
                progress__lt=70
            ).values('employee__department__department').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if low_performance:
                recommendations.append({
                    'category': 'training_policy',
                    'recommendation': 'Departemen yang memerlukan program pelatihan tambahan',
                    'data': list(low_performance)
                })
            
            return {
                'success': True,
                'recommendations': recommendations,
                'review_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in policy review: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class NotificationService:
    """
    Service untuk mengirim notifikasi HR
    """
    
    def send_birthday_notifications(self) -> Dict[str, Any]:
        """
        Kirim notifikasi ulang tahun karyawan
        """
        try:
            from employee.models import Employee
            
            today = datetime.now().date()
            
            # Cari karyawan yang berulang tahun hari ini
            birthday_employees = Employee.objects.filter(
                dob__month=today.month,
                dob__day=today.day,
                is_active=True
            )
            
            notifications_sent = []
            
            for employee in birthday_employees:
                # Kirim notifikasi ke HR dan manajer
                if employee.employee_work_info.reporting_manager_id:
                    manager = employee.employee_work_info.reporting_manager_id
                    
                    notification_data = {
                        'employee_name': employee.get_full_name(),
                        'employee_id': employee.id,
                        'department': employee.employee_work_info.department.department if employee.employee_work_info.department else 'N/A',
                        'manager_notified': True
                    }
                    
                    notifications_sent.append(notification_data)
            
            return {
                'success': True,
                'notifications_sent': len(notifications_sent),
                'details': notifications_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending birthday notifications: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_pending_leave_alerts(self) -> Dict[str, Any]:
        """
        Kirim alert untuk permintaan cuti yang tertunda lama
        """
        try:
            from leave.models import LeaveRequest
            
            # Cari permintaan cuti yang tertunda lebih dari 3 hari
            three_days_ago = datetime.now() - timedelta(days=3)
            
            pending_requests = LeaveRequest.objects.filter(
                status='requested',
                created_at__lt=three_days_ago
            ).select_related('employee', 'leave_type')
            
            alerts_sent = []
            
            for request in pending_requests:
                alert_data = {
                    'employee_name': request.employee.get_full_name(),
                    'leave_type': request.leave_type.name,
                    'start_date': request.start_date.isoformat(),
                    'end_date': request.end_date.isoformat(),
                    'days_pending': (datetime.now().date() - request.created_at.date()).days,
                    'request_id': request.id
                }
                
                alerts_sent.append(alert_data)
            
            return {
                'success': True,
                'alerts_sent': len(alerts_sent),
                'details': alerts_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending pending leave alerts: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class ReminderService:
    """
    Service untuk mengirim reminder HR
    """
    
    def send_leave_expiry_reminders(self) -> Dict[str, Any]:
        """
        Kirim reminder untuk cuti yang akan berakhir
        """
        try:
            from leave.models import AvailableLeave
            
            # Cari cuti yang akan berakhir dalam 30 hari
            thirty_days_from_now = datetime.now().date() + timedelta(days=30)
            
            expiring_leaves = AvailableLeave.objects.filter(
                expiry_date__lte=thirty_days_from_now,
                expiry_date__gte=datetime.now().date(),
                available_days__gt=0
            ).select_related('employee', 'leave_type')
            
            reminders_sent = []
            
            for leave in expiring_leaves:
                reminder_data = {
                    'employee_name': leave.employee.get_full_name(),
                    'leave_type': leave.leave_type.name,
                    'available_days': float(leave.available_days),
                    'expiry_date': leave.expiry_date.isoformat(),
                    'days_until_expiry': (leave.expiry_date - datetime.now().date()).days
                }
                
                reminders_sent.append(reminder_data)
            
            return {
                'success': True,
                'reminders_sent': len(reminders_sent),
                'details': reminders_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending leave expiry reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_performance_review_reminders(self) -> Dict[str, Any]:
        """
        Kirim reminder untuk review kinerja yang jatuh tempo
        """
        try:
            from pms.models import EmployeeObjective, Period
            
            # Cari periode yang akan berakhir dalam 7 hari
            seven_days_from_now = datetime.now().date() + timedelta(days=7)
            
            ending_periods = Period.objects.filter(
                period_end__lte=seven_days_from_now,
                period_end__gte=datetime.now().date()
            )
            
            reminders_sent = []
            
            for period in ending_periods:
                # Cari objektif yang belum selesai di periode ini
                incomplete_objectives = EmployeeObjective.objects.filter(
                    period=period,
                    progress__lt=100
                ).select_related('employee')
                
                for objective in incomplete_objectives:
                    reminder_data = {
                        'employee_name': objective.employee.get_full_name(),
                        'objective_title': objective.title,
                        'current_progress': float(objective.progress),
                        'period_end': period.period_end.isoformat(),
                        'days_remaining': (period.period_end - datetime.now().date()).days
                    }
                    
                    reminders_sent.append(reminder_data)
            
            return {
                'success': True,
                'reminders_sent': len(reminders_sent),
                'details': reminders_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending performance review reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_contract_expiry_reminders(self) -> Dict[str, Any]:
        """
        Kirim reminder untuk kontrak yang akan berakhir
        """
        try:
            from payroll.models import Contract
            
            # Cari kontrak yang akan berakhir dalam 60 hari
            sixty_days_from_now = datetime.now().date() + timedelta(days=60)
            
            expiring_contracts = Contract.objects.filter(
                contract_end_date__lte=sixty_days_from_now,
                contract_end_date__gte=datetime.now().date()
            ).select_related('employee')
            
            reminders_sent = []
            
            for contract in expiring_contracts:
                reminder_data = {
                    'employee_name': contract.employee.get_full_name(),
                    'contract_type': contract.contract_type,
                    'end_date': contract.contract_end_date.isoformat(),
                    'days_until_expiry': (contract.contract_end_date - datetime.now().date()).days,
                    'basic_salary': float(contract.basic_pay)
                }
                
                reminders_sent.append(reminder_data)
            
            return {
                'success': True,
                'reminders_sent': len(reminders_sent),
                'details': reminders_sent
            }
            
        except Exception as e:
            logger.error(f"Error sending contract expiry reminders: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

class ReportService:
    """
    Service untuk generate laporan HR otomatis
    """
    
    def generate_weekly_attendance_report(self) -> Dict[str, Any]:
        """
        Generate laporan kehadiran mingguan
        """
        try:
            from attendance.models import Attendance
            
            # Hitung minggu ini
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Ambil data kehadiran minggu ini
            weekly_attendance = Attendance.objects.filter(
                attendance_date__gte=week_start,
                attendance_date__lte=week_end
            ).select_related('employee')
            
            # Analisis data
            total_employees = weekly_attendance.values('employee').distinct().count()
            total_present = weekly_attendance.filter(attendance_validated=True).count()
            total_absent = weekly_attendance.filter(attendance_validated=False).count()
            
            # Departemen dengan kehadiran terbaik
            dept_attendance = weekly_attendance.filter(
                attendance_validated=True
            ).values(
                'employee__employee_work_info__department__department'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            return {
                'success': True,
                'week_period': f'{week_start.isoformat()} to {week_end.isoformat()}',
                'summary': {
                    'total_employees': total_employees,
                    'total_present': total_present,
                    'total_absent': total_absent,
                    'attendance_rate': (total_present / (total_present + total_absent) * 100) if (total_present + total_absent) > 0 else 0
                },
                'department_performance': list(dept_attendance)
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly attendance report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_weekly_leave_report(self) -> Dict[str, Any]:
        """
        Generate laporan cuti mingguan
        """
        try:
            from leave.models import LeaveRequest
            
            # Hitung minggu ini
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Ambil data cuti minggu ini
            weekly_leaves = LeaveRequest.objects.filter(
                created_at__date__gte=week_start,
                created_at__date__lte=week_end
            ).select_related('employee', 'leave_type')
            
            # Analisis data
            total_requests = weekly_leaves.count()
            approved_requests = weekly_leaves.filter(status='approved').count()
            pending_requests = weekly_leaves.filter(status='requested').count()
            rejected_requests = weekly_leaves.filter(status='rejected').count()
            
            # Tipe cuti yang paling banyak diminta
            leave_types = weekly_leaves.values(
                'leave_type__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            return {
                'success': True,
                'week_period': f'{week_start.isoformat()} to {week_end.isoformat()}',
                'summary': {
                    'total_requests': total_requests,
                    'approved_requests': approved_requests,
                    'pending_requests': pending_requests,
                    'rejected_requests': rejected_requests,
                    'approval_rate': (approved_requests / total_requests * 100) if total_requests > 0 else 0
                },
                'popular_leave_types': list(leave_types)
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly leave report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_team_productivity_analysis(self) -> Dict[str, Any]:
        """
        Generate analisis produktivitas tim
        """
        try:
            from pms.models import EmployeeObjective, KeyResult
            
            # Hitung minggu ini
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            # Analisis progress objektif minggu ini
            weekly_objectives = EmployeeObjective.objects.filter(
                updated_at__date__gte=week_start
            ).select_related('employee')
            
            # Hitung rata-rata progress per departemen
            dept_progress = weekly_objectives.values(
                'employee__employee_work_info__department__department'
            ).annotate(
                avg_progress=Avg('progress'),
                total_objectives=Count('id')
            ).order_by('-avg_progress')
            
            # Key results yang diselesaikan minggu ini
            completed_kr = KeyResult.objects.filter(
                updated_at__date__gte=week_start,
                status='completed'
            ).count()
            
            return {
                'success': True,
                'analysis_period': f'Week starting {week_start.isoformat()}',
                'summary': {
                    'total_objectives_updated': weekly_objectives.count(),
                    'completed_key_results': completed_kr,
                    'top_performing_department': dept_progress[0]['employee__employee_work_info__department__department'] if dept_progress else 'N/A'
                },
                'department_performance': list(dept_progress)
            }
            
        except Exception as e:
            logger.error(f"Error generating team productivity analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_monthly_hr_report(self) -> Dict[str, Any]:
        """
        Generate laporan HR komprehensif bulanan
        """
        try:
            from employee.models import Employee
            from leave.models import LeaveRequest
            from pms.models import EmployeeObjective
            from attendance.models import Attendance
            
            # Hitung bulan ini
            today = datetime.now().date()
            month_start = today.replace(day=1)
            
            # Data karyawan
            total_employees = Employee.objects.filter(is_active=True).count()
            new_employees = Employee.objects.filter(
                employee_work_info__date_joining__gte=month_start
            ).count()
            
            # Data cuti bulan ini
            monthly_leaves = LeaveRequest.objects.filter(
                created_at__date__gte=month_start
            )
            
            # Data kehadiran bulan ini
            monthly_attendance = Attendance.objects.filter(
                attendance_date__gte=month_start
            )
            
            attendance_rate = 0
            if monthly_attendance.exists():
                total_attendance = monthly_attendance.count()
                validated_attendance = monthly_attendance.filter(attendance_validated=True).count()
                attendance_rate = (validated_attendance / total_attendance * 100) if total_attendance > 0 else 0
            
            # Data kinerja bulan ini
            monthly_objectives = EmployeeObjective.objects.filter(
                updated_at__date__gte=month_start
            )
            
            avg_performance = monthly_objectives.aggregate(
                avg_progress=Avg('progress')
            )['avg_progress'] or 0
            
            return {
                'success': True,
                'report_month': month_start.strftime('%Y-%m'),
                'employee_metrics': {
                    'total_active_employees': total_employees,
                    'new_hires': new_employees
                },
                'leave_metrics': {
                    'total_requests': monthly_leaves.count(),
                    'approved_requests': monthly_leaves.filter(status='approved').count(),
                    'pending_requests': monthly_leaves.filter(status='requested').count()
                },
                'attendance_metrics': {
                    'attendance_rate': round(attendance_rate, 2),
                    'total_records': monthly_attendance.count()
                },
                'performance_metrics': {
                    'average_objective_progress': round(avg_performance, 2),
                    'objectives_updated': monthly_objectives.count()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating monthly HR report: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_turnover_analysis(self) -> Dict[str, Any]:
        """
        Generate analisis turnover dan retention
        """
        try:
            from employee.models import Employee
            
            # Hitung 12 bulan terakhir
            twelve_months_ago = datetime.now().date() - timedelta(days=365)
            
            # Total karyawan aktif
            total_active = Employee.objects.filter(is_active=True).count()
            
            # Karyawan yang keluar dalam 12 bulan terakhir
            departed_employees = Employee.objects.filter(
                is_active=False,
                employee_work_info__date_joining__gte=twelve_months_ago
            ).count()
            
            # Karyawan baru dalam 12 bulan terakhir
            new_employees = Employee.objects.filter(
                employee_work_info__date_joining__gte=twelve_months_ago,
                is_active=True
            ).count()
            
            # Hitung turnover rate
            turnover_rate = 0
            if total_active > 0:
                turnover_rate = (departed_employees / total_active * 100)
            
            # Analisis per departemen
            dept_turnover = Employee.objects.filter(
                is_active=False,
                employee_work_info__date_joining__gte=twelve_months_ago
            ).values(
                'employee_work_info__department__department'
            ).annotate(
                departed_count=Count('id')
            ).order_by('-departed_count')
            
            return {
                'success': True,
                'analysis_period': f'Last 12 months from {twelve_months_ago.isoformat()}',
                'summary': {
                    'total_active_employees': total_active,
                    'departed_employees': departed_employees,
                    'new_employees': new_employees,
                    'turnover_rate': round(turnover_rate, 2),
                    'net_growth': new_employees - departed_employees
                },
                'department_turnover': list(dept_turnover)
            }
            
        except Exception as e:
            logger.error(f"Error generating turnover analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }