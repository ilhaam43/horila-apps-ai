# RAG & N8N Integration Documentation

## Overview

This document provides comprehensive documentation for the Retrieval-Augmented Generation (RAG) system and N8N workflow automation integration in the Horilla recruitment module.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django API    │    │   RAG Service   │    │  Vector Database│
│                 │────│                 │────│   (ChromaDB)    │
│  - REST APIs    │    │ - Resume Analysis│    │                 │
│  - ViewSets     │    │ - Similarity    │    │ - Embeddings    │
│  - Serializers  │    │ - Recommendations│    │ - Search        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Celery Tasks   │    │   Ollama LLM    │    │      N8N        │
│                 │    │                 │    │                 │
│ - Async Process │    │ - Local AI      │    │ - Workflows     │
│ - Batch Jobs    │    │ - Text Analysis │    │ - Automation    │
│ - Scheduling    │    │ - Embeddings    │    │ - Notifications │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Components

### 1. RAG Service (`services.py`)

The core service that handles:
- Resume text extraction and analysis
- Similarity scoring between candidates and job descriptions
- AI-powered candidate recommendations
- Vector database operations

#### Key Methods:

```python
# Analyze candidate resume
result = await rag_service.analyze_resume(
    candidate_id=123,
    job_description="Software engineer position..."
)

# Find similar candidates
similar = rag_service.find_similar_candidates(
    job_description="Looking for Python developer",
    limit=10
)

# Trigger recruitment workflow
workflow_result = await rag_service.trigger_recruitment_workflow(
    candidate_id=123,
    workflow_type="resume_screening"
)
```

### 2. N8N Integration

#### Workflow Types:

1. **Resume Screening** (`resume_screening`)
   - Automated initial candidate evaluation
   - AI-powered skill matching
   - Automatic stage progression

2. **Interview Scheduling** (`interview_scheduling`)
   - Calendar integration
   - Automated email notifications
   - Reminder systems

3. **Candidate Notification** (`candidate_notification`)
   - Status update emails
   - SMS notifications
   - Custom messaging

4. **Hiring Decision** (`hiring_decision`)
   - Final evaluation workflow
   - Approval processes
   - Contract generation

5. **Onboarding Trigger** (`onboarding_trigger`)
   - New hire setup
   - Document collection
   - System access provisioning

#### Workflow Configuration (`n8n_workflows.json`):

```json
{
  "workflows": {
    "resume_screening": {
      "id": "resume-screening-workflow",
      "name": "Resume Screening Automation",
      "description": "Automated resume analysis and initial screening",
      "trigger": {
        "type": "webhook",
        "method": "POST",
        "path": "/webhook/resume-screening"
      },
      "actions": [
        {
          "type": "ai_analysis",
          "model": "ollama",
          "prompt": "Analyze this resume for technical skills..."
        },
        {
          "type": "email_notification",
          "template": "resume_received"
        },
        {
          "type": "stage_update",
          "condition": "score > 0.7"
        }
      ]
    }
  }
}
```

### 3. API Endpoints

#### RAG Endpoints:

```bash
# Analyze resume (async)
POST /api/recruitment/rag/analyze-resume/
{
  "candidate_id": 123,
  "job_description": "Software engineer position...",
  "async": true
}

# Find similar candidates
POST /api/recruitment/rag/find-similar-candidates/
{
  "job_description": "Looking for Python developer",
  "limit": 10,
  "similarity_threshold": 0.7
}

# Check analysis status
GET /api/recruitment/rag/analysis-status/{candidate_id}/

# Batch analyze candidates
POST /api/recruitment/rag/batch-analyze/
{
  "recruitment_id": 456,
  "job_description": "Software engineer position...",
  "async": true
}
```

#### Workflow Endpoints:

```bash
# Trigger workflow
POST /api/recruitment/workflow/trigger/
{
  "candidate_id": 123,
  "workflow_type": "resume_screening",
  "async": true,
  "data": {
    "priority": "high",
    "department": "engineering"
  }
}

# Check workflow status
GET /api/recruitment/workflow/status/{execution_id}/

# Service health check
GET /api/recruitment/workflow/service-health/
```

