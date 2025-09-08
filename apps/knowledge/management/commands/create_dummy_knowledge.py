from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from knowledge.models import DocumentCategory, DocumentTag, KnowledgeDocument
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Create dummy knowledge management data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing knowledge data before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing knowledge data...')
            KnowledgeDocument.objects.all().delete()
            DocumentTag.objects.all().delete()
            DocumentCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create categories
        categories_data = [
            {
                'name': 'Human Resources',
                'description': 'Kebijakan, prosedur, dan panduan terkait sumber daya manusia',
                'color': '#3498db'
            },
            {
                'name': 'Information Technology',
                'description': 'Dokumentasi teknis, panduan sistem, dan prosedur IT',
                'color': '#2ecc71'
            },
            {
                'name': 'Finance & Accounting',
                'description': 'Prosedur keuangan, akuntansi, dan pelaporan',
                'color': '#e74c3c'
            },
            {
                'name': 'Operations',
                'description': 'Prosedur operasional, workflow, dan standar kerja',
                'color': '#f39c12'
            },
            {
                'name': 'Marketing & Sales',
                'description': 'Strategi pemasaran, panduan penjualan, dan materi promosi',
                'color': '#9b59b6'
            },
            {
                'name': 'Quality Assurance',
                'description': 'Standar kualitas, prosedur pengujian, dan kontrol mutu',
                'color': '#1abc9c'
            },
            {
                'name': 'Legal & Compliance',
                'description': 'Dokumen hukum, kebijakan kepatuhan, dan regulasi',
                'color': '#34495e'
            }
        ]

        categories = []
        for cat_data in categories_data:
            category, created = DocumentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color']
                }
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create tags
        tags_data = [
            'kebijakan', 'prosedur', 'panduan', 'template', 'checklist',
            'training', 'onboarding', 'performance', 'recruitment', 'payroll',
            'sistem', 'database', 'network', 'security', 'backup',
            'budget', 'invoice', 'expense', 'audit', 'tax',
            'workflow', 'sop', 'quality', 'maintenance', 'inventory',
            'campaign', 'lead', 'customer', 'product', 'pricing',
            'testing', 'documentation', 'standard', 'certification', 'review',
            'contract', 'regulation', 'policy', 'compliance', 'risk'
        ]

        tags = []
        for tag_name in tags_data:
            tag, created = DocumentTag.objects.get_or_create(
                name=tag_name,
                defaults={'color': '#6c757d'}
            )
            tags.append(tag)
            if created:
                self.stdout.write(f'Created tag: {tag.name}')

        # Get or create a default user
        try:
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            if not default_user:
                default_user = User.objects.create_user(
                    username='admin',
                    email='admin@company.com',
                    password='admin123',
                    is_superuser=True,
                    is_staff=True
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating user: {e}'))
            return

        # Create knowledge documents
        documents_data = [
            # HR Documents
            {
                'title': 'Panduan Onboarding Karyawan Baru',
                'description': 'Prosedur lengkap untuk orientasi dan integrasi karyawan baru ke dalam organisasi',
                'category': 'Human Resources',
                'content': '''# Panduan Onboarding Karyawan Baru

## Tujuan
Memastikan karyawan baru dapat beradaptasi dengan cepat dan efektif dalam lingkungan kerja.

## Tahapan Onboarding

### Hari Pertama
1. **Penyambutan dan Orientasi**
   - Perkenalan dengan tim dan supervisor langsung
   - Tour fasilitas kantor
   - Penjelasan budaya perusahaan

2. **Administrasi**
   - Pengisian formulir kepegawaian
   - Foto untuk ID card
   - Setup akun sistem dan email

### Minggu Pertama
1. **Training Dasar**
   - Kebijakan perusahaan
   - Prosedur keselamatan kerja
   - Sistem dan tools yang digunakan

2. **Penugasan Awal**
   - Briefing job description
   - Target dan ekspektasi
   - Jadwal training lanjutan

### Bulan Pertama
1. **Evaluasi Progress**
   - Meeting dengan supervisor
   - Feedback dan penyesuaian
   - Rencana pengembangan

## Checklist Onboarding
- [ ] Kontrak kerja ditandatangani
- [ ] ID card dan akses sistem
- [ ] Training dasar selesai
- [ ] Evaluasi 30 hari

## Kontak
HR Department: hr@company.com''',
                'tags': ['onboarding', 'training', 'prosedur', 'checklist'],
                'status': 'published'
            },
            {
                'title': 'Kebijakan Cuti dan Absensi',
                'description': 'Aturan dan prosedur terkait pengajuan cuti, izin, dan sistem absensi karyawan',
                'category': 'Human Resources',
                'content': '''# Kebijakan Cuti dan Absensi

## Jenis Cuti

### Cuti Tahunan
- Hak: 12 hari per tahun
- Dapat diambil setelah masa kerja 6 bulan
- Maksimal 3 hari berturut-turut tanpa persetujuan khusus

### Cuti Sakit
- Maksimal 30 hari per tahun
- Wajib melampirkan surat dokter untuk >3 hari
- Dapat diperpanjang dengan persetujuan manajemen

### Cuti Khusus
- Pernikahan: 3 hari
- Kelahiran anak: 2 hari
- Kematian keluarga: 2-3 hari
- Ibadah haji: 40 hari

## Prosedur Pengajuan
1. Isi form pengajuan cuti
2. Approval supervisor langsung
3. Submit ke HR minimal 3 hari sebelumnya
4. Konfirmasi persetujuan

## Sistem Absensi
- Jam kerja: 08:00 - 17:00
- Toleransi keterlambatan: 15 menit
- Absen menggunakan fingerprint/card
- Lembur harus mendapat persetujuan

## Sanksi
- Terlambat >3x dalam sebulan: teguran lisan
- Alpha tanpa keterangan: potongan gaji
- Pelanggaran berulang: teguran tertulis''',
                'tags': ['kebijakan', 'cuti', 'absensi', 'prosedur'],
                'status': 'published'
            },
            
            # IT Documents
            {
                'title': 'Panduan Keamanan Sistem Informasi',
                'description': 'Kebijakan dan prosedur keamanan untuk melindungi aset digital perusahaan',
                'category': 'Information Technology',
                'content': '''# Panduan Keamanan Sistem Informasi

## Kebijakan Password

### Persyaratan Password
- Minimal 8 karakter
- Kombinasi huruf besar, kecil, angka, dan simbol
- Tidak menggunakan informasi personal
- Diganti setiap 90 hari

### Larangan
- Sharing password dengan orang lain
- Menggunakan password yang sama untuk multiple akun
- Menyimpan password di tempat yang mudah diakses

## Akses Sistem

### Prinsip Least Privilege
- User hanya mendapat akses sesuai kebutuhan kerja
- Review akses dilakukan setiap 6 bulan
- Akses dicabut saat karyawan resign/pindah divisi

### Remote Access
- Wajib menggunakan VPN
- Two-factor authentication untuk sistem kritikal
- Monitoring aktivitas remote access

## Backup dan Recovery

### Jadwal Backup
- Daily: Database dan file kritikal
- Weekly: Full system backup
- Monthly: Archive ke offsite storage

### Testing Recovery
- Test restore dilakukan bulanan
- Dokumentasi prosedur recovery
- RTO (Recovery Time Objective): 4 jam

## Incident Response

### Pelaporan
- Segera laporkan insiden keamanan ke IT Security
- Jangan mencoba mengatasi sendiri
- Dokumentasikan kronologi kejadian

### Eskalasi
1. Level 1: IT Support
2. Level 2: IT Security Team
3. Level 3: IT Manager
4. Level 4: Management''',
                'tags': ['security', 'sistem', 'kebijakan', 'backup'],
                'status': 'published'
            },
            {
                'title': 'Prosedur Instalasi Software',
                'description': 'Panduan untuk instalasi dan konfigurasi software di lingkungan perusahaan',
                'category': 'Information Technology',
                'content': '''# Prosedur Instalasi Software

## Persetujuan Instalasi

### Software yang Diizinkan
- Software berlisensi resmi
- Open source dengan lisensi kompatibel
- Software yang telah disetujui IT Security

### Proses Approval
1. Submit request melalui IT Service Desk
2. Review kebutuhan bisnis
3. Security assessment
4. Approval dari IT Manager

## Tahapan Instalasi

### Pre-Installation
1. **Backup System**
   - Create system restore point
   - Backup critical data
   - Document current configuration

2. **Environment Check**
   - Verify system requirements
   - Check compatibility
   - Ensure sufficient disk space

### Installation Process
1. **Download Software**
   - Dari sumber resmi/trusted
   - Verify checksum/digital signature
   - Scan dengan antivirus

2. **Installation**
   - Run dengan admin privileges
   - Follow installation wizard
   - Configure security settings

### Post-Installation
1. **Configuration**
   - Apply security hardening
   - Configure user permissions
   - Setup monitoring/logging

2. **Testing**
   - Functional testing
   - Integration testing
   - Performance testing

3. **Documentation**
   - Update asset inventory
   - Document configuration
   - Create user guide

## Software Categories

### Productivity Software
- Microsoft Office Suite
- Adobe Creative Suite
- Project management tools

### Development Tools
- IDEs (Visual Studio, IntelliJ)
- Version control (Git)
- Database tools

### Security Software
- Antivirus/Anti-malware
- VPN clients
- Encryption tools

## Maintenance
- Regular updates dan patches
- License compliance monitoring
- Performance monitoring
- Periodic security scans''',
                'tags': ['software', 'instalasi', 'prosedur', 'dokumentasi'],
                'status': 'published'
            },
            
            # Finance Documents
            {
                'title': 'Prosedur Pengajuan Reimbursement',
                'description': 'Panduan lengkap untuk pengajuan penggantian biaya operasional dan perjalanan dinas',
                'category': 'Finance & Accounting',
                'content': '''# Prosedur Pengajuan Reimbursement

## Jenis Reimbursement

### Perjalanan Dinas
- Transportasi (pesawat, kereta, bus)
- Akomodasi hotel
- Makan dan minum
- Transportasi lokal

### Operasional
- Supplies kantor
- Komunikasi (pulsa, internet)
- Entertainment klien
- Training dan seminar

## Persyaratan Dokumen

### Dokumen Wajib
1. **Form Reimbursement**
   - Diisi lengkap dan ditandatangani
   - Approval dari supervisor
   - Kode budget yang benar

2. **Bukti Pembayaran**
   - Kwitansi/invoice asli
   - Struk pembayaran
   - Boarding pass (untuk tiket pesawat)

3. **Dokumen Pendukung**
   - Surat tugas (untuk perjalanan dinas)
   - Laporan kegiatan
   - Foto kegiatan (jika diperlukan)

## Batas Waktu dan Nominal

### Batas Waktu Pengajuan
- Maksimal 30 hari setelah pengeluaran
- Pengajuan di atas 30 hari perlu approval khusus
- Deadline akhir tahun: 15 Desember

### Batas Nominal
- Makan: Rp 150,000/hari
- Hotel: Sesuai grade jabatan
- Transportasi: Actual cost
- Entertainment: Maksimal Rp 500,000/bulan

## Proses Approval

### Alur Persetujuan
1. **Supervisor Langsung**
   - Review kelengkapan dokumen
   - Validasi kebutuhan bisnis
   - Approval pertama

2. **Finance Team**
   - Verifikasi dokumen
   - Check budget availability
   - Validasi perhitungan

3. **Finance Manager**
   - Final approval
   - Authorization pembayaran

### Timeline Proses
- Pengajuan lengkap: 5-7 hari kerja
- Pengajuan tidak lengkap: dikembalikan untuk perbaikan
- Pembayaran: setiap Jumat

## Tips Pengajuan

### Persiapan Dokumen
- Scan dokumen dengan kualitas baik
- Susun dokumen sesuai urutan
- Beri keterangan yang jelas

### Hindari Kesalahan
- Pastikan tanggal tidak expired
- Cek kesesuaian nama dan nominal
- Lengkapi semua field yang required

## Kontak
- Finance Team: finance@company.com
- Ext: 1234
- Lokasi: Lantai 2, Ruang Finance''',
                'tags': ['reimbursement', 'finance', 'prosedur', 'expense'],
                'status': 'published'
            },
            {
                'title': 'Panduan Budgeting dan Forecasting',
                'description': 'Metodologi dan prosedur untuk penyusunan anggaran dan proyeksi keuangan',
                'category': 'Finance & Accounting',
                'content': '''# Panduan Budgeting dan Forecasting

## Overview

Budgeting dan forecasting adalah proses penting dalam perencanaan keuangan perusahaan yang membantu dalam pengambilan keputusan strategis dan operasional.

## Siklus Budgeting

### Timeline Tahunan
- **Juli-Agustus**: Guideline dan asumsi dasar
- **September**: Draft budget departemen
- **Oktober**: Konsolidasi dan review
- **November**: Finalisasi dan approval
- **Desember**: Komunikasi budget final

### Komponen Budget

#### Revenue Budget
- Sales forecast berdasarkan historical data
- Market analysis dan trend
- New product/service launch
- Seasonal adjustment

#### Expense Budget
- **Fixed Costs**: Gaji, sewa, insurance
- **Variable Costs**: Material, commission
- **Discretionary**: Marketing, training, R&D

#### Capital Budget
- Equipment dan technology
- Facility improvement
- Strategic investment

## Metodologi Forecasting

### Quantitative Methods
1. **Trend Analysis**
   - Linear regression
   - Moving averages
   - Seasonal decomposition

2. **Statistical Models**
   - ARIMA models
   - Exponential smoothing
   - Multiple regression

### Qualitative Methods
1. **Expert Opinion**
   - Management judgment
   - Sales team input
   - Industry expert consultation

2. **Market Research**
   - Customer surveys
   - Competitor analysis
   - Economic indicators

## Budget Monitoring

### Monthly Review
- Actual vs Budget comparison
- Variance analysis
- Forecast update
- Action plan untuk deviasi

### Key Metrics
- Revenue growth rate
- Gross margin percentage
- Operating expense ratio
- EBITDA margin

### Reporting Format
- Executive dashboard
- Departmental reports
- Variance explanation
- Corrective actions

## Best Practices

### Preparation
- Involve key stakeholders
- Use reliable data sources
- Consider multiple scenarios
- Document assumptions

### Execution
- Regular monitoring
- Flexible adjustment
- Clear communication
- Accountability measures

### Tools dan Software
- Excel/Google Sheets
- Specialized budgeting software
- ERP integration
- Business intelligence tools

## Common Challenges

### Data Quality
- Incomplete historical data
- Inconsistent reporting
- Manual errors

### Solutions
- Data validation procedures
- Automated data collection
- Regular data cleansing

### Organizational
- Lack of buy-in
- Unrealistic targets
- Poor communication

### Solutions
- Stakeholder involvement
- Realistic goal setting
- Regular communication''',
                'tags': ['budget', 'forecasting', 'planning', 'finance'],
                'status': 'published'
            },
            
            # Operations Documents
            {
                'title': 'Standard Operating Procedure (SOP) Produksi',
                'description': 'Prosedur standar untuk proses produksi yang memastikan kualitas dan efisiensi',
                'category': 'Operations',
                'content': '''# Standard Operating Procedure (SOP) Produksi

## Tujuan
Memastikan proses produksi berjalan konsisten, efisien, dan menghasilkan produk berkualitas sesuai standar.

## Ruang Lingkup
SOP ini berlaku untuk semua aktivitas produksi di fasilitas manufacturing perusahaan.

## Tahapan Produksi

### 1. Persiapan Produksi

#### Material Preparation
- **Inspeksi Raw Material**
  - Check kualitas sesuai spesifikasi
  - Verifikasi quantity dan batch number
  - Update inventory system

- **Setup Mesin**
  - Kalibrasi equipment
  - Test run untuk memastikan performance
  - Safety check semua komponen

#### Work Order Processing
- Review production schedule
- Assign operator dan supervisor
- Prepare work instruction
- Set quality parameters

### 2. Proses Produksi

#### Pre-Production Check
1. **Safety Briefing**
   - Review safety procedures
   - Check PPE (Personal Protective Equipment)
   - Identify potential hazards

2. **Quality Setup**
   - Set quality control points
   - Prepare inspection tools
   - Define acceptance criteria

#### Production Execution
1. **Start-up Procedure**
   - Follow machine start-up sequence
   - Monitor initial output quality
   - Adjust parameters if needed

2. **Continuous Monitoring**
   - Regular quality checks
   - Monitor production rate
   - Record process parameters
   - Document any deviations

3. **In-Process Quality Control**
   - Sampling setiap 2 jam
   - Dimensional checks
   - Visual inspection
   - Functional testing

### 3. Post-Production

#### Shutdown Procedure
- Clean equipment
- Store tools dan materials
- Update production records
- Handover ke shift berikutnya

#### Final Inspection
- Complete quality audit
- Package finished goods
- Update inventory
- Generate production report

## Quality Standards

### Acceptance Criteria
- Dimensional tolerance: ±0.1mm
- Surface finish: Ra 1.6
- Functional test: 100% pass rate
- Visual defects: Zero tolerance

### Rejection Handling
- Segregate defective products
- Root cause analysis
- Corrective action
- Rework if possible

## Safety Requirements

### Personal Protective Equipment
- Safety glasses (mandatory)
- Steel-toed boots
- Gloves (when handling materials)
- Hearing protection (noise >85dB)

### Emergency Procedures
- Emergency stop locations
- First aid procedures
- Fire evacuation plan
- Incident reporting

## Documentation

### Required Records
- Production log sheets
- Quality inspection reports
- Material consumption
- Downtime analysis
- Maintenance activities

### Retention Period
- Production records: 3 years
- Quality data: 5 years
- Safety incidents: Permanent

## Continuous Improvement

### Performance Metrics
- Overall Equipment Effectiveness (OEE)
- First Pass Yield (FPY)
- Cycle time
- Defect rate

### Review Process
- Monthly performance review
- Quarterly SOP update
- Annual comprehensive audit
- Feedback incorporation''',
                'tags': ['sop', 'produksi', 'quality', 'workflow'],
                'status': 'published'
            },
            {
                'title': 'Prosedur Maintenance Preventif',
                'description': 'Panduan untuk pelaksanaan maintenance preventif equipment dan fasilitas',
                'category': 'Operations',
                'content': '''# Prosedur Maintenance Preventif

## Definisi
Maintenance preventif adalah kegiatan perawatan yang dilakukan secara terjadwal untuk mencegah kerusakan equipment dan mempertahankan performance optimal.

## Tujuan
- Mencegah breakdown yang tidak terduga
- Memperpanjang umur equipment
- Menjaga kualitas produk
- Mengurangi biaya maintenance
- Meningkatkan safety

## Klasifikasi Equipment

### Critical Equipment (A)
- Equipment yang berdampak langsung pada produksi
- Downtime cost tinggi
- Safety critical
- **Frequency**: Weekly inspection, Monthly maintenance

### Important Equipment (B)
- Equipment pendukung produksi
- Moderate downtime impact
- **Frequency**: Bi-weekly inspection, Quarterly maintenance

### Standard Equipment (C)
- Equipment non-critical
- Minimal production impact
- **Frequency**: Monthly inspection, Semi-annual maintenance

## Jadwal Maintenance

### Daily Checks (Operator)
- Visual inspection
- Basic cleaning
- Lubrication points
- Parameter monitoring
- Abnormality reporting

### Weekly Maintenance
- **Mechanical Systems**
  - Belt tension check
  - Bearing lubrication
  - Coupling alignment
  - Vibration monitoring

- **Electrical Systems**
  - Connection tightness
  - Insulation check
  - Motor temperature
  - Control system test

### Monthly Maintenance
- **Comprehensive Inspection**
  - Disassembly critical components
  - Wear measurement
  - Replacement consumables
  - Calibration instruments

- **Performance Testing**
  - Efficiency measurement
  - Accuracy verification
  - Speed/torque testing
  - Safety system check

### Annual Overhaul
- Complete equipment teardown
- Major component replacement
- System upgrade
- Comprehensive testing
- Documentation update

## Maintenance Procedures

### Pre-Maintenance
1. **Work Permit**
   - Obtain maintenance permit
   - LOTO (Lock Out Tag Out) procedure
   - Safety briefing
   - Tool preparation

2. **Documentation Review**
   - Equipment manual
   - Previous maintenance history
   - Spare parts availability
   - Special procedures

### During Maintenance
1. **Safety First**
   - Follow LOTO procedures
   - Use appropriate PPE
   - Monitor hazardous conditions
   - Emergency contact ready

2. **Systematic Approach**
   - Follow checklist
   - Document findings
   - Take photos if needed
   - Measure critical parameters

3. **Quality Control**
   - Use calibrated tools
   - Follow torque specifications
   - Verify proper installation
   - Test functionality

### Post-Maintenance
1. **Testing dan Commissioning**
   - Function test
   - Performance verification
   - Safety system check
   - Production trial run

2. **Documentation**
   - Complete work order
   - Update maintenance records
   - Parts consumption
   - Recommendations

## Spare Parts Management

### Inventory Categories
- **Critical Spares**: Always in stock
- **Insurance Spares**: Long lead time items
- **Consumables**: Regular replenishment
- **Standard Parts**: Available from suppliers

### Procurement Planning
- Annual spare parts budget
- Vendor agreements
- Emergency procurement procedures
- Obsolescence management

## Key Performance Indicators

### Maintenance Metrics
- **MTBF** (Mean Time Between Failures)
- **MTTR** (Mean Time To Repair)
- **Planned vs Unplanned Maintenance Ratio**
- **Maintenance Cost per Unit**
- **Equipment Availability**

### Targets
- Equipment availability: >95%
- Planned maintenance: >80%
- Emergency repairs: <10%
- Maintenance cost: <5% of production cost

## Continuous Improvement

### Root Cause Analysis
- Failure mode analysis
- Trend identification
- Corrective actions
- Preventive measures

### Technology Integration
- Condition monitoring systems
- Predictive maintenance tools
- CMMS (Computerized Maintenance Management System)
- IoT sensors implementation''',
                'tags': ['maintenance', 'preventif', 'equipment', 'prosedur'],
                'status': 'published'
            },
            
            # Marketing Documents
            {
                'title': 'Strategi Digital Marketing 2024',
                'description': 'Rencana komprehensif untuk implementasi strategi pemasaran digital',
                'category': 'Marketing & Sales',
                'content': '''# Strategi Digital Marketing 2024

## Executive Summary

Strategi digital marketing ini dirancang untuk meningkatkan brand awareness, lead generation, dan customer acquisition melalui channel digital yang terintegrasi.

## Situasi Saat Ini

### Market Analysis
- **Target Market**: B2B dan B2C
- **Market Size**: Rp 50 miliar
- **Growth Rate**: 15% annually
- **Competition**: 5 major competitors

### Digital Presence Audit
- Website traffic: 10,000 monthly visitors
- Social media followers: 25,000 total
- Email subscribers: 5,000 active
- Conversion rate: 2.5%

## Objectives 2024

### Primary Goals
1. **Increase Website Traffic**: 50% growth (15,000 monthly visitors)
2. **Lead Generation**: 200% increase (300 qualified leads/month)
3. **Brand Awareness**: 40% increase in brand recognition
4. **Customer Acquisition**: 100 new customers
5. **ROI**: Achieve 300% return on marketing investment

### Secondary Goals
- Social media engagement: +60%
- Email open rates: >25%
- Customer lifetime value: +30%
- Market share: +5%

## Target Audience

### Primary Personas

#### Persona 1: Business Decision Maker
- **Demographics**: 35-50 years, Manager/Director level
- **Behavior**: Research-oriented, value-conscious
- **Channels**: LinkedIn, Industry publications, Email
- **Pain Points**: Cost efficiency, ROI measurement

#### Persona 2: Technical Evaluator
- **Demographics**: 28-40 years, Technical specialist
- **Behavior**: Detail-oriented, peer-influenced
- **Channels**: Technical blogs, Forums, YouTube
- **Pain Points**: Implementation complexity, Integration

#### Persona 3: End User
- **Demographics**: 25-45 years, Operational staff
- **Behavior**: Convenience-focused, mobile-first
- **Channels**: Social media, Mobile apps, Reviews
- **Pain Points**: Ease of use, Support availability

## Channel Strategy

### Search Engine Optimization (SEO)

#### Technical SEO
- Website speed optimization (<3 seconds)
- Mobile responsiveness
- SSL certificate implementation
- XML sitemap optimization

#### Content SEO
- **Target Keywords**: 50 primary, 200 long-tail
- **Content Calendar**: 4 blog posts/month
- **Local SEO**: Google My Business optimization
- **Link Building**: 20 quality backlinks/month

### Pay-Per-Click (PPC) Advertising

#### Google Ads
- **Budget**: Rp 50 juta/month
- **Campaigns**: Search, Display, Shopping
- **Target CPC**: Rp 5,000
- **Target CTR**: >3%

#### Social Media Ads
- **Facebook/Instagram**: Rp 20 juta/month
- **LinkedIn**: Rp 15 juta/month
- **YouTube**: Rp 10 juta/month

### Content Marketing

#### Blog Strategy
- **Frequency**: 4 posts/month
- **Types**: How-to guides, Case studies, Industry insights
- **Distribution**: Website, Social media, Email newsletter

#### Video Content
- **YouTube Channel**: 2 videos/month
- **Types**: Product demos, Customer testimonials, Tutorials
- **Live Streaming**: Monthly webinars

#### Downloadable Resources
- **E-books**: 1 per quarter
- **Whitepapers**: Industry research
- **Templates**: Practical tools for customers
- **Checklists**: Quick reference guides

### Social Media Marketing

#### Platform Strategy
- **LinkedIn**: B2B networking, thought leadership
- **Facebook**: Community building, customer service
- **Instagram**: Visual storytelling, behind-the-scenes
- **YouTube**: Educational content, product demos
- **Twitter**: News, customer support, industry discussions

#### Content Mix
- 40% Educational content
- 30% Company updates
- 20% User-generated content
- 10% Promotional content

### Email Marketing

#### Campaign Types
- **Newsletter**: Bi-weekly industry insights
- **Nurture Sequences**: 7-email onboarding series
- **Product Updates**: Monthly feature announcements
- **Event Invitations**: Webinars, trade shows

#### Segmentation
- Industry vertical
- Company size
- Engagement level
- Purchase history
- Geographic location

## Implementation Timeline

### Q1 2024 (Jan-Mar)
- Website optimization
- SEO foundation setup
- Content calendar creation
- PPC campaign launch
- Social media strategy implementation

### Q2 2024 (Apr-Jun)
- Content production ramp-up
- Email automation setup
- Influencer partnerships
- Video content creation
- Performance optimization

### Q3 2024 (Jul-Sep)
- Advanced SEO tactics
- Retargeting campaigns
- Customer advocacy program
- Marketing automation enhancement
- Mid-year performance review

### Q4 2024 (Oct-Dec)
- Holiday campaigns
- Year-end promotions
- Strategy refinement
- Planning for 2025
- Annual performance analysis

## Budget Allocation

### Total Annual Budget: Rp 1.2 miliar

- **Paid Advertising**: 40% (Rp 480 juta)
- **Content Creation**: 25% (Rp 300 juta)
- **Tools dan Software**: 15% (Rp 180 juta)
- **Personnel**: 15% (Rp 180 juta)
- **Events dan PR**: 5% (Rp 60 juta)

## Measurement dan Analytics

### Key Performance Indicators (KPIs)

#### Traffic Metrics
- Organic traffic growth
- Paid traffic ROI
- Bounce rate
- Session duration
- Pages per session

#### Conversion Metrics
- Lead conversion rate
- Cost per lead
- Customer acquisition cost
- Lifetime value
- Return on ad spend (ROAS)

#### Engagement Metrics
- Social media engagement rate
- Email open/click rates
- Video view duration
- Content shares
- Brand mention sentiment

### Reporting Schedule
- **Daily**: Campaign performance monitoring
- **Weekly**: Traffic dan conversion analysis
- **Monthly**: Comprehensive performance report
- **Quarterly**: Strategy review dan optimization

## Risk Management

### Potential Risks
- Algorithm changes (Google, Facebook)
- Increased competition
- Economic downturn
- Technology disruptions
- Regulatory changes

### Mitigation Strategies
- Diversified channel approach
- Continuous monitoring dan adaptation
- Flexible budget allocation
- Strong organic presence
- Regular strategy updates''',
                'tags': ['marketing', 'digital', 'strategy', 'campaign'],
                'status': 'published'
            },
            {
                'title': 'Panduan Customer Relationship Management (CRM)',
                'description': 'Prosedur dan best practices untuk mengelola hubungan pelanggan menggunakan sistem CRM',
                'category': 'Marketing & Sales',
                'content': '''# Panduan Customer Relationship Management (CRM)

## Overview

CRM adalah strategi bisnis yang berfokus pada membangun dan memelihara hubungan jangka panjang dengan pelanggan untuk meningkatkan kepuasan, loyalitas, dan profitabilitas.

## Tujuan CRM

### Primary Objectives
- Meningkatkan customer satisfaction
- Meningkatkan customer retention rate
- Mengoptimalkan customer lifetime value
- Meningkatkan efisiensi sales process
- Memperbaiki customer service quality

### Secondary Objectives
- Centralized customer data
- Improved communication
- Better sales forecasting
- Enhanced marketing effectiveness
- Streamlined business processes

## Customer Lifecycle Management

### 1. Lead Generation

#### Lead Sources
- **Digital Marketing**: Website, social media, email campaigns
- **Traditional Marketing**: Print ads, radio, TV
- **Referrals**: Existing customers, partners
- **Events**: Trade shows, seminars, webinars
- **Cold Outreach**: Cold calls, emails

#### Lead Qualification
- **BANT Criteria**:
  - **Budget**: Financial capability
  - **Authority**: Decision-making power
  - **Need**: Business requirement
  - **Timeline**: Purchase timeframe

#### Lead Scoring
- **Demographic Score** (0-25 points)
  - Company size, industry, location
- **Behavioral Score** (0-25 points)
  - Website visits, content downloads, email engagement
- **Engagement Score** (0-25 points)
  - Sales interactions, demo requests
- **Fit Score** (0-25 points)
  - Match with ideal customer profile

### 2. Sales Process

#### Opportunity Management
1. **Qualification Stage**
   - Verify BANT criteria
   - Understand pain points
   - Identify stakeholders
   - Assess competition

2. **Proposal Stage**
   - Solution presentation
   - Proposal development
   - Pricing negotiation
   - Contract terms discussion

3. **Closing Stage**
   - Final objection handling
   - Contract finalization
   - Implementation planning
   - Handover to delivery team

#### Sales Pipeline Stages
- **Prospecting** (0-10% probability)
- **Qualification** (10-25% probability)
- **Needs Analysis** (25-50% probability)
- **Proposal** (50-75% probability)
- **Negotiation** (75-90% probability)
- **Closed Won/Lost** (100%/0% probability)

### 3. Customer Onboarding

#### Onboarding Process
1. **Welcome Package**
   - Welcome email/call
   - Account setup information
   - Implementation timeline
   - Key contact information

2. **Implementation**
   - Project kickoff meeting
   - System configuration
   - Data migration
   - User training

3. **Go-Live Support**
   - Launch preparation
   - Go-live assistance
   - Initial support
   - Success measurement

### 4. Customer Success

#### Account Management
- **Regular Check-ins**: Monthly/quarterly reviews
- **Health Scoring**: Usage metrics, satisfaction surveys
- **Expansion Opportunities**: Upsell/cross-sell identification
- **Renewal Management**: Contract renewal preparation

#### Customer Support
- **Multi-channel Support**: Phone, email, chat, portal
- **Ticket Management**: Priority-based routing
- **Knowledge Base**: Self-service resources
- **Escalation Procedures**: Clear escalation paths

## CRM System Management

### Data Management

#### Data Quality Standards
- **Completeness**: All required fields filled
- **Accuracy**: Correct and up-to-date information
- **Consistency**: Standardized formats
- **Uniqueness**: No duplicate records

#### Data Hygiene Practices
- **Regular Audits**: Monthly data quality checks
- **Duplicate Management**: Automated duplicate detection
- **Data Validation**: Input validation rules
- **Data Enrichment**: Third-party data integration

### User Management

#### Role-Based Access Control
- **Sales Rep**: Own accounts and opportunities
- **Sales Manager**: Team accounts and reporting
- **Marketing**: Lead management and campaigns
- **Customer Success**: Account health and renewals
- **Admin**: System configuration and user management

#### Training dan Adoption
- **Initial Training**: System basics and processes
- **Ongoing Training**: New features and best practices
- **User Support**: Help desk and documentation
- **Adoption Monitoring**: Usage analytics and coaching

## Performance Metrics

### Sales Metrics
- **Conversion Rates**: Lead to opportunity, opportunity to customer
- **Sales Cycle Length**: Average time from lead to close
- **Win Rate**: Percentage of opportunities won
- **Average Deal Size**: Mean value of closed deals
- **Sales Velocity**: (Opportunities × Win Rate × Average Deal Size) / Sales Cycle Length

### Customer Metrics
- **Customer Acquisition Cost (CAC)**: Total cost to acquire a customer
- **Customer Lifetime Value (CLV)**: Total value of customer relationship
- **Churn Rate**: Percentage of customers lost per period
- **Net Promoter Score (NPS)**: Customer satisfaction and loyalty
- **Customer Satisfaction (CSAT)**: Service quality measurement

### System Metrics
- **User Adoption Rate**: Percentage of active users
- **Data Quality Score**: Overall data health rating
- **System Uptime**: Availability and reliability
- **Response Time**: System performance metrics

## Best Practices

### Data Entry
- **Consistent Formatting**: Use standardized formats
- **Complete Information**: Fill all relevant fields
- **Timely Updates**: Update records promptly
- **Accurate Logging**: Record all customer interactions

### Communication
- **Personalization**: Tailor messages to customer needs
- **Consistency**: Maintain consistent brand voice
- **Timeliness**: Respond promptly to inquiries
- **Documentation**: Record all communications

### Process Optimization
- **Regular Reviews**: Assess and improve processes
- **Automation**: Automate repetitive tasks
- **Integration**: Connect with other business systems
- **Feedback Loop**: Incorporate user feedback

## Integration Strategy

### System Integrations
- **Marketing Automation**: Lead nurturing and scoring
- **Email Marketing**: Campaign management and tracking
- **Customer Support**: Ticket and case management
- **Accounting**: Invoice and payment tracking
- **E-commerce**: Order and transaction data

### Data Synchronization
- **Real-time Sync**: Critical data updates
- **Batch Processing**: Large data transfers
- **Error Handling**: Failed sync resolution
- **Audit Trail**: Change tracking and logging

## Continuous Improvement

### Regular Assessments
- **Quarterly Reviews**: Performance and process evaluation
- **User Feedback**: Collect and analyze user input
- **System Audits**: Technical and data quality checks
- **Competitive Analysis**: Market and technology trends

### Optimization Initiatives
- **Process Refinement**: Streamline workflows
- **Feature Enhancement**: Add new capabilities
- **Training Updates**: Refresh user skills
- **Technology Upgrades**: System improvements''',
                'tags': ['crm', 'customer', 'sales', 'panduan'],
                'status': 'published'
            },
            
            # Quality Assurance Documents
            {
                'title': 'Manual Quality Control dan Testing',
                'description': 'Panduan komprehensif untuk implementasi quality control dan testing procedures',
                'category': 'Quality Assurance',
                'content': '''# Manual Quality Control dan Testing

## Pendahuluan

Quality Control (QC) adalah proses sistematis untuk memastikan produk atau layanan memenuhi standar kualitas yang ditetapkan melalui inspeksi, testing, dan verifikasi.

## Filosofi Kualitas

### Prinsip Dasar
- **Customer Focus**: Kualitas didefinisikan oleh kepuasan pelanggan
- **Prevention**: Mencegah defect lebih baik daripada mendeteksi
- **Continuous Improvement**: Peningkatan berkelanjutan
- **Employee Involvement**: Semua karyawan bertanggung jawab atas kualitas
- **Data-Driven Decisions**: Keputusan berdasarkan data dan fakta

### Quality Policy
"Kami berkomitmen untuk menyediakan produk dan layanan berkualitas tinggi yang memenuhi atau melampaui ekspektasi pelanggan melalui proses yang efisien dan peningkatan berkelanjutan."

## Quality Control Framework

### 1. Incoming Material Inspection

#### Raw Material Testing
- **Physical Properties**
  - Dimensi dan toleransi
  - Berat dan density
  - Surface finish
  - Color consistency

- **Chemical Properties**
  - Composition analysis
  - Purity testing
  - Contamination check
  - pH level measurement

- **Mechanical Properties**
  - Tensile strength
  - Hardness testing
  - Flexibility test
  - Impact resistance

#### Supplier Quality Management
- **Vendor Qualification**
  - Quality system audit
  - Capability assessment
  - Sample evaluation
  - Certification verification

- **Supplier Monitoring**
  - Performance scorecards
  - Regular audits
  - Corrective action tracking
  - Continuous improvement programs

### 2. In-Process Quality Control

#### Process Monitoring
- **Statistical Process Control (SPC)**
  - Control charts implementation
  - Process capability studies
  - Trend analysis
  - Out-of-control action plans

- **First Article Inspection (FAI)**
  - Setup verification
  - Dimensional inspection
  - Functional testing
  - Documentation requirements

#### Quality Checkpoints
- **Stage 1**: Material preparation
- **Stage 2**: Initial processing
- **Stage 3**: Intermediate inspection
- **Stage 4**: Final processing
- **Stage 5**: Pre-packaging inspection

### 3. Final Product Testing

#### Comprehensive Testing Protocol

##### Functional Testing
1. **Performance Verification**
   - Specification compliance
   - Operating parameters
   - Efficiency measurement
   - Reliability testing

2. **Safety Testing**
   - Electrical safety
   - Mechanical safety
   - Chemical safety
   - Environmental safety

3. **Durability Testing**
   - Life cycle testing
   - Stress testing
   - Environmental testing
   - Accelerated aging

##### Quality Attributes
- **Appearance**: Visual defects, finish quality
- **Dimensions**: Critical measurements, tolerances
- **Function**: Performance specifications
- **Reliability**: Failure rate, MTBF
- **Safety**: Compliance with safety standards

## Testing Methodologies

### Destructive Testing

#### When to Use
- Material property verification
- Failure mode analysis
- Batch qualification
- Research and development

#### Common Tests
- **Tensile Testing**: Ultimate strength, yield point
- **Impact Testing**: Toughness, brittleness
- **Fatigue Testing**: Cyclic loading resistance
- **Corrosion Testing**: Environmental resistance

### Non-Destructive Testing (NDT)

#### Methods
1. **Visual Inspection**
   - Surface defects
   - Dimensional verification
   - Assembly correctness
   - Cleanliness assessment

2. **Ultrasonic Testing**
   - Internal defect detection
   - Thickness measurement
   - Material characterization
   - Bond integrity

3. **X-Ray Inspection**
   - Internal structure analysis
   - Void detection
   - Assembly verification
   - Foreign object detection

4. **Magnetic Particle Testing**
   - Surface crack detection
   - Subsurface defects
   - Weld inspection
   - Material discontinuities

### Statistical Sampling

#### Sampling Plans
- **Single Sampling**: One sample, accept/reject decision
- **Double Sampling**: Two-stage sampling process
- **Multiple Sampling**: Sequential sampling approach
- **Skip-lot Sampling**: Reduced inspection frequency

#### Sample Size Determination
- **Population Size**: Total lot quantity
- **Confidence Level**: Typically 95% or 99%
- **Acceptable Quality Level (AQL)**: Maximum defect rate
- **Risk Levels**: Producer and consumer risks

## Quality Documentation

### Test Records

#### Required Information
- **Test Identification**
  - Part number and revision
  - Lot/batch number
  - Test date and time
  - Inspector identification

- **Test Results**
  - Measured values
  - Pass/fail status
  - Deviations noted
  - Corrective actions

- **Equipment Information**
  - Instrument identification
  - Calibration status
  - Environmental conditions
  - Test method reference

### Quality Reports

#### Daily Quality Report
- Production summary
- Defect analysis
- Yield rates
- Corrective actions

#### Weekly Quality Summary
- Trend analysis
- Supplier performance
- Customer complaints
- Process improvements

#### Monthly Quality Review
- KPI performance
- Cost of quality
- Audit results
- Training needs

## Defect Management

### Defect Classification

#### Critical Defects
- Safety hazards
- Functional failures
- Regulatory non-compliance
- Customer-specified requirements

#### Major Defects
- Performance degradation
- Appearance issues
- Durability concerns
- Assembly problems

#### Minor Defects
- Cosmetic imperfections
- Documentation errors
- Packaging issues
- Non-critical dimensions

### Corrective Action Process

#### 8D Problem Solving
1. **D1**: Team formation
2. **D2**: Problem description
3. **D3**: Containment actions
4. **D4**: Root cause analysis
5. **D5**: Corrective actions
6. **D6**: Implementation
7. **D7**: Prevention
8. **D8**: Team recognition

## Quality Metrics dan KPIs

### Process Metrics
- **First Pass Yield (FPY)**: Percentage passing first inspection
- **Defect Rate**: Defects per million opportunities (DPMO)
- **Process Capability (Cp, Cpk)**: Process variation vs. specifications
- **Sigma Level**: Process performance measurement

### Product Metrics
- **Customer Satisfaction**: Survey results, NPS scores
- **Return Rate**: Percentage of products returned
- **Warranty Claims**: Frequency and cost of warranty issues
- **Field Failures**: Product failures in customer use

### Cost Metrics
- **Cost of Quality (COQ)**
  - Prevention costs
  - Appraisal costs
  - Internal failure costs
  - External failure costs

- **Quality ROI**: Return on quality investments
- **Scrap and Rework**: Cost of defective products
- **Inspection Costs**: Resources spent on quality control

## Continuous Improvement

### Improvement Methodologies

#### Six Sigma
- **DMAIC**: Define, Measure, Analyze, Improve, Control
- **Statistical Tools**: Hypothesis testing, regression analysis
- **Project Management**: Structured improvement projects
- **Belt System**: Training and certification levels

#### Lean Manufacturing
- **Waste Elimination**: Seven types of waste (TIMWOOD)
- **Value Stream Mapping**: Process flow analysis
- **5S Methodology**: Workplace organization
- **Kaizen**: Continuous small improvements

### Quality Circles
- **Team Formation**: Cross-functional groups
- **Problem Identification**: Data-driven selection
- **Solution Development**: Collaborative approach
- **Implementation**: Pilot testing and rollout

## Training dan Competency

### Quality Training Program

#### Basic Quality Awareness
- Quality concepts and principles
- Company quality policy
- Individual responsibilities
- Customer focus

#### Technical Training
- Inspection techniques
- Test equipment operation
- Statistical methods
- Problem-solving tools

#### Advanced Training
- Quality system management
- Audit techniques
- Leadership skills
- Change management

### Competency Assessment
- **Knowledge Tests**: Written examinations
- **Practical Demonstrations**: Hands-on evaluations
- **Certification Requirements**: External certifications
- **Continuous Learning**: Ongoing development plans''',
                'tags': ['quality', 'testing', 'control', 'standard'],
                'status': 'published'
            },
            
            # Legal Documents
            {
                'title': 'Kebijakan Kepatuhan dan Regulasi',
                'description': 'Panduan komprehensif untuk memastikan kepatuhan terhadap regulasi dan standar industri',
                'category': 'Legal & Compliance',
                'content': '''# Kebijakan Kepatuhan dan Regulasi

## Pendahuluan

Kebijakan ini menetapkan framework untuk memastikan perusahaan beroperasi sesuai dengan semua hukum, regulasi, dan standar industri yang berlaku.

## Tujuan

### Primary Objectives
- Memastikan kepatuhan penuh terhadap regulasi
- Meminimalkan risiko hukum dan finansial
- Melindungi reputasi perusahaan
- Menciptakan budaya compliance
- Mendukung operasional bisnis yang berkelanjutan

### Secondary Objectives
- Meningkatkan transparansi operasional
- Memperkuat governance structure
- Memfasilitasi audit dan review
- Mendukung ekspansi bisnis
- Meningkatkan stakeholder confidence

## Ruang Lingkup Regulasi

### 1. Regulasi Ketenagakerjaan

#### Undang-Undang Ketenagakerjaan
- **UU No. 13 Tahun 2003**: Ketenagakerjaan
- **PP No. 35 Tahun 2021**: Perjanjian Kerja Waktu Tertentu
- **Permenaker**: Berbagai peraturan teknis

#### Compliance Requirements
- **Kontrak Kerja**
  - Format dan isi sesuai regulasi
  - Jangka waktu yang tepat
  - Hak dan kewajiban yang jelas
  - Prosedur pemutusan hubungan kerja

- **Upah dan Tunjangan**
  - Upah minimum regional (UMR)
  - Overtime calculation
  - Tunjangan wajib (BPJS, THR)
  - Sistem penggajian yang transparan

- **Keselamatan dan Kesehatan Kerja (K3)**
  - Program K3 perusahaan
  - Pelatihan safety awareness
  - Penyediaan APD (Alat Pelindung Diri)
  - Laporan kecelakaan kerja

### 2. Regulasi Perpajakan

#### Jenis Pajak
- **Pajak Penghasilan (PPh)**
  - PPh Pasal 21: Pajak karyawan
  - PPh Pasal 23: Pajak atas jasa
  - PPh Pasal 25: Angsuran pajak bulanan
  - PPh Pasal 29: Pajak tahunan

- **Pajak Pertambahan Nilai (PPN)**
  - PPN Masukan dan Keluaran
  - Faktur pajak elektronik
  - Restitusi PPN
  - Pelaporan SPT Masa

#### Compliance Procedures
- **Pembukuan dan Pencatatan**
  - Sistem akuntansi yang memadai
  - Dokumentasi transaksi lengkap
  - Rekonsiliasi bank reguler
  - Audit trail yang jelas

- **Pelaporan Pajak**
  - SPT Masa bulanan
  - SPT Tahunan
  - Laporan keuangan audited
  - E-filing compliance

### 3. Regulasi Lingkungan

#### Environmental Compliance
- **UU No. 32 Tahun 2009**: Perlindungan dan Pengelolaan Lingkungan Hidup
- **PP No. 22 Tahun 2021**: Penyelenggaraan Perlindungan dan Pengelolaan Lingkungan Hidup

#### Requirements
- **Environmental Impact Assessment (AMDAL)**
  - Studi kelayakan lingkungan
  - Rencana pengelolaan lingkungan (RKL)
  - Rencana pemantauan lingkungan (RPL)
  - Pelaporan berkala

- **Waste Management**
  - Sistem pengelolaan limbah
  - Treatment dan disposal procedures
  - Monitoring dan reporting
  - Third-party waste management

### 4. Regulasi Data Protection

#### Personal Data Protection
- **UU No. 27 Tahun 2022**: Pelindungan Data Pribadi
- **Peraturan teknis terkait**

#### Compliance Framework
- **Data Collection**
  - Informed consent
  - Purpose limitation
  - Data minimization
  - Lawful basis

- **Data Processing**
  - Security measures
  - Access controls
  - Data retention policies
  - Cross-border transfers

- **Data Subject Rights**
  - Right to access
  - Right to rectification
  - Right to erasure
  - Right to portability

## Compliance Management System

### 1. Governance Structure

#### Compliance Committee
- **Composition**
  - Chief Compliance Officer (CCO)
  - Legal Counsel
  - HR Director
  - Finance Director
  - Operations Director

- **Responsibilities**
  - Policy development
  - Risk assessment
  - Compliance monitoring
  - Incident investigation
  - Training oversight

#### Roles dan Responsibilities
- **Board of Directors**
  - Strategic oversight
  - Policy approval
  - Resource allocation
  - Performance review

- **Management Team**
  - Implementation leadership
  - Resource provision
  - Performance monitoring
  - Corrective actions

- **Department Heads**
  - Departmental compliance
  - Staff training
  - Incident reporting
  - Process improvement

- **All Employees**
  - Policy adherence
  - Incident reporting
  - Continuous learning
  - Ethical behavior

### 2. Risk Assessment

#### Risk Identification
- **Regulatory Changes**
  - New legislation
  - Regulatory updates
  - Industry standards
  - International requirements

- **Operational Risks**
  - Process non-compliance
  - System failures
  - Human errors
  - Third-party risks

#### Risk Evaluation
- **Impact Assessment**
  - Financial impact
  - Reputational damage
  - Operational disruption
  - Legal consequences

- **Probability Assessment**
  - Historical data
  - Industry benchmarks
  - Expert judgment
  - Scenario analysis

#### Risk Treatment
- **Risk Mitigation**: Implement controls to reduce risk
- **Risk Avoidance**: Eliminate risk-causing activities
- **Risk Transfer**: Insurance and contractual arrangements
- **Risk Acceptance**: Accept residual risks

### 3. Monitoring dan Audit

#### Internal Monitoring
- **Regular Reviews**: Monthly compliance checks
- **Key Performance Indicators**: Compliance metrics
- **Exception Reporting**: Non-compliance incidents
- **Trend Analysis**: Compliance performance trends

#### External Audit
- **Regulatory Audits**: Government inspections
- **Third-party Audits**: Independent assessments
- **Certification Audits**: ISO, industry standards
- **Customer Audits**: Client compliance reviews

## Training dan Awareness

### Training Program
- **New Employee Orientation**: Basic compliance training
- **Annual Refresher**: Updated regulations and policies
- **Specialized Training**: Role-specific compliance
- **Leadership Training**: Management responsibilities

### Communication
- **Policy Updates**: Regular communication of changes
- **Compliance Bulletins**: Important regulatory updates
- **Success Stories**: Best practice sharing
- **Lessons Learned**: Incident-based learning

## Incident Management

### Reporting Procedures
- **Immediate Reporting**: Critical incidents within 24 hours
- **Investigation Process**: Root cause analysis
- **Corrective Actions**: Remediation measures
- **Follow-up**: Effectiveness verification

### Documentation
- **Incident Records**: Complete documentation
- **Investigation Reports**: Detailed analysis
- **Action Plans**: Corrective and preventive measures
- **Lessons Learned**: Knowledge sharing''',
                'tags': ['compliance', 'regulasi', 'kebijakan', 'risk'],
                'status': 'published'
            }
        ]

        # Create documents
        created_count = 0
        for doc_data in documents_data:
            try:
                # Find category
                category = next((cat for cat in categories if cat.name == doc_data['category']), None)
                if not category:
                    self.stdout.write(self.style.WARNING(f'Category not found: {doc_data["category"]}'))
                    continue

                # Create document
                document, created = KnowledgeDocument.objects.get_or_create(
                    title=doc_data['title'],
                    defaults={
                        'description': doc_data['description'],
                        'content': doc_data['content'],
                        'category': category,
                        'status': doc_data['status'],
                        'created_by': default_user,
                        'updated_by': default_user,
                        'created_at': timezone.now() - timedelta(days=random.randint(1, 90))
                    }
                )

                if created:
                    # Add tags
                    doc_tags = [tag for tag in tags if tag.name in doc_data['tags']]
                    document.tags.set(doc_tags)
                    
                    created_count += 1
                    self.stdout.write(f'Created document: {document.title}')
                else:
                    self.stdout.write(f'Document already exists: {document.title}')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating document {doc_data["title"]}: {e}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} knowledge documents with '
                f'{len(categories)} categories and {len(tags)} tags.'
            )
        )