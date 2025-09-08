# Horilla HR System - Enterprise Edition

🚀 **Sistem Manajemen SDM Terpadu dengan AI dan Automasi Canggih**

Horilla adalah sistem Human Resource Management System (HRMS) yang komprehensif dan modern, dirancang khusus untuk organisasi Indonesia dengan dukungan AI lokal, automasi workflow, dan monitoring real-time untuk mencapai SLA 99.99%.

## 🌟 Fitur Unggulan

### 🎯 Modul HR Inti
- **Employee Management**: Manajemen lengkap siklus hidup karyawan
- **Attendance Tracking**: Pelacakan kehadiran dengan biometric dan geofencing
- **Leave Management**: Sistem cuti dengan approval workflow otomatis
- **Payroll Processing**: Perhitungan gaji otomatis sesuai regulasi Indonesia
- **Performance Management**: Evaluasi kinerja dengan AI insights
- **Recruitment**: Rekrutmen end-to-end dengan AI screening

### 🤖 Fitur AI & Automasi Terbaru
- **Budget Control System**: Kontrol anggaran real-time dengan prediksi AI dan filter lanjutan
- **Knowledge Management**: Sistem pengetahuan dengan AI Assistant
- **Indonesian NLP**: Pemrosesan bahasa Indonesia untuk sentiment analysis
- **RAG + N8N Integration**: Automasi workflow recruitment dengan AI
- **AI Document Classification**: Klasifikasi dokumen otomatis
- **Intelligent Search**: Pencarian cerdas dengan semantic understanding

### 💰 Budget Management (v1.1 - Enhanced)
- **Advanced Filtering**: Filter multi-kriteria dengan tata letak responsif
- **Real-time Dashboard**: Monitoring anggaran dengan visualisasi interaktif
- **Currency Management**: Pengaturan mata uang terpusat (IDR/USD/dll)
- **Custom Branding**: Logo dan branding perusahaan yang dapat disesuaikan
- **Expense Tracking**: Pelacakan pengeluaran dengan kategorisasi otomatis
- **Budget Planning**: Perencanaan anggaran dengan approval workflow

### 🔧 Teknologi & Infrastruktur
- **Local AI Processing**: Ollama integration untuk edge computing
- **Real-time Monitoring**: Sistem monitoring untuk SLA 99.99%
- **Scalable Architecture**: Arsitektur microservices yang dapat diskalakan
- **Security First**: Keamanan berlapis dengan audit trail
- **Responsive UI**: Interface modern dan responsif
- **Multi-language**: Dukungan Bahasa Indonesia dan Inggris

## 🚀 Quick Start (5 Menit Setup)

### Metode 1: Setup Otomatis (Recommended)
```bash
# Clone atau masuk ke direktori aplikasi
cd /path/to/horilla-app

# Jalankan setup script otomatis
./setup.sh

# Ikuti instruksi di layar
```

### Metode 2: Setup Manual
```bash
# 1. Setup environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup database
python manage.py migrate
python manage.py createsuperuser

# 4. Jalankan aplikasi
python manage.py runserver
```

### 🎯 Akses Aplikasi
| Fitur | URL | Deskripsi |
|-------|-----|----------|
| **Dashboard** | http://127.0.0.1:8000/ | Halaman utama |
| **Admin Panel** | http://127.0.0.1:8000/admin/ | Panel administrasi |
| **Budget Control** | http://127.0.0.1:8000/budget/ | Kontrol anggaran dengan filter lanjutan |
| **Currency Settings** | http://127.0.0.1:8000/payroll/settings | Pengaturan mata uang (IDR/USD) |
| **Knowledge Base** | http://127.0.0.1:8000/knowledge/ | Manajemen pengetahuan |
| **Health Check** | http://127.0.0.1:8000/health/ | Status sistem |
| **Metrics** | http://127.0.0.1:8000/metrics/ | Monitoring metrics |

## 📚 Dokumentasi Lengkap

### 📖 Panduan Pengguna
- **[Panduan Instalasi Lengkap](PANDUAN_INSTALASI.md)** - Instalasi detail step-by-step
- **[Quick Start Guide](QUICK_START.md)** - Setup cepat 5 menit
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Panduan deployment production

### 🏗️ Dokumentasi Teknis
- **[System Architecture](SYSTEM_ARCHITECTURE.md)** - Arsitektur sistem lengkap
- **[API Documentation](monitoring/API_DOCUMENTATION.md)** - Dokumentasi API endpoints
- **[Monitoring Guide](monitoring/README.md)** - Panduan sistem monitoring

