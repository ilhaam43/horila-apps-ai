# Indonesian NLP Module

Modul pemrosesan bahasa alami (Natural Language Processing) khusus untuk bahasa Indonesia yang terintegrasi dengan sistem HR Horilla. Modul ini menyediakan berbagai fitur analisis teks bahasa Indonesia termasuk analisis sentimen, pengenalan entitas bernama (NER), dan klasifikasi teks.

## 🚀 Fitur Utama

### Analisis Teks
- **Analisis Sentimen**: Mendeteksi sentimen positif, negatif, atau netral dalam teks bahasa Indonesia
- **Named Entity Recognition (NER)**: Mengidentifikasi entitas seperti nama orang, tempat, organisasi, dll.
- **Klasifikasi Teks**: Mengkategorikan teks berdasarkan topik atau jenis konten
- **Pemrosesan Batch**: Memproses multiple teks secara bersamaan

### Pemrosesan Teks Indonesia
- **Pembersihan Teks**: Menghilangkan karakter tidak diinginkan dan normalisasi
- **Normalisasi Slang**: Mengubah kata-kata slang Indonesia ke bentuk baku
- **Penghilangan Stopwords**: Menghapus kata-kata umum yang tidak informatif
- **Stemming**: Mengubah kata ke bentuk dasarnya
- **Tokenisasi**: Memecah teks menjadi kata atau kalimat

### Manajemen Model
- **Multi-Framework Support**: Mendukung Transformers, spaCy, dan framework lainnya
- **Model Loading**: Pemuatan model secara dinamis dan caching
- **Performance Tracking**: Pelacakan performa dan statistik penggunaan model
- **Model Versioning**: Manajemen versi model dan konfigurasi

### Sistem Asinkron
- **Celery Integration**: Pemrosesan asinkron menggunakan Celery
- **Job Management**: Manajemen antrian dan status pekerjaan
- **Real-time Updates**: Update status real-time melalui WebSocket
- **Batch Processing**: Pemrosesan batch untuk volume besar

## 📋 Persyaratan Sistem

### Software Requirements
- Python 3.8+
- Django 4.2+
- Redis (untuk Celery dan caching)
- PostgreSQL/MySQL (database)

### Hardware Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB+ RAM, 4+ CPU cores
- **GPU**: Optional, untuk model deep learning yang lebih besar

## 🛠️ Instalasi

### 1. Clone Repository
```bash
cd /path/to/your/project
git clone <repository-url>
```

### 2. Install Dependencies
```bash
pip install -r indonesian_nlp/requirements.txt
```

### 3. Download NLTK Data
```python
import nltk
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
```

### 4. Setup Database
```bash
python manage.py makemigrations indonesian_nlp
python manage.py migrate
```

### 5. Setup Indonesian NLP Module
```bash
python manage.py setup_indonesian_nlp --download-models --test-setup
```

### 6. Start Celery Worker
```bash
celery -A your_project worker -l info
```

### 7. Start Celery Beat (untuk scheduled tasks)
```bash
celery -A your_project beat -l info
```

## ⚙️ Konfigurasi

### Django Settings
Tambahkan ke `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... apps lainnya
    'indonesian_nlp',
    'rest_framework',
    'django_celery_beat',
    'django_celery_results',
]
```

### URL Configuration
Tambahkan ke `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... URL patterns lainnya
    path('api/nlp/', include('indonesian_nlp.urls')),
]
```

### Celery Configuration
```python
# settings.py
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Jakarta'
```

### Cache Configuration
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

## 📖 Penggunaan

### 1. Quick Analysis (Analisis Cepat)
```python
from indonesian_nlp.client import IndonesianNLPClient

client = IndonesianNLPClient()

# Analisis sentimen
result = client.analyze_sentiment("Saya sangat senang dengan layanan ini!")
print(result)  # {'label': 'positive', 'confidence': 0.95}

# Ekstraksi entitas
entities = client.extract_entities("Joko Widodo adalah Presiden Indonesia.")
print(entities)  # [{'text': 'Joko Widodo', 'label': 'PERSON'}, ...]

# Klasifikasi teks
classification = client.classify_text("Artikel tentang teknologi AI terbaru.")
print(classification)  # {'label': 'technology', 'confidence': 0.88}
```

### 2. Batch Processing
```python
from indonesian_nlp.tasks import batch_process_texts

texts = [
    "Produk ini sangat bagus!",
    "Pelayanan mengecewakan.",
    "Harga terjangkau dan berkualitas."
]

# Proses secara asinkron
task = batch_process_texts.delay(texts, analysis_type='sentiment')
result = task.get()  # Tunggu hasil
```

