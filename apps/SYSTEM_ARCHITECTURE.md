# Horilla HR System - System Architecture

## Overview

Horilla HR System adalah platform HR management yang komprehensif dengan fitur-fitur advanced termasuk Budget Control, Knowledge Management dengan AI Assistant, Indonesian NLP, dan sistem monitoring untuk mencapai SLA 99.99%.

## Architecture Principles

### 1. Scalability First
- **Horizontal Scaling**: Mendukung multiple instances dengan load balancing
- **Vertical Scaling**: Optimized untuk peningkatan resources
- **Microservices Ready**: Modular design untuk future decomposition

### 2. Security by Design
- **Defense in Depth**: Multiple layers of security
- **Zero Trust**: Verify everything, trust nothing
- **Data Protection**: Encryption at rest and in transit

### 3. High Availability
- **Redundancy**: Multiple instances dan failover mechanisms
- **Health Monitoring**: Comprehensive health checks
- **Auto-recovery**: Automatic restart dan healing

### 4. Performance Optimization
- **Caching Strategy**: Multi-level caching
- **Database Optimization**: Indexing dan query optimization
- **Asynchronous Processing**: Background tasks dengan Celery

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Load Balancer                          │
│                        (Nginx/HAProxy)                         │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                     │           Web Layer                       │
│  ┌─────────────────┐│┌─────────────────┐ ┌─────────────────┐   │
│  │   Django App    │││   Django App    │ │   Django App    │   │
│  │   Instance 1    │││   Instance 2    │ │   Instance 3    │   │
│  │   (Gunicorn)    │││   (Gunicorn)    │ │   (Gunicorn)    │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                     │        Application Layer                  │
│  ┌─────────────────┐│┌─────────────────┐ ┌─────────────────┐   │
│  │     Budget      │││  Knowledge Mgmt │ │   Recruitment   │   │
│  │    Control      │││   + AI Assistant│ │   + N8N + RAG   │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
│  ┌─────────────────┐││┌─────────────────┐ ┌─────────────────┐   │
│  │   Indonesian    │││    Monitoring   │ │   Core Horilla  │   │
│  │      NLP        │││    System       │ │     Modules     │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                     │         Service Layer                     │
│  ┌─────────────────┐│┌─────────────────┐ ┌─────────────────┐   │
│  │     Celery      │││      Redis      │ │     Ollama      │   │
│  │   Task Queue    │││     Cache       │ │   AI Models     │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                     │          Data Layer                       │
│  ┌─────────────────┐│┌─────────────────┐ ┌─────────────────┐   │
│  │   PostgreSQL    │││   File Storage  │ │   Vector DB     │   │
│  │   Primary DB    │││   (Media/Docs)  │ │   (Embeddings)  │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
└─────────────────────┼───────────────────────────────────────────┘
                      │
┌─────────────────────┼───────────────────────────────────────────┐
│                     │       Monitoring Layer                    │
│  ┌─────────────────┐│┌─────────────────┐ ┌─────────────────┐   │
│  │   Prometheus    │││     Grafana     │ │   Log Aggreg.   │   │
│  │    Metrics      │││   Dashboards    │ │   (ELK Stack)   │   │
│  └─────────────────┘││└─────────────────┘ └─────────────────┘   │
└─────────────────────┴───────────────────────────────────────────┘
```

## Component Architecture

### 1. Web Layer

#### Load Balancer (Nginx)
- **Purpose**: Distribute traffic across multiple Django instances
- **Features**:
  - SSL termination
  - Rate limiting
  - Static file serving
  - Health check routing
  - Security headers

#### Django Application Instances
- **Purpose**: Handle HTTP requests dan business logic
- **Configuration**:
  - Gunicorn WSGI server
  - Multiple workers (CPU cores × 2 + 1)
  - Process recycling
  - Graceful shutdowns

### 2. Application Layer

#### Core Modules
```
horilla/
├── employee/          # Employee management
├── attendance/        # Time tracking
├── leave/            # Leave management
├── payroll/          # Payroll processing
├── recruitment/      # Hiring process
├── onboarding/       # Employee onboarding
├── offboarding/      # Employee offboarding
├── pms/              # Performance management
├── asset/            # Asset management
├── helpdesk/         # Support tickets
└── notifications/    # Notification system
```

#### Enhanced Modules
```
enhanced_modules/
├── budget/           # Budget Control System
│   ├── models.py     # Budget, Transaction, Category
│   ├── views.py      # CRUD operations
│   ├── analytics.py  # Real-time analytics
│   └── alerts.py     # Budget alerts
├── knowledge/        # Knowledge Management
│   ├── models.py     # Document, Category, Tag
│   ├── ai_assistant.py # AI-powered assistance
│   ├── search.py     # Advanced search
│   └── classification.py # Auto-classification
├── indonesian_nlp/   # Indonesian NLP
│   ├── sentiment.py  # Sentiment analysis
│   ├── tokenizer.py  # Text processing
│   └── models.py     # NLP models
├── monitoring/       # System Monitoring
│   ├── health.py     # Health checks
│   ├── metrics.py    # Prometheus metrics
│   └── alerts.py     # System alerts
└── rag_n8n/         # RAG + N8N Integration
    ├── rag_system.py # Retrieval-Augmented Generation
    ├── n8n_client.py # N8N workflow client
    └── workflows.py  # Automated workflows
