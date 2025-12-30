# 🚀 JANUS-AI Deployment Guide

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Government Integration](#government-integration)
6. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Local Development Setup

### Step 1: Environment Setup

```bash
# Create virtual environment
python -m venv janus-env

# Activate environment
# On Linux/Mac:
source janus-env/bin/activate
# On Windows:
janus-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Run System

```bash
# Run complete pipeline
python main_pipeline.py

# Launch dashboard
streamlit run dashboard_app.py
```

### Step 3: Verify Installation

```bash
# Test data generation
python data_generator.py

# Test individual modules
python financial_anomaly_detector.py
python network_collusion_detector.py
```

---

## Production Deployment

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                         │
└────────────┬────────────────────────────────────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────┐      ┌───▼─────┐
│ Web App │      │   API   │
│ (Dash)  │      │ Service │
└────┬────┘      └────┬────┘
     │                │
     └───────┬────────┘
             │
┌────────────▼──────────────┐
│   Processing Queue        │
│   (Celery + Redis)        │
└────────────┬──────────────┘
             │
     ┌───────┴────────┐
     │                │
┌────▼────┐      ┌───▼─────┐
│ Worker  │      │ Worker  │
│ Node 1  │      │ Node 2  │
└────┬────┘      └────┬────┘
     │                │
     └───────┬────────┘
             │
┌────────────▼──────────────┐
│   Database Cluster        │
│   (PostgreSQL/MongoDB)    │
└───────────────────────────┘
```

### Step 1: Database Setup

**PostgreSQL Schema**

```sql
-- Transactions table
CREATE TABLE transactions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    date TIMESTAMP NOT NULL,
    department VARCHAR(100),
    vendor_id VARCHAR(50),
    official_id VARCHAR(50),
    amount DECIMAL(15, 2),
    category VARCHAR(100),
    payment_mode VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fraud scores table
CREATE TABLE fraud_scores (
    transaction_id VARCHAR(50) PRIMARY KEY,
    financial_score DECIMAL(5, 2),
    temporal_score DECIMAL(5, 2),
    network_score DECIMAL(5, 2),
    nlp_score DECIMAL(5, 2),
    citizen_score DECIMAL(5, 2),
    meta_score DECIMAL(5, 2),
    risk_level VARCHAR(20),
    investigation_priority DECIMAL(5, 2),
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
);

-- Audit trail table
CREATE TABLE audit_trail (
    audit_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50),
    action VARCHAR(100),
    user_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

-- Indexes for performance
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_vendor ON transactions(vendor_id);
CREATE INDEX idx_fraud_scores_risk ON fraud_scores(risk_level);
CREATE INDEX idx_fraud_scores_meta ON fraud_scores(meta_score);
```

### Step 2: Configuration

**config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost/janusai')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-production')
    API_KEY = os.getenv('API_KEY', 'change-me-in-production')
    
    # Module weights
    MODULE_WEIGHTS = {
        'financial': 0.25,
        'temporal': 0.20,
        'network': 0.25,
        'nlp': 0.15,
        'citizen': 0.15
    }
    
    # Risk thresholds
    RISK_THRESHOLDS = {
        'low': 30,
        'medium': 50,
        'high': 70,
        'critical': 85
    }
    
    # Processing
    BATCH_SIZE = 1000
    MAX_WORKERS = 4
```

### Step 3: API Service

**api_service.py**

```python
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required
import pandas as pd

app = Flask(__name__)
app.config.from_object('config.Config')

jwt = JWTManager(app)

@app.route('/api/v1/analyze', methods=['POST'])
@jwt_required()
def analyze_transaction():
    """Analyze a single transaction"""
    data = request.get_json()
    
    # Run fraud detection pipeline
    result = run_fraud_detection(data)
    
    return jsonify(result), 200

@app.route('/api/v1/batch', methods=['POST'])
@jwt_required()
def analyze_batch():
    """Analyze batch of transactions"""
    transactions = request.get_json()['transactions']
    
    # Queue batch processing
    task = process_batch.delay(transactions)
    
    return jsonify({
        'task_id': task.id,
        'status': 'queued'
    }), 202

