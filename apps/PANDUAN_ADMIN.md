# Panduan Administrator Horilla HR System

## Daftar Isi

1. [Pengenalan Administrator](#pengenalan-administrator)
2. [Setup dan Konfigurasi Sistem](#setup-dan-konfigurasi-sistem)
3. [Manajemen User dan Permissions](#manajemen-user-dan-permissions)
4. [Konfigurasi Modul HR](#konfigurasi-modul-hr)
5. [Sistem Monitoring dan Analytics](#sistem-monitoring-dan-analytics)
6. [Backup dan Recovery](#backup-dan-recovery)
7. [Security Management](#security-management)
8. [API Management](#api-management)
9. [Troubleshooting Advanced](#troubleshooting-advanced)
10. [Maintenance dan Updates](#maintenance-dan-updates)

---

## Pengenalan Administrator

### Role dan Responsibilities

#### System Administrator:
- **Server Management**: Maintenance server dan infrastructure
- **Database Administration**: Backup, optimization, dan monitoring database
- **Security Management**: Implementasi security policies dan monitoring
- **Performance Optimization**: Tuning sistem untuk optimal performance
- **Integration Management**: Setup dan maintenance third-party integrations

#### HR Administrator:
- **User Management**: Create, update, dan deactivate user accounts
- **Policy Configuration**: Setup HR policies dan workflows
- **Data Management**: Import/export data dan reporting
- **Training Coordination**: User training dan documentation updates
- **Compliance Monitoring**: Ensure compliance dengan regulations

### Admin Dashboard Overview

Setelah login sebagai administrator, dashboard menampilkan:

```
┌─────────────────────────────────────────────────────────────┐
│                    ADMIN DASHBOARD                         │
├─────────────────────────────────────────────────────────────┤
│ System Health    │ User Activity    │ Performance Metrics │
│ ✅ All Systems OK │ 🟢 245 Active    │ 📊 Response: 120ms  │
│ 🔄 Last Backup:  │ 🔵 12 New Today  │ 💾 DB Size: 2.3GB   │
│    2 hours ago   │ ⚠️ 3 Locked      │ 🚀 Uptime: 99.98%   │
├─────────────────────────────────────────────────────────────┤
│ Quick Actions                                               │
│ [Add User] [Backup Now] [System Check] [View Logs]         │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup dan Konfigurasi Sistem

### 1. Initial System Setup

#### Environment Configuration:
```bash
# 1. Setup Environment Variables
cp .env.dist .env

# 2. Configure Database
DATABASE_URL=postgresql://user:password@localhost:5432/horilla_db
REDIS_URL=redis://localhost:6379/0

# 3. Setup AI Services
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:7b-chat

# 4. Configure Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@company.com
EMAIL_HOST_PASSWORD=your-app-password

# 5. Setup Storage
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=horilla-storage
```

#### Database Setup:
```bash
# 1. Create Database
psql -U postgres
CREATE DATABASE horilla_db;
CREATE USER horilla_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE horilla_db TO horilla_user;

# 2. Run Migrations
python manage.py makemigrations
python manage.py migrate

# 3. Create Superuser
python manage.py createsuperuser

# 4. Load Initial Data
python manage.py loaddata initial_data.json
```

### 2. Company Configuration

#### Basic Company Settings:
1. **Masuk ke Admin Panel**: `/admin/`
2. **Company Profile Setup**:
   ```
   Navigation: Admin > Company > Company Profile
   
   Required Fields:
   - Company Name: PT. Your Company Name
   - Legal Name: PT. Your Company Name Tbk
   - Tax ID: NPWP Number
   - Address: Complete company address
   - Phone/Email: Contact information
   - Logo: Upload company logo (recommended: 200x200px)
   - Timezone: Asia/Jakarta
   - Currency: IDR (Indonesian Rupiah)
   - Fiscal Year: January - December
   ```

#### Working Hours Configuration:
```python
# Settings > Working Hours
DEFAULT_WORKING_HOURS = {
    'monday': {'start': '08:00', 'end': '17:00', 'break_start': '12:00', 'break_end': '13:00'},
    'tuesday': {'start': '08:00', 'end': '17:00', 'break_start': '12:00', 'break_end': '13:00'},
    'wednesday': {'start': '08:00', 'end': '17:00', 'break_start': '12:00', 'break_end': '13:00'},
    'thursday': {'start': '08:00', 'end': '17:00', 'break_start': '12:00', 'break_end': '13:00'},
    'friday': {'start': '08:00', 'end': '17:00', 'break_start': '12:00', 'break_end': '13:00'},
    'saturday': {'start': '08:00', 'end': '12:00'},  # Half day
    'sunday': None  # Off day
}

# Overtime Rules
OVERTIME_RULES = {
    'weekday_multiplier': 1.5,
    'weekend_multiplier': 2.0,
    'holiday_multiplier': 3.0,
    'minimum_overtime_minutes': 30,
    'maximum_daily_overtime': 4  # hours
}
```

### 3. Department dan Job Position Setup

#### Department Hierarchy:
```
Navigation: Admin > Organization > Departments

Example Structure:
├── Executive
│   ├── CEO
│   └── Board of Directors
├── Human Resources
│   ├── HR Manager
│   ├── HR Generalist
│   └── Recruiter
├── Information Technology
│   ├── IT Manager
│   ├── Software Developer
│   ├── System Administrator
│   └── DevOps Engineer
├── Finance & Accounting
│   ├── Finance Manager
│   ├── Accountant
│   └── Finance Analyst
└── Marketing & Sales
    ├── Marketing Manager
    ├── Sales Representative
    └── Digital Marketing Specialist
```

#### Job Position Configuration:
```json
{
  "position_code": "IT-DEV-001",
  "title": "Senior Software Developer",
  "department": "Information Technology",
  "level": "Senior",
  "reports_to": "IT Manager",
  "salary_range": {
    "min": 15000000,
    "max": 25000000,
    "currency": "IDR"
  },
  "requirements": [
    "Bachelor's degree in Computer Science",
    "5+ years experience in software development",
    "Proficiency in Python, Django, JavaScript",
    "Experience with cloud platforms (AWS/GCP)"
  ],
  "responsibilities": [
    "Develop and maintain web applications",
    "Code review and mentoring junior developers",
    "Participate in system architecture decisions",
    "Ensure code quality and best practices"
  ]
}
```

---

## Manajemen User dan Permissions

### 1. User Role Management

#### Predefined Roles:

```python
# Role Hierarchy
ROLES = {
    'SUPER_ADMIN': {
        'level': 1,
        'permissions': ['*'],  # All permissions
        'description': 'Full system access'
    },
    'HR_ADMIN': {
        'level': 2,
        'permissions': [
            'employee.view', 'employee.add', 'employee.change',
            'attendance.view', 'attendance.change',
            'leave.view', 'leave.approve',
            'payroll.view', 'payroll.process',
            'recruitment.view', 'recruitment.manage'
        ],
        'description': 'HR management access'
    },
    'MANAGER': {
        'level': 3,
        'permissions': [
            'employee.view_team',
            'attendance.view_team',
            'leave.approve_team',
            'performance.manage_team'
        ],
        'description': 'Team management access'
    },
    'EMPLOYEE': {
        'level': 4,
        'permissions': [
            'profile.view_own', 'profile.change_own',
            'attendance.view_own',
            'leave.apply',
            'payroll.view_own'
        ],
        'description': 'Basic employee access'
    }
}
```

#### Custom Permission Setup:
```python
# Navigation: Admin > Auth > Permissions

# Create Custom Permission
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# Example: Budget approval permission
content_type = ContentType.objects.get_for_model(Budget)
permission = Permission.objects.create(
    codename='approve_budget',
    name='Can approve budget requests',
    content_type=content_type,
)

# Assign to role
hr_admin_group = Group.objects.get(name='HR_ADMIN')
hr_admin_group.permissions.add(permission)
```

### 2. Bulk User Management

#### CSV Import Template:
```csv
first_name,last_name,email,employee_id,department,position,manager_email,start_date,salary
John,Doe,john.doe@company.com,EMP001,IT,Software Developer,it.manager@company.com,2024-01-15,15000000
Jane,Smith,jane.smith@company.com,EMP002,HR,HR Generalist,hr.manager@company.com,2024-01-20,12000000
```

#### Bulk Import Process:
```python
# Navigation: Admin > Employees > Bulk Import

# 1. Download template
# 2. Fill employee data
# 3. Upload CSV file
# 4. Review import preview
# 5. Confirm import

# Validation Rules:
VALIDATION_RULES = {
    'email': 'Must be unique and valid format',
    'employee_id': 'Must be unique',
    'department': 'Must exist in system',
    'position': 'Must exist in system',
    'manager_email': 'Must be existing employee',
    'start_date': 'Format: YYYY-MM-DD',
    'salary': 'Numeric value only'
}
```

### 3. User Lifecycle Management

#### Onboarding Workflow:
```python
# Automated Onboarding Process
ONBOARDING_CHECKLIST = {
    'pre_arrival': [
        'Create user account',
        'Setup email and system access',
        'Prepare workspace',
        'Order equipment',
        'Schedule orientation'
    ],
    'day_1': [
        'Welcome orientation',
        'System training',
        'Policy acknowledgment',
        'Emergency contact setup',
        'Photo and ID card'
    ],
    'week_1': [
        'Department introduction',
        'Role-specific training',
        'Mentor assignment',
        'Goal setting',
        'Feedback session'
    ],
    'month_1': [
        'Performance check-in',
        'Training completion review',
        'Feedback collection',
        'Probation evaluation'
    ]
}
```

#### Offboarding Process:
```python
# Employee Departure Checklist
OFFBOARDING_CHECKLIST = {
    'notice_period': [
        'Exit interview scheduling',
        'Knowledge transfer planning',
        'Access review',
        'Equipment inventory'
    ],
    'last_week': [
        'Final payroll calculation',
        'Benefits termination',
        'Return company property',
        'Access revocation',
        'Exit interview'
    ],
    'post_departure': [
        'Final documentation',
        'Reference letter preparation',
        'Alumni network invitation',
        'Feedback analysis'
    ]
}
```

---

## Konfigurasi Modul HR

### 1. Attendance Management

#### Geofencing Setup:
```python
# Navigation: Admin > Attendance > Geofencing

GEOFENCE_CONFIG = {
    'main_office': {
        'name': 'Head Office Jakarta',
        'latitude': -6.2088,
        'longitude': 106.8456,
        'radius': 100,  # meters
        'address': 'Jl. Sudirman No. 1, Jakarta',
        'timezone': 'Asia/Jakarta'
    },
    'branch_office': {
        'name': 'Branch Office Surabaya',
        'latitude': -7.2575,
        'longitude': 112.7521,
        'radius': 150,
        'address': 'Jl. Pemuda No. 50, Surabaya',
        'timezone': 'Asia/Jakarta'
    }
}

# Attendance Rules
ATTENDANCE_RULES = {
    'grace_period': 15,  # minutes
    'late_threshold': 30,  # minutes
    'half_day_threshold': 4,  # hours
    'overtime_threshold': 8,  # hours
    'break_duration': 60,  # minutes
    'auto_checkout': True,
    'auto_checkout_time': '18:00'
}
```

#### Shift Management:
```python
# Multiple Shift Configuration
SHIFT_PATTERNS = {
    'regular': {
        'name': 'Regular Shift',
        'start_time': '08:00',
        'end_time': '17:00',
        'break_start': '12:00',
        'break_end': '13:00',
        'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    },
    'early': {
        'name': 'Early Shift',
        'start_time': '06:00',
        'end_time': '15:00',
        'break_start': '10:00',
        'break_end': '10:30',
        'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
    },
    'night': {
        'name': 'Night Shift',
        'start_time': '22:00',
        'end_time': '06:00',  # Next day
        'break_start': '02:00',
        'break_end': '02:30',
        'days': ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']
    }
}
```

### 2. Leave Management

#### Leave Types Configuration:
```python
# Navigation: Admin > Leave > Leave Types

LEAVE_TYPES = {
    'annual': {
        'name': 'Annual Leave',
        'allocation': 12,  # days per year
        'carry_forward': 5,  # max days
        'advance_booking': 30,  # days
        'requires_approval': True,
        'approval_levels': 1,
        'documentation_required': False
    },
    'sick': {
        'name': 'Sick Leave',
        'allocation': 12,
        'carry_forward': 0,
        'advance_booking': 0,
        'requires_approval': True,
        'approval_levels': 1,
        'documentation_required': True,  # Medical certificate
        'max_consecutive_days': 3  # Without medical cert
    },
    'maternity': {
        'name': 'Maternity Leave',
        'allocation': 90,  # days
        'carry_forward': 0,
        'advance_booking': 60,
        'requires_approval': True,
        'approval_levels': 2,
        'documentation_required': True,
        'gender_restriction': 'female'
    },
    'paternity': {
        'name': 'Paternity Leave',
        'allocation': 14,
        'carry_forward': 0,
        'advance_booking': 30,
        'requires_approval': True,
        'approval_levels': 1,
        'documentation_required': True,
        'gender_restriction': 'male'
    }
}
```

#### Approval Workflow:
```python
# Multi-level Approval Configuration
APPROVAL_WORKFLOW = {
    'level_1': {
        'approver': 'direct_manager',
        'conditions': {
            'leave_days': {'max': 5},
            'leave_types': ['annual', 'sick']
        },
        'auto_approve': {
            'sick_leave': {'max_days': 1, 'frequency': 'monthly'}
        }
    },
    'level_2': {
        'approver': 'department_head',
        'conditions': {
            'leave_days': {'min': 6, 'max': 15},
            'leave_types': ['annual', 'emergency']
        }
    },
    'level_3': {
        'approver': 'hr_manager',
        'conditions': {
            'leave_days': {'min': 16},
            'leave_types': ['maternity', 'paternity', 'sabbatical']
        }
    }
}
```

### 3. Payroll Configuration

#### Salary Components:
```python
# Navigation: Admin > Payroll > Salary Components

SALARY_COMPONENTS = {
    'basic_salary': {
        'type': 'earning',
        'calculation': 'fixed',
        'taxable': True,
        'mandatory': True
    },
    'transport_allowance': {
        'type': 'earning',
        'calculation': 'fixed',
        'amount': 500000,  # IDR
        'taxable': True
    },
    'meal_allowance': {
        'type': 'earning',
        'calculation': 'attendance_based',
        'rate_per_day': 25000,
        'taxable': False
    },
    'overtime_pay': {
        'type': 'earning',
        'calculation': 'overtime_hours',
        'multiplier': 1.5,
        'taxable': True
    },
    'income_tax': {
        'type': 'deduction',
        'calculation': 'progressive_tax',
        'tax_brackets': [
            {'min': 0, 'max': 60000000, 'rate': 0.05},
            {'min': 60000000, 'max': 250000000, 'rate': 0.15},
            {'min': 250000000, 'max': 500000000, 'rate': 0.25},
            {'min': 500000000, 'max': None, 'rate': 0.30}
        ]
    },
    'bpjs_kesehatan': {
        'type': 'deduction',
        'calculation': 'percentage',
        'employee_rate': 0.01,  # 1%
        'employer_rate': 0.04,  # 4%
        'max_salary': 12000000
    }
}
```

#### Payroll Processing:
```python
# Monthly Payroll Process
PAYROLL_PROCESS = {
    'cutoff_date': 25,  # Day of month
    'processing_steps': [
        'attendance_calculation',
        'overtime_calculation',
        'leave_deduction',
        'tax_calculation',
        'bpjs_calculation',
        'net_salary_calculation',
        'payslip_generation',
        'bank_file_generation'
    ],
    'approval_required': True,
    'auto_email_payslips': True,
    'bank_integration': {
        'enabled': True,
        'format': 'BCA_H2H',
        'encryption': True
    }
}
```

---

## Sistem Monitoring dan Analytics

### 1. Real-time Monitoring

#### System Health Dashboard:
```python
# Navigation: Admin > Monitoring > System Health

MONITORING_METRICS = {
    'system_performance': {
        'cpu_usage': {'threshold': 80, 'critical': 95},
        'memory_usage': {'threshold': 85, 'critical': 95},
        'disk_usage': {'threshold': 80, 'critical': 90},
        'response_time': {'threshold': 500, 'critical': 1000}  # ms
    },
    'database_health': {
        'connection_count': {'threshold': 80, 'critical': 95},
        'query_performance': {'threshold': 1000, 'critical': 5000},  # ms
        'deadlocks': {'threshold': 5, 'critical': 10},  # per hour
        'backup_status': {'frequency': 'daily', 'retention': 30}  # days
    },
    'application_metrics': {
        'active_users': {'normal_range': [50, 300]},
        'login_failures': {'threshold': 10, 'critical': 50},  # per hour
        'api_errors': {'threshold': 5, 'critical': 20},  # per minute
        'queue_length': {'threshold': 100, 'critical': 500}
    }
}
```

#### Alert Configuration:
```python
# Alert Rules
ALERT_RULES = {
    'critical_alerts': {
        'recipients': ['admin@company.com', 'it-team@company.com'],
        'channels': ['email', 'slack', 'sms'],
        'escalation': {
            'level_1': {'delay': 0, 'recipients': ['on-call-engineer']},
            'level_2': {'delay': 15, 'recipients': ['it-manager']},
            'level_3': {'delay': 30, 'recipients': ['cto']}
        }
    },
    'warning_alerts': {
        'recipients': ['it-team@company.com'],
        'channels': ['email', 'slack'],
        'frequency': 'hourly'  # Suppress duplicate alerts
    }
}
```

### 2. HR Analytics

#### Employee Analytics:
```python
# Navigation: Admin > Analytics > Employee Insights

ANALYTICS_DASHBOARDS = {
    'employee_overview': {
        'total_employees': 'COUNT(active_employees)',
        'new_hires_mtd': 'COUNT(employees WHERE start_date >= month_start)',
        'departures_mtd': 'COUNT(employees WHERE end_date >= month_start)',
        'turnover_rate': '(departures_ytd / avg_headcount) * 100',
        'diversity_metrics': {
            'gender_distribution': 'GROUP BY gender',
            'age_distribution': 'GROUP BY age_bracket',
            'department_distribution': 'GROUP BY department'
        }
    },
    'attendance_analytics': {
        'attendance_rate': '(present_days / total_working_days) * 100',
        'punctuality_rate': '(on_time_arrivals / total_arrivals) * 100',
        'overtime_trends': 'SUM(overtime_hours) GROUP BY month',
        'absenteeism_rate': '(absent_days / total_working_days) * 100'
    },
    'performance_metrics': {
        'goal_completion_rate': '(completed_goals / total_goals) * 100',
        'performance_distribution': 'GROUP BY performance_rating',
        'training_completion': '(completed_trainings / assigned_trainings) * 100'
    }
}
```

#### Custom Reports:
```python
# Report Builder Configuration
REPORT_TEMPLATES = {
    'monthly_hr_report': {
        'sections': [
            'employee_summary',
            'attendance_overview',
            'leave_analysis',
            'recruitment_pipeline',
            'performance_highlights'
        ],
        'schedule': 'monthly',
        'recipients': ['hr-team@company.com', 'management@company.com'],
        'format': ['pdf', 'excel']
    },
    'payroll_summary': {
        'sections': [
            'payroll_costs',
            'overtime_analysis',
            'tax_summary',
            'benefit_costs'
        ],
        'schedule': 'monthly',
        'recipients': ['finance@company.com', 'hr-manager@company.com'],
        'format': ['excel']
    }
}
```

---

## Backup dan Recovery

### 1. Backup Strategy

#### Automated Backup Configuration:
```bash
# Database Backup Script
#!/bin/bash

# Configuration
DB_NAME="horilla_db"
DB_USER="horilla_user"
BACKUP_DIR="/var/backups/horilla"
S3_BUCKET="horilla-backups"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Generate backup filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${DB_NAME}_${TIMESTAMP}.sql"

# Create database backup
pg_dump -U $DB_USER -h localhost $DB_NAME > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Upload to S3
aws s3 cp $BACKUP_DIR/${BACKUP_FILE}.gz s3://$S3_BUCKET/database/

# Clean old local backups
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete

# Media files backup
rsync -av /path/to/media/ s3://$S3_BUCKET/media/

echo "Backup completed: ${BACKUP_FILE}.gz"
```

#### Backup Schedule:
```cron
# Crontab configuration
# Daily database backup at 2 AM
0 2 * * * /opt/horilla/scripts/backup_database.sh

# Weekly full system backup at 3 AM Sunday
0 3 * * 0 /opt/horilla/scripts/backup_full_system.sh

# Hourly media sync during business hours
0 8-18 * * 1-5 /opt/horilla/scripts/sync_media.sh
```

### 2. Disaster Recovery

#### Recovery Procedures:
```bash
# Database Recovery
#!/bin/bash

# 1. Stop application services
sudo systemctl stop horilla
sudo systemctl stop celery

# 2. Create new database
psql -U postgres
DROP DATABASE IF EXISTS horilla_db;
CREATE DATABASE horilla_db;
GRANT ALL PRIVILEGES ON DATABASE horilla_db TO horilla_user;

# 3. Restore from backup
gunzip -c /var/backups/horilla/horilla_db_20240115_020000.sql.gz | psql -U horilla_user horilla_db

# 4. Restore media files
aws s3 sync s3://horilla-backups/media/ /path/to/media/

# 5. Update configuration if needed
cp /etc/horilla/.env.backup /opt/horilla/.env

# 6. Run migrations (if needed)
cd /opt/horilla
python manage.py migrate

# 7. Restart services
sudo systemctl start horilla
sudo systemctl start celery

# 8. Verify system health
curl -f http://localhost:8000/health/
```

#### Recovery Testing:
```python
# Monthly DR Test Procedure
DR_TEST_CHECKLIST = [
    'Create test environment',
    'Restore latest backup',
    'Verify data integrity',
    'Test critical functions',
    'Measure recovery time',
    'Document issues',
    'Update procedures',
    'Cleanup test environment'
]

# Recovery Time Objectives (RTO)
RTO_TARGETS = {
    'database_recovery': '30 minutes',
    'full_system_recovery': '2 hours',
    'media_files_recovery': '1 hour',
    'user_access_restoration': '15 minutes'
}

# Recovery Point Objectives (RPO)
RPO_TARGETS = {
    'database': '1 hour',  # Max data loss
    'media_files': '24 hours',
    'configuration': '24 hours'
}
```

---

## Security Management

### 1. Authentication & Authorization

#### Multi-Factor Authentication:
```python
# MFA Configuration
MFA_SETTINGS = {
    'enabled': True,
    'required_roles': ['SUPER_ADMIN', 'HR_ADMIN'],
    'methods': {
        'totp': {
            'enabled': True,
            'issuer': 'Horilla HR System',
            'validity_period': 30  # seconds
        },
        'sms': {
            'enabled': True,
            'provider': 'twilio',
            'validity_period': 300  # seconds
        },
        'email': {
            'enabled': True,
            'validity_period': 600  # seconds
        }
    },
    'backup_codes': {
        'enabled': True,
        'count': 10,
        'single_use': True
    }
}
```

#### Password Policy:
```python
# Password Requirements
PASSWORD_POLICY = {
    'min_length': 12,
    'max_length': 128,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_numbers': True,
    'require_special_chars': True,
    'forbidden_patterns': [
        'password', '123456', 'qwerty',
        'company_name', 'user_name'
    ],
    'history_check': 5,  # Last 5 passwords
    'expiry_days': 90,
    'warning_days': 14,
    'lockout_attempts': 5,
    'lockout_duration': 30  # minutes
}
```

### 2. Data Protection

#### Encryption Configuration:
```python
# Data Encryption Settings
ENCRYPTION_CONFIG = {
    'database': {
        'encryption_at_rest': True,
        'algorithm': 'AES-256',
        'key_rotation': 'quarterly'
    },
    'file_storage': {
        'encryption': True,
        'algorithm': 'AES-256-GCM',
        'key_management': 'AWS_KMS'
    },
    'communication': {
        'tls_version': '1.3',
        'cipher_suites': [
            'TLS_AES_256_GCM_SHA384',
            'TLS_CHACHA20_POLY1305_SHA256'
        ]
    },
    'sensitive_fields': [
        'salary', 'bank_account', 'tax_id',
        'personal_id', 'medical_info'
    ]
}
```

#### Access Logging:
```python
# Audit Trail Configuration
AUDIT_SETTINGS = {
    'enabled': True,
    'log_level': 'INFO',
    'events': {
        'authentication': ['login', 'logout', 'failed_login'],
        'data_access': ['view', 'create', 'update', 'delete'],
        'admin_actions': ['user_create', 'permission_change', 'config_update'],
        'sensitive_operations': ['salary_view', 'report_export', 'bulk_update']
    },
    'retention': {
        'database': '2 years',
        'files': '7 years',
        'compliance': 'GDPR'  # or 'local_regulation'
    },
    'real_time_alerts': {
        'suspicious_activity': True,
        'privilege_escalation': True,
        'bulk_data_access': True
    }
}
```

### 3. Compliance Management

#### GDPR Compliance:
```python
# GDPR Configuration
GDPR_SETTINGS = {
    'data_protection_officer': 'dpo@company.com',
    'lawful_basis': 'legitimate_interest',
    'data_categories': {
        'personal_data': [
            'name', 'email', 'phone', 'address',
            'employee_id', 'photo'
        ],
        'sensitive_data': [
            'salary', 'performance_rating',
            'medical_info', 'disciplinary_records'
        ]
    },
    'retention_periods': {
        'active_employee': 'employment_duration',
        'former_employee': '7_years',
        'applicant_data': '1_year'
    },
    'data_subject_rights': {
        'access': True,
        'rectification': True,
        'erasure': True,
        'portability': True,
        'restriction': True,
        'objection': True
    }
}
```

---

## API Management

### 1. API Configuration

#### REST API Endpoints:
```python
# API URL Configuration
API_ENDPOINTS = {
    'v1': {
        'base_url': '/api/v1/',
        'authentication': 'token_based',
        'rate_limiting': {
            'requests_per_minute': 100,
            'requests_per_hour': 1000,
            'burst_limit': 20
        },
        'endpoints': {
            'employees': {
                'list': 'GET /employees/',
                'detail': 'GET /employees/{id}/',
                'create': 'POST /employees/',
                'update': 'PUT /employees/{id}/',
                'delete': 'DELETE /employees/{id}/'
            },
            'attendance': {
                'checkin': 'POST /attendance/checkin/',
                'checkout': 'POST /attendance/checkout/',
                'history': 'GET /attendance/history/',
                'summary': 'GET /attendance/summary/'
            },
            'leave': {
                'apply': 'POST /leave/apply/',
                'approve': 'POST /leave/{id}/approve/',
                'list': 'GET /leave/',
                'balance': 'GET /leave/balance/'
            }
        }
    }
}
```

#### API Authentication:
```python
# Token-based Authentication
API_AUTH_CONFIG = {
    'token_type': 'JWT',
    'token_expiry': 3600,  # 1 hour
    'refresh_token_expiry': 86400,  # 24 hours
    'algorithm': 'HS256',
    'secret_key': 'your-secret-key',
    'headers': {
        'Authorization': 'Bearer {token}'
    },
    'permissions': {
        'employee_read': ['employee.view_own', 'employee.view_team'],
        'employee_write': ['employee.change_own', 'employee.add'],
        'admin_access': ['*']
    }
}
```

### 2. Third-party Integrations

#### Slack Integration:
```python
# Slack Bot Configuration
SLACK_CONFIG = {
    'bot_token': 'xoxb-your-bot-token',
    'signing_secret': 'your-signing-secret',
    'channels': {
        'hr_notifications': '#hr-notifications',
        'general_announcements': '#general',
        'it_alerts': '#it-alerts'
    },
    'commands': {
        '/attendance': 'Show my attendance summary',
        '/leave-balance': 'Show my leave balance',
        '/apply-leave': 'Apply for leave',
        '/who-is-out': 'Show who is on leave today'
    },
    'notifications': {
        'leave_requests': True,
        'birthday_reminders': True,
        'system_alerts': True,
        'policy_updates': True
    }
}
```

#### Email Integration:
```python
# Email Service Configuration
EMAIL_CONFIG = {
    'provider': 'sendgrid',  # or 'ses', 'mailgun'
    'api_key': 'your-api-key',
    'templates': {
        'welcome_email': {
            'template_id': 'd-xxxxx',
            'subject': 'Welcome to {company_name}',
            'variables': ['employee_name', 'start_date', 'manager_name']
        },
        'leave_approval': {
            'template_id': 'd-yyyyy',
            'subject': 'Leave Request {status}',
            'variables': ['employee_name', 'leave_type', 'dates', 'status']
        },
        'payslip_notification': {
            'template_id': 'd-zzzzz',
            'subject': 'Payslip for {month} {year}',
            'variables': ['employee_name', 'month', 'year', 'net_pay']
        }
    },
    'automation': {
        'onboarding_sequence': True,
        'birthday_wishes': True,
        'policy_reminders': True,
        'training_notifications': True
    }
}
```

---

## Troubleshooting Advanced

### 1. Performance Issues

#### Database Optimization:
```sql
-- Common Performance Queries

-- 1. Identify Slow Queries
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 2. Check Index Usage
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;

-- 3. Analyze Table Sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 4. Optimize Attendance Queries
CREATE INDEX CONCURRENTLY idx_attendance_employee_date 
ON attendance_attendance(employee_id, attendance_date);

CREATE INDEX CONCURRENTLY idx_attendance_date_range 
ON attendance_attendance(attendance_date) 
WHERE attendance_date >= CURRENT_DATE - INTERVAL '30 days';
```

#### Application Performance:
```python
# Performance Monitoring
PERFORMANCE_CONFIG = {
    'caching': {
        'backend': 'redis',
        'location': 'redis://localhost:6379/1',
        'timeout': 3600,
        'key_prefix': 'horilla',
        'strategies': {
            'employee_list': 300,  # 5 minutes
            'department_tree': 1800,  # 30 minutes
            'leave_balance': 600,  # 10 minutes
            'payroll_summary': 3600  # 1 hour
        }
    },
    'database_pooling': {
        'max_connections': 20,
        'min_connections': 5,
        'connection_timeout': 30,
        'idle_timeout': 300
    },
    'async_tasks': {
        'broker': 'redis://localhost:6379/2',
        'result_backend': 'redis://localhost:6379/3',
        'task_routes': {
            'email_tasks': {'queue': 'email'},
            'report_generation': {'queue': 'reports'},
            'data_processing': {'queue': 'processing'}
        }
    }
}
```

### 2. Common Error Resolution

#### Database Connection Issues:
```bash
# Diagnosis Commands

# 1. Check PostgreSQL Status
sudo systemctl status postgresql

# 2. Check Connection Limits
psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# 3. Check Database Locks
psql -U postgres -c "
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;"

# 4. Kill Blocking Queries (if needed)
psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <blocking_pid>;"
```

#### Memory Issues:
```bash
# Memory Diagnosis

# 1. Check System Memory
free -h
cat /proc/meminfo

# 2. Check Process Memory Usage
ps aux --sort=-%mem | head -20

# 3. Check Django Memory Usage
python manage.py shell
>>> import psutil
>>> process = psutil.Process()
>>> print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# 4. Memory Optimization
# Add to settings.py
DATABASES = {
    'default': {
        # ... other settings
        'CONN_MAX_AGE': 600,  # Connection pooling
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    }
}

# Enable query optimization
DEBUG = False  # In production
ALLOWED_HOSTS = ['your-domain.com']
USE_TZ = True
```

### 3. Log Analysis

#### Log Configuration:
```python
# Comprehensive Logging Setup
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/horilla/django.log',
            'maxBytes': 1024*1024*50,  # 50 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/horilla/error.log',
            'maxBytes': 1024*1024*50,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/horilla/security.log',
            'maxBytes': 1024*1024*50,
            'backupCount': 10,
            'formatter': 'json',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'horilla': {
            'handlers': ['file', 'error_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

#### Log Analysis Scripts:
```bash
#!/bin/bash
# Log Analysis Script

LOG_DIR="/var/log/horilla"
DATE=$(date +"%Y-%m-%d")

echo "=== Horilla Log Analysis for $DATE ==="

# 1. Error Summary
echo "\n--- Error Summary ---"
grep "ERROR" $LOG_DIR/django.log | grep $DATE | wc -l
echo "Total errors today"

# 2. Most Common Errors
echo "\n--- Most Common Errors ---"
grep "ERROR" $LOG_DIR/django.log | grep $DATE | \
    awk '{print $6}' | sort | uniq -c | sort -nr | head -10

# 3. Performance Issues
echo "\n--- Slow Queries (>1s) ---"
grep "slow query" $LOG_DIR/django.log | grep $DATE | wc -l

# 4. Security Events
echo "\n--- Security Events ---"
grep -E "(failed login|suspicious|unauthorized)" $LOG_DIR/security.log | \
    grep $DATE | wc -l

# 5. User Activity
echo "\n--- User Activity ---"
grep "login" $LOG_DIR/django.log | grep $DATE | \
    awk '{print $8}' | sort | uniq -c | sort -nr | head -10

# 6. API Usage
echo "\n--- API Usage ---"
grep "api/v1" $LOG_DIR/django.log | grep $DATE | \
    awk '{print $7}' | sort | uniq -c | sort -nr | head -10
```

---

## Maintenance dan Updates

### 1. Regular Maintenance Tasks

#### Daily Tasks:
```bash
#!/bin/bash
# Daily Maintenance Script

# 1. Check System Health
curl -f http://localhost:8000/health/ || echo "Health check failed"

# 2. Database Maintenance
psql -U horilla_user -d horilla_db -c "VACUUM ANALYZE;"

# 3. Clear Old Sessions
python manage.py clearsessions

# 4. Update Search Index
python manage.py update_index

# 5. Process Pending Tasks
python manage.py process_pending_tasks

# 6. Generate Daily Reports
python manage.py generate_daily_reports

# 7. Check Disk Space
df -h | awk '$5 > 80 {print "Warning: " $1 " is " $5 " full"}'

# 8. Rotate Logs
logrotate /etc/logrotate.d/horilla
```

#### Weekly Tasks:
```bash
#!/bin/bash
# Weekly Maintenance Script

# 1. Full Database Backup
/opt/horilla/scripts/backup_database.sh

# 2. Update System Packages
sudo apt update && sudo apt upgrade -y

# 3. Clean Temporary Files
find /tmp -type f -atime +7 -delete
find /var/log -name "*.log.*.gz" -mtime +30 -delete

# 4. Optimize Database
psql -U horilla_user -d horilla_db -c "REINDEX DATABASE horilla_db;"

# 5. Update SSL Certificates (if needed)
certbot renew --quiet

# 6. Security Scan
/opt/horilla/scripts/security_scan.sh

# 7. Performance Report
python manage.py generate_performance_report
```

### 2. Update Procedures

#### Application Updates:
```bash
#!/bin/bash
# Application Update Script

APP_DIR="/opt/horilla"
BACKUP_DIR="/var/backups/horilla"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "Starting Horilla update process..."

# 1. Create backup
echo "Creating backup..."
mkdir -p $BACKUP_DIR/update_$TIMESTAMP
cp -r $APP_DIR $BACKUP_DIR/update_$TIMESTAMP/
pg_dump -U horilla_user horilla_db > $BACKUP_DIR/update_$TIMESTAMP/database.sql

# 2. Stop services
echo "Stopping services..."
sudo systemctl stop horilla
sudo systemctl stop celery

# 3. Update code
echo "Updating application..."
cd $APP_DIR
git fetch origin
git checkout main
git pull origin main

# 4. Update dependencies
echo "Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# 5. Run migrations
echo "Running database migrations..."
python manage.py migrate

# 6. Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# 7. Run tests
echo "Running tests..."
python manage.py test --keepdb

if [ $? -eq 0 ]; then
    echo "Tests passed. Starting services..."
    sudo systemctl start horilla
    sudo systemctl start celery
    
    # 8. Verify deployment
    sleep 10
    curl -f http://localhost:8000/health/
    
    if [ $? -eq 0 ]; then
        echo "Update completed successfully!"
    else
        echo "Health check failed. Rolling back..."
        # Rollback procedure here
    fi
else
    echo "Tests failed. Rolling back..."
    # Rollback procedure here
fi
```

#### Rollback Procedure:
```bash
#!/bin/bash
# Rollback Script

BACKUP_DIR="/var/backups/horilla"
APP_DIR="/opt/horilla"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Available backups:"
    ls -la $BACKUP_DIR/ | grep update_
    exit 1
fi

BACKUP_TIMESTAMP=$1
BACKUP_PATH="$BACKUP_DIR/update_$BACKUP_TIMESTAMP"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "Backup not found: $BACKUP_PATH"
    exit 1
fi

echo "Rolling back to backup: $BACKUP_TIMESTAMP"

# 1. Stop services
sudo systemctl stop horilla
sudo systemctl stop celery

# 2. Restore application files
rm -rf $APP_DIR
cp -r $BACKUP_PATH/horilla $APP_DIR

# 3. Restore database
psql -U postgres -c "DROP DATABASE horilla_db;"
psql -U postgres -c "CREATE DATABASE horilla_db;"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE horilla_db TO horilla_user;"
psql -U horilla_user horilla_db < $BACKUP_PATH/database.sql

# 4. Start services
sudo systemctl start horilla
sudo systemctl start celery

# 5. Verify rollback
sleep 10
curl -f http://localhost:8000/health/

if [ $? -eq 0 ]; then
    echo "Rollback completed successfully!"
else
    echo "Rollback failed. Manual intervention required."
fi
```

---

## Kesimpulan

Dokumentasi administrator ini memberikan panduan komprehensif untuk mengelola Horilla HR System secara efektif. Pastikan untuk:

1. **Backup Reguler**: Selalu maintain backup yang up-to-date
2. **Monitoring Proaktif**: Monitor sistem secara real-time
3. **Security First**: Implementasi security best practices
4. **Documentation**: Keep dokumentasi selalu updated
5. **Training**: Regular training untuk admin team

### Kontak Support

- **Technical Support**: tech-support@company.com
- **Emergency Hotline**: +62-21-XXXXXXX (24/7)
- **Documentation Updates**: docs@company.com

---

*Dokumen ini harus diupdate setiap ada perubahan sistem atau prosedur baru.*

**Last Updated**: [Current Date]
**Version**: 1.0
**Next Review**: [Date + 6 months]