# Technical Project Blueprint: Enhanced Horilla HR System

## Executive Summary

Proyek ini bertujuan untuk mengembangkan sistem HR berbasis Horilla dengan penambahan fitur-fitur advanced seperti Budget Control, Knowledge Management dengan AI, integrasi Ollama untuk local processing, NLP bahasa Indonesia, dan sistem RAG dengan N8N untuk automated recruitment. Target SLA 99.99% dengan arsitektur redundant dan monitoring komprehensif.

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Load Balancer (HAProxy/Nginx)               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                 Application Layer (Django)                     │
├─────────────────────────────────────────────────────────────────┤
│  Core Horilla  │  Budget Control  │  Knowledge Mgmt  │  AI/NLP  │
├─────────────────────────────────────────────────────────────────┤
│              Microservices Layer                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │   Ollama    │ │    N8N      │ │  RAG Engine │ │ Indonesian  ││n│  │   Service   │ │  Workflow   │ │   Service   │ │ NLP Service ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                    Data Layer                                   │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │ PostgreSQL  │ │    Redis    │ │ Elasticsearch│ │   Vector    ││
│  │  (Primary)  │ │   (Cache)   │ │  (Search)   │ │    DB       ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

#### Backend Framework
- **Django 4.2.21** (existing base)
- **Django REST Framework** untuk API
- **Celery** untuk background tasks
- **Redis** untuk caching dan message broker

#### Database Layer
- **PostgreSQL 15+** (primary database)
- **Redis 7+** (caching, sessions, queues)
- **Elasticsearch 8+** (full-text search, analytics)
- **ChromaDB/Pinecone** (vector database untuk RAG)

#### AI/ML Stack
- **Ollama** (local LLM deployment)
- **LangChain** (RAG implementation)
- **Transformers** (Hugging Face models)
- **spaCy** dengan model bahasa Indonesia
- **FastAPI** untuk AI microservices

#### Frontend
- **Django Templates** (existing)
- **Bootstrap 5** dengan custom CSS
- **Alpine.js** untuk interaktivitas
- **Chart.js** untuk visualisasi data
- **WebSocket** untuk real-time updates

#### Infrastructure
- **Docker & Docker Compose**
- **Kubernetes** (production)
- **HAProxy/Nginx** (load balancing)
- **Prometheus + Grafana** (monitoring)
- **ELK Stack** (logging)

## 2. Module Specifications

### 2.1 Budget Control Module

#### Features
- **Budget Planning**: Multi-level budget creation (department, project, category)
- **Real-time Tracking**: Live expense monitoring dengan alerts
- **Automated Reporting**: Daily, weekly, monthly financial reports
- **Approval Workflows**: Multi-stage budget approval process
- **Integration**: Sync dengan payroll dan expense modules

#### Technical Implementation
```python
# Models Structure
class BudgetPlan(models.Model):
    name = models.CharField(max_length=200)
    department = models.ForeignKey('employee.Department')
    fiscal_year = models.IntegerField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(choices=BUDGET_STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

class BudgetCategory(models.Model):
    budget_plan = models.ForeignKey(BudgetPlan)
    category_name = models.CharField(max_length=100)
    allocated_amount = models.DecimalField(max_digits=12, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2)

class Expense(models.Model):
    budget_category = models.ForeignKey(BudgetCategory)
    employee = models.ForeignKey('employee.Employee')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    receipt = models.FileField(upload_to='receipts/')
    status = models.CharField(choices=EXPENSE_STATUS_CHOICES)
    submitted_at = models.DateTimeField(auto_now_add=True)
```

#### API Endpoints
- `GET/POST /api/v1/budget/plans/` - Budget plans management
- `GET/POST /api/v1/budget/expenses/` - Expense tracking
- `GET /api/v1/budget/reports/` - Financial reports
- `GET /api/v1/budget/analytics/` - Real-time analytics

### 2.2 Knowledge Management System