```

### 3. Service Layer

#### Celery Task Queue
- **Purpose**: Asynchronous task processing
- **Components**:
  - **Worker Processes**: Execute background tasks
  - **Beat Scheduler**: Periodic task scheduling
  - **Flower Monitor**: Task monitoring dashboard

**Task Categories**:
```python
# Budget tasks
@shared_task
def process_budget_alert(budget_id):
    # Send budget threshold alerts

@shared_task
def generate_budget_report(period):
    # Generate periodic budget reports

# Knowledge management tasks
@shared_task
def classify_document(document_id):
    # Auto-classify uploaded documents

@shared_task
def update_search_index(document_id):
    # Update search index for new documents

# NLP tasks
@shared_task
def analyze_sentiment(text_id):
    # Perform sentiment analysis

@shared_task
def extract_entities(text_id):
    # Extract named entities

# Monitoring tasks
@shared_task
def collect_system_metrics():
    # Collect and store system metrics

@shared_task
def check_system_health():
    # Perform comprehensive health checks
```

#### Redis Cache
- **Purpose**: High-performance caching dan session storage
- **Usage**:
  - Session storage
  - Query result caching
  - Temporary data storage
  - Rate limiting counters
  - Real-time data caching

#### Ollama AI Service
- **Purpose**: Local AI model serving
- **Models**:
  - **LLaMA 2 7B**: General purpose AI assistant
  - **Mistral 7B**: Code generation dan analysis
  - **Custom Models**: Indonesian language models

### 4. Data Layer

#### PostgreSQL Database
- **Purpose**: Primary data storage
- **Configuration**:
  - Connection pooling
  - Read replicas (future)
  - Automated backups
  - Performance monitoring

**Database Schema**:
```sql
-- Core tables
auth_user              -- User authentication
employee_employee      -- Employee profiles
attendance_attendance  -- Time tracking
leave_leaverequest     -- Leave requests
payroll_payslip        -- Payroll data

-- Enhanced tables
budget_budget          -- Budget definitions
budget_transaction     -- Financial transactions
knowledge_document     -- Knowledge base documents
knowledge_category     -- Document categories
indonesian_nlp_analysis -- NLP analysis results
monitoring_healthcheck -- Health check logs
rag_embedding          -- Vector embeddings
```

#### File Storage
- **Purpose**: Media dan document storage
- **Structure**:
```
media/
├── employee_photos/   # Employee profile photos
├── documents/         # HR documents
├── knowledge_base/    # Knowledge management files
├── budget_receipts/   # Budget transaction receipts
└── system_logs/       # System log files
```

#### Vector Database (Future)
- **Purpose**: Semantic search dan RAG system
- **Technology**: Chroma/Pinecone/Weaviate
- **Usage**:
  - Document embeddings
  - Semantic search
  - AI assistant context

### 5. Monitoring Layer

#### Health Check System
```python
# Health check endpoints
/health/              # Basic health check
/health/ready/        # Readiness probe (K8s)
/health/live/         # Liveness probe (K8s)
/health/detailed/     # Comprehensive health check
/metrics/             # Prometheus metrics
```

#### Prometheus Metrics
```
# System metrics
system_cpu_usage_percent
system_memory_usage_percent
system_disk_usage_percent

