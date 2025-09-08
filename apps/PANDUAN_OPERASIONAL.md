# Panduan Operasional Horilla HR System

## Daftar Isi

1. [Prosedur Operasional Harian](#prosedur-operasional-harian)
2. [Monitoring dan Maintenance](#monitoring-dan-maintenance)
3. [User Management](#user-management)
4. [Data Management](#data-management)
5. [Troubleshooting Lanjutan](#troubleshooting-lanjutan)
6. [Performance Tuning](#performance-tuning)
7. [Security Operations](#security-operations)
8. [Disaster Recovery](#disaster-recovery)

---

## Prosedur Operasional Harian

### 1. Morning Startup Checklist

```bash
#!/bin/bash
# daily_startup.sh - Prosedur startup harian

echo "=== Horilla HR System Daily Startup ==="
date

# 1. Aktivasi environment
echo "[1/8] Activating virtual environment..."
source venv/bin/activate

# 2. System health check
echo "[2/8] Running system health check..."
python manage.py check --deploy

# 3. Database connectivity check
echo "[3/8] Checking database connectivity..."
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); print('✓ Database OK')"

# 4. Redis service check
echo "[4/8] Checking Redis service..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis OK"
else
    echo "⚠ Starting Redis..."
    redis-server --daemonize yes
fi

# 5. Ollama service check
echo "[5/8] Checking Ollama service..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama OK"
else
    echo "⚠ Starting Ollama..."
    ollama serve &
    sleep 5
fi

# 6. Clear expired sessions
echo "[6/8] Cleaning expired sessions..."
python manage.py clearsessions

# 7. Start background services
echo "[7/8] Starting background services..."
celery -A horilla worker --detach --loglevel=info --pidfile=celery_worker.pid
celery -A horilla beat --detach --loglevel=info --pidfile=celery_beat.pid

# 8. Start main application
echo "[8/8] Starting Django server..."
echo "✓ System ready at http://127.0.0.1:8000/"
python manage.py runserver 127.0.0.1:8000
```

### 2. Evening Shutdown Checklist

```bash
#!/bin/bash
# daily_shutdown.sh - Prosedur shutdown harian

echo "=== Horilla HR System Daily Shutdown ==="
date

# 1. Stop Celery services
echo "[1/5] Stopping Celery services..."
if [ -f celery_worker.pid ]; then
    kill -TERM $(cat celery_worker.pid)
    rm celery_worker.pid
fi

if [ -f celery_beat.pid ]; then
    kill -TERM $(cat celery_beat.pid)
    rm celery_beat.pid
fi

# 2. Backup database
echo "[2/5] Creating daily backup..."
mkdir -p backups/daily
cp db.sqlite3 backups/daily/db_$(date +%Y%m%d).sqlite3

# 3. Archive logs
echo "[3/5] Archiving logs..."
if [ -d logs ]; then
    tar -czf backups/daily/logs_$(date +%Y%m%d).tar.gz logs/
fi

# 4. Clean temporary files
echo "[4/5] Cleaning temporary files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 5. System status report
echo "[5/5] Generating status report..."
echo "Daily shutdown completed at $(date)" >> logs/operations.log
echo "✓ Shutdown complete"
```

### 3. Weekly Maintenance Tasks

```bash
#!/bin/bash
# weekly_maintenance.sh - Tugas maintenance mingguan

echo "=== Weekly Maintenance Tasks ==="
date

# 1. Database optimization
echo "[1/6] Optimizing database..."
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('VACUUM;')
cursor.execute('ANALYZE;')
print('✓ Database optimized')
"

# 2. Clear old logs
echo "[2/6] Cleaning old logs..."
find logs/ -name "*.log" -mtime +7 -delete
find backups/daily/ -name "*.sqlite3" -mtime +7 -delete

# 3. Update AI models
echo "[3/6] Checking AI model updates..."
ollama pull phi3:mini

# 4. System security scan
echo "[4/6] Running security checks..."
python manage.py check --deploy

# 5. Performance metrics
echo "[5/6] Collecting performance metrics..."
python manage.py shell -c "
import psutil
import os
print(f'CPU Usage: {psutil.cpu_percent()}%')
print(f'Memory Usage: {psutil.virtual_memory().percent}%')
print(f'Disk Usage: {psutil.disk_usage(".").percent}%')
"

# 6. Generate weekly report
echo "[6/6] Generating weekly report..."
python manage.py generate_weekly_report

echo "✓ Weekly maintenance completed"
```

---

## Monitoring dan Maintenance

### 1. Real-time Monitoring

#### System Resource Monitoring
```bash
#!/bin/bash
# monitor_resources.sh - Monitor sistem secara real-time

while true; do
    clear
    echo "=== Horilla HR System Monitor ==="
    echo "Time: $(date)"
    echo ""
    
    # CPU and Memory
    echo "=== System Resources ==="
    echo "CPU Usage: $(top -l 1 | grep "CPU usage" | awk '{print $3}' | sed 's/%//')%"
    echo "Memory Usage: $(ps -A -o %mem | awk '{s+=$1} END {print s "%"}')"
    echo "Disk Usage: $(df -h . | tail -1 | awk '{print $5}')"
    echo ""
    
    # Django processes
    echo "=== Django Processes ==="
    ps aux | grep "manage.py runserver" | grep -v grep
    echo ""
    
    # Celery processes
    echo "=== Celery Processes ==="
    ps aux | grep "celery" | grep -v grep
    echo ""
    
    # Database connections
    echo "=== Database Status ==="
    python manage.py shell -c "
from django.db import connection
print(f'Database connections: {len(connection.queries)}')
" 2>/dev/null
    
    # Redis status
    echo "=== Redis Status ==="
    redis-cli info memory | grep used_memory_human
    
    sleep 10
done
```

#### Application Health Monitoring
```python
# monitoring/health_check.py
import requests
import json
import time
from datetime import datetime

def check_application_health():
    """Comprehensive application health check"""
    
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'checks': {}
    }
    
    # Web interface check
    try:
        response = requests.get('http://127.0.0.1:8000/', timeout=10)
        health_status['checks']['web_interface'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'response_time': response.elapsed.total_seconds(),
            'status_code': response.status_code
        }
    except Exception as e:
        health_status['checks']['web_interface'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # API endpoints check
    try:
        response = requests.get('http://127.0.0.1:8000/api/', timeout=10)
        health_status['checks']['api'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'response_time': response.elapsed.total_seconds()
        }
    except Exception as e:
        health_status['checks']['api'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Database check
    try:
        response = requests.get('http://127.0.0.1:8000/health/', timeout=10)
        health_status['checks']['database'] = {
            'status': 'healthy' if 'database' in response.text.lower() else 'unhealthy'
        }
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # AI services check
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=10)
        health_status['checks']['ai_services'] = {
            'status': 'healthy' if response.status_code == 200 else 'unhealthy',
            'models': len(response.json().get('models', []))
        }
    except Exception as e:
        health_status['checks']['ai_services'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
    
    # Overall status
    unhealthy_checks = [k for k, v in health_status['checks'].items() if v['status'] == 'unhealthy']
    if unhealthy_checks:
        health_status['status'] = 'unhealthy'
        health_status['failed_checks'] = unhealthy_checks
    
    return health_status

if __name__ == '__main__':
    result = check_application_health()
    print(json.dumps(result, indent=2))
```

### 2. Log Analysis

#### Automated Log Analysis
```bash
#!/bin/bash
# analyze_logs.sh - Analisis log otomatis

LOG_DIR="logs"
REPORT_FILE="logs/daily_report_$(date +%Y%m%d).txt"

echo "=== Daily Log Analysis Report ===" > $REPORT_FILE
echo "Generated: $(date)" >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Error analysis
echo "=== ERROR SUMMARY ===" >> $REPORT_FILE
if [ -f "$LOG_DIR/django.log" ]; then
    echo "Django Errors:" >> $REPORT_FILE
    grep -i "error" "$LOG_DIR/django.log" | tail -10 >> $REPORT_FILE
fi

if [ -f "$LOG_DIR/celery.log" ]; then
    echo "Celery Errors:" >> $REPORT_FILE
    grep -i "error" "$LOG_DIR/celery.log" | tail -10 >> $REPORT_FILE
fi

# Performance metrics
echo "" >> $REPORT_FILE
echo "=== PERFORMANCE METRICS ===" >> $REPORT_FILE
echo "Slow queries (>1s):" >> $REPORT_FILE
grep "slow" "$LOG_DIR/django.log" 2>/dev/null | wc -l >> $REPORT_FILE

# User activity
echo "" >> $REPORT_FILE
echo "=== USER ACTIVITY ===" >> $REPORT_FILE
echo "Login attempts:" >> $REPORT_FILE
grep "login" "$LOG_DIR/django.log" 2>/dev/null | wc -l >> $REPORT_FILE

echo "Failed logins:" >> $REPORT_FILE
grep "failed.*login" "$LOG_DIR/django.log" 2>/dev/null | wc -l >> $REPORT_FILE

# System resources
echo "" >> $REPORT_FILE
echo "=== SYSTEM RESOURCES ===" >> $REPORT_FILE
echo "Current disk usage: $(df -h . | tail -1 | awk '{print $5}')" >> $REPORT_FILE
echo "Current memory usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')" >> $REPORT_FILE

echo "Log analysis completed: $REPORT_FILE"
```

---

## User Management

### 1. Bulk User Operations

#### Import Users from CSV
```python
# management/commands/import_users.py
import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employee.models import Employee, Department, JobPosition

class Command(BaseCommand):
    help = 'Import users from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--dry-run', action='store_true', help='Preview without creating')
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                username = row['username']
                email = row['email']
                first_name = row['first_name']
                last_name = row['last_name']
                employee_id = row['employee_id']
                department = row['department']
                position = row['position']
                
                if dry_run:
                    self.stdout.write(f"Would create: {username} ({email})")
                    continue
                
                try:
                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password='temp123'  # Temporary password
                    )
                    
                    # Get or create department
                    dept, _ = Department.objects.get_or_create(department=department)
                    
                    # Get or create position
                    pos, _ = JobPosition.objects.get_or_create(job_position=position)
                    
                    # Create employee
                    Employee.objects.create(
                        user=user,
                        employee_id=employee_id,
                        department=dept,
                        job_position=pos
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"Created user: {username}")
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error creating {username}: {e}")
                    )
```

#### Bulk Password Reset
```python
# management/commands/bulk_password_reset.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
import secrets
import string

class Command(BaseCommand):
    help = 'Reset passwords for multiple users'
    
    def add_arguments(self, parser):
        parser.add_argument('--usernames', nargs='+', help='List of usernames')
        parser.add_argument('--department', type=str, help='Reset for entire department')
        parser.add_argument('--send-email', action='store_true', help='Send reset emails')
    
    def generate_password(self, length=12):
        """Generate secure random password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def handle(self, *args, **options):
        users = []
        
        if options['usernames']:
            users = User.objects.filter(username__in=options['usernames'])
        elif options['department']:
            users = User.objects.filter(
                employee__department__department=options['department']
            )
        
        for user in users:
            new_password = self.generate_password()
            user.set_password(new_password)
            user.save()
            
            if options['send_email']:
                # Send password reset email
                send_mail(
                    'Password Reset - Horilla HR System',
                    f'Your new password is: {new_password}\nPlease change it after login.',
                    'admin@company.com',
                    [user.email],
                    fail_silently=False,
                )
                self.stdout.write(f"Password reset and email sent to {user.username}")
            else:
                self.stdout.write(f"Password reset for {user.username}: {new_password}")
```

### 2. User Activity Monitoring

```python
# monitoring/user_activity.py
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import timedelta
import json

def get_user_activity_report(days=7):
    """Generate user activity report"""
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Active users
    active_users = User.objects.filter(
        last_login__gte=start_date
    ).count()
    
    # Login activity
    recent_logins = LogEntry.objects.filter(
        action_time__gte=start_date,
        content_type__model='user'
    ).count()
    
    # Most active users
    most_active = LogEntry.objects.filter(
        action_time__gte=start_date
    ).values('user__username').annotate(
        activity_count=models.Count('id')
    ).order_by('-activity_count')[:10]
    
    report = {
        'period': f'{days} days',
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'active_users': active_users,
        'total_users': User.objects.count(),
        'recent_logins': recent_logins,
        'most_active_users': list(most_active)
    }
    
    return report

def export_user_activity(filename=None):
    """Export user activity to JSON file"""
    
    if not filename:
        filename = f'user_activity_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    report = get_user_activity_report()
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    return filename
```

---

## Data Management

### 1. Database Backup dan Restore

#### Automated Backup Script
```bash
#!/bin/bash
# backup_database.sh - Comprehensive database backup

BACKUP_DIR="backups/$(date +%Y%m%d)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

echo "=== Database Backup Started ==="
echo "Timestamp: $TIMESTAMP"
echo "Backup Directory: $BACKUP_DIR"

# SQLite backup
if [ -f "db.sqlite3" ]; then
    echo "Backing up SQLite database..."
    cp db.sqlite3 $BACKUP_DIR/db_$TIMESTAMP.sqlite3
    
    # Compress backup
    gzip $BACKUP_DIR/db_$TIMESTAMP.sqlite3
    echo "✓ SQLite backup completed: $BACKUP_DIR/db_$TIMESTAMP.sqlite3.gz"
fi

# PostgreSQL backup (if configured)
if [ ! -z "$DATABASE_URL" ] && [[ $DATABASE_URL == postgresql* ]]; then
    echo "Backing up PostgreSQL database..."
    pg_dump $DATABASE_URL > $BACKUP_DIR/postgres_$TIMESTAMP.sql
    gzip $BACKUP_DIR/postgres_$TIMESTAMP.sql
    echo "✓ PostgreSQL backup completed: $BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"
fi

# Media files backup
if [ -d "media" ]; then
    echo "Backing up media files..."
    tar -czf $BACKUP_DIR/media_$TIMESTAMP.tar.gz media/
    echo "✓ Media backup completed: $BACKUP_DIR/media_$TIMESTAMP.tar.gz"
fi

# Configuration backup
echo "Backing up configuration..."
cp .env $BACKUP_DIR/env_$TIMESTAMP.backup 2>/dev/null || echo "No .env file found"
cp -r logs/ $BACKUP_DIR/logs_$TIMESTAMP/ 2>/dev/null || echo "No logs directory found"

# Generate backup manifest
echo "Generating backup manifest..."
cat > $BACKUP_DIR/manifest.txt << EOF
Backup Manifest
===============
Timestamp: $TIMESTAMP
Backup Directory: $BACKUP_DIR
Files:
EOF

ls -la $BACKUP_DIR >> $BACKUP_DIR/manifest.txt

# Calculate checksums
echo "Calculating checksums..."
find $BACKUP_DIR -type f -name "*.gz" -o -name "*.tar.gz" | xargs md5sum > $BACKUP_DIR/checksums.md5

echo "=== Backup Completed ==="
echo "Total size: $(du -sh $BACKUP_DIR | cut -f1)"
echo "Files created:"
ls -la $BACKUP_DIR
```

#### Database Restore Script
```bash
#!/bin/bash
# restore_database.sh - Database restore utility

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_directory>"
    echo "Example: $0 backups/20240115"
    exit 1
fi

BACKUP_DIR=$1

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory $BACKUP_DIR not found"
    exit 1
fi

echo "=== Database Restore Started ==="
echo "Backup Directory: $BACKUP_DIR"

# Confirm restore
read -p "This will overwrite current data. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 1
fi

# Stop services
echo "Stopping services..."
pkill -f "manage.py runserver" 2>/dev/null
pkill -f "celery" 2>/dev/null

# Restore SQLite database
SQLITE_BACKUP=$(find $BACKUP_DIR -name "db_*.sqlite3.gz" | head -1)
if [ ! -z "$SQLITE_BACKUP" ]; then
    echo "Restoring SQLite database from $SQLITE_BACKUP..."
    gunzip -c $SQLITE_BACKUP > db.sqlite3
    echo "✓ SQLite database restored"
fi

# Restore PostgreSQL database
POSTGRES_BACKUP=$(find $BACKUP_DIR -name "postgres_*.sql.gz" | head -1)
if [ ! -z "$POSTGRES_BACKUP" ] && [ ! -z "$DATABASE_URL" ]; then
    echo "Restoring PostgreSQL database from $POSTGRES_BACKUP..."
    gunzip -c $POSTGRES_BACKUP | psql $DATABASE_URL
    echo "✓ PostgreSQL database restored"
fi

# Restore media files
MEDIA_BACKUP=$(find $BACKUP_DIR -name "media_*.tar.gz" | head -1)
if [ ! -z "$MEDIA_BACKUP" ]; then
    echo "Restoring media files from $MEDIA_BACKUP..."
    rm -rf media/
    tar -xzf $MEDIA_BACKUP
    echo "✓ Media files restored"
fi

# Restore configuration
ENV_BACKUP=$(find $BACKUP_DIR -name "env_*.backup" | head -1)
if [ ! -z "$ENV_BACKUP" ]; then
    echo "Restoring configuration from $ENV_BACKUP..."
    cp $ENV_BACKUP .env
    echo "✓ Configuration restored"
fi

echo "=== Restore Completed ==="
echo "Please restart the application services"
```

### 2. Data Migration dan Import

#### CSV Data Import
```python
# management/commands/import_csv_data.py
import csv
import os
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction

class Command(BaseCommand):
    help = 'Import data from CSV files'
    
    def add_arguments(self, parser):
        parser.add_argument('model', type=str, help='Model name (app.Model)')
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--mapping', type=str, help='Field mapping JSON file')
        parser.add_argument('--dry-run', action='store_true', help='Preview without importing')
    
    def handle(self, *args, **options):
        model_name = options['model']
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        
        # Get model class
        try:
            app_label, model_class = model_name.split('.')
            Model = apps.get_model(app_label, model_class)
        except (ValueError, LookupError) as e:
            self.stdout.write(self.style.ERROR(f'Invalid model: {e}'))
            return
        
        # Check if file exists
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file}'))
            return
        
        # Import data
        imported_count = 0
        error_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, 1):
                    try:
                        if dry_run:
                            self.stdout.write(f'Row {row_num}: {row}')
                            continue
                        
                        # Create model instance
                        instance = Model(**row)
                        instance.full_clean()  # Validate
                        instance.save()
                        
                        imported_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num} error: {e}')
                        )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Import completed: {imported_count} records imported, {error_count} errors'
                )
            )
        else:
            self.stdout.write('Dry run completed')
```

---

## Troubleshooting Lanjutan

### 1. Performance Issues

#### Database Query Optimization
```python
# monitoring/query_analyzer.py
from django.db import connection
from django.conf import settings
import time
import json

class QueryAnalyzer:
    def __init__(self):
        self.queries = []
        self.start_time = None
    
    def start_monitoring(self):
        """Start query monitoring"""
        self.start_time = time.time()
        self.queries = []
        settings.DEBUG = True  # Enable query logging
    
    def stop_monitoring(self):
        """Stop monitoring and analyze queries"""
        end_time = time.time()
        total_time = end_time - self.start_time
        
        queries = connection.queries
        slow_queries = [q for q in queries if float(q['time']) > 0.1]
        duplicate_queries = self._find_duplicate_queries(queries)
        
        analysis = {
            'total_time': total_time,
            'total_queries': len(queries),
            'slow_queries': len(slow_queries),
            'duplicate_queries': len(duplicate_queries),
            'slowest_queries': sorted(slow_queries, key=lambda x: float(x['time']), reverse=True)[:5],
            'most_frequent_duplicates': duplicate_queries[:5]
        }
        
        return analysis
    
    def _find_duplicate_queries(self, queries):
        """Find duplicate queries"""
        query_counts = {}
        for query in queries:
            sql = query['sql']
            if sql in query_counts:
                query_counts[sql] += 1
            else:
                query_counts[sql] = 1
        
        duplicates = [(sql, count) for sql, count in query_counts.items() if count > 1]
        return sorted(duplicates, key=lambda x: x[1], reverse=True)
    
    def generate_report(self, filename=None):
        """Generate performance report"""
        analysis = self.stop_monitoring()
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
        
        return analysis

# Usage example
analyzer = QueryAnalyzer()
analyzer.start_monitoring()
# ... perform operations ...
report = analyzer.generate_report('performance_report.json')
```

#### Memory Usage Optimization
```python
# monitoring/memory_profiler.py
import psutil
import os
import gc
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Monitor and optimize memory usage'
    
    def handle(self, *args, **options):
        process = psutil.Process(os.getpid())
        
        # Initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.stdout.write(f'Initial memory usage: {initial_memory:.2f} MB')
        
        # Force garbage collection
        collected = gc.collect()
        self.stdout.write(f'Garbage collected: {collected} objects')
        
        # Memory after GC
        after_gc_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.stdout.write(f'Memory after GC: {after_gc_memory:.2f} MB')
        
        # Memory saved
        saved = initial_memory - after_gc_memory
        self.stdout.write(f'Memory saved: {saved:.2f} MB')
        
        # Memory usage by type
        import sys
        from collections import defaultdict
        
        type_counts = defaultdict(int)
        for obj in gc.get_objects():
            type_counts[type(obj).__name__] += 1
        
        # Top memory consumers
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        self.stdout.write('\nTop memory consumers:')
        for obj_type, count in top_types:
            self.stdout.write(f'{obj_type}: {count} objects')
```

### 2. Network dan Connectivity Issues

#### Network Diagnostics
```bash
#!/bin/bash
# network_diagnostics.sh - Network connectivity diagnostics

echo "=== Network Diagnostics ==="
date

# Check local services
echo "\n=== Local Services ==="
echo "Django server (8000):"
netstat -an | grep :8000 || echo "Not running"

echo "Redis (6379):"
netstat -an | grep :6379 || echo "Not running"

echo "Ollama (11434):"
netstat -an | grep :11434 || echo "Not running"

# Test connectivity
echo "\n=== Connectivity Tests ==="
echo "Local Django:"
curl -s -o /dev/null -w "%{http_code} - %{time_total}s" http://127.0.0.1:8000/ || echo "Failed"

echo "\nLocal Redis:"
redis-cli ping || echo "Failed"

echo "\nLocal Ollama:"
curl -s http://localhost:11434/api/tags | jq '.models | length' || echo "Failed"

# DNS resolution
echo "\n=== DNS Resolution ==="
nslookup google.com || echo "DNS resolution failed"

# Internet connectivity
echo "\n=== Internet Connectivity ==="
ping -c 3 8.8.8.8 || echo "Internet connectivity failed"

# Port availability
echo "\n=== Port Availability ==="
for port in 8000 6379 11434; do
    if lsof -i :$port > /dev/null 2>&1; then
        echo "Port $port: In use"
    else
        echo "Port $port: Available"
    fi
done

echo "\n=== Diagnostics Complete ==="
```

### 3. AI Services Troubleshooting

#### Ollama Service Manager
```bash
#!/bin/bash
# ollama_manager.sh - Ollama service management

OLLAMA_LOG="logs/ollama.log"
OLLAMA_PID="ollama.pid"

case "$1" in
    start)
        echo "Starting Ollama service..."
        if [ -f "$OLLAMA_PID" ] && kill -0 $(cat $OLLAMA_PID) 2>/dev/null; then
            echo "Ollama is already running (PID: $(cat $OLLAMA_PID))"
        else
            nohup ollama serve > $OLLAMA_LOG 2>&1 &
            echo $! > $OLLAMA_PID
            echo "Ollama started (PID: $!)"
        fi
        ;;
    stop)
        echo "Stopping Ollama service..."
        if [ -f "$OLLAMA_PID" ]; then
            kill $(cat $OLLAMA_PID) 2>/dev/null
            rm -f $OLLAMA_PID
            echo "Ollama stopped"
        else
            echo "Ollama is not running"
        fi
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f "$OLLAMA_PID" ] && kill -0 $(cat $OLLAMA_PID) 2>/dev/null; then
            echo "Ollama is running (PID: $(cat $OLLAMA_PID))"
            curl -s http://localhost:11434/api/tags | jq '.models | length' | xargs echo "Models available:"
        else
            echo "Ollama is not running"
        fi
        ;;
    models)
        echo "Available models:"
        ollama list
        ;;
    pull)
        if [ -z "$2" ]; then
            echo "Usage: $0 pull <model_name>"
            echo "Example: $0 pull phi3:mini"
        else
            echo "Pulling model: $2"
            ollama pull $2
        fi
        ;;
    test)
        echo "Testing Ollama service..."
        curl -s http://localhost:11434/api/generate -d '{
            "model": "phi3:mini",
            "prompt": "Hello, world!",
            "stream": false
        }' | jq '.response' || echo "Test failed"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|models|pull|test}"
        exit 1
        ;;
esac
```

---

## Performance Tuning

### 1. Database Performance

#### SQLite Optimization
```python
# settings/performance.py
# SQLite performance settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'check_same_thread': False,
            'init_command': '''
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;
                PRAGMA temp_store=MEMORY;
                PRAGMA mmap_size=268435456;
            '''
        }
    }
}

# Connection pooling
CONN_MAX_AGE = 600
```

#### Query Optimization
```python
# utils/query_optimization.py
from django.db import models
from django.core.cache import cache

class OptimizedQuerySet(models.QuerySet):
    """Optimized queryset with caching and prefetching"""
    
    def with_cache(self, timeout=300):
        """Cache queryset results"""
        cache_key = f"queryset_{self.model._meta.label}_{hash(str(self.query))}"
        result = cache.get(cache_key)
        
        if result is None:
            result = list(self)
            cache.set(cache_key, result, timeout)
        
        return result
    
    def optimized_for_list(self):
        """Optimize for list views"""
        return self.select_related().prefetch_related()
    
    def optimized_for_detail(self):
        """Optimize for detail views"""
        return self.select_related().prefetch_related()

class OptimizedManager(models.Manager):
    def get_queryset(self):
        return OptimizedQuerySet(self.model, using=self._db)
    
    def cached(self, timeout=300):
        return self.get_queryset().with_cache(timeout)
```

### 2. Caching Strategy

#### Redis Cache Configuration
```python
# settings/cache.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
        },
        'KEY_PREFIX': 'horilla',
        'TIMEOUT': 300,
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'horilla_session',
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 3600  # 1 hour
```

#### Template Caching
```python
# Template caching middleware
class TemplateCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check cache for template
        cache_key = f"template_{request.path}_{request.user.id}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return cached_response
        
        response = self.get_response(request)
        
        # Cache successful responses
        if response.status_code == 200:
            cache.set(cache_key, response, 300)  # 5 minutes
        
        return response
```

---

## Security Operations

### 1. Security Monitoring

#### Failed Login Monitor
```python
# security/login_monitor.py
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger('security')

@receiver(user_login_failed)
def login_failed_handler(sender, credentials, request, **kwargs):
    """Monitor failed login attempts"""
    
    username = credentials.get('username', 'unknown')
    ip_address = get_client_ip(request)
    
    # Log failed attempt
    logger.warning(f'Failed login attempt: {username} from {ip_address}')
    
    # Track attempts per IP
    ip_key = f'failed_login_ip_{ip_address}'
    ip_attempts = cache.get(ip_key, 0) + 1
    cache.set(ip_key, ip_attempts, 3600)  # 1 hour
    
    # Track attempts per username
    user_key = f'failed_login_user_{username}'
    user_attempts = cache.get(user_key, 0) + 1
    cache.set(user_key, user_attempts, 3600)  # 1 hour
    
    # Alert on suspicious activity
    if ip_attempts >= 5 or user_attempts >= 3:
        send_security_alert(username, ip_address, ip_attempts, user_attempts)

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def send_security_alert(username, ip_address, ip_attempts, user_attempts):
    """Send security alert email"""
    
    subject = 'Security Alert - Multiple Failed Login Attempts'
    message = f'''
    Security Alert: Multiple failed login attempts detected
    
    Username: {username}
    IP Address: {ip_address}
    IP Attempts: {ip_attempts}
    User Attempts: {user_attempts}
    Time: {timezone.now()}
    
    Please investigate this activity.
    '''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [settings.SECURITY_EMAIL],
        fail_silently=False,
    )
```

#### Security Audit Script
```bash
#!/bin/bash
# security_audit.sh - Security audit script

AUDIT_LOG="logs/security_audit_$(date +%Y%m%d).log"

echo "=== Security Audit Report ===" > $AUDIT_LOG
echo "Date: $(date)" >> $AUDIT_LOG
echo "" >> $AUDIT_LOG

# Check file permissions
echo "=== File Permissions ===" >> $AUDIT_LOG
find . -name "*.py" -perm +o+w -exec ls -la {} \; >> $AUDIT_LOG
find . -name "db.sqlite3" -exec ls -la {} \; >> $AUDIT_LOG
find . -name ".env" -exec ls -la {} \; >> $AUDIT_LOG

# Check for sensitive data in logs
echo "" >> $AUDIT_LOG
echo "=== Sensitive Data in Logs ===" >> $AUDIT_LOG
grep -r "password\|secret\|key" logs/ 2>/dev/null | head -10 >> $AUDIT_LOG

# Check Django security settings
echo "" >> $AUDIT_LOG
echo "=== Django Security Check ===" >> $AUDIT_LOG
python manage.py check --deploy >> $AUDIT_LOG 2>&1

# Check for outdated packages
echo "" >> $AUDIT_LOG
echo "=== Package Security ===" >> $AUDIT_LOG
pip list --outdated >> $AUDIT_LOG 2>&1

# Check SSL certificate (if applicable)
if [ ! -z "$DOMAIN" ]; then
    echo "" >> $AUDIT_LOG
    echo "=== SSL Certificate ===" >> $AUDIT_LOG
    echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -dates >> $AUDIT_LOG
fi

echo "Security audit completed: $AUDIT_LOG"
```

### 2. Data Protection

#### Sensitive Data Encryption
```python
# utils/encryption.py
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os

class DataEncryption:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Get or create encryption key"""
        key_file = 'encryption.key'
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def encrypt(self, data):
        """Encrypt sensitive data"""
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data):
        """Decrypt sensitive data"""
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def encrypt_field(self, value):
        """Encrypt field value for database storage"""
        if not value:
            return value
        encrypted = self.encrypt(value)
        return base64.b64encode(encrypted).decode()
    
    def decrypt_field(self, encrypted_value):
        """Decrypt field value from database"""
        if not encrypted_value:
            return encrypted_value
        encrypted_data = base64.b64decode(encrypted_value.encode())
        return self.decrypt(encrypted_data)

# Usage in models
from django.db import models

class EncryptedField(models.TextField):
    """Custom field for encrypted data"""
    
    def __init__(self, *args, **kwargs):
        self.encryptor = DataEncryption()
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.encryptor.decrypt_field(value)
    
    def to_python(self, value):
        if isinstance(value, str):
            return value
        if value is None:
            return value
        return self.encryptor.decrypt_field(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encryptor.encrypt_field(value)
```

---

## Disaster Recovery

### 1. Backup Strategy

#### Comprehensive Backup Plan
```bash
#!/bin/bash
# disaster_recovery_backup.sh - Comprehensive backup for disaster recovery

BACKUP_ROOT="/backups/horilla"
DATE=$(date +%Y%m%d)
TIME=$(date +%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE/$TIME"

# Create backup directory
mkdir -p $BACKUP_DIR

echo "=== Disaster Recovery Backup Started ==="
echo "Backup Location: $BACKUP_DIR"
echo "Started at: $(date)"

# 1. Application code backup
echo "[1/8] Backing up application code..."
tar -czf $BACKUP_DIR/application_code.tar.gz \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='logs' \
    --exclude='backups' \
    .

# 2. Database backup
echo "[2/8] Backing up database..."
if [ -f "db.sqlite3" ]; then
    cp db.sqlite3 $BACKUP_DIR/
    sqlite3 db.sqlite3 ".backup $BACKUP_DIR/db_backup.sqlite3"
fi

# 3. Media files backup
echo "[3/8] Backing up media files..."
if [ -d "media" ]; then
    tar -czf $BACKUP_DIR/media_files.tar.gz media/
fi

# 4. Configuration backup
echo "[4/8] Backing up configuration..."
mkdir -p $BACKUP_DIR/config
cp .env $BACKUP_DIR/config/ 2>/dev/null || echo "No .env file"
cp -r logs/ $BACKUP_DIR/config/ 2>/dev/null || echo "No logs directory"

# 5. Virtual environment requirements
echo "[5/8] Backing up Python environment..."
source venv/bin/activate 2>/dev/null
pip freeze > $BACKUP_DIR/requirements_backup.txt

# 6. System information
echo "[6/8] Collecting system information..."
cat > $BACKUP_DIR/system_info.txt << EOF
System Information
==================
Hostname: $(hostname)
OS: $(uname -a)
Python Version: $(python --version 2>&1)
Django Version: $(python -c "import django; print(django.get_version())" 2>/dev/null)
Backup Date: $(date)
Backup Location: $BACKUP_DIR

Installed Packages:
$(pip list 2>/dev/null)

Disk Usage:
$(df -h)

Memory Usage:
$(free -h 2>/dev/null || vm_stat)
EOF

# 7. Database schema
echo "[7/8] Backing up database schema..."
python manage.py sqlmigrate employee 0001 > $BACKUP_DIR/schema_dump.sql 2>/dev/null

# 8. Create recovery instructions
echo "[8/8] Creating recovery instructions..."
cat > $BACKUP_DIR/RECOVERY_INSTRUCTIONS.md << 'EOF'
# Disaster Recovery Instructions

## Prerequisites
- Python 3.9+
- Git
- Virtual environment tools

## Recovery Steps

1. **Prepare Environment**
   ```bash
   mkdir horilla-recovery
   cd horilla-recovery
   python -m venv venv
   source venv/bin/activate
   ```

2. **Restore Application Code**
   ```bash
   tar -xzf application_code.tar.gz
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements_backup.txt
   ```

4. **Restore Database**
   ```bash
   cp db.sqlite3 ./
   # or restore from backup:
   cp db_backup.sqlite3 db.sqlite3
   ```

5. **Restore Media Files**
   ```bash
   tar -xzf media_files.tar.gz
   ```

6. **Restore Configuration**
   ```bash
   cp config/.env ./
   ```

7. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

8. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```

9. **Test Application**
   ```bash
   python manage.py check
   python manage.py runserver
   ```

## Verification Checklist
- [ ] Application starts without errors
- [ ] Database connectivity works
- [ ] User login functions
- [ ] Media files are accessible
- [ ] AI services connect properly

EOF

# Calculate backup size and create manifest
echo "Creating backup manifest..."
BACKUP_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
cat > $BACKUP_DIR/MANIFEST.txt << EOF
Horilla HR System - Disaster Recovery Backup
============================================

Backup Date: $(date)
Backup Size: $BACKUP_SIZE
Backup Location: $BACKUP_DIR

Contents:
EOF

ls -la $BACKUP_DIR >> $BACKUP_DIR/MANIFEST.txt

# Create checksums
echo "Generating checksums..."
find $BACKUP_DIR -type f -name "*.tar.gz" -o -name "*.sqlite3" | xargs md5sum > $BACKUP_DIR/checksums.md5

echo "=== Backup Completed ==="
echo "Total Size: $BACKUP_SIZE"
echo "Location: $BACKUP_DIR"
echo "Files:"
ls -la $BACKUP_DIR

# Optional: Upload to cloud storage
if [ ! -z "$CLOUD_BACKUP_ENABLED" ]; then
    echo "Uploading to cloud storage..."
    # Add your cloud upload commands here
    # aws s3 sync $BACKUP_DIR s3://your-backup-bucket/horilla/$DATE/$TIME/
fi

echo "Disaster recovery backup completed successfully!"
```

### 2. Recovery Testing

#### Automated Recovery Test
```bash
#!/bin/bash
# test_recovery.sh - Test disaster recovery procedures

TEST_DIR="recovery_test_$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "=== Disaster Recovery Test ==="
echo "Backup Directory: $BACKUP_DIR"
echo "Test Directory: $TEST_DIR"

# Create test environment
mkdir $TEST_DIR
cd $TEST_DIR

# Test recovery steps
echo "[1/8] Creating virtual environment..."
python -m venv venv
source venv/bin/activate

echo "[2/8] Restoring application code..."
tar -xzf $BACKUP_DIR/application_code.tar.gz

echo "[3/8] Installing dependencies..."
pip install -r $BACKUP_DIR/requirements_backup.txt

echo "[4/8] Restoring database..."
cp $BACKUP_DIR/db.sqlite3 ./

echo "[5/8] Restoring media files..."
if [ -f "$BACKUP_DIR/media_files.tar.gz" ]; then
    tar -xzf $BACKUP_DIR/media_files.tar.gz
fi

echo "[6/8] Restoring configuration..."
cp $BACKUP_DIR/config/.env ./ 2>/dev/null || echo "No .env file to restore"

echo "[7/8] Running system checks..."
python manage.py check

echo "[8/8] Testing application startup..."
timeout 10s python manage.py runserver --noreload &
SERVER_PID=$!
sleep 5

# Test web interface
if curl -s http://127.0.0.1:8000/ > /dev/null; then
    echo "✓ Web interface test: PASSED"
else
    echo "✗ Web interface test: FAILED"
fi

# Cleanup
kill $SERVER_PID 2>/dev/null
cd ..
rm -rf $TEST_DIR

echo "=== Recovery Test Completed ==="
```

---

**Catatan**: Dokumen ini melengkapi panduan instalasi utama dengan fokus pada operasional harian, troubleshooting lanjutan, dan disaster recovery. Pastikan untuk menyesuaikan script dan konfigurasi sesuai dengan environment spesifik Anda.

*Dokumen dibuat: $(date +"%Y-%m-%d %H:%M:%S")*
*Versi: 1.0*