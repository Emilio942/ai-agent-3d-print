# AI Agent 3D Print System - Deployment Guide

## Overview

This guide covers deploying the AI Agent 3D Print System in production environments, including containerization, orchestration, monitoring, and maintenance procedures.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Configuration Management](#configuration-management)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Load Balancing](#load-balancing)
7. [Database Setup](#database-setup)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Security](#security)
10. [Backup and Recovery](#backup-and-recovery)
11. [Scaling](#scaling)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores, 2.5 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **OS**: Ubuntu 20.04 LTS or newer, CentOS 8+, or Debian 11+

#### Recommended Requirements
- **CPU**: 8 cores, 3.0 GHz
- **RAM**: 16 GB
- **Storage**: 100 GB NVMe SSD
- **OS**: Ubuntu 22.04 LTS

#### For CAD Operations
- **GPU**: Optional but recommended for complex CAD operations
- **Additional Storage**: 200+ GB for model files and cache

### Software Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv python3.12-dev

# Install system dependencies
sudo apt install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    unzip \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxrender1 \
    libxext6 \
    libxft2 \
    libxss1

# Install FreeCAD
sudo apt install freecad-python3

# Install PrusaSlicer (if using)
wget -O - https://get.prusa3d.com/linux | sudo bash
```

## Environment Setup

### 1. Create System User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash ai3dprint
sudo usermod -aG sudo ai3dprint

# Switch to user
sudo su - ai3dprint
```

### 2. Setup Python Environment

```bash
# Create virtual environment
python3.12 -m venv /home/ai3dprint/venv
source /home/ai3dprint/venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 3. Clone and Install Application

```bash
# Clone repository
cd /home/ai3dprint
git clone https://github.com/your-org/ai-agent-3d-print.git
cd ai-agent-3d-print

# Install dependencies
pip install -r requirements.txt

# Install additional production dependencies
pip install gunicorn redis prometheus-client
```

## Configuration Management

### 1. Environment-Specific Configuration

Create production configuration:

```bash
# Copy production config template
cp config/production.yaml.example config/production.yaml

# Edit configuration
nano config/production.yaml
```

### 2. Environment Variables

Create environment file:

```bash
# Create .env file
cat > /home/ai3dprint/ai-agent-3d-print/.env << 'EOF'
# Application
APP_ENVIRONMENT=production
APP_DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://ai3dprint:secure_password@localhost:5432/ai_3d_print_prod

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your-super-secure-jwt-secret-key-change-this
API_KEY=your-api-key-for-authentication

# Hardware paths
PRINTER_PORT=/dev/ttyUSB0
SLICER_PATH=/usr/bin/prusa-slicer

# Monitoring
PROMETHEUS_ENABLED=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

# Backup
BACKUP_S3_BUCKET=ai3dprint-backups
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
EOF

# Secure the file
chmod 600 .env
```

### 3. SSL Certificates

```bash
# Create SSL directory
sudo mkdir -p /etc/ssl/ai3dprint

# Generate self-signed certificate (for testing)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/ai3dprint/ai_3d_print.key \
    -out /etc/ssl/ai3dprint/ai_3d_print.crt

# Or use Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d api.your-domain.com
```

## Docker Deployment

### 1. Create Dockerfile

```dockerfile
# Production Dockerfile
FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    freecad-python3 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set ownership
RUN chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "start_api_production.py"]
```

### 2. Docker Compose Setup

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: .
    container_name: ai3dprint-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - APP_ENVIRONMENT=production
      - DATABASE_URL=postgresql://ai3dprint:${DB_PASSWORD}@db:5432/ai_3d_print_prod
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - /dev/ttyUSB0:/dev/ttyUSB0  # Printer connection
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    networks:
      - ai3dprint-network

  db:
    image: postgres:15-alpine
    container_name: ai3dprint-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=ai_3d_print_prod
      - POSTGRES_USER=ai3dprint
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - ai3dprint-network

  redis:
    image: redis:7-alpine
    container_name: ai3dprint-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - ai3dprint-network

  nginx:
    image: nginx:alpine
    container_name: ai3dprint-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/ai3dprint
    depends_on:
      - api
    networks:
      - ai3dprint-network

  prometheus:
    image: prom/prometheus:latest
    container_name: ai3dprint-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - ai3dprint-network

  grafana:
    image: grafana/grafana:latest
    container_name: ai3dprint-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - ai3dprint-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  ai3dprint-network:
    driver: bridge
```

### 3. Deploy with Docker Compose

```bash
# Create environment file
echo "DB_PASSWORD=secure_db_password" > .env
echo "GRAFANA_PASSWORD=secure_grafana_password" >> .env

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f api

# Scale API service
docker-compose -f docker-compose.prod.yml up -d --scale api=3
```

## Kubernetes Deployment

### 1. Namespace and ConfigMaps

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai3dprint

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ai3dprint-config
  namespace: ai3dprint
data:
  APP_ENVIRONMENT: "production"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  PROMETHEUS_ENABLED: "true"
```

### 2. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ai3dprint-secrets
  namespace: ai3dprint
type: Opaque
data:
  database-url: cG9zdGdyZXNxbDovL2FpM2RwcmludDpwYXNzd29yZEBkYi01NDMyL2FpXzNkX3ByaW50X3Byb2Q=
  jwt-secret: eW91ci1zdXBlci1zZWN1cmUtand0LXNlY3JldA==
  api-key: eW91ci1hcGkta2V5
```

### 3. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai3dprint-api
  namespace: ai3dprint
  labels:
    app: ai3dprint-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai3dprint-api
  template:
    metadata:
      labels:
        app: ai3dprint-api
    spec:
      containers:
      - name: api
        image: ai3dprint:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: ai3dprint-secrets
              key: database-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: ai3dprint-secrets
              key: jwt-secret
        envFrom:
        - configMapRef:
            name: ai3dprint-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: ai3dprint-data-pvc
      - name: logs-volume
        persistentVolumeClaim:
          claimName: ai3dprint-logs-pvc
```

### 4. Services and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ai3dprint-api-service
  namespace: ai3dprint
spec:
  selector:
    app: ai3dprint-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ai3dprint-ingress
  namespace: ai3dprint
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.your-domain.com
    secretName: ai3dprint-tls
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ai3dprint-api-service
            port:
              number: 80
```

### 5. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment
kubectl get pods -n ai3dprint
kubectl logs -f deployment/ai3dprint-api -n ai3dprint

# Scale deployment
kubectl scale deployment ai3dprint-api --replicas=5 -n ai3dprint
```

## Database Setup

### PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE ai_3d_print_prod;
CREATE USER ai3dprint WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_3d_print_prod TO ai3dprint;
ALTER USER ai3dprint CREATEDB;
\q
EOF

# Configure PostgreSQL
sudo nano /etc/postgresql/14/main/postgresql.conf
# Set: shared_preload_libraries = 'pg_stat_statements'
# Set: max_connections = 200

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Add: host ai_3d_print_prod ai3dprint 127.0.0.1/32 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Redis Setup

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Set: maxmemory 1gb
# Set: maxmemory-policy allkeys-lru

# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## Monitoring and Logging

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "ai3dprint_rules.yml"

scrape_configs:
  - job_name: 'ai3dprint-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['localhost:9187']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. Grafana Dashboards

```json
{
  "dashboard": {
    "title": "AI 3D Print System",
    "panels": [
      {
        "title": "Active Workflows",
        "type": "stat",
        "targets": [
          {
            "expr": "ai3d_active_workflows",
            "refId": "A"
          }
        ]
      },
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])",
            "refId": "A"
          }
        ]
      },
      {
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by (instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "refId": "CPU"
          },
          {
            "expr": "(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100",
            "refId": "Memory"
          }
        ]
      }
    ]
  }
}
```

### 3. Log Aggregation

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /home/ai3dprint/ai-agent-3d-print/logs/*.log
  json.keys_under_root: true
  json.message_key: message

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "ai3dprint-logs-%{+yyyy.MM.dd}"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
```