### 💰 Dokumentasi Modul Spesifik
- **[Budget Module Documentation](BUDGET_MODULE_DOCUMENTATION.md)** - Panduan lengkap modul budget v1.1
- **[Database Documentation](DATABASE_DOCUMENTATION_README.md)** - Skema database dan relasi
- **[Documentation Index](DOCUMENTATION_INDEX.md)** - Indeks semua dokumentasi

## 🏗️ Arsitektur Sistem

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Layer     │    │  Application    │    │   Data Layer    │
│                 │    │     Layer       │    │                 │
│ • Django Views  │◄──►│ • Business      │◄──►│ • PostgreSQL    │
│ • REST API      │    │   Logic         │    │ • Redis Cache   │
│ • WebSocket     │    │ • AI Services   │    │ • File Storage  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Monitoring      │    │   AI & ML       │    │   External      │
│                 │    │                 │    │   Services      │
│ • Prometheus    │    │ • Ollama        │    │ • N8N Workflow  │
│ • Health Checks │    │ • ChromaDB      │    │ • Email Service │
│ • Metrics       │    │ • Transformers  │    │ • Cloud Storage │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Konfigurasi & Persyaratan

### Persyaratan Sistem
- **Python**: 3.8+ (Recommended: 3.11)
- **Database**: PostgreSQL 12+ / MySQL 8+ / SQLite (dev)
- **Cache**: Redis 6+
- **AI Engine**: Ollama dengan model llama2/mistral
- **OS**: macOS, Linux, Windows

### Environment Variables Penting
```env
# Core Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com

# Database
DATABASE_URL=postgresql://user:pass@localhost/horilla

# AI Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Monitoring
PROMETHEUS_ENABLED=True
METRICS_ENABLED=True
```

## 🧪 Testing & Quality Assurance

```bash
# Jalankan semua tes
python manage.py test

# Tes modul spesifik
python manage.py test monitoring
python manage.py test budget
python manage.py test knowledge

# Tes keamanan
python manage.py test monitoring.tests.MonitoringSecurityTests

# Health check
curl http://127.0.0.1:8000/health/
```

### Status Testing
- ✅ **Core System**: 100% pass
- ✅ **Security Tests**: 100% pass
- ✅ **API Endpoints**: 100% functional
- ✅ **AI Integration**: Fully operational
- ✅ **Monitoring**: Real-time metrics active

## 🚀 Deployment Production

### Docker Deployment
```bash
# Build dan jalankan dengan Docker
docker-compose up -d

# Atau dengan Kubernetes
kubectl apply -f k8s/
```

### Manual Deployment
```bash
# Setup production server
gunicorn horilla.wsgi:application --bind 0.0.0.0:8000

# Background services
celery -A horilla worker --loglevel=info
celery -A horilla beat --loglevel=info
```

## 📊 Monitoring & Analytics

### Real-time Monitoring
- **Health Checks**: `/health/`, `/health/ready/`, `/health/live/`
- **Metrics**: `/metrics/` (Prometheus format)
- **Performance**: Response time, throughput, error rates
- **Security**: Failed login attempts, API rate limiting

### SLA Targets
- **Uptime**: 99.99% (< 4.32 minutes downtime/month)
- **Response Time**: < 200ms (95th percentile)
- **Error Rate**: < 0.1%
- **Recovery Time**: < 30 seconds

## 🤝 Contributing & Development

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd horilla

# Setup development environment
./setup.sh