### 4. Celery Tasks

#### Available Tasks:

```python
# Process candidate analysis
from recruitment.tasks import process_candidate_analysis
task = process_candidate_analysis.delay(candidate_id=123)

# Trigger workflow
from recruitment.tasks import trigger_recruitment_workflow_task
task = trigger_recruitment_workflow_task.delay(
    candidate_id=123,
    workflow_type="resume_screening"
)

# Batch analyze candidates
from recruitment.tasks import batch_analyze_candidates
task = batch_analyze_candidates.delay(
    recruitment_id=456,
    job_description="Software engineer..."
)

# Sync to vector database
from recruitment.tasks import sync_candidate_to_vector_db
task = sync_candidate_to_vector_db.delay(candidate_id=123)

# Generate insights
from recruitment.tasks import generate_recruitment_insights
task = generate_recruitment_insights.delay(recruitment_id=456)
```

## Configuration

### Environment Variables (`.env`):

```bash
# RAG Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
SIMILARITY_THRESHOLD=0.7

# Vector Database
VECTOR_DB_PROVIDER=chromadb
CHROMADB_HOST=localhost
CHROMADB_PORT=8000
CHROMADB_PERSIST_DIRECTORY=./data/chromadb

# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# N8N Configuration
N8N_BASE_URL=http://localhost:5678
N8N_AUTH_TOKEN=your_n8n_auth_token
N8N_WEBHOOK_SECRET=your_webhook_secret

# Document Processing
MAX_FILE_SIZE_MB=10
SUPPORTED_FORMATS=pdf,docx,txt
EXTRACT_IMAGES=true

# Cache Configuration
RAG_CACHE_TTL=3600
ANALYSIS_CACHE_PREFIX=resume_analysis_
WORKFLOW_CACHE_PREFIX=workflow_status_
```

### RAG Configuration (`rag_config.py`):

```python
from recruitment.rag_config import RAGConfigManager

# Load configuration
config_manager = RAGConfigManager()
config = config_manager.get_config()

# Update configuration
config.similarity_threshold = 0.8
config_manager.save_config(config)

# Environment-based configuration
config = config_manager.load_from_environment()
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
cd /Users/haryanto.bonti/apps
pip install -r requirements.txt
pip install -r recruitment/requirements.txt

# Install system dependencies (macOS)
brew install chromadb
brew install ollama
```

### 2. Setup Services

```bash
# Start services using Docker Compose
docker-compose -f docker-compose.rag.yml up -d

# Or start services individually

# Start ChromaDB
chroma run --host localhost --port 8000 --path ./data/chromadb

# Start Ollama
ollama serve
ollama pull llama2
ollama pull nomic-embed-text

# Start N8N
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n

# Start Redis (for Celery)
redis-server

# Start Celery worker
celery -A horilla worker -l info

# Start Celery beat (scheduler)
celery -A horilla beat -l info
```

### 3. Initialize RAG System

```bash
# Run setup command
python manage.py setup_rag_system

# This will:
# - Initialize ChromaDB collections
# - Download required Ollama models
# - Setup N8N workflows
# - Run health checks
```

### 4. Verify Installation

```bash
# Run tests
python manage.py test recruitment.test_rag_integration

# Check service health
curl http://localhost:8000/api/recruitment/workflow/service-health/

# Test RAG functionality
curl -X POST http://localhost:8000/api/recruitment/rag/analyze-resume/ \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": 1,
    "job_description": "Software engineer position",
    "async": false
  }'
```

## Usage Examples

### 1. Analyze Candidate Resume

```python
from recruitment.services import RecruitmentRAGService

# Initialize service
rag_service = RecruitmentRAGService()

# Analyze resume
result = await rag_service.analyze_resume(
    candidate_id=123,
    job_description="We are looking for a Python developer with Django experience..."
)

print(f"Similarity Score: {result['similarity_score']}")
print(f"Recommendation: {result['recommendation']}")
print(f"Analysis: {result['analysis']}")
```

### 2. Find Similar Candidates