@app.route('/api/v1/status/<task_id>', methods=['GET'])
@jwt_required()
def check_status(task_id):
    """Check processing status"""
    task = celery.AsyncResult(task_id)
    
    return jsonify({
        'task_id': task_id,
        'status': task.state,
        'result': task.result if task.ready() else None
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create reports directory
RUN mkdir -p reports

# Expose ports
EXPOSE 8501 5000

# Run application
CMD ["streamlit", "run", "dashboard_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: janusai
      POSTGRES_USER: janususer
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  web:
    build: .
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://janususer:secure_password@postgres/janusai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./reports:/app/reports

  api:
    build: .
    command: python api_service.py
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://janususer:secure_password@postgres/janusai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  worker:
    build: .
    command: celery -A tasks worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://janususer:secure_password@postgres/janusai
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### Run with Docker

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Cloud Deployment

### AWS Deployment

**Architecture**

```
Internet → ALB → ECS Fargate Cluster
                  ├─ Dashboard Containers
                  ├─ API Containers
                  └─ Worker Containers
                       ↓
                  RDS PostgreSQL
                  ElastiCache Redis
                  S3 (Reports)
```

**Deployment Steps**

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name janus-ai

# 2. Build and push image
docker build -t janus-ai .
docker tag janus-ai:latest <account-id>.dkr.ecr.<region>.amazonaws.com/janus-ai:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/janus-ai:latest

# 3. Create ECS cluster
aws ecs create-cluster --cluster-name janus-ai-cluster

# 4. Deploy using CloudFormation/Terraform
terraform apply
```

### Azure Deployment

```bash
# 1. Create resource group
az group create --name janus-ai-rg --location eastus

# 2. Create container registry
az acr create --resource-group janus-ai-rg --name janusai --sku Basic

# 3. Build and push
az acr build --registry janusai --image janus-ai:latest .

# 4. Deploy to AKS
kubectl apply -f kubernetes/
```

### GCP Deployment

```bash
# 1. Create GKE cluster
gcloud container clusters create janus-ai-cluster

# 2. Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/janus-ai

# 3. Deploy
kubectl apply -f kubernetes/
```

---

## Government Integration

### Integration Points

**1. Financial Management System**

```python
# Connector for government FMS
class FMSConnector:
    def fetch_transactions(self, start_date, end_date):
        """Fetch transactions from FMS"""
        # Connect to government FMS API
        response = requests.post(
            f"{FMS_API_URL}/transactions",
            headers={'Authorization': f'Bearer {FMS_API_KEY}'},
            json={'start_date': start_date, 'end_date': end_date}
        )
        return pd.DataFrame(response.json())
```

**2. E-Procurement Portal**

```python
# Connector for tender documents
class EProcurementConnector:
    def fetch_tenders(self, start_date, end_date):
        """Fetch tenders from e-procurement"""
        response = requests.get(
            f"{EPROCUREMENT_URL}/api/tenders",
            params={'from': start_date, 'to': end_date}
        )
        return pd.DataFrame(response.json())
```

**3. Citizen Feedback Portal**

```python
# Connector for citizen complaints
class FeedbackConnector:
    def fetch_feedback(self, department=None):
        """Fetch citizen feedback"""
        response = requests.get(
            f"{FEEDBACK_PORTAL_URL}/api/complaints",
            params={'department': department}
        )
        return pd.DataFrame(response.json())
```

### Security Considerations

**Authentication & Authorization**

```python
from flask_jwt_extended import create_access_token

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # Verify against government AD/LDAP
    if verify_credentials(username, password):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    
    return jsonify({"msg": "Bad credentials"}), 401
```

**Audit Logging**

```python
def log_action(user_id, action, transaction_id, details):
    """Log all user actions"""
    audit_entry = {
        'user_id': user_id,
        'action': action,
        'transaction_id': transaction_id,
        'details': details,
        'timestamp': datetime.now(),
        'ip_address': request.remote_addr
    }
    
    db.audit_trail.insert_one(audit_entry)
```

---

## Monitoring & Maintenance

### Application Monitoring

**Prometheus Metrics**

```python
from prometheus_client import Counter, Histogram

# Metrics
transactions_processed = Counter('transactions_processed_total', 'Total transactions processed')
fraud_cases_detected = Counter('fraud_cases_detected_total', 'Total fraud cases detected')
processing_time = Histogram('processing_time_seconds', 'Time to process transaction')

# Use in code
with processing_time.time():
    result = detect_fraud(transaction)
    transactions_processed.inc()
    if result['is_fraud']:
        fraud_cases_detected.inc()
```

### Health Checks

```python
@app.route('/health')
def health():
    """System health check"""
    return jsonify({
        'status': 'healthy',
        'database': check_database(),
        'redis': check_redis(),
        'workers': check_workers()
    })
```

### Backup Strategy

```bash
# Daily database backup
0 2 * * * pg_dump janusai | gzip > /backups/janusai-$(date +\%Y\%m\%d).sql.gz

# Weekly full backup
0 3 * * 0 tar -czf /backups/janus-ai-full-$(date +\%Y\%m\%d).tar.gz /app

# Retention: 30 days
find /backups -type f -mtime +30 -delete
```

### Performance Tuning

**Database Optimization**

```sql
-- Analyze and vacuum
ANALYZE transactions;
VACUUM ANALYZE fraud_scores;

-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_transactions_dept_date 
ON transactions(department, date);
```

**Application Tuning**

```python
# Configure connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40
)

# Batch processing optimization
BATCH_SIZE = 1000
for i in range(0, len(transactions), BATCH_SIZE):
    batch = transactions[i:i+BATCH_SIZE]
    process_batch(batch)
```

---

## Troubleshooting

### Common Issues

**Issue: High memory usage**
```bash
# Solution: Increase batch processing size
# In config.py, reduce BATCH_SIZE from 1000 to 500
```

**Issue: Slow graph analysis**
```bash
# Solution: Sample large networks
# In network_collusion_detector.py, add sampling logic
if len(graph.nodes()) > 10000:
    graph = sample_graph(graph, max_nodes=10000)
```

**Issue: Dashboard timeout**
```bash
# Solution: Add caching
# In dashboard_app.py, use @st.cache_data more aggressively
```

---

## Production Checklist

- [ ] Environment variables configured
- [ ] Database schema created
- [ ] SSL/TLS certificates installed
- [ ] Firewall rules configured
- [ ] Backup strategy implemented
- [ ] Monitoring dashboards set up
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation updated
- [ ] Team trained on system

---

## Support

For deployment assistance:
- Technical Documentation: [Wiki](https://github.com/your-org/janus-ai/wiki)
- Issues: [GitHub Issues](https://github.com/your-org/janus-ai/issues)
- Email: support@janus-ai.gov

---

**Last Updated**: December 2024
