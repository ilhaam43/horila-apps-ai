# Small Language Model (SLM) Implementation

## Overview

Sistem ini sekarang mendukung Small Language Models (SLM) sebagai alternatif dari Ollama untuk chatbot AI. Implementasi SLM menggunakan HuggingFace Transformers dan menyediakan solusi yang lebih ringan dan mudah di-deploy.

## Keunggulan SLM vs Ollama

### Small Language Models (SLM)
✅ **Keunggulan:**
- Tidak memerlukan server terpisah (Ollama)
- Lebih ringan dan cepat untuk model kecil
- Mudah di-deploy dan dikonfigurasi
- Mendukung berbagai model HuggingFace
- Dapat berjalan di CPU dengan performa yang baik
- Lebih stabil untuk production

❌ **Keterbatasan:**
- Kualitas respons mungkin tidak sebaik model besar
- Konteks yang lebih terbatas
- Kemampuan reasoning yang lebih sederhana

### Ollama
✅ **Keunggulan:**
- Model yang lebih besar dan canggih (Llama2, Mistral)
- Kualitas respons yang lebih baik
- Kemampuan reasoning yang lebih advanced

❌ **Keterbatasan:**
- Memerlukan instalasi dan konfigurasi server Ollama
- Konsumsi resource yang lebih besar
- Kompleksitas deployment yang lebih tinggi
- Memerlukan GPU untuk performa optimal

## Arsitektur SLM

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Query    │───▶│  SLM Chatbot     │───▶│   Knowledge     │
│                 │    │  Service         │    │   AI Service    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   SLM Service    │    │   Document      │
                       │   (HuggingFace)  │    │   Retrieval     │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Text Generation │    │   Vector        │
                       │  QA & Summary    │    │   Search        │
                       └──────────────────┘    └─────────────────┘
```

## Komponen Utama

### 1. SLM Service (`ai_services/slm_service.py`)
- **Text Generation**: GPT-2 untuk generasi teks
- **Question Answering**: T5-small untuk QA
- **Summarization**: T5-small untuk peringkasan
- **Indonesian Support**: Model khusus Indonesia
- **Caching**: Redis caching untuk performa

### 2. Chatbot SLM Service (`knowledge/chatbot_slm_service.py`)
- **Document Retrieval**: Multiple search strategies
- **Context Building**: Optimized untuk SLM
- **Response Generation**: Menggunakan SLM Service
- **Conversation Management**: Sama seperti Ollama version

### 3. API Views (`knowledge/views_slm.py`)
- **Chat Query**: `/api/chatbot/slm/chat/`
- **Conversations**: `/api/chatbot/slm/conversations/`
- **Service Status**: `/api/chatbot/slm/status/`
- **Document Search**: `/api/chatbot/slm/search/`

## Konfigurasi

### Environment Variables
```bash
# SLM Configuration
SLM_TEXT_MODEL=gpt2
SLM_QA_MODEL=t5-small
SLM_SUMMARY_MODEL=t5-small
SLM_INDONESIAN_MODEL=gpt2
SLM_MAX_RESPONSE_LENGTH=300
SLM_USE_INDONESIAN=True
CHATBOT_MAX_CONTEXT_LENGTH=2000
CHATBOT_SIMILARITY_THRESHOLD=0.3
```

### Django Settings
```python
# Small Language Model Settings
SLM_TEXT_MODEL = os.getenv('SLM_TEXT_MODEL', 'gpt2')
SLM_QA_MODEL = os.getenv('SLM_QA_MODEL', 't5-small')
SLM_SUMMARY_MODEL = os.getenv('SLM_SUMMARY_MODEL', 't5-small')
SLM_INDONESIAN_MODEL = os.getenv('SLM_INDONESIAN_MODEL', 'gpt2')
SLM_MAX_RESPONSE_LENGTH = int(os.getenv('SLM_MAX_RESPONSE_LENGTH', '300'))
SLM_USE_INDONESIAN = os.getenv('SLM_USE_INDONESIAN', 'True').lower() == 'true'
CHATBOT_MAX_CONTEXT_LENGTH = int(os.getenv('CHATBOT_MAX_CONTEXT_LENGTH', '2000'))
CHATBOT_SIMILARITY_THRESHOLD = float(os.getenv('CHATBOT_SIMILARITY_THRESHOLD', '0.3'))
```

## Model yang Didukung

### Text Generation Models
- `gpt2` (default) - 124M parameters
- `gpt2-medium` - 355M parameters
- `gpt2-large` - 774M parameters
- `distilgpt2` - 82M parameters (lebih cepat)

### Question Answering Models
- `t5-small` (default) - 60M parameters
- `t5-base` - 220M parameters
- `distilbert-base-cased-distilled-squad` - 66M parameters

### Indonesian Models
- `cahya/gpt2-small-indonesian-522M`
- `flax-community/gpt2-base-indonesian`
- `indolem/indobert-base-uncased`

## Strategi Pencarian Dokumen

### 1. AI Semantic Search
- Menggunakan KnowledgeAI Service
- Vector similarity search
- Highest accuracy

### 2. Keyword Search
- Traditional text matching
- Jaccard similarity
- Title boosting

### 3. Embedding Search
- SentenceTransformer embeddings
- Cosine similarity
- Semantic understanding

## API Endpoints

### Chat Query
```http
POST /api/chatbot/slm/chat/
Content-Type: application/json