## Security

### 1. Firewall Configuration

```bash
# Configure UFW
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API (if direct access needed)
sudo ufw allow 8000/tcp

# Allow monitoring
sudo ufw allow from 10.0.0.0/8 to any port 9090
```

### 2. SSL/TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/ssl/ai3dprint/ai_3d_print.crt;
    ssl_certificate_key /etc/ssl/ai3dprint/ai_3d_print.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 3. Security Headers

```python
# Add to FastAPI app
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.your-domain.com"])
app.add_middleware(HTTPSRedirectMiddleware)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

## Backup and Recovery

### 1. Database Backup

```bash
#!/bin/bash
# backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ai3dprint/backups"
DB_NAME="ai_3d_print_prod"
DB_USER="ai3dprint"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME -f $BACKUP_DIR/db_backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/db_backup_$DATE.sql

# Upload to S3 (if configured)
if [ ! -z "$BACKUP_S3_BUCKET" ]; then
    aws s3 cp $BACKUP_DIR/db_backup_$DATE.sql.gz s3://$BACKUP_S3_BUCKET/database/
fi

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: db_backup_$DATE.sql.gz"
```

### 2. Application Data Backup

```bash
#!/bin/bash
# backup_data.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/ai3dprint/backups"
APP_DIR="/home/ai3dprint/ai-agent-3d-print"

# Backup data directory
tar -czf $BACKUP_DIR/data_backup_$DATE.tar.gz -C $APP_DIR data/

# Backup logs
tar -czf $BACKUP_DIR/logs_backup_$DATE.tar.gz -C $APP_DIR logs/

# Backup configuration
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz -C $APP_DIR config/

# Upload to S3
if [ ! -z "$BACKUP_S3_BUCKET" ]; then
    aws s3 cp $BACKUP_DIR/data_backup_$DATE.tar.gz s3://$BACKUP_S3_BUCKET/data/
    aws s3 cp $BACKUP_DIR/logs_backup_$DATE.tar.gz s3://$BACKUP_S3_BUCKET/logs/
    aws s3 cp $BACKUP_DIR/config_backup_$DATE.tar.gz s3://$BACKUP_S3_BUCKET/config/