#### Features
- **AI-Powered Search**: Semantic search dengan Ollama
- **Document Classification**: Automatic categorization
- **Knowledge Base**: Centralized document storage
- **Version Control**: Document versioning dan approval
- **AI Assistant**: Chatbot untuk knowledge retrieval

#### Technical Implementation
```python
# Knowledge Management Models
class KnowledgeBase(models.Model):
    title = models.CharField(max_length=300)
    content = models.TextField()
    category = models.ForeignKey('KnowledgeCategory')
    tags = models.ManyToManyField('Tag')
    author = models.ForeignKey('employee.Employee')
    version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False)
    embedding_vector = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DocumentClassification(models.Model):
    document = models.OneToOneField(KnowledgeBase)
    predicted_category = models.CharField(max_length=100)
    confidence_score = models.FloatField()
    manual_override = models.BooleanField(default=False)

class AIAssistantQuery(models.Model):
    user = models.ForeignKey('employee.Employee')
    query = models.TextField()
    response = models.TextField()
    relevant_documents = models.ManyToManyField(KnowledgeBase)
    satisfaction_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2.3 Ollama Integration Service

#### Features
- **Local LLM Deployment**: Ollama server setup
- **Model Management**: Multiple model support (Llama2, Mistral, etc.)
- **Edge Computing**: Offline processing capabilities
- **Security**: Local data processing tanpa cloud dependency

#### Technical Implementation
```python
# Ollama Service Integration
class OllamaService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.client = httpx.Client()
    
    async def generate_response(self, prompt: str, model: str = "llama2"):
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json()
    
    async def embed_text(self, text: str, model: str = "nomic-embed-text"):
        response = await self.client.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": model,
                "prompt": text
            }
        )
        return response.json()["embedding"]
```

### 2.4 Indonesian NLP Service

#### Features
- **Text Processing**: Tokenization, POS tagging untuk bahasa Indonesia
- **Sentiment Analysis**: Local sentiment analysis
- **Named Entity Recognition**: Ekstraksi entitas dalam bahasa Indonesia
- **Text Summarization**: Ringkasan dokumen otomatis

#### Technical Implementation
```python
# Indonesian NLP Service
import spacy
from transformers import pipeline

class IndonesianNLPService:
    def __init__(self):
        self.nlp = spacy.load("id_core_news_sm")
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="indobenchmark/indobert-base-p1"
        )
    
    def analyze_sentiment(self, text: str):
        result = self.sentiment_analyzer(text)
        return {
            "label": result[0]["label"],
            "score": result[0]["score"]
        }
    
    def extract_entities(self, text: str):
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        return entities
    
    def summarize_text(self, text: str, max_length: int = 150):
        # Implementation using Indonesian summarization model
        pass
```

### 2.5 RAG System dengan N8N Integration

#### Features
- **Automated Recruitment**: AI-powered candidate screening
- **Resume Analysis**: Automatic resume parsing dan scoring
- **Interview Scheduling**: Automated interview workflow
- **Candidate Matching**: Job-candidate matching algorithm

#### Technical Implementation
```python
# RAG System for Recruitment
class RecruitmentRAGService:
    def __init__(self):
        self.vector_db = ChromaDB()
        self.llm_service = OllamaService()
        self.n8n_client = N8NClient()
    
    async def analyze_resume(self, resume_text: str, job_description: str):
        # Extract resume information
        resume_embedding = await self.llm_service.embed_text(resume_text)
        job_embedding = await self.llm_service.embed_text(job_description)
        
        # Calculate similarity score
        similarity_score = self.calculate_similarity(resume_embedding, job_embedding)
        
        # Generate analysis report
        analysis_prompt = f"""
        Analyze this resume against the job description:
        
        Resume: {resume_text}
        Job Description: {job_description}
        
        Provide a detailed analysis including:
        1. Skills match percentage
        2. Experience relevance
        3. Education alignment
        4. Recommendations
        """
        
        analysis = await self.llm_service.generate_response(analysis_prompt)
        
        return {
            "similarity_score": similarity_score,
            "analysis": analysis["response"],
            "recommendation": "PROCEED" if similarity_score > 0.7 else "REVIEW"
        }
    
    async def trigger_n8n_workflow(self, workflow_id: str, data: dict):
        return await self.n8n_client.trigger_workflow(workflow_id, data)
