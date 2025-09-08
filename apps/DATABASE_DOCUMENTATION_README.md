# Dokumentasi Database Horilla HR Management System

## 📋 Gambaran Umum

Repositori ini berisi dokumentasi lengkap untuk database Horilla HR Management System, sebuah sistem manajemen sumber daya manusia yang komprehensif yang dibangun menggunakan Django framework.

## 📁 Struktur Dokumentasi

### 1. [DATABASE_SCHEMA_DOCUMENTATION.md](./DATABASE_SCHEMA_DOCUMENTATION.md)
**Dokumentasi Skema Database Lengkap**
- Gambaran umum sistem dan aplikasi
- Detail tabel dengan kolom, tipe data, dan constraints
- Relasi antar tabel dan kardinalitas
- Business rules dan validasi

### 2. [DATABASE_ERD_DIAGRAM.svg](./DATABASE_ERD_DIAGRAM.svg)
**Diagram Entity Relationship (ERD)**
- Visualisasi entitas dan relasi dalam format SVG
- Kardinalitas antar entitas
- Legend dan informasi database
- Catatan penting untuk developer

### 3. [DATABASE_TECHNICAL_SPECIFICATIONS.md](./DATABASE_TECHNICAL_SPECIFICATIONS.md)
**Spesifikasi Teknis Database**
- Arsitektur database dan multi-tenant support
- Detail constraints dan validasi
- Strategi indexing dan optimasi
- Security dan permissions
- Migration strategy dan performance considerations

## 🏗️ Arsitektur Sistem

### Database Engine
- **Development**: SQLite 3.x
- **Production**: PostgreSQL 12+ (Recommended) / MySQL 8.0+
- **ORM**: Django ORM 4.x

### Aplikasi Utama
| Aplikasi | Deskripsi | Tabel Utama |
|----------|-----------|-------------|
| **base** | Manajemen perusahaan, departemen, posisi | Company, Department, JobPosition, JobRole |
| **employee** | Manajemen karyawan dan informasi kerja | Employee, EmployeeWorkInformation |
| **attendance** | Sistem absensi dan aktivitas kehadiran | Attendance, AttendanceActivity |
| **leave** | Manajemen cuti dan izin | LeaveType, LeaveRequest |
| **recruitment** | Sistem rekrutmen dan seleksi | Recruitment, Candidate, Skill |
| **payroll** | Sistem penggajian dan tunjangan | Allowance, Deduction, Payslip |
| **project** | Manajemen proyek | Project, Task |
| **budget** | Manajemen anggaran dan keuangan | BudgetCategory, BudgetPlan |
| **knowledge** | Sistem manajemen pengetahuan | DocumentCategory, Document |
| **indonesian_nlp** | Pemrosesan bahasa alami Indonesia | NLPModel, TextAnalysisJob |
| **ollama_integration** | Integrasi AI/ML | OllamaModel |

## 🔗 Relasi Utama

### Hierarki Organisasi
```
Company (1:M) → Department (1:M) → JobPosition (1:M) → JobRole
                     ↓
                Employee (1:M) → Attendance
                     ↓
                LeaveRequest
```

### Sistem Rekrutmen
```
Recruitment (M:M) ↔ JobPosition
     ↓
Candidate (1:M) → Interview
```

### Sistem Penggajian
```
Employee (M:M) ↔ Allowance
Employee (M:M) ↔ Deduction
     ↓
  Payslip
```

## 📊 Statistik Database

- **Total Tabel**: 100+
- **Aplikasi Django**: 15+
- **Primary Keys**: BigAutoField untuk semua tabel
- **Foreign Key Constraints**: PROTECT, CASCADE, SET_NULL
- **Unique Constraints**: Email, nama kategori, nama model
- **Audit Trail**: created_at, updated_at, is_active

## 🛠️ Penggunaan Dokumentasi

### Untuk Developer
1. **Setup Database**: Gunakan informasi dari technical specifications
2. **Model Development**: Referensi schema documentation untuk struktur tabel
3. **Query Optimization**: Ikuti panduan indexing dan performance
4. **Migration**: Gunakan migration strategy yang aman

### Untuk Database Administrator
1. **Database Setup**: Konfigurasi PostgreSQL/MySQL untuk production
2. **Performance Tuning**: Implementasi indexing dan optimization
3. **Security**: Setup row-level security dan access control
4. **Monitoring**: Setup monitoring dan alerting

