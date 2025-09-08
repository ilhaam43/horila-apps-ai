# Dokumentasi Modul Budget - Horilla HRMS

## Daftar Isi
1. [Gambaran Umum](#gambaran-umum)
2. [Hak Akses dan Kredensial](#hak-akses-dan-kredensial)
3. [Prosedur Pembuatan Budget Plan](#prosedur-pembuatan-budget-plan)
4. [Panduan Penggunaan Modul Budget](#panduan-penggunaan-modul-budget)
5. [Pengaturan Mata Uang](#pengaturan-mata-uang)
6. [Customization Logo dan Branding](#customization-logo-dan-branding)
7. [Solusi Error yang Mungkin Terjadi](#solusi-error-yang-mungkin-terjadi)
8. [FAQ](#faq)

---

## Gambaran Umum

Modul Budget pada Horilla HRMS adalah sistem manajemen anggaran yang memungkinkan organisasi untuk:
- Membuat dan mengelola rencana anggaran (Budget Plans)
- Melacak pengeluaran (Expenses) 
- Menghasilkan laporan keuangan (Financial Reports)
- Memantau utilisasi anggaran secara real-time

### Fitur Utama:
- ✅ Pembuatan rencana anggaran dengan kategori dan departemen
- ✅ Tracking pengeluaran dengan approval workflow
- ✅ Dashboard visualisasi anggaran dengan filter lanjutan
- ✅ Laporan keuangan komprehensif
- ✅ Notifikasi ketika anggaran mendekati batas
- ✅ Multi-level approval system
- ✅ **BARU**: Filter tanggal dan rentang jumlah di semua modul
- ✅ **BARU**: Filter status pemanfaatan dan prioritas
- ✅ **BARU**: Pencarian berdasarkan nama rencana
- ✅ **BARU**: Tata letak filter responsif 4 kolom

---

## Hak Akses dan Kredensial

### Kredensial Admin Default
- **Username**: `admin`
- **Password**: `admin123`
- **Status**: Superuser dengan akses penuh ke semua modul

### Grup Pengguna Budget
Sistem memiliki beberapa grup dengan hak akses berbeda:

1. **Admin** - Akses penuh ke semua fitur
2. **Budget Manager** - Dapat membuat, mengedit, dan menyetujui budget plans
3. **Finance Team** - Dapat melihat laporan dan mengelola expenses
4. **Budget Viewer** - Hanya dapat melihat budget plans dan laporan

### Cara Menambah User ke Grup Budget:
1. Login sebagai admin
2. Masuk ke Django Admin (`/admin/`)
3. Pilih **Users** → Pilih user yang ingin diubah
4. Di bagian **Groups**, tambahkan grup yang sesuai
5. Simpan perubahan

---

## Prosedur Pembuatan Budget Plan

### Langkah-langkah:

1. **Akses Halaman Budget Plans**
   - Login ke sistem
   - Navigasi ke menu **Budget** → **Plans**
   - Klik tombol **"Create New Budget Plan"**

2. **Isi Form Budget Plan**
   - **Plan Name**: Nama rencana anggaran (wajib)
   - **Category**: Kategori anggaran (wajib)
   - **Description**: Deskripsi detail rencana
   - **Budget Amount**: Jumlah anggaran dalam USD (wajib)
   - **Start Date**: Tanggal mulai periode anggaran (wajib)
   - **End Date**: Tanggal akhir periode anggaran (wajib)
   - **Department**: Departemen yang bertanggung jawab
   - **Status**: Status rencana (Draft/Active/Completed/Cancelled)
   - **Active Plan**: Centang jika rencana aktif

3. **Validasi Form**
   - End date harus setelah start date
   - Budget amount harus lebih besar dari 0
   - Semua field wajib harus diisi

4. **Simpan Budget Plan**
   - Klik tombol **"Create Budget Plan"**
   - Sistem akan memvalidasi dan menyimpan data
   - Redirect ke halaman detail budget plan

### Tips Pembuatan Budget Plan:
- 💡 Gunakan nama yang deskriptif untuk memudahkan pencarian
- 📅 Pilih periode yang realistis sesuai siklus bisnis
- 💰 Set budget amount berdasarkan data historis
- 🏢 Assign ke departemen yang tepat untuk tracking yang akurat

---

## Panduan Penggunaan Modul Budget

### 1. Dashboard Budget
- **URL**: `/budget/`
- **Fitur**: 
  - Overview semua budget plans, statistik, dan grafik utilisasi
  - **Filter Lanjutan**:
    - Filter status (All Status, Active, Completed, etc.)
    - Filter kategori (All Categories, Facilities, HR, IT, Marketing, etc.)
    - Filter tanggal mulai dan akhir
    - Filter status pemanfaatan (Under Budget, Over Budget, At Limit)
    - Filter rentang anggaran (Budget Min/Max)
    - Pencarian berdasarkan nama rencana
  - Tata letak filter responsif 4 kolom
- **Akses**: Semua user dengan akses budget

### 2. Budget Plans
- **URL**: `/budget/plans/`
- **Fitur**: 
  - List semua budget plans
  - **Filter Lanjutan**:
    - Filter status dan kategori
    - Filter tanggal mulai dan akhir (`start_date`, `end_date`)
    - Filter rentang jumlah alokasi (`allocated_amount_min`, `allocated_amount_max`)
    - Filter status anggaran (`is_over_budget`)
  - Create, edit, delete budget plans
  - View detail utilisasi anggaran
  - Tata letak filter responsif

### 3. Expenses
- **URL**: `/budget/expenses/`
- **Fitur**:
  - Record pengeluaran terhadap budget plan
  - Upload receipt/dokumen pendukung
  - Approval workflow
  - Tracking status expense
  - **Filter Lanjutan**:
    - Filter judul, status, rencana anggaran, dan tipe pengeluaran
    - Filter tanggal (`date_after`, `date_before`)
    - Filter rentang jumlah (`amount_min`, `amount_max`)
    - Filter prioritas pengeluaran
  - Tata letak filter responsif

### 4. Reports
- **URL**: `/budget/reports/`
- **Fitur**:
  - Generate laporan keuangan
  - Export ke PDF/Excel
  - Filter berdasarkan periode, departemen
  - Analisis variance budget vs actual

### 5. API Endpoints
- **Budget Plans API**: `/api/budget/plans/`
- **Expenses API**: `/api/budget/expenses/`
- **Reports API**: `/api/budget/reports/`

---

## Pengaturan Mata Uang

### Mengubah Mata Uang dari '$' ke 'IDR'

**Lokasi Menu Pengaturan:**
- **URL**: `http://127.0.0.1:8000/payroll/settings`
- **Menu**: Payroll → Settings
- **Nama Route**: `payroll-settings`

**Langkah-langkah Mengubah Mata Uang:**

1. **Akses Menu Pengaturan**
   - Login sebagai admin atau user dengan permission `payroll.change_payrollsettings`
   - Navigasi ke menu **Payroll** → **Settings**
   - Atau akses langsung: `/payroll/settings`

2. **Ubah Pengaturan Mata Uang**
   - Pada formulir pengaturan, cari field **Currency Symbol**
   - Ubah nilai dari `$` menjadi `IDR`
   - Pilih **Position** untuk menentukan posisi simbol:
     - **Before**: IDR 100,000
     - **After**: 100,000 IDR

3. **Simpan Perubahan**
   - Klik tombol **Save Changes**
   - Sistem akan memperbarui semua tampilan mata uang

**Implementasi Teknis:**
- **Model**: `PayrollSettings` di `payroll/models/tax_models.py`
- **View Handler**: Fungsi `settings` di `payroll/views/views.py`
- **Template Filter**: `currency_symbol_position` di `base/templatetags/horillafilters.py`
- **Context Processor**: `default_currency` di `payroll/context_processors.py`

**Catatan Penting:**
- Perubahan mata uang akan mempengaruhi semua modul yang menampilkan nilai uang
- Sistem mendukung mata uang IDR dan USD secara default
- Jika tidak ada pengaturan, sistem akan menggunakan '$' sebagai default

---

## Customization Logo dan Branding

### Logo Perusahaan di Header

**Lokasi Implementasi:**
- **File Template**: `budget/templates/budget/base_budget.html`
- **Logika**: Logo dimuat dari `white_label_company.icon`

**Cara Mengganti Logo:**

1. **Melalui White Label Company Settings**
   - Upload logo perusahaan melalui pengaturan White Label Company
   - Logo akan otomatis muncul di header semua halaman budget
   - Format yang didukung: PNG, JPG, SVG

2. **Fallback ke Logo Default**
   - Jika tidak ada logo perusahaan, sistem menggunakan ikon default
   - Lokasi default: `static/favicons/`

### Ikon Navigasi dan UI

**Lokasi File:**
- **Navbar**: `budget/templates/budget/navbar_budget.html`
- **Static Files**: `static/images/`

**Ikon yang Dapat Diganti:**
- **Menu Hamburger**: `menu.svg`
- **Foto Profil**: `userphoto.png`
- **Favicon**: File di `static/favicons/`

**Cara Mengganti Ikon:**

1. **Ganti File Statis**
   ```bash
   # Backup file lama
   cp static/images/menu.svg static/images/menu_backup.svg
   
   # Upload file baru dengan nama yang sama
   cp new_menu_icon.svg static/images/menu.svg
   ```

2. **Update Template (Opsional)**
   - Edit file template jika ingin menggunakan nama file berbeda
   - Pastikan path file sesuai dengan lokasi baru

### Ikon Ionicon

**Penggunaan:**
- Sistem menggunakan Ionicon untuk berbagai elemen UI
- Ikon tersedia secara online, tidak perlu file lokal
- Dapat diganti dengan mengubah class CSS di template

**Contoh Penggunaan:**
```html
<ion-icon name="home-outline"></ion-icon>
<ion-icon name="person-circle-outline"></ion-icon>
```

**Opsi Default yang Tersedia:**
- ✅ Fallback otomatis ke ikon default
- ✅ Template responsif untuk berbagai ukuran logo
- ✅ Dukungan format SVG, PNG, JPG
- ✅ Integrasi dengan sistem White Label

---

## Solusi Error yang Mungkin Terjadi

### 1. TemplateSyntaxError: 'block' tag with name 'extra_js' appears more than once

**Penyebab**: Duplikasi block `extra_js` dalam template

**Solusi**: 
✅ **SUDAH DIPERBAIKI** - Template `budget_plan_form.html` telah diupdate untuk menggabungkan script yang duplikat

### 2. ValueError: Cannot query 'admin': Must be 'Employee' instance

**Penyebab**: User admin tidak memiliki profil Employee

**Solusi**: 
✅ **SUDAH DIPERBAIKI** - Ditambahkan error handling di `views.py` dan `serializers.py`

```python
# Contoh penanganan error
try:
    employee = employee_get(request)
except (AttributeError, Employee.DoesNotExist):
    employee = None
```

### 3. AttributeError: 'User' object has no attribute 'employee_get'

**Penyebab**: User tidak memiliki relasi dengan model Employee

**Solusi**: 
✅ **SUDAH DIPERBAIKI** - Ditambahkan validasi dan fallback handling

### 4. ImportError: No module named 'budget.tests'

**Penyebab**: File test tidak ada di direktori budget

**Solusi**: 
- Buat file `tests.py` di direktori budget jika diperlukan
- Atau gunakan Django shell untuk testing manual

### 5. DisallowedHost Error

**Penyebab**: Host tidak ada di `ALLOWED_HOSTS` settings

**Solusi**: 
- Tambahkan host ke `ALLOWED_HOSTS` di `settings.py`
- Untuk development: `ALLOWED_HOSTS = ['*']`

### 6. Permission Denied Error

**Penyebab**: User tidak memiliki permission yang cukup

**Solusi**: 
- Pastikan user ada di grup yang tepat
- Cek permission di Django Admin
- Untuk superuser: semua permission otomatis granted

---

## FAQ

### Q: Apakah kredensial admin default sudah diubah?
**A**: Ya, kredensial admin default telah dikonfirmasi:
- Username: `admin`
- Password: `admin123`
- Status: Superuser aktif

### Q: Bagaimana cara memberikan akses budget ke user baru?
**A**: 
1. Buat user baru di Django Admin
2. Tambahkan user ke salah satu grup budget:
   - **Budget Manager**: Untuk akses penuh
   - **Finance Team**: Untuk akses laporan dan expenses
   - **Budget Viewer**: Untuk akses read-only

### Q: Apakah ada grup 'adminbudget'?
**A**: Tidak, grup 'adminbudget' tidak ada. Gunakan grup yang tersedia:
- Admin
- Budget Manager  
- Finance Team
- Budget Viewer

### Q: Bagaimana cara backup data budget?
**A**: 
```bash
# Backup semua data budget
python manage.py dumpdata budget > budget_backup.json

# Restore data budget
python manage.py loaddata budget_backup.json
```

### Q: Bagaimana cara mengintegrasikan dengan sistem payroll?
**A**: Modul budget dapat diintegrasikan dengan modul payroll melalui:
- Shared Employee model
- API endpoints untuk data exchange
- Custom signals untuk sinkronisasi data
- Pengaturan mata uang terpusat melalui PayrollSettings

### Q: Apakah ada limit jumlah budget plans?
**A**: Tidak ada limit hard-coded. Limit tergantung pada:
- Kapasitas database
- Performance server
- Konfigurasi pagination

### Q: Bagaimana cara menggunakan filter baru yang telah ditambahkan?
**A**: Filter baru tersedia di semua halaman budget:
- **Dashboard**: Filter status, kategori, tanggal, rentang anggaran, dan pencarian nama
- **Budget Plans**: Filter tanggal, rentang alokasi, dan status anggaran
- **Expenses**: Filter tanggal, rentang jumlah, dan prioritas
- Semua filter menggunakan tata letak responsif 4 kolom

### Q: Apakah perubahan mata uang mempengaruhi data yang sudah ada?
**A**: 
- Perubahan simbol mata uang hanya mempengaruhi tampilan (display)
- Data numerik di database tetap sama
- Semua modul akan menggunakan simbol mata uang baru secara otomatis
- Tidak perlu migrasi data

### Q: Bagaimana cara mengganti logo perusahaan?
**A**: 
- **Otomatis**: Upload melalui White Label Company settings
- **Manual**: Ganti file di `static/favicons/` untuk favicon
- **Custom**: Edit template `base_budget.html` untuk customization lanjutan
- Logo mendukung format PNG, JPG, dan SVG

---

## Kontak Support

Jika mengalami masalah yang tidak tercakup dalam dokumentasi ini:

1. **Check Logs**: Periksa log Django di console/file log
2. **Django Admin**: Gunakan `/admin/` untuk troubleshooting data
3. **Database**: Periksa konsistensi data di database
4. **Permissions**: Verifikasi user permissions dan group membership

---

## Changelog dan Update Terbaru

### Version 1.1 - Filter Enhancement Update
**Tanggal**: Desember 2024

**✅ Fitur Baru yang Ditambahkan:**
- Filter lanjutan di Dashboard Budget (status, kategori, tanggal, rentang anggaran, pencarian)
- Filter tanggal dan rentang alokasi di Budget Plans
- Filter tanggal, rentang jumlah, dan prioritas di Expenses
- Tata letak filter responsif 4 kolom di semua halaman
- Dokumentasi lengkap pengaturan mata uang
- Panduan customization logo dan branding

**🔧 Perbaikan Teknis:**
- Template `dashboard.html` - Ditambahkan filter lanjutan
- Template `budget_plan_list.html` - Ditambahkan filter tanggal dan rentang
- Template `expense_list.html` - Ditambahkan filter tanggal dan prioritas
- Semua filter menggunakan tata letak responsif

**📚 Dokumentasi:**
- Ditambahkan bagian "Pengaturan Mata Uang"
- Ditambahkan bagian "Customization Logo dan Branding"
- Diperbarui FAQ dengan informasi filter baru
- Ditambahkan changelog dan version tracking

---

**Dokumentasi ini dibuat pada**: 2024
**Versi Modul**: Budget v1.1
**Last Updated**: Desember 2024
**Status**: ✅ Semua fitur telah diperbaiki dan ditingkatkan - Modul siap production