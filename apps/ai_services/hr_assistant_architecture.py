"""HR Assistant Architecture Design

Arsitektur AI Assistant untuk HR yang terintegrasi dengan semua modul HR:
- Employee Management
- Leave Management
- Performance Management
- Payroll Management
- Attendance Management
- Recruitment & Onboarding
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from django.db.models import QuerySet

# Import models HR
from employee.models import Employee, EmployeeWorkInformation
from leave.models import LeaveRequest, LeaveType, AvailableLeave
from attendance.models import AttendanceActivity, Attendance
from pms.models import EmployeeObjective, KeyResult, Feedback
from payroll.models.models import Payslip, Contract, Allowance, Deduction
from recruitment.models import Candidate, Recruitment
from onboarding.models import OnboardingTask, OnboardingPortal


class HRDataProcessor(ABC):
    """Abstract base class untuk processor data HR"""
    
    @abstractmethod
    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process HR query dan return hasil"""
        pass
    
    @abstractmethod
    def get_data_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get summary data untuk employee atau company"""
        pass


class EmployeeDataProcessor(HRDataProcessor):
    """Processor untuk data karyawan"""
    
    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process employee-related queries"""
        try:
            employee_id = context.get('employee_id')
            
            if not employee_id:
                return {
                    'success': False,
                    'error': 'Employee ID diperlukan untuk query data karyawan'
                }
            
            employee = Employee.objects.get(id=employee_id)
            work_info = employee.employee_work_info
            
            # Extract relevant information based on query
            query_lower = query.lower()
            
            data = {}
            
            # Profile information
            if any(keyword in query_lower for keyword in ['profil', 'profile', 'informasi', 'info', 'data diri', 'personal']):
                data['personal_info'] = {
                    'name': f"{employee.employee_first_name} {employee.employee_last_name or ''}".strip(),
                    'email': employee.email,
                    'phone': employee.phone,
                    'employee_id': employee.badge_id,
                    'date_of_birth': employee.dob.strftime('%Y-%m-%d') if employee.dob else None,
                    'gender': employee.gender,
                    'marital_status': employee.marital_status,
                    'address': employee.address,
                    'qualification': employee.qualification,
                    'experience': employee.experience
                }
                
                if work_info:
                    data['work_info'] = {
                        'employee_id': employee.badge_id,
                        'department': work_info.department.department if work_info.department else None,
                        'position': work_info.job_position.job_position if work_info.job_position else None,
                        'manager': work_info.reporting_manager.get_full_name() if work_info.reporting_manager else None,
                        'join_date': work_info.date_joining.strftime('%Y-%m-%d') if work_info.date_joining else None,
                        'employee_type': work_info.employee_type.employee_type if work_info.employee_type else None,
                        'work_type': work_info.work_type_id.work_type if work_info.work_type_id else None,
                        'shift': work_info.shift_id.employee_shift if work_info.shift_id else None
                    }
            
            # Department information
            elif any(keyword in query_lower for keyword in ['departemen', 'department']):
                return self._get_department_info(employee_id)
            
            # Manager information
            elif any(keyword in query_lower for keyword in ['manajer', 'manager', 'atasan', 'supervisor', 'boss']):
                return self._get_manager_info(employee_id)
            
            # Team/colleagues information
            elif any(keyword in query_lower for keyword in ['tim', 'team', 'colleague', 'rekan']):
                return self._get_team_members(employee_id)
            
            # Default: return basic profile
            else:
                data['personal_info'] = {
                    'name': f"{employee.employee_first_name} {employee.employee_last_name or ''}".strip(),
                    'email': employee.email,
                    'employee_id': employee.badge_id
                }
                
                if work_info:
                    data['work_info'] = {
                        'department': work_info.department.department if work_info.department else None,
                        'position': work_info.job_position.job_position if work_info.job_position else None
                    }
            
            return {
                'success': True,
                'data': data,
                'query_type': 'employee_data'
            }
        
        except Employee.DoesNotExist:
            return {
                'success': False,
                'error': 'Data karyawan tidak ditemukan'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error mengambil data karyawan: {str(e)}'
            }
    
    def get_data_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get employee data summary"""
        if employee_id:
            employee = Employee.objects.get(id=employee_id)
            work_info = employee.employee_work_info
            
            return {
                'name': f"{employee.employee_first_name} {employee.employee_last_name}",
                'email': employee.email,
                'department': work_info.department.department if work_info.department else None,
                'position': work_info.job_position.job_position if work_info.job_position else None,
                'manager': work_info.reporting_manager.get_full_name() if work_info.reporting_manager else None,
                'join_date': work_info.date_joining,
                'employee_type': work_info.employee_type.employee_type if work_info.employee_type else None
            }
        else:
            # Company-wide summary
            total_employees = Employee.objects.filter(is_active=True).count()
            departments = Employee.objects.values_list(
                'employee_work_info__department__department', flat=True
            ).distinct()
            
            return {
                'total_employees': total_employees,
                'departments': list(departments),
                'active_employees': Employee.objects.filter(is_active=True).count()
            }
    
    def _get_employee_profile(self, employee_id: int) -> Dict[str, Any]:
        """Get detailed employee profile"""
        try:
            employee = Employee.objects.select_related(
                'employee_work_info__department',
                'employee_work_info__job_position',
                'employee_work_info__reporting_manager'
            ).get(id=employee_id)
            
            work_info = employee.employee_work_info
            
            return {
                'success': True,
                'data': {
                    'personal_info': {
                        'name': f"{employee.employee_first_name} {employee.employee_last_name}",
                        'email': employee.email,
                        'phone': employee.phone,
                        'date_of_birth': employee.dob,
                        'gender': employee.gender,
                        'marital_status': employee.marital_status
                    },
                    'work_info': {
                        'employee_id': employee.badge_id,
                        'department': work_info.department.department if work_info.department else None,
                        'position': work_info.job_position.job_position if work_info.job_position else None,
                        'manager': work_info.reporting_manager.get_full_name() if work_info.reporting_manager else None,
                        'join_date': work_info.date_joining,
                        'employee_type': work_info.employee_type.employee_type if work_info.employee_type else None,
                        'work_type': work_info.work_type_id.work_type if work_info.work_type_id else None,
                        'shift': work_info.shift_id.employee_shift if work_info.shift_id else None
                    }
                }
            }
        except Employee.DoesNotExist:
            return {'success': False, 'error': 'Employee tidak ditemukan'}
    
    def _get_department_info(self, employee_id: int) -> Dict[str, Any]:
        """Get department information"""
        try:
            employee = Employee.objects.select_related(
                'employee_work_info__department'
            ).get(id=employee_id)
            
            department = employee.employee_work_info.department
            if not department:
                return {'success': False, 'error': 'Department tidak ditemukan'}
            
            # Get department colleagues
            colleagues = Employee.objects.filter(
                employee_work_info__department=department,
                is_active=True
            ).exclude(id=employee_id)
            
            return {
                'success': True,
                'data': {
                    'department_name': department.department,
                    'total_employees': colleagues.count() + 1,  # +1 for current employee
                    'colleagues': [
                        {
                            'name': f"{emp.employee_first_name} {emp.employee_last_name}",
                            'position': emp.employee_work_info.job_position.job_position if emp.employee_work_info.job_position else None
                        }
                        for emp in colleagues[:10]  # Limit to 10 colleagues
                    ]
                }
            }
        except Employee.DoesNotExist:
            return {'success': False, 'error': 'Employee tidak ditemukan'}
    
    def _get_manager_info(self, employee_id: int) -> Dict[str, Any]:
        """Get manager information"""
        try:
            employee = Employee.objects.select_related(
                'employee_work_info__reporting_manager'
            ).get(id=employee_id)
            
            manager = employee.employee_work_info.reporting_manager
            if not manager:
                return {'success': False, 'error': 'Manager tidak ditemukan'}
            
            return {
                'success': True,
                'data': {
                    'manager_name': manager.get_full_name(),
                    'manager_email': manager.email,
                    'manager_position': manager.employee_work_info.job_position.job_position if manager.employee_work_info.job_position else None,
                    'manager_department': manager.employee_work_info.department.department if manager.employee_work_info.department else None
                }
            }
        except Employee.DoesNotExist:
            return {'success': False, 'error': 'Employee tidak ditemukan'}
    
    def _get_team_members(self, employee_id: int) -> Dict[str, Any]:
        """Get team members (subordinates)"""
        try:
            employee = Employee.objects.get(id=employee_id)
            
            # Get subordinates
            subordinates = Employee.objects.filter(
                employee_work_info__reporting_manager=employee,
                is_active=True
            )
            
            return {
                'success': True,
                'data': {
                    'total_subordinates': subordinates.count(),
                    'team_members': [
                        {
                            'name': f"{emp.employee_first_name} {emp.employee_last_name}",
                            'position': emp.employee_work_info.job_position.job_position if emp.employee_work_info.job_position else None,
                            'email': emp.email
                        }
                        for emp in subordinates
                    ]
                }
            }
        except Employee.DoesNotExist:
            return {'success': False, 'error': 'Employee tidak ditemukan'}


class LeaveDataProcessor(HRDataProcessor):
    """Processor untuk data cuti"""
    
    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process leave-related queries"""
        try:
            from leave.models import LeaveRequest, AvailableLeave, LeaveType, Holiday, CompanyLeave
            from datetime import datetime, timedelta
            
            employee_id = context.get('employee_id')
            if not employee_id:
                return {
                    'success': False,
                    'error': 'Employee ID diperlukan untuk query data cuti'
                }
            
            query_lower = query.lower()
            data = {}
            
            # Leave balance query
            if any(keyword in query_lower for keyword in ['saldo', 'balance', 'sisa', 'available', 'tersedia']):
                available_leaves = AvailableLeave.objects.filter(employee_id=employee_id)
                data['leave_balance'] = []
                
                for leave in available_leaves:
                    data['leave_balance'].append({
                        'leave_type': leave.leave_type_id.name,
                        'available_days': float(leave.available_days),
                        'carryforward_days': float(leave.carryforward_days) if leave.carryforward_days else 0,
                        'total_days': float(leave.available_days) + (float(leave.carryforward_days) if leave.carryforward_days else 0)
                    })
            
            # Leave history query
            elif any(keyword in query_lower for keyword in ['riwayat', 'history', 'request', 'permintaan', 'pengajuan']):
                leave_requests = LeaveRequest.objects.filter(employee_id=employee_id).order_by('-created_at')[:20]
                data['leave_history'] = []
                
                for request in leave_requests:
                    data['leave_history'].append({
                        'leave_type': request.leave_type_id.name,
                        'start_date': request.start_date.strftime('%Y-%m-%d'),
                        'end_date': request.end_date.strftime('%Y-%m-%d'),
                        'days': float(request.requested_days),
                        'status': request.status,
                        'reason': request.description,
                        'created_date': request.created_at.strftime('%Y-%m-%d'),
                        'approved_by': request.approved_by.get_full_name() if request.approved_by else None
                    })
            
            # Pending leave requests
            elif any(keyword in query_lower for keyword in ['pending', 'menunggu', 'diajukan', 'belum disetujui']):
                pending_requests = LeaveRequest.objects.filter(
                    employee_id=employee_id,
                    status__in=['requested', 'pending']
                ).order_by('-created_at')
                
                data['pending_requests'] = []
                for request in pending_requests:
                    data['pending_requests'].append({
                        'leave_type': request.leave_type_id.name,
                        'start_date': request.start_date.strftime('%Y-%m-%d'),
                        'end_date': request.end_date.strftime('%Y-%m-%d'),
                        'days': float(request.requested_days),
                        'reason': request.description,
                        'created_date': request.created_at.strftime('%Y-%m-%d')
                    })
            
            # Approved leave requests
            elif any(keyword in query_lower for keyword in ['approved', 'disetujui', 'diterima']):
                approved_requests = LeaveRequest.objects.filter(
                    employee_id=employee_id,
                    status='approved'
                ).order_by('-start_date')[:10]
                
                data['approved_requests'] = []
                for request in approved_requests:
                    data['approved_requests'].append({
                        'leave_type': request.leave_type_id.name,
                        'start_date': request.start_date.strftime('%Y-%m-%d'),
                        'end_date': request.end_date.strftime('%Y-%m-%d'),
                        'days': float(request.requested_days),
                        'approved_by': request.approved_by.get_full_name() if request.approved_by else None,
                        'approved_date': request.approved_at.strftime('%Y-%m-%d') if request.approved_at else None
                    })
            
            # Leave types available
            elif any(keyword in query_lower for keyword in ['jenis', 'type', 'kategori']):
                leave_types = LeaveType.objects.filter(is_active=True)
                data['leave_types'] = []
                
                for lt in leave_types:
                    data['leave_types'].append({
                        'name': lt.name,
                        'is_paid': lt.is_paid,
                        'total_days': float(lt.total_days) if lt.total_days else None,
                        'carryforward_type': lt.carryforward_type,
                        'carryforward_max': float(lt.carryforward_max) if lt.carryforward_max else None
                    })
            
            # Upcoming holidays
            elif any(keyword in query_lower for keyword in ['holiday', 'libur', 'hari libur']):
                today = datetime.now().date()
                upcoming_holidays = Holiday.objects.filter(
                    start_date__gte=today
                ).order_by('start_date')[:10]
                
                data['upcoming_holidays'] = []
                for holiday in upcoming_holidays:
                    data['upcoming_holidays'].append({
                        'name': holiday.name,
                        'start_date': holiday.start_date.strftime('%Y-%m-%d'),
                        'end_date': holiday.end_date.strftime('%Y-%m-%d') if holiday.end_date else holiday.start_date.strftime('%Y-%m-%d'),
                        'recurring': holiday.recurring
                    })
            
            # This year's leave statistics
            elif any(keyword in query_lower for keyword in ['tahun ini', 'this year', 'statistik', 'stats']):
                current_year = datetime.now().year
                year_requests = LeaveRequest.objects.filter(
                    employee_id=employee_id,
                    start_date__year=current_year
                )
                
                from django.db import models
                approved_days = year_requests.filter(status='approved').aggregate(
                    total=models.Sum('requested_days')
                )['total'] or 0
                
                pending_days = year_requests.filter(status__in=['requested', 'pending']).aggregate(
                    total=models.Sum('requested_days')
                )['total'] or 0
                
                rejected_days = year_requests.filter(status='rejected').aggregate(
                    total=models.Sum('requested_days')
                )['total'] or 0
                
                data['yearly_statistics'] = {
                    'year': current_year,
                    'approved_days': float(approved_days),
                    'pending_days': float(pending_days),
                    'rejected_days': float(rejected_days),
                    'total_requests': year_requests.count()
                }
            
            # Default: return leave balance and recent history
            else:
                # Get leave balance
                available_leaves = AvailableLeave.objects.filter(employee_id=employee_id)
                data['leave_balance'] = []
                
                for leave in available_leaves:
                    data['leave_balance'].append({
                        'leave_type': leave.leave_type_id.name,
                        'available_days': float(leave.available_days),
                        'carryforward_days': float(leave.carryforward_days) if leave.carryforward_days else 0
                    })
                
                # Get recent requests
                recent_requests = LeaveRequest.objects.filter(employee_id=employee_id).order_by('-created_at')[:5]
                data['recent_requests'] = []
                
                for request in recent_requests:
                    data['recent_requests'].append({
                        'leave_type': request.leave_type_id.name,
                        'start_date': request.start_date.strftime('%Y-%m-%d'),
                        'end_date': request.end_date.strftime('%Y-%m-%d'),
                        'days': float(request.requested_days),
                        'status': request.status
                    })
            
            return {
                'success': True,
                'data': data,
                'query_type': 'leave_data'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error mengambil data cuti: {str(e)}'
            }
    
    def get_data_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get leave data summary"""
        if employee_id:
            # Individual employee leave summary
            available_leaves = AvailableLeave.objects.filter(
                employee_id=employee_id
            ).select_related('leave_type_id')
            
            pending_requests = LeaveRequest.objects.filter(
                employee_id=employee_id,
                status='requested'
            ).count()
            
            return {
                'available_leaves': [
                    {
                        'leave_type': leave.leave_type_id.name,
                        'available_days': leave.available_days,
                        'carryforward_days': leave.carryforward_days
                    }
                    for leave in available_leaves
                ],
                'pending_requests': pending_requests
            }
        else:
            # Company-wide leave summary
            total_requests = LeaveRequest.objects.count()
            pending_requests = LeaveRequest.objects.filter(status='requested').count()
            approved_requests = LeaveRequest.objects.filter(status='approved').count()
            
            return {
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'approval_rate': (approved_requests / total_requests * 100) if total_requests > 0 else 0
            }
    
    def _get_recent_leave_requests(self, employee_id: int) -> Dict[str, Any]:
        """Get recent leave requests"""
        try:
            recent_requests = LeaveRequest.objects.filter(
                employee_id=employee_id
            ).select_related('leave_type_id').order_by('-created_at')[:10]
            
            requests_data = []
            for request in recent_requests:
                requests_data.append({
                    'id': request.id,
                    'leave_type': request.leave_type_id.name,
                    'start_date': request.start_date.strftime('%Y-%m-%d'),
                    'end_date': request.end_date.strftime('%Y-%m-%d'),
                    'days': float(request.requested_days),
                    'status': request.status,
                    'reason': request.description or '',
                    'created_date': request.created_at.strftime('%Y-%m-%d %H:%M'),
                    'approved_by': request.approved_by.get_full_name() if request.approved_by else None
                })
            
            return {
                'success': True,
                'data': {
                    'recent_requests': requests_data
                },
                'query_type': 'leave_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil permintaan cuti terbaru: {str(e)}'}
    
    def _get_leave_calendar(self, employee_id: int) -> Dict[str, Any]:
        """Get leave calendar/schedule"""
        try:
            from datetime import datetime, timedelta
            
            # Get approved leaves for next 3 months
            start_date = datetime.now().date()
            end_date = start_date + timedelta(days=90)
            
            approved_leaves = LeaveRequest.objects.filter(
                employee_id=employee_id,
                status='approved',
                start_date__gte=start_date,
                start_date__lte=end_date
            ).select_related('leave_type_id').order_by('start_date')
            
            calendar_data = []
            for leave in approved_leaves:
                calendar_data.append({
                    'leave_type': leave.leave_type_id.name,
                    'start_date': leave.start_date.strftime('%Y-%m-%d'),
                    'end_date': leave.end_date.strftime('%Y-%m-%d'),
                    'days': float(leave.requested_days),
                    'reason': leave.description or '',
                    'days_until': (leave.start_date - datetime.now().date()).days
                })
            
            # Get upcoming holidays
            holidays = Holiday.objects.filter(
                start_date__gte=start_date,
                start_date__lte=end_date
            ).order_by('start_date')
            
            holidays_data = []
            for holiday in holidays:
                holidays_data.append({
                    'name': holiday.name,
                    'start_date': holiday.start_date.strftime('%Y-%m-%d'),
                    'end_date': holiday.end_date.strftime('%Y-%m-%d') if holiday.end_date else holiday.start_date.strftime('%Y-%m-%d'),
                    'days_until': (holiday.start_date - datetime.now().date()).days
                })
            
            return {
                'success': True,
                'data': {
                    'upcoming_leaves': calendar_data,
                    'upcoming_holidays': holidays_data,
                    'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
                },
                'query_type': 'leave_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil kalender cuti: {str(e)}'}
    
    def _get_loans(self, employee_id: int) -> Dict[str, Any]:
        """Get employee loans"""
        try:
            from payroll.models.models import LoanAccount
            
            loans = LoanAccount.objects.filter(employee_id=employee_id).order_by('-created_at')[:10]
            loans_data = []
            
            for loan in loans:
                loans_data.append({
                    'title': loan.title,
                    'amount': float(loan.amount) if loan.amount else 0,
                    'interest_rate': float(loan.interest_rate) if loan.interest_rate else 0,
                    'installment': float(loan.installment) if loan.installment else 0,
                    'balance': float(loan.balance) if loan.balance else 0,
                    'status': loan.status,
                    'start_date': loan.start_date.strftime('%Y-%m-%d') if loan.start_date else None,
                    'created_date': loan.created_at.strftime('%Y-%m-%d')
                })
            
            return {
                'success': True,
                'data': {
                    'loans': loans_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil data pinjaman: {str(e)}'}
    
    def _get_reimbursements(self, employee_id: int) -> Dict[str, Any]:
        """Get employee reimbursements"""
        try:
            from payroll.models.models import Reimbursement
            
            reimbursements = Reimbursement.objects.filter(employee_id=employee_id).order_by('-created_at')[:10]
            reimbursements_data = []
            
            for reimb in reimbursements:
                reimbursements_data.append({
                    'title': reimb.title,
                    'amount': float(reimb.amount) if reimb.amount else 0,
                    'status': reimb.status,
                    'created_date': reimb.created_at.strftime('%Y-%m-%d'),
                    'approved_date': reimb.approved_date.strftime('%Y-%m-%d') if reimb.approved_date else None
                })
            
            return {
                'success': True,
                'data': {
                    'reimbursements': reimbursements_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil data reimbursement: {str(e)}'}
    
    def _get_salary_statistics(self, employee_id: int) -> Dict[str, Any]:
        """Get salary statistics"""
        try:
            from payroll.models.models import Payslip
            from django.db import models
            from datetime import datetime
            
            current_year = datetime.now().year
            year_payslips = Payslip.objects.filter(
                employee_id=employee_id,
                start_date__year=current_year
            ).order_by('-start_date')
            
            # Calculate statistics
            total_gross = year_payslips.aggregate(total=models.Sum('gross_pay'))['total'] or 0
            total_net = year_payslips.aggregate(total=models.Sum('net_pay'))['total'] or 0
            total_deductions = year_payslips.aggregate(total=models.Sum('deduction'))['total'] or 0
            total_allowances = year_payslips.aggregate(total=models.Sum('allowance'))['total'] or 0
            
            avg_gross = year_payslips.aggregate(avg=models.Avg('gross_pay'))['avg'] or 0
            avg_net = year_payslips.aggregate(avg=models.Avg('net_pay'))['avg'] or 0
            
            statistics_data = {
                'year': current_year,
                'total_payslips': year_payslips.count(),
                'total_gross_pay': float(total_gross),
                'total_net_pay': float(total_net),
                'total_deductions': float(total_deductions),
                'total_allowances': float(total_allowances),
                'average_gross_pay': float(avg_gross),
                'average_net_pay': float(avg_net),
                'paid_payslips': year_payslips.filter(status='paid').count(),
                'pending_payslips': year_payslips.filter(status__in=['draft', 'review_ongoing']).count()
            }
            
            # Add recent payslips
            recent_payslips = []
            for payslip in year_payslips[:6]:
                recent_payslips.append({
                    'title': payslip.title,
                    'net_pay': float(payslip.net_pay) if payslip.net_pay else 0,
                    'status': payslip.status,
                    'start_date': payslip.start_date.strftime('%Y-%m-%d') if payslip.start_date else None,
                    'end_date': payslip.end_date.strftime('%Y-%m-%d') if payslip.end_date else None
                })
            
            return {
                'success': True,
                'data': {
                    'salary_statistics': statistics_data,
                    'recent_payslips': recent_payslips
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil statistik gaji: {str(e)}'}
    
    def _get_leave_history(self, employee_id: int) -> Dict[str, Any]:
        """Get employee leave history"""
        try:
            leave_requests = LeaveRequest.objects.filter(
                employee_id=employee_id
            ).select_related('leave_type_id').order_by('-created_at')[:10]
            
            history_data = []
            for request in leave_requests:
                history_data.append({
                    'leave_type': request.leave_type_id.name,
                    'start_date': request.start_date,
                    'end_date': request.end_date,
                    'requested_days': request.requested_days,
                    'status': request.status,
                    'description': request.description,
                    'created_at': request.created_at
                })
            
            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'leave_history': history_data
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_pending_requests(self, employee_id: int) -> Dict[str, Any]:
        """Get pending leave requests"""
        try:
            pending_requests = LeaveRequest.objects.filter(
                employee_id=employee_id,
                status='requested'
            ).select_related('leave_type_id')
            
            pending_data = []
            for request in pending_requests:
                pending_data.append({
                    'id': request.id,
                    'leave_type': request.leave_type_id.name,
                    'start_date': request.start_date,
                    'end_date': request.end_date,
                    'requested_days': request.requested_days,
                    'description': request.description,
                    'created_at': request.created_at
                })
            
            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'pending_requests': pending_data
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_leave_types(self) -> Dict[str, Any]:
        """Get available leave types"""
        try:
            leave_types = LeaveType.objects.filter(is_active=True)
            
            types_data = []
            for leave_type in leave_types:
                types_data.append({
                    'id': leave_type.id,
                    'name': leave_type.name,
                    'is_paid': leave_type.is_paid,
                    'total_days': leave_type.total_days,
                    'carryforward_max': leave_type.carryforward_max
                })
            
            return {
                'success': True,
                'data': {
                    'leave_types': types_data
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class PerformanceDataProcessor(HRDataProcessor):
    """Processor untuk data evaluasi kinerja"""
    
    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process performance-related queries"""
        try:
            from pms.models import EmployeeObjective, KeyResult, Feedback, Comment, Meetings, EmployeeBonusPoint
            from datetime import datetime, timedelta
            
            employee_id = context.get('employee_id')
            if not employee_id:
                return {
                    'success': False,
                    'error': 'Employee ID diperlukan untuk query data kinerja'
                }
            
            query_lower = query.lower()
            data = {}
            
            # Objectives query
            if any(keyword in query_lower for keyword in ['objektif', 'objective', 'target', 'tujuan', 'goal']):
                objectives = EmployeeObjective.objects.filter(employee_id=employee_id).order_by('-created_at')[:15]
                data['objectives'] = []
                
                for obj in objectives:
                    data['objectives'].append({
                        'title': obj.objective_id.title,
                        'description': obj.objective_id.description,
                        'status': obj.status,
                        'progress': float(obj.progress) if obj.progress else 0,
                        'start_date': obj.start_date.strftime('%Y-%m-%d') if obj.start_date else None,
                        'end_date': obj.end_date.strftime('%Y-%m-%d') if obj.end_date else None
                    })
            
            # Key results query
            elif any(keyword in query_lower for keyword in ['key result', 'hasil kunci', 'kpi', 'indikator']):
                key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id
                ).order_by('-created_at')[:15]
                data['key_results'] = []
                
                for kr in key_results:
                    data['key_results'].append({
                        'title': kr.title,
                        'description': kr.description,
                        'target_value': float(kr.target_value) if kr.target_value else None,
                        'current_value': float(kr.current_value) if kr.current_value else 0,
                        'progress': float(kr.progress_percentage) if kr.progress_percentage else 0,
                        'status': kr.status,
                        'start_date': kr.start_date.strftime('%Y-%m-%d') if kr.start_date else None,
                        'end_date': kr.end_date.strftime('%Y-%m-%d') if kr.end_date else None
                    })
            
            # Feedback query
            elif any(keyword in query_lower for keyword in ['feedback', 'umpan balik', 'review', 'evaluasi']):
                feedbacks = Feedback.objects.filter(
                    employee_id=employee_id
                ).order_by('-created_at')[:10]
                
                data['feedbacks'] = []
                for feedback in feedbacks:
                    data['feedbacks'].append({
                        'review_cycle': feedback.review_cycle,
                        'manager_id': feedback.manager_id.id if feedback.manager_id else None,
                        'manager_name': feedback.manager_id.get_full_name() if feedback.manager_id else None,
                        'status': feedback.status,
                        'created_date': feedback.created_at.strftime('%Y-%m-%d'),
                        'start_date': feedback.start_date.strftime('%Y-%m-%d') if feedback.start_date else None,
                        'end_date': feedback.end_date.strftime('%Y-%m-%d') if feedback.end_date else None
                    })
            
            # Performance statistics
            elif any(keyword in query_lower for keyword in ['statistik', 'stats', 'ringkasan', 'summary']):
                # Current year statistics
                current_year = datetime.now().year
                year_objectives = EmployeeObjective.objects.filter(
                    employee_id=employee_id,
                    created_at__year=current_year
                )
                
                completed_objectives = year_objectives.filter(status='completed').count()
                in_progress_objectives = year_objectives.filter(status='in_progress').count()
                
                # Average progress calculation
                from django.db import models
                avg_progress = year_objectives.aggregate(
                    avg=models.Avg('progress')
                )['avg'] or 0
                
                data['performance_statistics'] = {
                    'year': current_year,
                    'total_objectives': year_objectives.count(),
                    'completed_objectives': completed_objectives,
                    'in_progress_objectives': in_progress_objectives,
                    'objectives_completion_rate': (completed_objectives / year_objectives.count() * 100) if year_objectives.count() > 0 else 0,
                    'average_objectives_progress': float(avg_progress)
                }
            
            # Bonus points query
            elif any(keyword in query_lower for keyword in ['bonus', 'poin', 'reward', 'penghargaan']):
                bonus_points = EmployeeBonusPoint.objects.filter(
                    employee_id=employee_id
                ).order_by('-created_at')[:10]
                
                data['bonus_points'] = []
                total_points = 0
                for bonus in bonus_points:
                    points = float(bonus.points) if bonus.points else 0
                    total_points += points
                    data['bonus_points'].append({
                        'reason': bonus.reason,
                        'points': points,
                        'created_date': bonus.created_at.strftime('%Y-%m-%d'),
                        'created_by': bonus.created_by.get_full_name() if bonus.created_by else None
                    })
                
                data['total_bonus_points'] = total_points
            
            # Meetings/1-on-1 query
            elif any(keyword in query_lower for keyword in ['meeting', 'pertemuan', '1-on-1', 'one on one']):
                meetings = Meetings.objects.filter(
                    employee_id=employee_id
                ).order_by('-created_at')[:10]
                
                data['meetings'] = []
                for meeting in meetings:
                    data['meetings'].append({
                        'title': meeting.title,
                        'description': meeting.description,
                        'date': meeting.date.strftime('%Y-%m-%d') if meeting.date else None,
                        'status': meeting.status,
                        'manager_id': meeting.manager_id.id if meeting.manager_id else None,
                        'manager_name': meeting.manager_id.get_full_name() if meeting.manager_id else None,
                        'created_date': meeting.created_at.strftime('%Y-%m-%d')
                    })
            
            # Default: return current objectives and key results
            else:
                # Get active objectives
                active_objectives = EmployeeObjective.objects.filter(
                    employee_id=employee_id,
                    status__in=['in_progress', 'not_started']
                ).order_by('-created_at')[:5]
                
                data['active_objectives'] = []
                for obj in active_objectives:
                    data['active_objectives'].append({
                        'title': obj.objective_id.title,
                        'progress': float(obj.progress) if obj.progress else 0,
                        'status': obj.status,
                        'end_date': obj.end_date.strftime('%Y-%m-%d') if obj.end_date else None
                    })
                
                # Get recent key results
                recent_key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id
                ).order_by('-created_at')[:3]
                
                data['recent_key_results'] = []
                for kr in recent_key_results:
                    data['recent_key_results'].append({
                        'title': kr.title,
                        'progress': float(kr.progress_percentage) if kr.progress_percentage else 0,
                        'status': kr.status
                    })
                
                # Get active key results
                active_key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id,
                    status__in=['in_progress', 'not_started']
                ).order_by('-created_at')[:5]
                
                data['active_key_results'] = []
                for kr in active_key_results:
                    data['active_key_results'].append({
                        'title': kr.title,
                        'progress': float(kr.progress_percentage) if kr.progress_percentage else 0,
                        'current_value': float(kr.current_value) if kr.current_value else 0,
                        'target_value': float(kr.target_value) if kr.target_value else None,
                        'status': kr.status
                    })
            
            return {
                'success': True,
                'data': data,
                'query_type': 'performance_data'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error mengambil data kinerja: {str(e)}'
            }
    
    def _get_performance_summary(self, employee_id: int) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            from pms.models import EmployeeObjective, KeyResult, Feedback, EmployeeBonusPoint
            from datetime import datetime
            from django.db import models
            
            current_year = datetime.now().year
            
            # Objectives summary
            year_objectives = EmployeeObjective.objects.filter(
                employee_id=employee_id,
                created_at__year=current_year
            )
            
            objectives_summary = {
                'total': year_objectives.count(),
                'completed': year_objectives.filter(status='completed').count(),
                'in_progress': year_objectives.filter(status='in_progress').count(),
                'not_started': year_objectives.filter(status='not_started').count(),
                'average_progress': year_objectives.aggregate(avg=models.Avg('progress'))['avg'] or 0
            }
            
            # Key results summary
            year_key_results = KeyResult.objects.filter(
                employee_objective__employee_id=employee_id,
                created_at__year=current_year
            )
            
            key_results_summary = {
                'total': year_key_results.count(),
                'completed': year_key_results.filter(status='completed').count(),
                'in_progress': year_key_results.filter(status='in_progress').count(),
                'average_progress': year_key_results.aggregate(avg=models.Avg('progress_percentage'))['avg'] or 0
            }
            
            # Bonus points summary
            year_bonus_points = EmployeeBonusPoint.objects.filter(
                employee_id=employee_id,
                created_at__year=current_year
            )
            
            total_bonus_points = year_bonus_points.aggregate(total=models.Sum('points'))['total'] or 0
            
            # Feedback summary
            year_feedbacks = Feedback.objects.filter(
                employee_id=employee_id,
                created_at__year=current_year
            )
            
            feedback_summary = {
                'total_reviews': year_feedbacks.count(),
                'completed_reviews': year_feedbacks.filter(status='completed').count(),
                'pending_reviews': year_feedbacks.filter(status='pending').count()
            }
            
            return {
                'success': True,
                'data': {
                    'year': current_year,
                    'objectives_summary': objectives_summary,
                    'key_results_summary': key_results_summary,
                    'total_bonus_points': float(total_bonus_points),
                    'feedback_summary': feedback_summary
                },
                'query_type': 'performance_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil ringkasan kinerja: {str(e)}'}
    
    def _get_performance_trends(self, employee_id: int) -> Dict[str, Any]:
        """Get performance trends over time"""
        try:
            from pms.models import EmployeeObjective, KeyResult
            from datetime import datetime, timedelta
            from django.db import models
            
            # Get last 6 months of data
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=180)
            
            # Monthly objective progress
            monthly_progress = {}
            for i in range(6):
                month_start = end_date - timedelta(days=(i+1)*30)
                month_end = end_date - timedelta(days=i*30)
                
                month_objectives = EmployeeObjective.objects.filter(
                    employee_id=employee_id,
                    created_at__date__gte=month_start,
                    created_at__date__lte=month_end
                )
                
                avg_progress = month_objectives.aggregate(avg=models.Avg('progress'))['avg'] or 0
                month_name = month_end.strftime('%B %Y')
                monthly_progress[month_name] = float(avg_progress)
            
            # Key results completion rate
            key_results_trend = {}
            for i in range(6):
                month_start = end_date - timedelta(days=(i+1)*30)
                month_end = end_date - timedelta(days=i*30)
                
                month_key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id,
                    created_at__date__gte=month_start,
                    created_at__date__lte=month_end
                )
                
                total_kr = month_key_results.count()
                completed_kr = month_key_results.filter(status='completed').count()
                completion_rate = (completed_kr / total_kr * 100) if total_kr > 0 else 0
                
                month_name = month_end.strftime('%B %Y')
                key_results_trend[month_name] = completion_rate
            
            return {
                'success': True,
                'data': {
                    'monthly_objective_progress': monthly_progress,
                    'key_results_completion_trend': key_results_trend,
                    'period': f'{start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
                },
                'query_type': 'performance_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil tren kinerja: {str(e)}'}
    
    def get_data_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get performance data summary"""
        try:
            from django.db import models
            from datetime import datetime, timedelta
            
            if employee_id:
                # Individual performance summary
                total_objectives = EmployeeObjective.objects.filter(employee_id=employee_id).count()
                completed_objectives = EmployeeObjective.objects.filter(
                    employee_id=employee_id,
                    status='completed'
                ).count()
                
                in_progress_objectives = EmployeeObjective.objects.filter(
                    employee_id=employee_id,
                    status='in_progress'
                ).count()
                
                # Get average progress
                avg_progress = EmployeeObjective.objects.filter(
                    employee_id=employee_id
                ).aggregate(avg=models.Avg('progress'))['avg'] or 0
                
                # Get key results summary
                total_key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id
                ).count()
                
                completed_key_results = KeyResult.objects.filter(
                    employee_objective__employee_id=employee_id,
                    status='completed'
                ).count()
                
                # Get recent feedback count
                recent_feedbacks = Feedback.objects.filter(
                    employee_id=employee_id,
                    created_at__gte=datetime.now() - timedelta(days=90)
                ).count()
                
                return {
                    'total_objectives': total_objectives,
                    'completed_objectives': completed_objectives,
                    'in_progress_objectives': in_progress_objectives,
                    'completion_rate': (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0,
                    'average_progress': float(avg_progress),
                    'total_key_results': total_key_results,
                    'completed_key_results': completed_key_results,
                    'recent_feedbacks_count': recent_feedbacks
                }
            else:
                # Company-wide performance summary
                total_objectives = EmployeeObjective.objects.count()
                completed_objectives = EmployeeObjective.objects.filter(status='completed').count()
                
                return {
                    'total_objectives': total_objectives,
                    'completed_objectives': completed_objectives,
                    'completion_rate': (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0
                }
        except Exception as e:
            return {
                'error': f'Error getting performance summary: {str(e)}'
            }
    
    def _get_employee_objectives(self, employee_id: int) -> Dict[str, Any]:
        """Get employee objectives"""
        try:
            objectives = EmployeeObjective.objects.filter(
                employee_id=employee_id
            ).select_related('objective_id')
            
            objectives_data = []
            for obj in objectives:
                objectives_data.append({
                    'id': obj.id,
                    'title': obj.objective_id.title,
                    'description': obj.objective_id.description,
                    'status': obj.status,
                    'progress': obj.progress,
                    'start_date': obj.start_date,
                    'end_date': obj.end_date
                })
            
            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'objectives': objectives_data
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_feedback_history(self, employee_id: int) -> Dict[str, Any]:
        """Get feedback history"""
        try:
            feedbacks = Feedback.objects.filter(
                employee_id=employee_id
            ).order_by('-created_at')[:10]
            
            feedback_data = []
            for feedback in feedbacks:
                feedback_data.append({
                    'id': feedback.id,
                    'feedback_type': 'received',  # Could be 'given' or 'received'
                    'created_at': feedback.created_at,
                    'status': getattr(feedback, 'status', 'active')
                })
            
            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'feedback_history': feedback_data
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_performance_summary(self, employee_id: int) -> Dict[str, Any]:
        """Get performance summary"""
        try:
            # Get objectives summary
            total_objectives = EmployeeObjective.objects.filter(
                employee_id=employee_id
            ).count()
            
            completed_objectives = EmployeeObjective.objects.filter(
                employee_id=employee_id,
                status='completed'
            ).count()
            
            # Get key results summary
            key_results = KeyResult.objects.filter(
                employee_objective__employee_id=employee_id
            )
            
            avg_progress = 0
            if key_results.exists():
                total_progress = sum([kr.progress_percentage for kr in key_results if kr.progress_percentage])
                avg_progress = total_progress / key_results.count()
            
            return {
                'success': True,
                'data': {
                    'employee_id': employee_id,
                    'objectives_summary': {
                        'total': total_objectives,
                        'completed': completed_objectives,
                        'completion_rate': (completed_objectives / total_objectives * 100) if total_objectives > 0 else 0
                    },
                    'average_progress': avg_progress,
                    'total_key_results': key_results.count()
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class PayrollDataProcessor(HRDataProcessor):
    """Processor untuk data payroll"""
    
    def process_query(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process payroll-related queries"""
        try:
            from payroll.models.models import Payslip, Contract, Allowance, Deduction, LoanAccount, Reimbursement
            from datetime import datetime, timedelta
            
            employee_id = context.get('employee_id')
            if not employee_id:
                return {
                    'success': False,
                    'error': 'Employee ID diperlukan untuk query data penggajian'
                }
            
            query_lower = query.lower()
            data = {}
            
            # Payslip query
            if any(keyword in query_lower for keyword in ['slip gaji', 'payslip', 'gaji', 'salary', 'pembayaran']):
                return self._get_recent_payslips(employee_id)
            
            # Contract query
            elif any(keyword in query_lower for keyword in ['kontrak', 'contract', 'perjanjian', 'employment']):
                return self._get_contract_info(employee_id)
            
            # Allowances query
            elif any(keyword in query_lower for keyword in ['tunjangan', 'allowance', 'benefit', 'tambahan']):
                return self._get_allowances(employee_id)
            
            # Deductions query
            elif any(keyword in query_lower for keyword in ['potongan', 'deduction', 'pengurangan']):
                return self._get_deductions(employee_id)
            
            # Loan account query
            elif any(keyword in query_lower for keyword in ['pinjaman', 'loan', 'hutang', 'kredit']):
                return self._get_loans(employee_id)
            
            # Reimbursement query
            elif any(keyword in query_lower for keyword in ['reimbursement', 'penggantian', 'klaim', 'refund']):
                return self._get_reimbursements(employee_id)
            
            # Salary history/statistics
            elif any(keyword in query_lower for keyword in ['riwayat', 'history', 'statistik', 'stats', 'total']):
                return self._get_salary_statistics(employee_id)
            
            # Default: return salary info
            else:
                return self._get_salary_info(employee_id)
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error memproses query penggajian: {str(e)}'
            }
    
    def get_data_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get payroll data summary"""
        try:
            from payroll.models.models import Payslip, Contract, LoanAccount, Reimbursement
            from django.db import models
            from datetime import datetime
            
            if employee_id:
                # Individual payroll summary
                latest_payslip = Payslip.objects.filter(
                    employee_id=employee_id
                ).order_by('-created_at').first()
                
                active_contract = Contract.objects.filter(
                    employee_id=employee_id,
                    contract_status='active'
                ).first()
                
                # Get this year's total earnings
                current_year = datetime.now().year
                year_payslips = Payslip.objects.filter(
                    employee_id=employee_id,
                    start_date__year=current_year,
                    status='paid'
                )
                
                total_earnings = year_payslips.aggregate(
                    total=models.Sum('net_pay')
                )['total'] or 0
                
                # Get pending payslips
                pending_payslips = Payslip.objects.filter(
                    employee_id=employee_id,
                    status__in=['draft', 'review_ongoing']
                ).count()
                
                # Get active loans
                active_loans = LoanAccount.objects.filter(
                    employee_id=employee_id,
                    status='active'
                )
                
                total_loan_balance = active_loans.aggregate(
                    total=models.Sum('balance')
                )['total'] or 0
                
                # Get pending reimbursements
                pending_reimbursements = Reimbursement.objects.filter(
                    employee_id=employee_id,
                    status__in=['requested', 'pending']
                ).count()
                
                return {
                    'latest_payslip': {
                        'gross_pay': float(latest_payslip.gross_pay) if latest_payslip and latest_payslip.gross_pay else 0,
                        'net_pay': float(latest_payslip.net_pay) if latest_payslip and latest_payslip.net_pay else 0,
                        'status': latest_payslip.status if latest_payslip else None,
                        'period': f"{latest_payslip.start_date} - {latest_payslip.end_date}" if latest_payslip else None
                    },
                    'contract': {
                        'basic_salary': float(active_contract.basic_pay) if active_contract and active_contract.basic_pay else 0,
                        'wage_type': active_contract.wage_type if active_contract else None,
                        'status': active_contract.contract_status if active_contract else None
                    },
                    'year_summary': {
                        'total_earnings': float(total_earnings),
                        'pending_payslips': pending_payslips,
                        'year': current_year
                    },
                    'loans': {
                        'active_count': active_loans.count(),
                        'total_balance': float(total_loan_balance)
                    },
                    'reimbursements': {
                        'pending_count': pending_reimbursements
                    }
                }
            else:
                # Company-wide payroll summary
                total_payslips = Payslip.objects.count()
                total_gross_pay = Payslip.objects.aggregate(
                    total=models.Sum('gross_pay')
                )['total'] or 0
                
                return {
                    'total_payslips': total_payslips,
                    'total_gross_pay': float(total_gross_pay),
                    'average_gross_pay': float(total_gross_pay) / total_payslips if total_payslips > 0 else 0
                }
        except Exception as e:
            return {
                'error': f'Error getting payroll summary: {str(e)}'
            }
    
    def _get_recent_payslips(self, employee_id: int) -> Dict[str, Any]:
        """Get recent payslips"""
        try:
            from payroll.models.models import Payslip
            
            payslips = Payslip.objects.filter(
                employee_id=employee_id
            ).order_by('-created_at')[:12]  # Last 12 payslips
            
            payslips_data = []
            for payslip in payslips:
                payslips_data.append({
                    'title': payslip.title,
                    'period': f"{payslip.start_date} - {payslip.end_date}" if payslip.start_date and payslip.end_date else None,
                    'basic_pay': float(payslip.basic_pay) if payslip.basic_pay else 0,
                    'gross_pay': float(payslip.gross_pay) if payslip.gross_pay else 0,
                    'deduction': float(payslip.deduction) if payslip.deduction else 0,
                    'allowance': float(payslip.allowance) if payslip.allowance else 0,
                    'net_pay': float(payslip.net_pay) if payslip.net_pay else 0,
                    'status': payslip.status,
                    'created_date': payslip.created_at.strftime('%Y-%m-%d')
                })
            
            return {
                'success': True,
                'data': {
                    'payslips': payslips_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil slip gaji: {str(e)}'}
    
    def _get_contract_info(self, employee_id: int) -> Dict[str, Any]:
        """Get contract information"""
        try:
            from payroll.models.models import Contract
            
            contracts = Contract.objects.filter(
                employee_id=employee_id
            ).select_related(
                'department', 'job_position', 'job_role'
            ).order_by('-created_at')[:5]
            
            contracts_data = []
            for contract in contracts:
                contracts_data.append({
                    'contract_name': contract.contract_name,
                    'wage_type': contract.wage_type,
                    'pay_frequency': contract.pay_frequency,
                    'basic_pay': float(contract.basic_pay) if contract.basic_pay else 0,
                    'contract_status': contract.contract_status,
                    'start_date': contract.contract_start_date.strftime('%Y-%m-%d') if contract.contract_start_date else None,
                    'end_date': contract.contract_end_date.strftime('%Y-%m-%d') if contract.contract_end_date else None,
                    'department': contract.department.department if contract.department else None,
                    'job_position': contract.job_position.job_position if contract.job_position else None,
                    'job_role': contract.job_role.job_role if contract.job_role else None,
                    'notice_period': contract.notice_period
                })
            
            return {
                'success': True,
                'data': {
                    'contracts': contracts_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil informasi kontrak: {str(e)}'}
    
    def _get_salary_info(self, employee_id: int) -> Dict[str, Any]:
        """Get salary information"""
        try:
            from payroll.models.models import Payslip, Contract
            
            # Get latest payslip for current salary info
            latest_payslip = Payslip.objects.filter(
                employee_id=employee_id
            ).order_by('-created_at').first()
            
            # Get active contract for base salary
            active_contract = Contract.objects.filter(
                employee_id=employee_id,
                contract_status='active'
            ).first()
            
            salary_data = {}
            
            if latest_payslip:
                salary_data['latest_payslip'] = {
                    'title': latest_payslip.title,
                    'basic_pay': float(latest_payslip.basic_pay) if latest_payslip.basic_pay else 0,
                    'gross_pay': float(latest_payslip.gross_pay) if latest_payslip.gross_pay else 0,
                    'net_pay': float(latest_payslip.net_pay) if latest_payslip.net_pay else 0,
                    'status': latest_payslip.status,
                    'start_date': latest_payslip.start_date.strftime('%Y-%m-%d') if latest_payslip.start_date else None,
                    'end_date': latest_payslip.end_date.strftime('%Y-%m-%d') if latest_payslip.end_date else None
                }
            
            if active_contract:
                salary_data['active_contract'] = {
                    'contract_name': active_contract.contract_name,
                    'basic_pay': float(active_contract.basic_pay) if active_contract.basic_pay else 0,
                    'wage_type': active_contract.wage_type,
                    'pay_frequency': active_contract.pay_frequency,
                    'contract_status': active_contract.contract_status
                }
            
            return {
                'success': True,
                'data': salary_data,
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil informasi gaji: {str(e)}'}
    
    def _get_allowances(self, employee_id: int) -> Dict[str, Any]:
        """Get employee allowances"""
        try:
            from payroll.models.models import Allowance
            from django.db import models
            
            # Get allowances that apply to this employee
            allowances = Allowance.objects.filter(
                specific_employees=employee_id
            ).order_by('-created_at')[:10]
            
            # Also get general allowances for all employees
            general_allowances = Allowance.objects.filter(
                include_active_employees=True
            ).order_by('-created_at')[:10]
            
            allowances_data = []
            
            # Add specific allowances
            for allowance in allowances:
                allowances_data.append({
                    'title': allowance.title,
                    'amount': float(allowance.amount) if allowance.amount else 0,
                    'is_fixed': allowance.is_fixed,
                    'is_taxable': allowance.is_taxable,
                    'type': 'specific',
                    'created_date': allowance.created_at.strftime('%Y-%m-%d')
                })
            
            # Add general allowances
            for allowance in general_allowances:
                allowances_data.append({
                    'title': allowance.title,
                    'amount': float(allowance.amount) if allowance.amount else 0,
                    'is_fixed': allowance.is_fixed,
                    'is_taxable': allowance.is_taxable,
                    'type': 'general',
                    'created_date': allowance.created_at.strftime('%Y-%m-%d')
                })
            
            return {
                'success': True,
                'data': {
                    'allowances': allowances_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil data tunjangan: {str(e)}'}
    
    def _get_deductions(self, employee_id: int) -> Dict[str, Any]:
        """Get employee deductions"""
        try:
            from payroll.models.models import Deduction
            from django.db import models
            
            # Get deductions that apply to this employee
            deductions = Deduction.objects.filter(
                specific_employees=employee_id
            ).order_by('-created_at')[:10]
            
            # Also get general deductions
            general_deductions = Deduction.objects.filter(
                include_active_employees=True
            ).order_by('-created_at')[:10]
            
            deductions_data = []
            
            # Add specific deductions
            for deduction in deductions:
                deductions_data.append({
                    'title': deduction.title,
                    'amount': float(deduction.amount) if deduction.amount else 0,
                    'is_fixed': deduction.is_fixed,
                    'is_pretax': deduction.is_pretax,
                    'type': 'specific',
                    'created_date': deduction.created_at.strftime('%Y-%m-%d')
                })
            
            # Add general deductions
            for deduction in general_deductions:
                deductions_data.append({
                    'title': deduction.title,
                    'amount': float(deduction.amount) if deduction.amount else 0,
                    'is_fixed': deduction.is_fixed,
                    'is_pretax': deduction.is_pretax,
                    'type': 'general',
                    'created_date': deduction.created_at.strftime('%Y-%m-%d')
                })
            
            return {
                'success': True,
                'data': {
                    'deductions': deductions_data
                },
                'query_type': 'payroll_data'
            }
        except Exception as e:
            return {'success': False, 'error': f'Error mengambil data potongan: {str(e)}'}


class HRAssistantOrchestrator:
    """Main orchestrator untuk HR Assistant"""
    
    def __init__(self):
        self.processors = {
            'employee': EmployeeDataProcessor(),
            'leave': LeaveDataProcessor(),
            'performance': PerformanceDataProcessor(),
            'payroll': PayrollDataProcessor()
        }
    
    def process_hr_query(self, query: str, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Process HR query dan route ke processor yang tepat"""
        query_lower = query.lower()
        context = {'employee_id': employee_id}
        
        # Determine which processor to use based on query content
        if any(keyword in query_lower for keyword in ['profil', 'profile', 'karyawan', 'employee', 'departemen', 'department', 'manajer', 'manager', 'tim', 'team']):
            return self.processors['employee'].process_query(query, context)
        
        elif any(keyword in query_lower for keyword in ['cuti', 'leave', 'saldo', 'balance', 'libur', 'holiday']):
            return self.processors['leave'].process_query(query, context)
        
        elif any(keyword in query_lower for keyword in ['kinerja', 'performance', 'objektif', 'objective', 'feedback', 'evaluasi', 'evaluation']):
            return self.processors['performance'].process_query(query, context)
        
        elif any(keyword in query_lower for keyword in ['gaji', 'salary', 'payslip', 'slip gaji', 'kontrak', 'contract', 'tunjangan', 'allowance', 'potongan', 'deduction']):
            return self.processors['payroll'].process_query(query, context)
        
        else:
            # If no specific processor matches, provide general HR summary
            return self._get_general_hr_summary(employee_id)
    
    def _get_general_hr_summary(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Get general HR summary from all processors"""
        summary = {
            'success': True,
            'data': {
                'employee_summary': self.processors['employee'].get_data_summary(employee_id),
                'leave_summary': self.processors['leave'].get_data_summary(employee_id),
                'performance_summary': self.processors['performance'].get_data_summary(employee_id),
                'payroll_summary': self.processors['payroll'].get_data_summary(employee_id)
            }
        }
        
        return summary
    
    def get_hr_insights(self, employee_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate HR insights and recommendations"""
        summary = self._get_general_hr_summary(employee_id)
        
        insights = []
        
        if employee_id:
            # Individual insights
            leave_data = summary['data']['leave_summary']
            performance_data = summary['data']['performance_summary']
            
            # Leave insights
            if leave_data.get('pending_requests', 0) > 0:
                insights.append({
                    'type': 'leave',
                    'message': f"Anda memiliki {leave_data['pending_requests']} permintaan cuti yang menunggu persetujuan.",
                    'priority': 'medium'
                })
            
            # Performance insights
            completion_rate = performance_data.get('completion_rate', 0)
            if completion_rate < 50:
                insights.append({
                    'type': 'performance',
                    'message': f"Tingkat penyelesaian objektif Anda {completion_rate:.1f}%. Pertimbangkan untuk fokus pada objektif yang belum selesai.",
                    'priority': 'high'
                })
            elif completion_rate > 80:
                insights.append({
                    'type': 'performance',
                    'message': f"Excellent! Tingkat penyelesaian objektif Anda {completion_rate:.1f}%.",
                    'priority': 'low'
                })
        
        return {
            'success': True,
            'data': {
                'insights': insights,
                'summary': summary['data']
            }
        }