### Untuk Business Analyst
1. **Data Model**: Pahami business rules dari schema documentation
2. **Reporting**: Gunakan ERD untuk memahami relasi data
3. **Requirements**: Referensi untuk new feature development

## 🔧 Tools dan Utilities

### Database Management
```bash
# Django management commands
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell

# Database optimization
python manage.py optimize_database --create-indexes --vacuum
```

### Development Tools
```bash
# Generate ERD (jika menggunakan django-extensions)
python manage.py graph_models -a -o database_erd.png

# Database inspection
python manage.py inspectdb > models_backup.py

# SQL debugging
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)
```

## 📈 Performance Guidelines

### Query Optimization
```python
# ✅ Good - Use select_related for ForeignKey
Employee.objects.select_related('department', 'job_position')

# ✅ Good - Use prefetch_related for ManyToMany
Recruitment.objects.prefetch_related('open_positions', 'skills')

# ❌ Bad - N+1 query problem
for employee in Employee.objects.all():
    print(employee.department.name)  # Causes N+1 queries
```

### Indexing Strategy
```sql
-- Composite indexes untuk frequent queries
CREATE INDEX attendance_employee_date_idx ON attendance_attendance (employee_id, attendance_date);

-- Partial indexes untuk active records
CREATE INDEX employee_active_idx ON employee_employee (id) WHERE is_active = true;
```

## 🔒 Security Considerations

### Data Protection
- **Encryption**: Sensitive fields menggunakan encrypted storage
- **Access Control**: Row-level security untuk multi-tenant
- **Audit Trail**: Tracking semua perubahan data
- **Soft Delete**: Menggunakan is_active field

### Best Practices
```python
# ✅ Good - Use parameterized queries
Employee.objects.filter(email=user_email)

# ❌ Bad - SQL injection risk
Employee.objects.extra(where=[f"email = '{user_email}'"])
```

## 🚀 Deployment Checklist

### Pre-Production
- [ ] Database schema review
- [ ] Index optimization
- [ ] Security configuration
- [ ] Backup strategy
- [ ] Migration testing

### Production
- [ ] Connection pooling setup
- [ ] Monitoring implementation
- [ ] Performance baseline
- [ ] Disaster recovery plan
- [ ] Documentation update

## 📝 Maintenance

### Regular Tasks
```sql
-- PostgreSQL maintenance (weekly)
VACUUM ANALYZE;
REINDEX DATABASE horilla_db;

-- Performance monitoring
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
```

### Backup Strategy
```bash
# Database backup
pg_dump horilla_db > backup_$(date +%Y%m%d).sql

# Django fixtures backup
python manage.py dumpdata > fixtures_backup.json
```

## 🤝 Contributing

### Documentation Updates
1. Update schema documentation saat ada perubahan model
2. Regenerate ERD diagram jika ada relasi baru
3. Update technical specifications untuk perubahan arsitektur
4. Test semua migration sebelum production

### Review Process
1. **Schema Changes**: Review oleh senior developer
2. **Performance Impact**: Analisis query performance
3. **Security Review**: Validasi access control
4. **Documentation**: Update semua dokumentasi terkait

## 📞 Support

### Troubleshooting
- **Migration Issues**: Cek migration dependencies
- **Performance Problems**: Analisis query execution plan
- **Data Integrity**: Validasi constraints dan foreign keys
- **Connection Issues**: Cek database connection pooling

### Resources
- [Django ORM Documentation](https://docs.djangoproject.com/en/stable/topics/db/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [Database Design Best Practices](https://www.postgresql.org/docs/current/ddl.html)

---

## 📄 File Manifest

| File | Deskripsi | Update Terakhir |
|------|-----------|------------------|
| `DATABASE_SCHEMA_DOCUMENTATION.md` | Dokumentasi skema lengkap | 2024-01-15 |
| `DATABASE_ERD_DIAGRAM.svg` | Diagram ERD visual | 2024-01-15 |
| `DATABASE_TECHNICAL_SPECIFICATIONS.md` | Spesifikasi teknis | 2024-01-15 |
| `DATABASE_DOCUMENTATION_README.md` | Panduan utama (file ini) | 2024-01-15 |

---

**© 2024 Horilla HR Management System**  
*Dokumentasi ini dibuat untuk mendukung pengembangan dan maintenance sistem yang efektif.*