### 3. REST API

#### Analisis Sentimen
```bash
curl -X POST http://localhost:8000/api/nlp/sentiment/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Saya sangat puas dengan produk ini!"}'
```

#### Ekstraksi Entitas
```bash
curl -X POST http://localhost:8000/api/nlp/entities/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Budi bekerja di Jakarta untuk perusahaan Google."}'
```

#### Klasifikasi Teks
```bash
curl -X POST http://localhost:8000/api/nlp/classify/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Berita tentang perkembangan ekonomi Indonesia."}'
```

### 4. Text Processing Utilities
```python
from indonesian_nlp.utils import IndonesianTextProcessor

processor = IndonesianTextProcessor()

# Pembersihan teks
clean_text = processor.clean_text("Halooo!!! Apa kabar??? 😊")
print(clean_text)  # "Halo! Apa kabar?"

# Normalisasi slang
normalized = processor.normalize_slang("gue lagi bete nih bro")
print(normalized)  # "saya sedang kesal ini bro"

# Tokenisasi
words = processor.tokenize_words("Ini adalah contoh kalimat.")
print(words)  # ['Ini', 'adalah', 'contoh', 'kalimat']

# Stemming
stemmed = processor.stem_text("bermain-main dengan teman-teman")
print(stemmed)  # "main main dengan teman teman"
```

## 🔧 Management Commands

### Setup dan Konfigurasi
```bash
# Setup awal dengan download model
python manage.py setup_indonesian_nlp --download-models --test-setup

# Setup tanpa download model
python manage.py setup_indonesian_nlp --skip-models

# Force setup (override existing)
python manage.py setup_indonesian_nlp --force
```

### Maintenance dan Monitoring
```bash
# Cek status sistem
python manage.py nlp_maintenance status --detailed

# Cleanup data lama
python manage.py nlp_maintenance cleanup --days 30

# Health check
python manage.py nlp_maintenance health --fix

# Statistik penggunaan
python manage.py nlp_maintenance stats --period week --export stats.json

# Manajemen cache
python manage.py nlp_maintenance cache --clear

# Manajemen model
python manage.py nlp_maintenance models --list --validate

# Backup konfigurasi
python manage.py nlp_maintenance config --backup config_backup.json
```

### Benchmarking dan Testing
```bash
# Performance benchmark
python manage.py nlp_benchmark performance --iterations 100 --export results.json

# Accuracy test
python manage.py nlp_benchmark accuracy --test-data test_dataset.json

# Load test
python manage.py nlp_benchmark load --concurrent 10 --duration 60

# Memory test
python manage.py nlp_benchmark memory --monitor-duration 300

# Stress test
python manage.py nlp_benchmark stress --max-concurrent 50

# Text processing test
python manage.py nlp_benchmark text-processing --sample-size 1000
```

## 📊 Monitoring dan Analytics

### Dashboard Web
Akses dashboard di: `http://localhost:8000/nlp/dashboard/`

### API Endpoints untuk Monitoring
- `GET /api/nlp/status/` - Status sistem
- `GET /api/nlp/models/` - Daftar model
- `GET /api/nlp/jobs/` - Status pekerjaan
- `GET /api/nlp/statistics/` - Statistik penggunaan

### Metrics yang Dipantau
- **Performance**: Response time, throughput, error rate
- **Resource Usage**: CPU, memory, disk usage
- **Model Performance**: Accuracy, confidence scores
- **Job Statistics**: Success rate, queue length, processing time

## 🔒 Keamanan

### Input Validation
- Validasi panjang teks maksimal
- Sanitasi input untuk mencegah injection
- Rate limiting untuk API endpoints

### Authentication & Authorization
- Django authentication integration
- Permission-based access control
- API key authentication untuk external access

### Data Privacy
- Tidak menyimpan teks sensitif secara permanen
- Enkripsi data dalam transit
- Audit logging untuk akses data

## 🚀 Performance Optimization

### Caching Strategy
- **Model Caching**: Cache model yang sudah dimuat
- **Result Caching**: Cache hasil analisis untuk teks yang sama
- **Configuration Caching**: Cache konfigurasi sistem

### Async Processing
- **Celery Workers**: Pemrosesan asinkron untuk job berat
- **Batch Processing**: Optimasi untuk multiple teks
- **Priority Queues**: Prioritas job berdasarkan urgency

### Resource Management
- **Model Unloading**: Unload model yang tidak digunakan
- **Memory Monitoring**: Monitoring penggunaan memory
- **CPU Throttling**: Pembatasan penggunaan CPU