# Activate development mode
export DJANGO_DEBUG=True
python manage.py runserver
```

### Code Quality
- **Code Style**: PEP 8 compliant
- **Testing**: 90%+ coverage required
- **Security**: OWASP guidelines followed
- **Documentation**: Comprehensive inline docs

## 🔒 Security Features

- **Authentication**: Multi-factor authentication support
- **Authorization**: Role-based access control (RBAC)
- **API Security**: Rate limiting, JWT tokens
- **Data Protection**: Encryption at rest and in transit
- **Audit Trail**: Complete activity logging
- **Compliance**: GDPR, SOX compliance ready

## 🌍 Internationalization

- **Bahasa Indonesia**: Full localization
- **English**: Complete translation
- **Currency**: IDR, USD support
- **Date/Time**: Local timezone support
- **Number Format**: Indonesian formatting

## 📄 License & Support

- **License**: MIT License
- **Commercial Support**: Available
- **Community**: GitHub Discussions
- **Documentation**: Comprehensive guides
- **Updates**: Regular security and feature updates

## 🙏 Acknowledgments

- **Django Community**: Excellent framework foundation
- **AI/ML Libraries**: Transformers, LangChain, ChromaDB
- **Indonesian NLP**: Sastrawi, local language models
- **Monitoring**: Prometheus, Grafana ecosystem
- **Contributors**: All developers who made this possible

---

**Horilla HR System** - Revolutionizing HR management with AI-powered automation and Indonesian-first approach.

🚀 **Ready for Enterprise** | 🤖 **AI-Powered** | 🇮🇩 **Made for Indonesia**

---

## **Installation (Legacy Documentation)**

Horilla can be installed on your system by following the steps below. Ensure you have **Python**, **Django**, and a **database** (preferably PostgreSQL) installed as prerequisites.

---

## **Prerequisites**

### **1. Python Installation**

#### **Ubuntu**
1. Open the terminal and install Python:
   ```bash
   sudo apt-get install python3
   ```
2. Verify the installation:
   ```bash
   python3 --version
   ```

#### **Windows**
1. Download Python from the [official website](https://www.python.org/downloads/windows/).
2. During installation, ensure you select **"Add Python to PATH"**.
3. Verify the installation:
   ```bash
   python3 --version
   ```

#### **macOS**
1. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python:
   ```bash
   brew install python
   ```
3. Verify the installation:
   ```bash
   python3 --version
   ```

---


### **2. PostgreSQL Installation**

#### **Ubuntu**
1. **Update System Packages**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install PostgreSQL**:
   ```bash
   sudo apt install postgresql postgresql-contrib -y
   ```

3. **Start and Enable PostgreSQL**:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

4. **Verify Installation**:
   ```bash
   psql --version
   ```

5. **Configure PostgreSQL Database and User**:
   - Switch to the `postgres` user:
     ```bash
     sudo su postgres
     psql
     ```
   - Create a new role and database:
     ```sql
     CREATE ROLE horilla LOGIN PASSWORD 'horilla';
     CREATE DATABASE horilla_main OWNER horilla;
     \q
     ```
   - Exit the `postgres` user:
     ```bash
     exit
     ```

---

#### **Windows**
1. **Download PostgreSQL**:
   - Download the installer from the [PostgreSQL Official Site](https://www.postgresql.org/download/windows/).

2. **Install PostgreSQL**:
   - Follow the setup wizard and set a password for the PostgreSQL superuser.

3. **Verify Installation**:
   ```powershell
   psql -U postgres
   ```

4. **Configure PostgreSQL Database and User**:
   - Access PostgreSQL:
     ```powershell
     psql -U postgres
     ```
   - Create a new role and database:
     ```sql
     CREATE ROLE horilla LOGIN PASSWORD 'horilla';
     CREATE DATABASE horilla_main OWNER horilla;
     \q
     ```

---

#### **macOS**
1. **Install PostgreSQL via Homebrew**:
   ```bash
   brew install postgresql
   ```

2. **Start PostgreSQL**:
   ```bash
   brew services start postgresql
   ```

3. **Verify Installation**:
   ```bash
   psql --version
   ```

4. **Configure PostgreSQL Database and User**:
   - Create a database and user:
     ```bash
     createdb horilla_main
     createuser horilla
     psql -c "ALTER USER horilla WITH PASSWORD 'horilla';"
     ```

---

## **Install Horilla**

Follow the steps below to install **Horilla** on your system. Horilla is compatible with **Ubuntu**, **Windows**, and **macOS**.

---

### **1. Clone the Repository**

#### **Ubuntu**
```bash
sudo git init
sudo git remote add horilla https://horilla-opensource@github.com/horilla-opensource/horilla.git
sudo git pull horilla master
```

#### **Windows**
```powershell
git init
git remote add horilla https://horilla-opensource@github.com/horilla-opensource/horilla.git
git pull horilla master
```

#### **macOS**
```bash
git init
git remote add horilla https://horilla-opensource@github.com/horilla-opensource/horilla.git
git pull horilla master
```

### **2. Set Up Python Virtual Environment**

#### **Ubuntu**
1. Install `python3-venv`:
   ```bash
   sudo apt-get install python3-venv
   ```
2. Create and activate the virtual environment:
   ```bash
   python3 -m venv horillavenv
   source horillavenv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### **Windows**