# Application metrics
django_request_duration_seconds
django_request_total
django_database_connections
django_cache_hits_total
django_cache_misses_total

# Business metrics
budget_transactions_total
knowledge_documents_total
employee_count
active_sessions_total
```

#### Grafana Dashboards
- **System Overview**: CPU, Memory, Disk, Network
- **Application Performance**: Response times, throughput
- **Business Metrics**: Budget usage, document access
- **Error Tracking**: Error rates, failed requests

## Data Flow Architecture

### 1. Request Processing Flow

```
User Request → Load Balancer → Django Instance → Business Logic
     ↓
Database Query ← Cache Check → Redis Cache
     ↓
Response Generation → Template Rendering → HTTP Response
```

### 2. Asynchronous Task Flow

```
User Action → Task Creation → Celery Queue → Worker Process
     ↓
Task Execution → Database Update → Notification/Alert
     ↓
Result Storage → User Notification → Task Completion
```

### 3. AI Processing Flow

```
User Input → Text Processing → Ollama API → Model Inference
     ↓
Result Processing → Context Enhancement → Response Generation
     ↓
Cache Result → Return to User → Log Interaction
```

### 4. Monitoring Data Flow

```
System Metrics → Prometheus Scraping → Time Series DB
     ↓
Grafana Visualization → Alert Rules → Notification Channels
     ↓
Dashboard Updates → Real-time Monitoring → Incident Response
```

## Security Architecture

### 1. Authentication & Authorization

```python
# Multi-layer security
class SecurityMiddleware:
    def __init__(self):
        self.layers = [
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'horilla.middleware.CustomAuthMiddleware',
        ]
```

### 2. Data Protection

- **Encryption at Rest**: Database encryption
- **Encryption in Transit**: TLS 1.3
- **Field-level Encryption**: Sensitive data fields
- **Access Controls**: Role-based permissions

### 3. Network Security

```
Internet → WAF → Load Balancer → Application Servers
    ↓
Firewall Rules → VPC/Network Segmentation → Internal Services
    ↓
Database Access → Encrypted Connections → Audit Logging
```

## Scalability Architecture

### 1. Horizontal Scaling

```yaml
# Kubernetes scaling configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: horilla-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: horilla
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. Database Scaling

```
Primary Database (Write) → Read Replicas (Read)
     ↓
Connection Pooling → Query Optimization → Caching Layer
     ↓
Sharding Strategy → Partitioning → Archive Strategy
```

### 3. Cache Scaling

```
Redis Cluster → Multiple Nodes → Consistent Hashing
     ↓
Cache Warming → TTL Management → Eviction Policies
     ↓
Multi-level Caching → CDN Integration → Edge Caching
```

## Deployment Architecture

### 1. Development Environment

```
Local Development:
├── SQLite Database
├── Local Redis
├── Django Dev Server
├── Local Ollama
└── File-based Storage
```

### 2. Staging Environment

```
Staging Environment:
├── PostgreSQL Database
├── Redis Cluster
├── Gunicorn + Nginx
├── Docker Containers
├── Ollama Service
└── S3-compatible Storage
```

### 3. Production Environment

```
Production Environment:
├── PostgreSQL Cluster (Primary + Replicas)
├── Redis Cluster (HA)
├── Kubernetes Cluster
├── Load Balancer (HA)
├── Ollama Cluster
├── Object Storage (S3/MinIO)
├── Monitoring Stack
└── Backup Systems
```

## Performance Architecture

### 1. Caching Strategy

```python
# Multi-level caching
class CacheStrategy:
    levels = {
        'L1': 'Browser Cache (Static Assets)',
        'L2': 'CDN Cache (Global)',
        'L3': 'Nginx Cache (Reverse Proxy)',
        'L4': 'Redis Cache (Application)',
        'L5': 'Database Query Cache',
    }
```

### 2. Database Optimization

