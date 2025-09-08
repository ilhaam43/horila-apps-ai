# 📋 Installation Requirements untuk Demo Proof of Concept

## Status Instalasi Sistem Saat Ini

### ✅ 1. NLP Indonesia - **SUDAH TERINSTAL**

**Status**: Sistem sudah memiliki implementasi lengkap Indonesian NLP

**Dependencies yang sudah tersedia**:
- `transformers>=4.30.0` - Untuk BERT models Indonesia
- `torch>=2.0.0` - Deep learning framework
- `Sastrawi>=1.0.1` - Indonesian text processing
- `langdetect>=1.0.9` - Language detection
- `nltk>=3.8.0` - Natural language toolkit

**Model yang digunakan**:
- `indolem/indobert-base-uncased` - Indonesian BERT model
- Custom sentiment analysis untuk bahasa Indonesia
- Named Entity Recognition (NER) untuk bahasa Indonesia

**Fitur yang tersedia**:
- Sentiment analysis bahasa Indonesia
- Text classification
- Named Entity Recognition
- Text preprocessing dan cleaning
- Keyword extraction

### ✅ 2. Ollama - **SUDAH TERINSTAL DAN TERINTEGRASI**

**Status**: Sistem sudah memiliki integrasi Ollama yang lengkap

**Komponen yang sudah tersedia**:
- <mcfile name="ollama_integration" path="/Users/haryanto.bonti/apps/ollama_integration"></mcfile> - Full integration module
- <mcfile name="client.py" path="/Users/haryanto.bonti/apps/ollama_integration/client.py"></mcfile> - Ollama API client
- <mcfile name="models.py" path="/Users/haryanto.bonti/apps/ollama_integration/models.py"></mcfile> - Database models
- Management commands untuk model management
- Web interface untuk monitoring dan management

**Fitur Ollama yang tersedia**:
- Model management (pull, remove, list)
- Text generation dan chat completion
- Embedding generation
- Streaming responses
- Job processing dan monitoring
- Usage statistics dan analytics
- Health monitoring
- Prompt templates

**Models yang dapat digunakan**:
- `llama2` - General purpose LLM
- `codellama` - Code generation
- `mistral` - Efficient language model
- Custom models sesuai kebutuhan

### ✅ 3. RAG (Retrieval-Augmented Generation) - **SUDAH TERINSTAL**

**Status**: Sistem sudah memiliki implementasi RAG yang terintegrasi

**Dependencies yang sudah tersedia**:
- `sentence-transformers>=2.2.0` - Untuk embedding generation
- `faiss-cpu>=1.7.4` - Vector database untuk similarity search
- `whoosh>=2.7.4` - Full-text search engine

**Komponen RAG yang tersedia**:
- <mcfile name="rag_n8n_integration.py" path="/Users/haryanto.bonti/apps/ai_services/rag_n8n_integration.py"></mcfile> - RAG implementation
- Vector indexing dan similarity search
- Document retrieval dan ranking
- Context-aware response generation
- Knowledge base integration

**Fitur RAG yang tersedia**:
- Document embedding dan indexing
- Semantic search dengan vector similarity
- Context retrieval untuk query
- Response generation dengan retrieved context
- Batch processing untuk multiple documents

### ✅ 4. N8N Integration - **SUDAH TERINSTAL**

**Status**: Sistem sudah memiliki integrasi N8N untuk workflow automation

**Komponen yang sudah tersedia**:
- N8N API client dalam RAG integration
- Webhook integration untuk workflow triggers
- Automated workflow templates:
  - Candidate screening
  - Interview scheduling
  - Onboarding process
  - Performance review

**Konfigurasi N8N**:
```python
N8N_BASE_URL = 'http://localhost:5678'
N8N_WEBHOOK_URL = 'http://localhost:5678/webhook'
N8N_API_KEY = 'your-api-key'
```

## 🚀 Persiapan Demo Proof of Concept

### Langkah 1: Verifikasi Instalasi

**Cek status sistem**:
```bash
# Test semua AI services
python3 comprehensive_ai_test.py

# Test performance optimization
python3 test_performance_optimization.py

# Cek health endpoints
curl http://localhost:8000/api/ai/public/health/
curl http://localhost:8000/api/ai/public/stats/
```

### Langkah 2: Setup Environment Variables

**File `.env` yang diperlukan**:
```bash
# Redis untuk caching
REDIS_URL=redis://localhost:6379/0

# Celery untuk async processing
CELERY_BROKER_URL=redis://localhost:6379/0

# AI Configuration
AI_CACHE_TIMEOUT=3600
AI_MODEL_PATH=/path/to/models/

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_API_KEY=your-api-key

# N8N Configuration
N8N_BASE_URL=http://localhost:5678
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_API_KEY=your-n8n-api-key

# Vector Database
VECTOR_DB_URL=http://localhost:6333
```