1. Create and activate the virtual environment:
   ```powershell
   python -m venv horillavenv
   .\horillavenv\Scripts\activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

#### **macOS**
1. Create and activate the virtual environment:
   ```bash
   python3 -m venv horillavenv
   source horillavenv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```


### **3. Configure Environment Variables**

1. Rename the environment file:
   ```bash
   mv .env.dist .env
   ```

2. Edit the `.env` file and set the following values:
   ```env
   DEBUG=True
   TIME_ZONE=Asia/Kolkata
   SECRET_KEY=django-insecure-j8op9)1q8$1&@^s&p*_0%d#pr@w9qj@lo=3#@d=a(^@9@zd@%j
   ALLOWED_HOSTS=www.example.com,example.com,*
   DB_INIT_PASSWORD=d3f6a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=horilla_main
   DB_USER=horilla
   DB_PASSWORD=horilla
   DB_HOST=localhost
   DB_PORT=5432
   ```

---

### **4. Run Django Migrations**

Follow these steps to run migrations and set up the database.

#### **Ubuntu/macOS**
1. Apply migrations:
   ```bash
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```

#### **Windows**
1. Apply migrations:
   ```powershell
   python manage.py makemigrations
   python manage.py migrate
   ```
---

### **5. Enable Translation**

To enable translations and breadcrumbs text, compile the translations using the following commands.

#### **Ubuntu/macOS**
```bash
python3 manage.py compilemessages
```

#### **Windows**
```powershell
python manage.py compilemessages
```

---

### **6. Run the Project**

To run the project locally, execute the following commands.

#### **Ubuntu/macOS**
```bash
python3 manage.py runserver
```

#### **Windows**
```powershell
python manage.py runserver
```

---

### **Accessing Horilla**

If everything is configured correctly, you should be able to access your Horilla app at **http://localhost:8000**.
![Initialize Database in Horilla HRMS](https://www.horilla.com/wp-content/uploads/2024/12/how-to-initialize-the-database-in-horilla-hrms-step-by-step-1-1024x576.png)


#### **Initial Setup**
From the login page, you will have two options:
1. **Initialize Database**: Use this option to initialize the Horilla database by creating a super admin, headquarter company, department, and job position. Authenticate using the `DB_INIT_PASSWORD` specified in the `.env` file.
2. **Load Demo Data**: Use this option if you want to work with demo data. Authenticate using the `DB_INIT_PASSWORD` specified in the `.env` file.

#### **Running on a Custom Port**
If you wish to run the Horilla application on a different port, specify the port number after the `runserver` command. For example:
```bash
python3 manage.py runserver 8080  # For Ubuntu/macOS
python manage.py runserver 8080   # For Windows
```


## **Features**

- **Recruitment**
- **Onboarding**
- **Employee Management**
- **Attendance Tracking**
- **Leave Management**
- **Asset Management**
- **Payroll**
- **Performance Management System**
- **Offboarding**
- **Helpdesk**

---

## **Roadmap**

- **Calendar App** - Development Under Process
- **Project Management** - Development Under Process
- **Chat App** - Development Under Process
- **More to come...**

---

## **Languages and Tools Used**

<p align="left">
  <a href="https://getbootstrap.com" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/bootstrap/bootstrap-plain-wordmark.svg" alt="bootstrap" width="40" height="40"/>
  </a>
  <a href="https://www.chartjs.org" target="_blank" rel="noreferrer">
    <img src="https://www.chartjs.org/media/logo-title.svg" alt="chartjs" width="40" height="40"/>
  </a>
  <a href="https://www.w3schools.com/css/" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/css3/css3-original-wordmark.svg" alt="css3" width="40" height="40"/>
  </a>
  <a href="https://www.djangoproject.com/" target="_blank" rel="noreferrer">
    <img src="https://cdn.worldvectorlogo.com/logos/django.svg" alt="django" width="40" height="40"/>
  </a>
  <a href="https://git-scm.com/" target="_blank" rel="noreferrer">
    <img src="https://www.vectorlogo.zone/logos/git-scm/git-scm-icon.svg" alt="git" width="40" height="40"/>
  </a>
  <a href="https://www.w3.org/html/" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/html5/html5-original-wordmark.svg" alt="html5" width="40" height="40"/>
  </a>
  <a href="https://www.linux.org/" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/linux/linux-original.svg" alt="linux" width="40" height="40"/>
  </a>
  <a href="https://www.postgresql.org" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/postgresql/postgresql-original-wordmark.svg" alt="postgresql" width="40" height="40"/>
  </a>
  <a href="https://www.python.org" target="_blank" rel="noreferrer">
    <img src="https://raw.githubusercontent.com/devicons/devicon/master/icons/python/python-original.svg" alt="python" width="40" height="40"/>
  </a>
</p>

---

## **Authors**

[Cybrosys Technologies](https://www.cybrosys.com/)

---

## **About**

[Horilla](https://www.horilla.com/) is an open-source HRMS solution designed to simplify HR operations and improve organizational efficiency.

---

This README provides a comprehensive guide to installing and setting up Horilla on various platforms. If you encounter any issues, feel free to reach out to the Horilla community for support. Happy coding! 🚀