{
    "query": "Bagaimana cara mengajukan cuti?",
    "conversation_id": "optional-uuid"
}
```

**Response:**
```json
{
    "success": true,
    "conversation_id": "uuid",
    "response": "Untuk mengajukan cuti...",
    "confidence_score": 0.85,
    "processing_time": 1.2,
    "model_used": "t5-small",
    "approach": "qa_with_context",
    "referenced_documents": [
        {
            "id": 1,
            "title": "Panduan Cuti Karyawan",
            "category": "HR",
            "url": "/knowledge/documents/1/"
        }
    ]
}
```

### Service Status
```http
GET /api/chatbot/slm/status/
```

**Response:**
```json
{
    "success": true,
    "service_status": {
        "slm_service_available": true,
        "embedding_model_available": true,
        "knowledge_ai_available": true,
        "slm_test_success": true,
        "configuration": {
            "max_context_length": 2000,
            "similarity_threshold": 0.3,
            "slm_config": {
                "TEXT_GENERATION_MODEL": "gpt2",
                "QA_MODEL": "t5-small",
                "MAX_RESPONSE_LENGTH": 300
            }
        }
    }
}
```

## Instalasi dan Setup

### 1. Install Dependencies
```bash
pip install transformers torch sentence-transformers
```

### 2. Download Models (Optional)
```python
from transformers import GPT2LMHeadModel, GPT2Tokenizer, T5ForConditionalGeneration, T5Tokenizer

# Download models untuk offline usage
GPT2LMHeadModel.from_pretrained('gpt2')
GPT2Tokenizer.from_pretrained('gpt2')
T5ForConditionalGeneration.from_pretrained('t5-small')
T5Tokenizer.from_pretrained('t5-small')
```

### 3. Configure Settings
Tambahkan konfigurasi SLM ke `settings.py` dan `.env`

### 4. Test Service
```bash
# Test SLM service
curl -X GET http://localhost:8000/knowledge/api/chatbot/slm/status/

# Test chat
curl -X POST http://localhost:8000/knowledge/api/chatbot/slm/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "Test query"}'
```

## Testing dan Verifikasi

### 1. Test SLM Service
```bash
python3 manage.py shell -c "from ai_services.slm_service import slm_service; result = slm_service.generate_text('Hello world', 'gpt2'); print(result)"
```

### 2. Test Chatbot SLM Service
```bash
# Jalankan script test yang sudah disediakan
python3 test_slm_integration.py
```

### 3. Test API Endpoints
```bash
# Test dengan authentication
curl -X POST http://localhost:8000/api/knowledge/api/chatbot/slm/chat/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "Apa itu artificial intelligence?", "conversation_id": "test-123"}'