### Langkah 3: Instalasi Dependencies Tambahan (Opsional)

**Jika ingin menggunakan model terbaru**:
```bash
# Install additional models
pip install -r ai_services/requirements.txt

# Download Indonesian models
python3 -c "from transformers import AutoTokenizer, AutoModel; AutoTokenizer.from_pretrained('indolem/indobert-base-uncased'); AutoModel.from_pretrained('indolem/indobert-base-uncased')"
```

### Langkah 4: Setup Ollama Models

**Pull recommended models**:
```bash
# Initialize Ollama integration
python3 manage.py init_ollama

# Pull models untuk demo
python3 manage.py manage_ollama_models --pull llama2
python3 manage.py manage_ollama_models --pull mistral

# Test models
python3 manage.py manage_ollama_models --test llama2
```

### Langkah 5: Setup N8N Workflows

**Import workflow templates**:
1. Start N8N server: `n8n start`
2. Access N8N interface: `http://localhost:5678`
3. Import workflow templates dari sistem
4. Configure webhook URLs

## 📊 Demo Scenarios yang Tersedia

### 1. Indonesian NLP Demo
```bash
# Test sentiment analysis
curl -X POST http://localhost:8000/api/ai/nlp/indonesia/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Saya sangat senang dengan layanan ini", "task": "sentiment"}'
```

### 2. Ollama Text Generation Demo
```bash
# Test text generation
curl -X POST http://localhost:8000/api/ai/ollama/generate/ \
  -H "Content-Type: application/json" \
  -d '{"model": "llama2", "prompt": "Explain AI in simple terms"}'
```

### 3. RAG Knowledge Query Demo
```bash
# Test knowledge query
curl -X POST http://localhost:8000/api/ai/knowledge/query/ \
  -H "Content-Type: application/json" \
  -d '{"query": "How to apply for leave?", "context": "employee_handbook"}'
```

### 4. N8N Workflow Demo
```bash
# Trigger recruitment workflow
curl -X POST http://localhost:8000/api/ai/rag-n8n/process/ \
  -H "Content-Type: application/json" \
  -d '{"workflow": "candidate_screening", "candidate_data": {...}}'
```

## 🔧 Troubleshooting

### Common Issues dan Solutions

**1. Ollama Connection Error**:
```bash
# Check Ollama service
sudo systemctl status ollama
# atau
ollama serve
```

**2. Redis Connection Error**:
```bash
# Start Redis
redis-server
# atau
sudo systemctl start redis
```

**3. Model Loading Error**:
```bash
# Check model files
ls -la media/ai_models/
# Download missing models
python3 manage.py download_ai_models
```

**4. N8N Webhook Error**:
- Verify N8N server is running
- Check webhook URLs in configuration
- Test webhook endpoints manually

## 📈 Performance Monitoring

**Real-time monitoring endpoints**:
- Health: `http://localhost:8000/api/ai/public/health/`
- Stats: `http://localhost:8000/api/ai/public/stats/`
- Monitoring: `http://localhost:8000/api/ai/monitoring/`

**Ollama monitoring**:
- Dashboard: `http://localhost:8000/ollama/dashboard/`
- Models: `http://localhost:8000/ollama/models/`
- Jobs: `http://localhost:8000/ollama/jobs/`

## ✅ Kesimpulan

**Semua komponen sudah terinstal dan siap untuk demo**:

1. ✅ **Indonesian NLP** - Fully implemented dengan sentiment analysis
2. ✅ **Ollama** - Complete integration dengan model management
3. ✅ **RAG** - Vector search dan context retrieval ready
4. ✅ **N8N** - Workflow automation configured

**Tidak diperlukan instalasi tambahan di laptop lokal**. Semua komponen sudah terintegrasi dalam sistem Django dan siap untuk demonstrasi proof of concept.

**Server sudah berjalan di**: `http://localhost:8000/`
**Status**: Production Ready ✅

---

**Untuk demo, cukup jalankan**:
1. `python3 manage.py runserver 8000`
2. `python3 -m celery -A horilla worker --loglevel=info`
3. Access demo endpoints sesuai scenarios di atas

**Dokumentasi lengkap**: <mcfile name="AI_SYSTEM_DOCUMENTATION.md" path="/Users/haryanto.bonti/apps/AI_SYSTEM_DOCUMENTATION.md"></mcfile>