fi

echo "Data backup completed"
```

### 3. Automated Backup Cron

```bash
# Add to crontab
crontab -e

# Database backup every 6 hours
0 */6 * * * /home/ai3dprint/scripts/backup_db.sh

# Data backup daily at 2 AM
0 2 * * * /home/ai3dprint/scripts/backup_data.sh

# Health check every minute
* * * * * curl -f http://localhost:8000/health || echo "Health check failed at $(date)" >> /var/log/ai3dprint_health.log
```

## Scaling

### 1. Horizontal Scaling

```bash
# Docker Compose scaling
docker-compose -f docker-compose.prod.yml up -d --scale api=5

# Kubernetes scaling
kubectl scale deployment ai3dprint-api --replicas=5 -n ai3dprint

# Auto-scaling in Kubernetes
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai3dprint-api-hpa
  namespace: ai3dprint
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai3dprint-api
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
EOF
```

### 2. Load Balancer Configuration

```nginx
# nginx.conf for load balancing
upstream ai3dprint_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8003 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://ai3dprint_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }
    
    location /health {
        access_log off;
        proxy_pass http://ai3dprint_backend;
    }
}
```

## Troubleshooting

### 1. Common Issues

#### Application Won't Start
```bash
# Check logs
tail -f logs/api.log

# Check system resources
htop
df -h

# Check dependencies
python -c "import FreeCAD"
python -c "import spacy"

# Check configuration
python -c "from config.settings import load_config; print(load_config())"
```

#### Database Connection Issues
```bash
# Test database connection
psql -h localhost -U ai3dprint -d ai_3d_print_prod -c "SELECT version();"

# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection limits
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"
```

#### High Memory Usage
```bash
# Monitor memory usage
watch -n 1 'free -h'

# Check process memory
ps aux --sort=-%mem | head -10

# Check for memory leaks
python -m memray run --live start_api_production.py
```

### 2. Performance Tuning

#### Database Optimization
```sql
-- Analyze slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Create indexes
CREATE INDEX idx_workflows_status ON workflows(status);
CREATE INDEX idx_workflows_created_at ON workflows(created_at);

-- Update statistics
ANALYZE;
```

#### API Optimization
```python
# Add to production config
{
    "api": {
        "workers": 4,
        "worker_connections": 1000,
        "keepalive": 2,
        "max_requests": 1000,
        "max_requests_jitter": 50
    }
}
```

### 3. Emergency Procedures

#### Service Recovery
```bash
#!/bin/bash
# emergency_restart.sh

echo "Performing emergency restart..."

# Stop services
docker-compose -f docker-compose.prod.yml down

# Clean up
docker system prune -f

# Restart services
docker-compose -f docker-compose.prod.yml up -d

# Wait for health check
sleep 30
curl -f http://localhost:8000/health || exit 1

echo "Emergency restart completed"
```

#### Data Recovery
```bash
#!/bin/bash
# restore_backup.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
docker-compose -f docker-compose.prod.yml stop api

# Restore database
gunzip -c $BACKUP_FILE | psql -h localhost -U ai3dprint -d ai_3d_print_prod

# Restart application
docker-compose -f docker-compose.prod.yml start api

echo "Data restoration completed"
```

## Maintenance

### 1. Regular Maintenance Tasks

```bash
#!/bin/bash
# maintenance.sh

echo "Starting maintenance tasks..."

# Update packages
sudo apt update && sudo apt upgrade -y

# Clean up logs
find /home/ai3dprint/ai-agent-3d-print/logs -name "*.log" -mtime +7 -delete

# Clean up temporary files
find /home/ai3dprint/ai-agent-3d-print/data/temp -type f -mtime +1 -delete

# Restart services to clear memory
docker-compose -f docker-compose.prod.yml restart

# Check disk space
df -h

# Check system health
curl -s http://localhost:8000/health/detailed | jq .

echo "Maintenance completed"
```

### 2. Security Updates

```bash
#!/bin/bash
# security_update.sh

# Update system packages
sudo apt update
sudo apt list --upgradable

# Update Python packages
pip list --outdated
pip install --upgrade -r requirements.txt

# Scan for vulnerabilities
pip-audit

# Update Docker images
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Monitoring and Alerts

Set up monitoring checks:

```bash
# Health monitoring script
#!/bin/bash
# monitor_health.sh

API_URL="http://localhost:8000/health"
SLACK_WEBHOOK="$ALERT_WEBHOOK_URL"

HEALTH=$(curl -s $API_URL | jq -r .status)

if [ "$HEALTH" != "healthy" ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"🚨 AI 3D Print System is $HEALTH\"}" \
        $SLACK_WEBHOOK
fi
```

Add to crontab:
```bash
# Monitor every 5 minutes
*/5 * * * * /home/ai3dprint/scripts/monitor_health.sh
```

This deployment guide provides comprehensive instructions for production deployment of the AI Agent 3D Print System with high availability, monitoring, security, and scalability considerations.
