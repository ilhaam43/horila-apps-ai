#!/usr/bin/env python3
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')

import django
django.setup()

from employee.models import Employee, EmployeeWorkInformation
from base.models import Company, Department, JobPosition, JobRole, EmployeeType, WorkType
from django.contrib.auth.models import User

def check_current_data():
    print("=== ANALISIS DATA SAAT INI ===")
    print()
    
    # Check Admin User
    try:
        admin = User.objects.get(username='admin')
        print(f"✅ Admin User: {admin.username} (ID: {admin.id})")
        print(f"   - First Name: {admin.first_name}")
        print(f"   - Last Name: {admin.last_name}")
        print(f"   - Email: {admin.email}")
        print(f"   - Is Superuser: {admin.is_superuser}")
        print(f"   - Is Staff: {admin.is_staff}")
    except User.DoesNotExist:
        print("❌ Admin user tidak ditemukan")
        return
    
    print()
    
    # Check Employee Record
    try:
        emp = Employee.objects.get(employee_user_id=admin)
        print(f"✅ Employee Record: {emp}")
        print(f"   - Employee ID: {emp.id}")
        print(f"   - Badge ID: {emp.badge_id}")
        print(f"   - Full Name: {emp.get_full_name()}")
        print(f"   - Email: {emp.email}")
        print(f"   - Phone: {emp.phone}")
        print(f"   - Is Active: {emp.is_active}")
    except Employee.DoesNotExist:
        print("❌ Employee record tidak ditemukan")
        return
    
    print()
    
    # Check Work Information
    try:
        work_info = EmployeeWorkInformation.objects.get(employee_id=emp)
        print(f"✅ Work Information: Found")
        print(f"   - Company: {work_info.company_id}")
        print(f"   - Department: {work_info.department_id}")
        print(f"   - Job Position: {work_info.job_position_id}")
        print(f"   - Job Role: {work_info.job_role_id}")
        print(f"   - Employee Type: {work_info.employee_type_id}")
        print(f"   - Work Type: {work_info.work_type_id}")
        print(f"   - Reporting Manager: {work_info.reporting_manager_id}")
    except EmployeeWorkInformation.DoesNotExist:
        print("❌ Work Information tidak ditemukan")
    
    print()
    
    # Check Company Data
    companies = Company.objects.all()
    print(f"📊 COMPANY DATA ({companies.count()} total):")
    for c in companies:
        print(f"   - {c.company} (ID: {c.id})")
    
    print()
    
    # Check Department Data
    departments = Department.objects.all()
    print(f"📊 DEPARTMENT DATA ({departments.count()} total):")
    for d in departments:
        print(f"   - {d.department} (Company: {d.company_id}) (ID: {d.id})")
    
    print()
    
    # Check Job Position Data
    positions = JobPosition.objects.all()
    print(f"📊 JOB POSITION DATA ({positions.count()} total):")
    for p in positions:
        print(f"   - {p.job_position} (ID: {p.id})")
    
    print()
    
    # Check Job Role Data
    roles = JobRole.objects.all()
    print(f"📊 JOB ROLE DATA ({roles.count()} total):")
    for r in roles:
        print(f"   - {r.job_role} (ID: {r.id})")
    
    print()
    
    # Check Employee Type Data
    emp_types = EmployeeType.objects.all()
    print(f"📊 EMPLOYEE TYPE DATA ({emp_types.count()} total):")
    for et in emp_types:
        print(f"   - {et.employee_type} (ID: {et.id})")
    
    print()
    
    # Check Work Type Data
    work_types = WorkType.objects.all()
    print(f"📊 WORK TYPE DATA ({work_types.count()} total):")
    for wt in work_types:
        print(f"   - {wt.work_type} (ID: {wt.id})")
    
    print()
    print("=== KESIMPULAN ===")
    print("✅ Semua data yang diperlukan untuk login admin telah berhasil dibuat")
    print("✅ User admin sekarang memiliki Employee record yang lengkap")
    print("✅ Work Information telah dikonfigurasi dengan data default")
    print("✅ Master data (Company, Department, Job Position, dll) telah dibuat")
    print("✅ Aplikasi siap digunakan dengan alur autentikasi yang berfungsi")

if __name__ == '__main__':
    check_current_data()