# Test service status
curl -X GET http://localhost:8000/api/knowledge/api/chatbot/slm/status/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Hasil Test
✅ **SLM Service**: Berhasil memuat dan menggunakan model GPT2  
✅ **Chatbot Integration**: Berhasil mengintegrasikan dengan RAG system  
✅ **API Endpoints**: Berhasil membuat endpoint alternatif untuk Ollama  
✅ **Document Retrieval**: Berhasil mencari dokumen relevan  
✅ **Response Generation**: Berhasil menghasilkan respons menggunakan SLM

## Performance Optimization

### 1. Model Caching
- Models di-cache setelah first load
- Redis caching untuk responses
- Disk caching untuk model files

### 2. Context Optimization
- Reduced context length (2000 chars)
- Smart document chunking
- Relevance-based filtering

### 3. Response Optimization
- Shorter max response length (300 chars)
- Early stopping untuk generation
- Confidence-based fallbacks

## Monitoring dan Logging

### Metrics yang Ditrack
- Response time
- Confidence scores
- Model usage statistics
- Error rates
- Cache hit rates

### Logging
```python
import logging
logger = logging.getLogger('slm_service')

# Log levels
logger.info("SLM response generated successfully")
logger.warning("Low confidence score: 0.3")
logger.error("Model loading failed")
```

## Troubleshooting

### Common Issues

1. **Model Loading Errors**
   ```bash
   # Clear model cache
   rm -rf ~/.cache/huggingface/transformers/
   
   # Reinstall transformers
   pip uninstall transformers
   pip install transformers
   ```

2. **Memory Issues**
   ```python
   # Use smaller models
   SLM_TEXT_MODEL=distilgpt2
   SLM_QA_MODEL=distilbert-base-cased-distilled-squad
   ```

3. **Slow Performance**
   ```python
   # Enable caching
   SLM_CACHE_ENABLED=True
   
   # Reduce context length
   CHATBOT_MAX_CONTEXT_LENGTH=1000
   ```

## Migration dari Ollama ke SLM

### 1. Backup Data
```bash
# Backup conversations
python manage.py dumpdata knowledge.ChatbotConversation > conversations_backup.json
```

### 2. Update Frontend
```javascript
// Change API endpoint
const API_ENDPOINT = '/api/chatbot/slm/chat/';

// Update error handling untuk SLM responses
if (response.approach === 'fallback') {
    // Handle fallback responses
}
```

### 3. Gradual Migration
- Deploy SLM alongside Ollama
- A/B test dengan user groups
- Monitor performance metrics
- Gradually shift traffic

## Best Practices

### 1. Model Selection
- Gunakan model terkecil yang memenuhi kebutuhan
- Test berbagai model untuk use case spesifik
- Consider trade-off antara speed vs quality

### 2. Context Management
- Limit context length untuk SLM
- Prioritize most relevant documents
- Use smart chunking strategies

### 3. Fallback Strategies
- Multiple model fallbacks
- Graceful degradation
- Clear error messages

### 4. Monitoring
- Track response quality
- Monitor resource usage
- Set up alerts untuk failures

## Kesimpulan

Implementasi SLM menyediakan alternatif yang praktis dan efisien untuk chatbot AI tanpa memerlukan kompleksitas Ollama. Meskipun kualitas respons mungkin tidak secanggih model besar, SLM cocok untuk:

- **Development Environment**: Quick setup dan testing
- **Production dengan Resource Terbatas**: CPU-only deployment
- **High Availability**: Lebih stabil dan predictable
- **Cost-Effective**: Lower infrastructure costs

Pilihan antara SLM dan Ollama tergantung pada kebutuhan spesifik aplikasi, resource yang tersedia, dan trade-off yang dapat diterima antara kualitas respons dan kemudahan deployment.