## 🧪 Testing

### Unit Tests
```bash
# Jalankan semua test
python manage.py test indonesian_nlp

# Test specific module
python manage.py test indonesian_nlp.tests.TestIndonesianNLPClient

# Test dengan coverage
coverage run --source='.' manage.py test indonesian_nlp
coverage report
```

### Integration Tests
```bash
# Test API endpoints
python manage.py test indonesian_nlp.tests.TestNLPAPIViews

# Test Celery tasks
python manage.py test indonesian_nlp.tests.TestCeleryTasks
```

### Load Testing
```bash
# Menggunakan built-in benchmark
python manage.py nlp_benchmark load --concurrent 20 --duration 120

# Menggunakan external tools
locust -f load_test.py --host=http://localhost:8000
```

## 📁 Struktur Direktori

```
indonesian_nlp/
├── __init__.py
├── admin.py                 # Django admin configuration
├── apps.py                  # App configuration
├── client.py               # Main NLP client
├── forms.py                # Django forms
├── jobs.py                 # Job management
├── models.py               # Database models
├── serializers.py          # DRF serializers
├── signals.py              # Django signals
├── tasks.py                # Celery tasks
├── tests.py                # Unit tests
├── urls.py                 # URL routing
├── utils.py                # Utility functions
├── views.py                # Django views
├── requirements.txt        # Python dependencies
├── README.md              # Documentation
├── management/
│   └── commands/
│       ├── __init__.py
│       ├── setup_indonesian_nlp.py
│       ├── nlp_maintenance.py
│       └── nlp_benchmark.py
├── templates/
│   └── indonesian_nlp/
│       ├── dashboard.html
│       ├── model_list.html
│       └── job_list.html
└── static/
    └── indonesian_nlp/
        ├── css/
        ├── js/
        └── img/
```

## 🔧 Troubleshooting

### Common Issues

#### Model Loading Errors
```bash
# Check model files
python manage.py nlp_maintenance models --validate

# Reload models
python manage.py setup_indonesian_nlp --force
```

#### Memory Issues
```bash
# Check memory usage
python manage.py nlp_benchmark memory

# Clear cache
python manage.py nlp_maintenance cache --clear

# Restart Celery workers
kill -HUP <celery_pid>
```

#### Performance Issues
```bash
# Run performance benchmark
python manage.py nlp_benchmark performance

# Check system status
python manage.py nlp_maintenance status --detailed

# Optimize models
python manage.py nlp_maintenance models --optimize
```

### Logging
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'indonesian_nlp.log',
        },
    },
    'loggers': {
        'indonesian_nlp': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd indonesian_nlp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install
```

### Code Style
```bash
# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run tests
pytest
```

### Pull Request Process
1. Fork repository
2. Create feature branch
3. Make changes dengan tests
4. Ensure code quality checks pass
5. Submit pull request

## 📄 License

MIT License - lihat file LICENSE untuk detail lengkap.

## 🆘 Support

### Documentation
- [API Documentation](docs/api.md)
- [Model Documentation](docs/models.md)
- [Deployment Guide](docs/deployment.md)

### Community
- GitHub Issues: Report bugs dan feature requests
- Discussions: Diskusi dan Q&A
- Wiki: Additional documentation

### Commercial Support
Untuk enterprise support dan custom development, hubungi tim development.

## 🗺️ Roadmap

### Version 1.1 (Q2 2024)
- [ ] Support untuk model BERT Indonesia yang lebih baru
- [ ] Integrasi dengan Elasticsearch untuk full-text search
- [ ] Dashboard analytics yang lebih advanced
- [ ] Support untuk multiple languages

### Version 1.2 (Q3 2024)
- [ ] Real-time streaming analysis
- [ ] Model fine-tuning capabilities
- [ ] Advanced caching strategies
- [ ] Kubernetes deployment support

### Version 2.0 (Q4 2024)
- [ ] Complete rewrite dengan FastAPI
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] Advanced ML pipeline management

## 📈 Changelog

### Version 1.0.0 (Current)
- ✅ Initial release
- ✅ Basic sentiment analysis
- ✅ Named entity recognition
- ✅ Text classification
- ✅ Batch processing
- ✅ REST API
- ✅ Django admin integration
- ✅ Celery task management
- ✅ Comprehensive testing
- ✅ Management commands
- ✅ Performance monitoring

---

**Indonesian NLP Module** - Powerful Indonesian language processing for Django applications.

Developed with ❤️ for the Indonesian developer community.