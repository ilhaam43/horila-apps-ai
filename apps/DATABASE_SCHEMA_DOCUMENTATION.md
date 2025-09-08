# Dokumentasi Skema Database Horilla HR Management System

## Daftar Isi
1. [Gambaran Umum](#gambaran-umum)
2. [Skema Database](#skema-database)
3. [Tabel dan Relasi](#tabel-dan-relasi)
4. [Constraints dan Indeks](#constraints-dan-indeks)
5. [Diagram ERD](#diagram-erd)

## Gambaran Umum

Horilla HR Management System menggunakan Django ORM dengan database SQLite (development) dan mendukung PostgreSQL/MySQL untuk production. Sistem ini terdiri dari 15+ aplikasi utama dengan lebih dari 100 tabel yang saling terhubung.

### Aplikasi Utama:
- **base**: Manajemen perusahaan, departemen, posisi kerja
- **employee**: Manajemen karyawan dan informasi kerja
- **attendance**: Sistem absensi dan aktivitas kehadiran
- **leave**: Manajemen cuti dan izin
- **recruitment**: Sistem rekrutmen dan seleksi
- **payroll**: Sistem penggajian dan tunjangan
- **project**: Manajemen proyek
- **asset**: Manajemen aset perusahaan
- **budget**: Manajemen anggaran dan keuangan
- **knowledge**: Sistem manajemen pengetahuan
- **indonesian_nlp**: Pemrosesan bahasa alami Indonesia
- **ollama_integration**: Integrasi AI/ML

## Skema Database

### 1. Base Module (Modul Dasar)

#### Tabel: base_company
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik perusahaan |
| company | CharField(50) | NOT NULL | Nama perusahaan |
| hq | BooleanField | DEFAULT FALSE | Apakah kantor pusat |
| address | TextField(255) | NOT NULL | Alamat perusahaan |
| country | CharField(50) | NOT NULL | Negara |
| state | CharField(50) | NOT NULL | Provinsi/negara bagian |
| city | CharField(50) | NOT NULL | Kota |
| zip | CharField(20) | NOT NULL | Kode pos |
| icon | FileField | NULL | Logo perusahaan |
| date_format | CharField(30) | NULL | Format tanggal |
| time_format | CharField(20) | NULL | Format waktu |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Constraints:**
- UNIQUE(company, address)

#### Tabel: base_department
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik departemen |
| department | CharField(50) | NOT NULL | Nama departemen |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- company_id: ManyToManyField ke base_company

#### Tabel: base_jobposition
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik posisi |
| job_position | CharField(50) | NOT NULL | Nama posisi kerja |
| department_id | ForeignKey | NOT NULL | Referensi ke departemen |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- department_id: ForeignKey ke base_department (PROTECT)
- company_id: ManyToManyField ke base_company

#### Tabel: base_jobrole
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik peran |
| job_role | CharField(50) | NOT NULL | Nama peran kerja |
| job_position_id | ForeignKey | NOT NULL | Referensi ke posisi kerja |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Constraints:**
- UNIQUE(job_position_id, job_role)

**Relasi:**
- job_position_id: ForeignKey ke base_jobposition (PROTECT)
- company_id: ManyToManyField ke base_company

#### Tabel: base_worktype
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik tipe kerja |
| work_type | CharField(50) | NOT NULL | Nama tipe kerja |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

### 2. Employee Module (Modul Karyawan)

#### Tabel: employee_employee
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik karyawan |
| badge_id | CharField(50) | NULL | ID badge karyawan |
| employee_user_id | OneToOneField | NULL | Referensi ke User Django |
| employee_first_name | CharField(200) | NOT NULL | Nama depan |
| employee_last_name | CharField(200) | NULL | Nama belakang |
| employee_profile | ImageField | NULL | Foto profil |
| email | EmailField(254) | UNIQUE | Email karyawan |
| phone | CharField(25) | NOT NULL | Nomor telepon |
| address | TextField(200) | NULL | Alamat |
| country | CharField(100) | NULL | Negara |
| state | CharField(100) | NULL | Provinsi |
| city | CharField(30) | NULL | Kota |
| zip | CharField(20) | NULL | Kode pos |
| dob | DateField | NULL | Tanggal lahir |
| gender | CharField(10) | DEFAULT 'male' | Jenis kelamin |
| qualification | CharField(50) | NULL | Kualifikasi |
| experience | IntegerField | NULL | Pengalaman (tahun) |
| marital_status | CharField(50) | DEFAULT 'single' | Status pernikahan |
| children | IntegerField | NULL | Jumlah anak |
| emergency_contact | CharField(15) | NULL | Kontak darurat |
| emergency_contact_name | CharField(20) | NULL | Nama kontak darurat |
| emergency_contact_relation | CharField(20) | NULL | Hubungan kontak darurat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |
| additional_info | JSONField | NULL | Informasi tambahan |
| is_from_onboarding | BooleanField | DEFAULT FALSE | Dari proses onboarding |
| is_directly_converted | BooleanField | DEFAULT FALSE | Konversi langsung |

**Constraints:**
- UNIQUE(email)

**Relasi:**
- employee_user_id: OneToOneField ke auth_user (CASCADE)

### 3. Attendance Module (Modul Absensi)

#### Tabel: attendance_attendanceactivity
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik aktivitas |
| employee_id | ForeignKey | NOT NULL | Referensi ke karyawan |
| attendance_date | DateField | NULL | Tanggal absensi |
| shift_day | ForeignKey | NULL | Referensi ke hari shift |
| in_datetime | DateTimeField | NULL | Waktu masuk lengkap |
| clock_in_date | DateField | NULL | Tanggal masuk |
| clock_in | TimeField | NOT NULL | Waktu masuk |
| clock_out_date | DateField | NULL | Tanggal keluar |
| out_datetime | DateTimeField | NULL | Waktu keluar lengkap |
| clock_out | TimeField | NULL | Waktu keluar |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- employee_id: ForeignKey ke employee_employee (PROTECT)
- shift_day: ForeignKey ke base_employeeshiftday (DO_NOTHING)

#### Tabel: attendance_attendance
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik absensi |
| employee_id | ForeignKey | NULL | Referensi ke karyawan |
| attendance_date | DateField | NOT NULL | Tanggal absensi |
| shift_id | ForeignKey | NULL | Referensi ke shift |
| work_type_id | ForeignKey | NULL | Referensi ke tipe kerja |
| attendance_day | ForeignKey | NULL | Referensi ke hari absensi |
| attendance_clock_in_date | DateField | NULL | Tanggal masuk |
| attendance_clock_in | TimeField | NULL | Waktu masuk |
| attendance_clock_out_date | DateField | NULL | Tanggal keluar |
| attendance_clock_out | TimeField | NULL | Waktu keluar |
| attendance_worked_hour | CharField(10) | DEFAULT '00:00' | Jam kerja |
| minimum_hour | CharField(10) | DEFAULT '00:00' | Jam minimum |
| batch_attendance_id | ForeignKey | NULL | Referensi ke batch absensi |
| attendance_overtime | CharField(10) | DEFAULT '00:00' | Lembur |
| attendance_overtime_approve | BooleanField | DEFAULT FALSE | Persetujuan lembur |
| attendance_validated | BooleanField | DEFAULT FALSE | Validasi absensi |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- employee_id: ForeignKey ke employee_employee (PROTECT)
- shift_id: ForeignKey ke base_employeeshift (SET_NULL)
- work_type_id: ForeignKey ke base_worktype (SET_NULL)
- attendance_day: ForeignKey ke base_employeeshiftday (DO_NOTHING)
- batch_attendance_id: ForeignKey ke attendance_batchattendance (PROTECT)

### 4. Leave Module (Modul Cuti)

#### Tabel: leave_leavetype
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik tipe cuti |
| icon | ImageField | NULL | Ikon tipe cuti |
| name | CharField(30) | NOT NULL | Nama tipe cuti |
| color | CharField(30) | NULL | Warna |
| payment | CharField(30) | DEFAULT 'unpaid' | Status pembayaran |
| count | FloatField | DEFAULT 1 | Jumlah |
| period_in | CharField(30) | DEFAULT 'day' | Periode dalam |
| limit_leave | BooleanField | DEFAULT TRUE | Batasi hari cuti |
| total_days | FloatField | DEFAULT 1 | Total hari |
| reset | BooleanField | DEFAULT FALSE | Reset |
| is_encashable | BooleanField | DEFAULT FALSE | Dapat dicairkan |
| reset_based | CharField(30) | NULL | Basis reset |
| reset_month | CharField(30) | NULL | Bulan reset |
| reset_day | CharField(30) | NULL | Hari reset |
| reset_weekend | CharField(10) | NULL | Akhir pekan reset |
| carryforward_type | CharField(30) | DEFAULT 'no carryforward' | Tipe carry forward |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

### 5. Recruitment Module (Modul Rekrutmen)

#### Tabel: recruitment_recruitment
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik rekrutmen |
| title | CharField(50) | NULL | Judul rekrutmen |
| description | TextField | NULL | Deskripsi |
| is_event_based | BooleanField | DEFAULT FALSE | Berbasis event |
| closed | BooleanField | DEFAULT FALSE | Status tutup |
| is_published | BooleanField | DEFAULT TRUE | Status publikasi |
| vacancy | IntegerField | DEFAULT 0 | Jumlah lowongan |
| company_id | ForeignKey | NULL | Referensi ke perusahaan |
| start_date | DateField | NOT NULL | Tanggal mulai |
| end_date | DateField | NULL | Tanggal selesai |
| linkedin_post_id | CharField(150) | NULL | ID post LinkedIn |
| publish_in_linkedin | BooleanField | DEFAULT TRUE | Publikasi di LinkedIn |
| optional_profile_image | BooleanField | DEFAULT FALSE | Foto profil opsional |
| optional_resume | BooleanField | DEFAULT FALSE | Resume opsional |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- open_positions: ManyToManyField ke base_jobposition
- job_position_id: ForeignKey ke base_jobposition (PROTECT)
- recruitment_managers: ManyToManyField ke employee_employee
- survey_templates: ManyToManyField ke recruitment_surveytemplate
- company_id: ForeignKey ke base_company (PROTECT)
- skills: ManyToManyField ke recruitment_skill
- linkedin_account_id: ForeignKey ke recruitment_linkedinaccount (PROTECT)

#### Tabel: recruitment_skill
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik skill |
| title | CharField(100) | NOT NULL | Nama skill |

### 6. Payroll Module (Modul Penggajian)

#### Tabel: payroll_allowance
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik tunjangan |
| title | CharField(255) | NOT NULL | Judul tunjangan |
| one_time_date | DateField | NULL | Tanggal satu kali |
| include_active_employees | BooleanField | DEFAULT FALSE | Sertakan semua karyawan aktif |
| is_taxable | BooleanField | DEFAULT TRUE | Kena pajak |
| is_condition_based | BooleanField | DEFAULT FALSE | Berbasis kondisi |
| field | CharField(50) | NULL | Field kondisi |
| condition | CharField(10) | NULL | Kondisi |
| value | FloatField | DEFAULT 0.0 | Nilai |
| is_fixed | BooleanField | DEFAULT TRUE | Tetap |
| amount | FloatField | DEFAULT 0.0 | Jumlah |
| based_on | CharField(50) | NULL | Berdasarkan |
| rate | FloatField | DEFAULT 0.0 | Rate |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- company_id: ForeignKey ke base_company (PROTECT)
- exclude_employees: ManyToManyField ke employee_employee
- specific_employees: ManyToManyField ke employee_employee
- shift_id: ForeignKey ke base_employeeshift (PROTECT)
- work_type_id: ForeignKey ke base_worktype (PROTECT)

#### Tabel: payroll_deduction
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik potongan |
| title | CharField(255) | NOT NULL | Judul potongan |
| one_time_date | DateField | NULL | Tanggal satu kali |
| include_active_employees | BooleanField | DEFAULT FALSE | Sertakan semua karyawan aktif |
| is_tax | BooleanField | DEFAULT FALSE | Pajak |
| is_pretax | BooleanField | DEFAULT TRUE | Sebelum pajak |
| is_condition_based | BooleanField | DEFAULT FALSE | Berbasis kondisi |
| field | CharField(50) | NULL | Field kondisi |
| condition | CharField(10) | NULL | Kondisi |
| value | FloatField | DEFAULT 0.0 | Nilai |
| is_fixed | BooleanField | DEFAULT TRUE | Tetap |
| amount | FloatField | DEFAULT 0.0 | Jumlah |
| based_on | CharField(50) | NULL | Berdasarkan |
| rate | FloatField | DEFAULT 0.0 | Rate |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |

**Relasi:**
- company_id: ForeignKey ke base_company (PROTECT)
- exclude_employees: ManyToManyField ke employee_employee
- specific_employees: ManyToManyField ke employee_employee

### 7. Budget Module (Modul Anggaran)

#### Tabel: budget_budgetcategory
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik kategori |
| name | CharField(100) | UNIQUE | Nama kategori |
| description | TextField | NULL | Deskripsi |
| parent_category | ForeignKey | NULL | Kategori induk |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| updated_at | DateTimeField | AUTO_NOW | Waktu diperbarui |

**Relasi:**
- parent_category: ForeignKey ke budget_budgetcategory (CASCADE)

### 8. Knowledge Module (Modul Pengetahuan)

#### Tabel: knowledge_documentcategory
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik kategori |
| name | CharField(100) | UNIQUE | Nama kategori |
| description | TextField | NULL | Deskripsi |
| color | CharField(7) | DEFAULT '#007bff' | Warna hex |
| icon | CharField(50) | DEFAULT 'fas fa-folder' | Kelas ikon FontAwesome |
| parent | ForeignKey | NULL | Kategori induk |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| updated_at | DateTimeField | AUTO_NOW | Waktu diperbarui |

**Relasi:**
- parent: ForeignKey ke knowledge_documentcategory (CASCADE)

### 9. Indonesian NLP Module

#### Tabel: indonesian_nlp_nlpmodel
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik model |
| name | CharField(200) | UNIQUE | Nama model |
| description | TextField | NULL | Deskripsi |
| model_type | CharField(50) | NOT NULL | Tipe model |
| framework | CharField(50) | NOT NULL | Framework |
| model_path | CharField(500) | NOT NULL | Path model |
| tokenizer_path | CharField(500) | NULL | Path tokenizer |
| config | JSONField | DEFAULT dict | Konfigurasi model |
| preprocessing_config | JSONField | DEFAULT dict | Konfigurasi preprocessing |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| updated_at | DateTimeField | AUTO_NOW | Waktu diperbarui |

### 10. Ollama Integration Module

#### Tabel: ollama_integration_ollamamodel
| Kolom | Tipe Data | Constraints | Deskripsi |
|-------|-----------|-------------|------------|
| id | BigAutoField | PRIMARY KEY | ID unik model |
| name | CharField(100) | UNIQUE | Nama model |
| model_name | CharField(100) | NOT NULL | Nama model Ollama |
| custom_model_name | CharField(200) | NULL | Nama model kustom |
| description | TextField | NULL | Deskripsi |
| task_type | CharField(50) | NOT NULL | Tipe tugas |
| is_active | BooleanField | DEFAULT TRUE | Status aktif |
| created_at | DateTimeField | AUTO_NOW_ADD | Waktu dibuat |
| updated_at | DateTimeField | AUTO_NOW | Waktu diperbarui |

## Constraints dan Indeks

### Primary Keys
Semua tabel menggunakan `BigAutoField` sebagai primary key dengan nama kolom `id`.

### Foreign Key Constraints
- **PROTECT**: Mencegah penghapusan record yang direferensikan
- **CASCADE**: Menghapus record terkait saat record induk dihapus
- **SET_NULL**: Mengatur nilai NULL saat record induk dihapus
- **DO_NOTHING**: Tidak melakukan aksi khusus

### Unique Constraints
- `base_company`: UNIQUE(company, address)
- `base_jobrole`: UNIQUE(job_position_id, job_role)
- `employee_employee`: UNIQUE(email)
- `budget_budgetcategory`: UNIQUE(name)
- `knowledge_documentcategory`: UNIQUE(name)
- `indonesian_nlp_nlpmodel`: UNIQUE(name)
- `ollama_integration_ollamamodel`: UNIQUE(name)

### Indeks Database
Sistem menggunakan indeks otomatis Django untuk:
- Primary keys
- Foreign keys
- Unique constraints
- Field dengan `db_index=True`

### Audit Trail
Sebagian besar tabel memiliki field audit:
- `created_at`: Waktu pembuatan record
- `updated_at`: Waktu pembaruan terakhir (jika ada)
- `created_by`: User yang membuat record
- `modified_by`: User yang memodifikasi record
- `is_active`: Status aktif/non-aktif record

## Relasi Antar Tabel

### Relasi Utama:
1. **Company → Department → JobPosition → JobRole** (Hierarki organisasi)
2. **Employee → EmployeeWorkInformation** (Informasi kerja karyawan)
3. **Employee → Attendance** (Absensi karyawan)
4. **Employee → Leave** (Cuti karyawan)
5. **Recruitment → JobPosition** (Lowongan kerja)
6. **Payroll → Employee** (Penggajian karyawan)
7. **Budget → BudgetCategory** (Anggaran dan kategori)
8. **Knowledge → DocumentCategory** (Dokumen dan kategori)

### Kardinalitas:
- **One-to-One**: Employee ↔ User, Employee ↔ EmployeeWorkInformation
- **One-to-Many**: Company → Department, Department → JobPosition, JobPosition → JobRole
- **Many-to-Many**: Department ↔ Company, Employee ↔ Skills, Recruitment ↔ JobPosition

Dokumentasi ini memberikan gambaran komprehensif tentang struktur database Horilla HR Management System yang dapat digunakan untuk pengembangan, maintenance, dan integrasi sistem.