```sql
-- Index strategy
CREATE INDEX CONCURRENTLY idx_employee_active ON employee_employee(is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY idx_attendance_date_employee ON attendance_attendance(attendance_date, employee_id);
CREATE INDEX CONCURRENTLY idx_budget_transaction_date ON budget_transaction(transaction_date);
CREATE INDEX CONCURRENTLY idx_knowledge_document_category ON knowledge_document(category_id);

-- Partitioning strategy
CREATE TABLE attendance_attendance_y2024m01 PARTITION OF attendance_attendance
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 3. Asynchronous Processing

```python
# Task prioritization
class TaskPriority:
    CRITICAL = 0    # System health, security
    HIGH = 1        # User-facing operations
    MEDIUM = 2      # Background processing
    LOW = 3         # Analytics, reporting

# Queue routing
CELERY_TASK_ROUTES = {
    'monitoring.*': {'queue': 'critical'},
    'budget.alerts.*': {'queue': 'high'},
    'knowledge.classification.*': {'queue': 'medium'},
    'analytics.*': {'queue': 'low'},
}
```

## Disaster Recovery Architecture

### 1. Backup Strategy

```
Database Backups:
├── Continuous WAL Archiving
├── Daily Full Backups
├── Point-in-Time Recovery
└── Cross-Region Replication

Application Backups:
├── Code Repository (Git)
├── Configuration Files
├── Media Files (S3)
└── Container Images
```

### 2. High Availability

```
HA Components:
├── Load Balancer (Active-Passive)
├── Application Servers (Active-Active)
├── Database (Primary-Replica)
├── Cache (Cluster Mode)
└── Storage (Replicated)
```

### 3. Recovery Procedures

```
RTO (Recovery Time Objective): < 15 minutes
RPO (Recovery Point Objective): < 5 minutes

Failover Sequence:
1. Health Check Failure Detection
2. Automatic Traffic Rerouting
3. Service Instance Restart
4. Database Failover (if needed)
5. Cache Warming
6. Service Validation
```

## Integration Architecture

### 1. External Integrations

```python
# API integrations
class ExternalIntegrations:
    services = {
        'email': 'SMTP/SendGrid',
        'sms': 'Twilio/AWS SNS',
        'storage': 'AWS S3/MinIO',
        'analytics': 'Google Analytics',
        'monitoring': 'Prometheus/Grafana',
        'logging': 'ELK Stack',
        'ai': 'Ollama/OpenAI',
        'workflow': 'N8N',
    }
```

### 2. API Architecture

```
RESTful APIs:
├── /api/v1/employees/     # Employee management
├── /api/v1/budget/        # Budget operations
├── /api/v1/knowledge/     # Knowledge base
├── /api/v1/ai/            # AI assistant
├── /api/v1/analytics/     # Analytics data
└── /api/v1/monitoring/    # System monitoring

WebSocket APIs:
├── /ws/notifications/     # Real-time notifications
├── /ws/chat/             # AI assistant chat
└── /ws/monitoring/       # Live monitoring data
```

### 3. Webhook Architecture

```python
# Webhook handlers
class WebhookHandlers:
    endpoints = {
        '/webhooks/n8n/': 'N8N workflow triggers',
        '/webhooks/payment/': 'Payment notifications',
        '/webhooks/hr/': 'HR system events',
        '/webhooks/monitoring/': 'Alert notifications',
    }
```

## Future Architecture Considerations

### 1. Microservices Migration

```
Monolith → Microservices:
├── User Service
├── Employee Service
├── Budget Service
├── Knowledge Service
├── AI Service
├── Notification Service
└── Analytics Service
```

### 2. Event-Driven Architecture

```
Event Bus (Apache Kafka):
├── Employee Events
├── Budget Events
├── Knowledge Events
├── System Events
└── Analytics Events
```

### 3. Cloud-Native Architecture

```
Cloud Services:
├── Container Orchestration (Kubernetes)
├── Serverless Functions (AWS Lambda)
├── Managed Databases (RDS/Aurora)
├── Object Storage (S3)
├── CDN (CloudFront)
├── Monitoring (CloudWatch)
└── Security (WAF/Shield)
```

## Conclusion

Arsitektur Horilla HR System dirancang dengan prinsip scalability, security, dan high availability. Sistem ini dapat berkembang dari deployment sederhana hingga enterprise-scale dengan minimal architectural changes. Monitoring dan observability yang komprehensif memastikan sistem dapat mencapai SLA 99.99% dengan proper operations dan maintenance.

---

**Architecture Version**: 1.0  
**Last Updated**: January 2025  
**Next Review**: April 2025