```

## 3. Database Schema Design

### 3.1 Budget Control Tables
```sql
-- Budget Control Schema
CREATE TABLE budget_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    department_id INTEGER REFERENCES employee_department(id),
    fiscal_year INTEGER NOT NULL,
    total_amount DECIMAL(15,2) NOT NULL,
    allocated_amount DECIMAL(15,2) DEFAULT 0,
    spent_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE budget_categories (
    id SERIAL PRIMARY KEY,
    budget_plan_id INTEGER REFERENCES budget_plans(id),
    category_name VARCHAR(100) NOT NULL,
    allocated_amount DECIMAL(12,2) NOT NULL,
    spent_amount DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE expenses (
    id SERIAL PRIMARY KEY,
    budget_category_id INTEGER REFERENCES budget_categories(id),
    employee_id INTEGER REFERENCES employee_employee(id),
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    receipt_url VARCHAR(500),
    status VARCHAR(20) DEFAULT 'PENDING',
    submitted_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP NULL
);
```

### 3.2 Knowledge Management Tables
```sql
-- Knowledge Management Schema
CREATE TABLE knowledge_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES knowledge_categories(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    category_id INTEGER REFERENCES knowledge_categories(id),
    author_id INTEGER REFERENCES employee_employee(id),
    version INTEGER DEFAULT 1,
    is_published BOOLEAN DEFAULT FALSE,
    embedding_vector JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_classifications (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES knowledge_base(id),
    predicted_category VARCHAR(100),
    confidence_score FLOAT,
    manual_override BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 4. API Design

### 4.1 RESTful API Structure

#### Budget Control APIs
```python
# Budget Control API Views
class BudgetPlanViewSet(viewsets.ModelViewSet):
    queryset = BudgetPlan.objects.all()
    serializer_class = BudgetPlanSerializer
    permission_classes = [IsAuthenticated, BudgetPermission]
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        budget_plan = self.get_object()
        analytics_data = {
            'total_budget': budget_plan.total_amount,
            'spent_percentage': (budget_plan.spent_amount / budget_plan.total_amount) * 100,
            'remaining_budget': budget_plan.total_amount - budget_plan.spent_amount,
            'monthly_spending': self.get_monthly_spending(budget_plan)
        }
        return Response(analytics_data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        budget_plan = self.get_object()
        budget_plan.status = 'APPROVED'
        budget_plan.save()
        return Response({'status': 'approved'})
```

#### Knowledge Management APIs
```python
# Knowledge Management API Views
class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    queryset = KnowledgeBase.objects.all()
    serializer_class = KnowledgeBaseSerializer
    
    @action(detail=False, methods=['post'])
    def semantic_search(self, request):
        query = request.data.get('query')
        
        # Generate embedding for query
        ollama_service = OllamaService()
        query_embedding = await ollama_service.embed_text(query)
        
        # Search similar documents
        similar_docs = self.find_similar_documents(query_embedding)
        
        serializer = self.get_serializer(similar_docs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def ai_assistant(self, request):
        query = request.data.get('query')
        
        # Get relevant documents using RAG
        relevant_docs = self.get_relevant_documents(query)
        
        # Generate response using Ollama
        context = "\n".join([doc.content for doc in relevant_docs])
        prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"
        
        ollama_service = OllamaService()
        response = await ollama_service.generate_response(prompt)
        
        return Response({
            'response': response['response'],
            'relevant_documents': [doc.id for doc in relevant_docs]
        })
```

## 5. Frontend Architecture

### 5.1 UI/UX Design Principles

#### Responsive Design
- **Mobile-first approach** dengan Bootstrap 5
- **Progressive Web App** capabilities
- **Accessibility compliance** (WCAG 2.1 AA)
- **Dark/Light theme** support

#### Component Structure
```html
<!-- Budget Dashboard Component -->
<div class="budget-dashboard" x-data="budgetDashboard()">
    <div class="row">
        <div class="col-md-3">
            <div class="card budget-summary">
                <div class="card-body">
                    <h5 class="card-title">Total Budget</h5>
                    <h2 class="text-primary" x-text="formatCurrency(totalBudget)"></h2>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card expense-summary">
                <div class="card-body">
                    <h5 class="card-title">Spent Amount</h5>
                    <h2 class="text-danger" x-text="formatCurrency(spentAmount)"></h2>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-body">
                    <canvas id="budgetChart"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function budgetDashboard() {
    return {
        totalBudget: 0,
        spentAmount: 0,
        
        init() {
            this.loadBudgetData();
            this.initChart();
        },
        
        async loadBudgetData() {
            const response = await fetch('/api/v1/budget/analytics/');
            const data = await response.json();
            this.totalBudget = data.total_budget;
            this.spentAmount = data.spent_amount;
        },
        
        formatCurrency(amount) {
            return new Intl.NumberFormat('id-ID', {
                style: 'currency',
                currency: 'IDR'
            }).format(amount);
        }
    }
}
</script>
```

### 5.2 Real-time Features

#### WebSocket Implementation
```python
# WebSocket Consumer for Real-time Updates
class BudgetConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.budget_group = f"budget_{self.scope['user'].id}"
        await self.channel_layer.group_add(
            self.budget_group,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.budget_group,
            self.channel_name
        )
    
    async def budget_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'budget_update',
            'data': event['data']
        }))
```

## 6. Infrastructure & Deployment

### 6.1 Docker Configuration

#### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/horilla
    depends_on:
      - db
      - redis
      - ollama
    volumes:
      - ./media:/app/media
      - ./staticfiles:/app/staticfiles
  
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: horilla
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
  
  elasticsearch:
    image: elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
  
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
    volumes:
      - n8n_data:/home/node/.n8n
  
  celery:
    build: .
    command: celery -A horilla worker -l info
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/horilla
  
  celery-beat:
    build: .
    command: celery -A horilla beat -l info
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/horilla

volumes:
  postgres_data:
  ollama_data:
  elasticsearch_data:
  n8n_data:
```

### 6.2 Kubernetes Deployment

#### Production Kubernetes Configuration
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: horilla-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: horilla-web
  template:
    metadata:
      labels:
        app: horilla-web
    spec:
      containers:
      - name: web
        image: horilla:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: horilla-secrets
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: horilla-web-service
spec:
  selector:
    app: horilla-web
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 7. Monitoring & Observability

### 7.1 Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'horilla'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics/'
  
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 7.2 Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Horilla HR System Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(django_http_requests_total[5m])",
            "legendFormat": "{{method}} {{handler}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(django_http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Database Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends{datname=\"horilla\"}"
          }
        ]
      }
    ]
  }
}
```

## 8. Security Implementation

### 8.1 Authentication & Authorization

```python
# Enhanced Security Settings
SECURITY_SETTINGS = {
    # JWT Configuration
    'SIMPLE_JWT': {
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
        'ROTATE_REFRESH_TOKENS': True,
        'BLACKLIST_AFTER_ROTATION': True,
    },
    
    # Rate Limiting
    'RATELIMIT_ENABLE': True,
    'RATELIMIT_USE_CACHE': 'default',
    
    # CORS Settings
    'CORS_ALLOWED_ORIGINS': [
        "https://hr.company.com",
        "https://api.company.com",
    ],
    
    # Content Security Policy
    'CSP_DEFAULT_SRC': ["'self'"],
    'CSP_SCRIPT_SRC': ["'self'", "'unsafe-inline'"],
    'CSP_STYLE_SRC': ["'self'", "'unsafe-inline'"],
}
```

### 8.2 Data Encryption

```python
# Data Encryption Service
from cryptography.fernet import Fernet

class EncryptionService:
    def __init__(self):
        self.key = settings.ENCRYPTION_KEY.encode()
        self.cipher = Fernet(self.key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# Model with encrypted fields
class EmployeeSensitiveData(models.Model):
    employee = models.OneToOneField(Employee)
    encrypted_salary = models.TextField()
    encrypted_bank_account = models.TextField()
    
    def set_salary(self, salary):
        encryption_service = EncryptionService()
        self.encrypted_salary = encryption_service.encrypt_sensitive_data(str(salary))
    
    def get_salary(self):
        encryption_service = EncryptionService()
        return float(encryption_service.decrypt_sensitive_data(self.encrypted_salary))
```

## 9. Testing Strategy

### 9.1 Unit Testing

```python
# Budget Control Tests
class BudgetControlTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.department = Department.objects.create(
            department='IT',
            company=Company.objects.create(company='Test Corp')
        )
        self.budget_plan = BudgetPlan.objects.create(
            name='IT Budget 2024',
            department=self.department,
            fiscal_year=2024,
            total_amount=100000.00
        )
    
    def test_budget_creation(self):
        self.assertEqual(self.budget_plan.total_amount, 100000.00)
        self.assertEqual(self.budget_plan.spent_amount, 0.00)
    
    def test_expense_tracking(self):
        expense = Expense.objects.create(
            budget_category=BudgetCategory.objects.create(
                budget_plan=self.budget_plan,
                category_name='Software',
                allocated_amount=50000.00
            ),
            employee=Employee.objects.create(
                employee_user_id=self.user,
                employee_first_name='John',
                employee_last_name='Doe'
            ),
            amount=1000.00,
            description='Software license'
        )
        
        self.assertEqual(expense.amount, 1000.00)
        self.assertEqual(expense.status, 'PENDING')
```

### 9.2 Integration Testing

```python
# API Integration Tests
class BudgetAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_budget_plan_creation_api(self):
        url = '/api/v1/budget/plans/'
        data = {
            'name': 'Test Budget',
            'department': 1,
            'fiscal_year': 2024,
            'total_amount': 50000.00
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BudgetPlan.objects.count(), 1)
    
    def test_budget_analytics_api(self):
        budget_plan = BudgetPlan.objects.create(
            name='Test Budget',
            total_amount=100000.00,
            spent_amount=25000.00
        )
        
        url = f'/api/v1/budget/plans/{budget_plan.id}/analytics/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['spent_percentage'], 25.0)
```

## 10. Performance Optimization

### 10.1 Database Optimization

```python
# Database Indexes
class BudgetPlan(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['department', 'fiscal_year']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['total_amount']),
        ]

# Query Optimization
class BudgetPlanViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return BudgetPlan.objects.select_related(
            'department',
            'department__company'
        ).prefetch_related(
            'budgetcategory_set',
            'budgetcategory_set__expense_set'
        )
```

### 10.2 Caching Strategy

```python
# Redis Caching Implementation
from django.core.cache import cache
from django.views.decorators.cache import cache_page

class BudgetAnalyticsView(APIView):
    def get(self, request, budget_id):
        cache_key = f'budget_analytics_{budget_id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        # Generate analytics data
        analytics_data = self.generate_analytics(budget_id)
        
        # Cache for 5 minutes
        cache.set(cache_key, analytics_data, 300)
        
        return Response(analytics_data)

# Celery Background Tasks
@shared_task
def update_budget_analytics():
    """Update budget analytics in background"""
    for budget_plan in BudgetPlan.objects.filter(status='ACTIVE'):
        analytics_data = generate_budget_analytics(budget_plan)
        cache_key = f'budget_analytics_{budget_plan.id}'
        cache.set(cache_key, analytics_data, 3600)  # Cache for 1 hour
```

## 11. Deployment Pipeline

### 11.1 CI/CD Configuration

```yaml
# .github/workflows/deploy.yml
name: Deploy Horilla HR System

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_horilla
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: |
        python manage.py test
        coverage run --source='.' manage.py test
        coverage report
    
    - name: Run linting
      run: |
        flake8 .
        black --check .
        isort --check-only .
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t horilla:${{ github.sha }} .
        docker tag horilla:${{ github.sha }} horilla:latest
    
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/horilla-web web=horilla:${{ github.sha }}
        kubectl rollout status deployment/horilla-web
```

## 12. Documentation Plan

### 12.1 Technical Documentation

1. **API Documentation** - Swagger/OpenAPI specs
2. **Database Schema** - ERD dan table descriptions
3. **Architecture Diagrams** - System dan component diagrams
4. **Deployment Guide** - Step-by-step deployment instructions
5. **Configuration Guide** - Environment variables dan settings

### 12.2 User Documentation

1. **User Manual** - End-user guide untuk setiap modul
2. **Admin Guide** - System administration guide
3. **Training Materials** - Video tutorials dan workshops
4. **FAQ** - Common questions dan troubleshooting

## 13. Project Timeline

### Phase 1: Foundation (Weeks 1-4)
- [ ] Setup development environment
- [ ] Database schema design dan migration
- [ ] Basic authentication dan authorization
- [ ] Core API structure

### Phase 2: Budget Control Module (Weeks 5-8)
- [ ] Budget planning functionality
- [ ] Expense tracking system
- [ ] Real-time analytics
- [ ] Approval workflows

### Phase 3: Knowledge Management (Weeks 9-12)
- [ ] Document storage system
- [ ] Search functionality
- [ ] AI assistant integration
- [ ] Document classification

### Phase 4: AI Integration (Weeks 13-16)
- [ ] Ollama setup dan configuration
- [ ] Indonesian NLP service
- [ ] RAG system implementation
- [ ] N8N workflow integration

### Phase 5: Testing & Deployment (Weeks 17-20)
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Security audit
- [ ] Production deployment

## 14. Risk Management

### 14.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Ollama performance issues | High | Medium | Load testing, fallback to cloud APIs |
| Database scalability | High | Low | Horizontal scaling, read replicas |
| AI model accuracy | Medium | Medium | Model fine-tuning, human oversight |
| Integration complexity | Medium | High | Modular architecture, extensive testing |

### 14.2 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Budget overrun | High | Medium | Agile development, regular reviews |
| Timeline delays | Medium | Medium | Buffer time, parallel development |
| User adoption | High | Low | User training, intuitive UI |
| Compliance issues | High | Low | Security audit, compliance review |

## 15. Success Metrics

### 15.1 Technical KPIs
- **System Uptime**: 99.99% SLA
- **Response Time**: < 200ms for API calls
- **Database Performance**: < 100ms query time
- **AI Accuracy**: > 85% for document classification

### 15.2 Business KPIs
- **User Adoption**: 90% of HR staff using system
- **Process Efficiency**: 50% reduction in manual tasks
- **Cost Savings**: 30% reduction in HR operational costs
- **User Satisfaction**: > 4.5/5 rating

## Conclusion

Blueprint teknis ini menyediakan roadmap komprehensif untuk pengembangan sistem HR berbasis Horilla dengan fitur-fitur advanced yang diminta. Dengan arsitektur modular, teknologi modern, dan fokus pada keamanan serta performa, sistem ini akan mampu memenuhi kebutuhan enterprise dengan SLA 99.99%.

Implementasi akan dilakukan secara bertahap dengan testing menyeluruh di setiap fase untuk memastikan kualitas dan reliability sistem. Dokumentasi lengkap dan training akan disediakan untuk memastikan adopsi yang sukses oleh end users.