```python
# Find candidates similar to job description
similar_candidates = rag_service.find_similar_candidates(
    job_description="Senior React developer with 5+ years experience",
    limit=10,
    similarity_threshold=0.7
)

for candidate in similar_candidates:
    print(f"Candidate: {candidate['candidate']['name']}")
    print(f"Similarity: {candidate['similarity_score']:.2f}")
```

### 3. Trigger Recruitment Workflow

```python
# Trigger resume screening workflow
workflow_result = await rag_service.trigger_recruitment_workflow(
    candidate_id=123,
    workflow_type="resume_screening",
    data={
        "priority": "high",
        "department": "engineering",
        "hiring_manager": "john.doe@company.com"
    }
)

print(f"Workflow Status: {workflow_result['status']}")
print(f"Execution ID: {workflow_result['execution_id']}")
```

### 4. Batch Process Candidates

```python
from recruitment.tasks import batch_analyze_candidates

# Start batch analysis
task = batch_analyze_candidates.delay(
    recruitment_id=456,
    job_description="Software engineer position..."
)

print(f"Task ID: {task.id}")

# Check task status
from celery.result import AsyncResult
result = AsyncResult(task.id)
print(f"Task Status: {result.status}")
```

## Monitoring and Troubleshooting

### 1. Health Checks

```bash
# Check all services
curl http://localhost:8000/api/recruitment/workflow/service-health/

# Check individual services
curl http://localhost:8000/healthz  # ChromaDB
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:5678/healthz  # N8N
```

### 2. Logs

```bash
# Django logs
tail -f logs/django.log

# Celery logs
tail -f logs/celery.log

# N8N logs
docker logs n8n

# ChromaDB logs
tail -f logs/chromadb.log
```

### 3. Common Issues

#### ChromaDB Connection Issues:
```bash
# Check if ChromaDB is running
curl http://localhost:8000/api/v1/heartbeat

# Restart ChromaDB
docker-compose restart chromadb
```

#### Ollama Model Issues:
```bash
# List available models
ollama list

# Pull required models
ollama pull llama2
ollama pull nomic-embed-text

# Check model status
ollama show llama2
```

#### N8N Workflow Issues:
```bash
# Check N8N status
curl http://localhost:5678/healthz

# List workflows
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5678/api/v1/workflows

# Check workflow execution
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:5678/api/v1/executions/EXECUTION_ID
```

## Performance Optimization

### 1. Vector Database Optimization

```python
# Optimize ChromaDB collection
collection.modify(
    metadata={
        "hnsw:space": "cosine",
        "hnsw:construction_ef": 200,
        "hnsw:M": 16
    }
)
```

### 2. Caching Strategy

```python
# Cache analysis results
from django.core.cache import cache

# Cache resume analysis for 1 hour
cache.set(f"resume_analysis_{candidate_id}", result, 3600)

# Cache similar candidates for 30 minutes
cache.set(f"similar_candidates_{job_hash}", candidates, 1800)
```

### 3. Batch Processing

```python
# Process candidates in batches
from recruitment.tasks import batch_analyze_candidates

# Analyze all candidates for a recruitment
batch_analyze_candidates.delay(
    recruitment_id=456,
    job_description="Software engineer...",
    batch_size=10
)
```

## Security Considerations

### 1. API Authentication

```python
# All API endpoints require authentication
from rest_framework.permissions import IsAuthenticated

class RecruitmentRAGViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
```

### 2. Data Privacy

```python
# Anonymize sensitive data in logs
import logging

logger = logging.getLogger(__name__)
logger.info(f"Processing candidate {candidate_id[:8]}...")
```

### 3. N8N Webhook Security

```python
# Verify webhook signatures
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)
```

## API Reference

For complete API documentation, see:
- [RAG API Endpoints](./api_docs/rag_endpoints.md)
- [Workflow API Endpoints](./api_docs/workflow_endpoints.md)
- [Celery Tasks Reference](./api_docs/celery_tasks.md)

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for API changes
4. Run the full test suite before submitting

```bash
# Run tests
python manage.py test recruitment.test_rag_integration

# Run linting
flake8 recruitment/

# Run type checking
mypy recruitment/
```

## License

This integration is part of the Horilla HR system and follows the same licensing terms.