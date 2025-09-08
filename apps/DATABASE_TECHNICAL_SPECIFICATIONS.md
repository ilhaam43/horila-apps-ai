# Spesifikasi Teknis Database Horilla HR Management System

## Daftar Isi
1. [Arsitektur Database](#arsitektur-database)
2. [Relasi dan Kardinalitas Detail](#relasi-dan-kardinalitas-detail)
3. [Constraints dan Validasi](#constraints-dan-validasi)
4. [Indeks dan Optimasi](#indeks-dan-optimasi)
5. [Audit Trail dan Logging](#audit-trail-dan-logging)
6. [Security dan Permissions](#security-dan-permissions)
7. [Migration Strategy](#migration-strategy)
8. [Performance Considerations](#performance-considerations)

## Arsitektur Database

### Database Engine Support
- **Development**: SQLite 3.x
- **Production**: PostgreSQL 12+ (Recommended) atau MySQL 8.0+
- **ORM**: Django ORM 4.x
- **Connection Pooling**: Enabled untuk production

### Multi-Tenant Architecture
Sistem mendukung multi-company dengan:
- Shared database, separate data per company
- Company-level data isolation
- Cross-company reporting capabilities

### Database Naming Conventions
- **Tables**: `{app_name}_{model_name}` (lowercase, underscore)
- **Columns**: snake_case
- **Indexes**: `{table_name}_{column_name}_idx`
- **Foreign Keys**: `{table_name}_{column_name}_fkey`
- **Unique Constraints**: `{table_name}_{column_name}_key`

## Relasi dan Kardinalitas Detail

### 1. Hierarchical Relationships (1:M)

#### Company → Department → JobPosition → JobRole
```sql
-- Company (1) → Department (M)
base_company.id → base_department_company.company_id (M:M through table)

-- Department (1) → JobPosition (M)
base_department.id → base_jobposition.department_id (1:M, PROTECT)

-- JobPosition (1) → JobRole (M)
base_jobposition.id → base_jobrole.job_position_id (1:M, PROTECT)
```

**Business Rules:**
- Department tidak dapat dihapus jika masih memiliki JobPosition aktif
- JobPosition tidak dapat dihapus jika masih memiliki JobRole atau Employee aktif
- Company dapat memiliki multiple departments
- Department dapat shared across multiple companies (M:M)

### 2. Employee Relationships

#### Employee Core Relationships
```sql
-- Employee (1) ↔ User (1)
employee_employee.employee_user_id → auth_user.id (1:1, CASCADE)

-- Employee (1) → Attendance (M)
employee_employee.id → attendance_attendance.employee_id (1:M, PROTECT)

-- Employee (1) → AttendanceActivity (M)
employee_employee.id → attendance_attendanceactivity.employee_id (1:M, PROTECT)

-- Employee (1) → Leave (M)
employee_employee.id → leave_leaverequest.employee_id (1:M, PROTECT)
```

**Business Rules:**
- Setiap Employee harus terhubung dengan Django User
- Employee tidak dapat dihapus jika memiliki attendance records
- Soft delete menggunakan `is_active` field

### 3. Recruitment Relationships

#### Recruitment Complex Relationships
```sql
-- Recruitment (M) ↔ JobPosition (M)
recruitment_recruitment_open_positions table (M:M)

-- Recruitment (M) ↔ Employee (M) [as managers]
recruitment_recruitment_recruitment_managers table (M:M)

-- Recruitment (M) ↔ Skill (M)
recruitment_recruitment_skills table (M:M)

-- Recruitment (1) → Company (1)
recruitment_recruitment.company_id → base_company.id (M:1, PROTECT)
```

**Business Rules:**
- Recruitment dapat memiliki multiple job positions
- Multiple employees dapat menjadi recruitment managers
- Skills dapat digunakan di multiple recruitments

### 4. Payroll Relationships

#### Allowance & Deduction Relationships
```sql
-- Allowance/Deduction (M) ↔ Employee (M)
payroll_allowance_specific_employees table (M:M)
payroll_allowance_exclude_employees table (M:M)
payroll_deduction_specific_employees table (M:M)
payroll_deduction_exclude_employees table (M:M)

-- Allowance/Deduction (M) → Company (1)
payroll_allowance.company_id → base_company.id (M:1, PROTECT)
payroll_deduction.company_id → base_company.id (M:1, PROTECT)
```

**Business Rules:**
- Allowance/Deduction dapat diterapkan ke specific employees atau exclude certain employees
- Company-level allowances/deductions
- Conditional allowances berdasarkan employee attributes

### 5. Self-Referencing Relationships

#### Hierarchical Categories
```sql
-- BudgetCategory Self-Reference
budget_budgetcategory.parent_category_id → budget_budgetcategory.id (M:1, CASCADE)

-- DocumentCategory Self-Reference
knowledge_documentcategory.parent_id → knowledge_documentcategory.id (M:1, CASCADE)
```

**Business Rules:**
- Unlimited hierarchy depth
- Cascade delete untuk child categories
- Root categories memiliki parent_id = NULL

## Constraints dan Validasi

### 1. Primary Key Constraints
```sql
-- Semua tabel menggunakan BigAutoField
ALTER TABLE {table_name} ADD CONSTRAINT {table_name}_pkey PRIMARY KEY (id);
```

### 2. Unique Constraints
```sql
-- Employee email uniqueness
ALTER TABLE employee_employee ADD CONSTRAINT employee_employee_email_key UNIQUE (email);

-- Company + Address uniqueness
ALTER TABLE base_company ADD CONSTRAINT base_company_company_address_key UNIQUE (company, address);

-- JobRole uniqueness per JobPosition
ALTER TABLE base_jobrole ADD CONSTRAINT base_jobrole_job_position_job_role_key UNIQUE (job_position_id, job_role);

-- Category name uniqueness
ALTER TABLE budget_budgetcategory ADD CONSTRAINT budget_budgetcategory_name_key UNIQUE (name);
ALTER TABLE knowledge_documentcategory ADD CONSTRAINT knowledge_documentcategory_name_key UNIQUE (name);

-- Model name uniqueness
ALTER TABLE indonesian_nlp_nlpmodel ADD CONSTRAINT indonesian_nlp_nlpmodel_name_key UNIQUE (name);
ALTER TABLE ollama_integration_ollamamodel ADD CONSTRAINT ollama_integration_ollamamodel_name_key UNIQUE (name);
```

### 3. Foreign Key Constraints
```sql
-- PROTECT Constraints (Prevent deletion)
ALTER TABLE base_jobposition ADD CONSTRAINT base_jobposition_department_id_fkey 
    FOREIGN KEY (department_id) REFERENCES base_department(id) ON DELETE RESTRICT;

ALTER TABLE attendance_attendance ADD CONSTRAINT attendance_attendance_employee_id_fkey 
    FOREIGN KEY (employee_id) REFERENCES employee_employee(id) ON DELETE RESTRICT;

-- CASCADE Constraints (Delete related records)
ALTER TABLE employee_employee ADD CONSTRAINT employee_employee_employee_user_id_fkey 
    FOREIGN KEY (employee_user_id) REFERENCES auth_user(id) ON DELETE CASCADE;

ALTER TABLE budget_budgetcategory ADD CONSTRAINT budget_budgetcategory_parent_category_id_fkey 
    FOREIGN KEY (parent_category_id) REFERENCES budget_budgetcategory(id) ON DELETE CASCADE;

-- SET_NULL Constraints (Set to NULL on deletion)
ALTER TABLE attendance_attendance ADD CONSTRAINT attendance_attendance_shift_id_fkey 
    FOREIGN KEY (shift_id) REFERENCES base_employeeshift(id) ON DELETE SET NULL;
```

### 4. Check Constraints
```sql
-- Gender validation
ALTER TABLE employee_employee ADD CONSTRAINT employee_employee_gender_check 
    CHECK (gender IN ('male', 'female', 'other'));

-- Marital status validation
ALTER TABLE employee_employee ADD CONSTRAINT employee_employee_marital_status_check 
    CHECK (marital_status IN ('single', 'married', 'divorced', 'widowed'));

-- Leave payment validation
ALTER TABLE leave_leavetype ADD CONSTRAINT leave_leavetype_payment_check 
    CHECK (payment IN ('paid', 'unpaid'));

-- Positive values validation
ALTER TABLE leave_leavetype ADD CONSTRAINT leave_leavetype_total_days_check 
    CHECK (total_days >= 0);

ALTER TABLE payroll_allowance ADD CONSTRAINT payroll_allowance_amount_check 
    CHECK (amount >= 0);

ALTER TABLE payroll_deduction ADD CONSTRAINT payroll_deduction_amount_check 
    CHECK (amount >= 0);
```

### 5. Not Null Constraints
```sql
-- Critical fields yang tidak boleh NULL
ALTER TABLE employee_employee ALTER COLUMN employee_first_name SET NOT NULL;
ALTER TABLE employee_employee ALTER COLUMN email SET NOT NULL;
ALTER TABLE employee_employee ALTER COLUMN phone SET NOT NULL;

ALTER TABLE base_company ALTER COLUMN company SET NOT NULL;
ALTER TABLE base_company ALTER COLUMN address SET NOT NULL;

ALTER TABLE attendance_attendance ALTER COLUMN attendance_date SET NOT NULL;
```

## Indeks dan Optimasi

### 1. Automatic Indexes
Django secara otomatis membuat indeks untuk:
- Primary keys
- Foreign keys
- Unique constraints
- Fields dengan `db_index=True`

### 2. Custom Indexes
```sql
-- Composite indexes untuk query optimization
CREATE INDEX attendance_employee_date_idx ON attendance_attendance (employee_id, attendance_date);
CREATE INDEX attendance_date_range_idx ON attendance_attendance (attendance_date) WHERE is_active = true;

-- Partial indexes untuk active records
CREATE INDEX employee_active_idx ON employee_employee (id) WHERE is_active = true;
CREATE INDEX company_active_idx ON base_company (id) WHERE is_active = true;

-- Text search indexes (PostgreSQL)
CREATE INDEX employee_name_search_idx ON employee_employee 
    USING gin(to_tsvector('english', employee_first_name || ' ' || COALESCE(employee_last_name, '')));

-- JSON field indexes (PostgreSQL)
CREATE INDEX nlp_config_gin_idx ON indonesian_nlp_nlpmodel USING gin(config);
CREATE INDEX employee_additional_info_gin_idx ON employee_employee USING gin(additional_info);
```

### 3. Performance Indexes
```sql
-- Frequently queried combinations
CREATE INDEX recruitment_company_status_idx ON recruitment_recruitment (company_id, closed, is_published);
CREATE INDEX leave_employee_type_idx ON leave_leaverequest (employee_id, leave_type_id);
CREATE INDEX payroll_company_active_idx ON payroll_allowance (company_id) WHERE is_active = true;
```

## Audit Trail dan Logging

### 1. Standard Audit Fields
Sebagian besar tabel memiliki:
```sql
created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
created_by INTEGER REFERENCES auth_user(id),
modified_by INTEGER REFERENCES auth_user(id),
is_active BOOLEAN DEFAULT true
```

### 2. Historical Data
Beberapa model menggunakan django-simple-history untuk tracking:
- Employee changes
- Attendance modifications
- Payroll adjustments
- Recruitment updates

### 3. Soft Delete Pattern
```sql
-- Soft delete menggunakan is_active field
UPDATE employee_employee SET is_active = false WHERE id = ?;
-- Query hanya active records
SELECT * FROM employee_employee WHERE is_active = true;
```

## Security dan Permissions

### 1. Row-Level Security (PostgreSQL)
```sql
-- Company-level data isolation
CREATE POLICY company_isolation ON employee_employee
    FOR ALL TO app_user
    USING (company_id = current_setting('app.current_company_id')::integer);
```

### 2. Sensitive Data Protection
```sql
-- Encrypted fields untuk data sensitif
-- Menggunakan django-encrypted-fields atau similar
-- Contoh: SSN, bank account numbers, etc.
```

### 3. Access Control
- Django permissions system
- Company-level permissions
- Role-based access control (RBAC)
- Field-level permissions

## Migration Strategy

### 1. Migration Best Practices
```python
# Contoh migration yang aman
class Migration(migrations.Migration):
    atomic = False  # Untuk large data migrations
    
    operations = [
        # Add column dengan default value
        migrations.AddField(
            model_name='employee',
            name='new_field',
            field=models.CharField(max_length=100, default=''),
        ),
        # Populate data
        migrations.RunPython(populate_new_field, reverse_code=migrations.RunPython.noop),
        # Add constraint setelah data populated
        migrations.AlterField(
            model_name='employee',
            name='new_field',
            field=models.CharField(max_length=100),
        ),
    ]
```

### 2. Zero-Downtime Migrations
- Add columns dengan default values
- Populate data dalam batches
- Add constraints setelah data migration
- Remove old columns dalam migration terpisah

### 3. Data Migration Patterns
```python
def migrate_data_forward(apps, schema_editor):
    Model = apps.get_model('app_name', 'ModelName')
    batch_size = 1000
    
    for batch in queryset_iterator(Model.objects.all(), batch_size):
        # Process batch
        Model.objects.bulk_update(batch, ['field_name'])
```

## Performance Considerations

### 1. Query Optimization
```python
# Gunakan select_related untuk ForeignKey
Employee.objects.select_related('department', 'job_position')

# Gunakan prefetch_related untuk ManyToMany
Recruitment.objects.prefetch_related('open_positions', 'skills')

# Gunakan only() untuk limit fields
Employee.objects.only('id', 'employee_first_name', 'email')

# Gunakan defer() untuk exclude heavy fields
Employee.objects.defer('employee_profile', 'additional_info')
```

### 2. Database Connection Pooling
```python
# settings.py untuk production
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        },
        'CONN_MAX_AGE': 600,
    }
}
```

### 3. Caching Strategy
```python
# Model-level caching
class Employee(models.Model):
    class Meta:
        cache_timeout = 300  # 5 minutes

# Query-level caching
from django.core.cache import cache

def get_active_employees():
    cache_key = 'active_employees'
    employees = cache.get(cache_key)
    if employees is None:
        employees = Employee.objects.filter(is_active=True)
        cache.set(cache_key, employees, 300)
    return employees
```

### 4. Database Maintenance
```sql
-- PostgreSQL maintenance commands
VACUUM ANALYZE;  -- Regular maintenance
REINDEX DATABASE horilla_db;  -- Rebuild indexes

-- Monitor query performance
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
```

### 5. Monitoring dan Alerting
- Database connection monitoring
- Query performance tracking
- Index usage analysis
- Storage space monitoring
- Backup verification

## Kesimpulan

Database Horilla HR Management System dirancang dengan prinsip:
- **Scalability**: Mendukung pertumbuhan data dan user
- **Performance**: Optimasi query dan indexing
- **Security**: Data protection dan access control
- **Maintainability**: Clear structure dan documentation
- **Reliability**: ACID compliance dan backup strategy

Dokumentasi ini harus diperbarui seiring dengan evolusi sistem dan perubahan requirements bisnis.