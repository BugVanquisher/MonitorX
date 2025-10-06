# MonitorX Deployment Guide

## Overview

This guide covers deploying MonitorX in production environments, including infrastructure setup, configuration, security, and scaling considerations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Configuration](#configuration)
5. [Security](#security)
6. [Scaling](#scaling)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB
- Python: 3.9+
- Docker (optional, but recommended)

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB+ (depends on metric retention)
- Python: 3.10+
- Docker + Docker Compose

### Dependencies

- InfluxDB 2.7+
- Python 3.9+
- Network access for alerting (SMTP, Slack webhooks)

---

## Quick Start

### Using Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
      - DOCKER_INFLUXDB_INIT_ORG=monitorx
      - DOCKER_INFLUXDB_INIT_BUCKET=metrics
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}
    volumes:
      - influxdb-data:/var/lib/influxdb2
      - influxdb-config:/etc/influxdb2
    restart: unless-stopped

  monitorx-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
      - INFLUXDB_ORG=monitorx
      - INFLUXDB_BUCKET=metrics
      - API_HOST=0.0.0.0
      - API_PORT=8000
    depends_on:
      - influxdb
    restart: unless-stopped
    command: uvicorn monitorx.server:app --host 0.0.0.0 --port 8000

  monitorx-dashboard:
    build: .
    ports:
      - "8501:8501"
    environment:
      - API_HOST=monitorx-api
      - API_PORT=8000
    depends_on:
      - monitorx-api
    restart: unless-stopped
    command: streamlit run src/monitorx/dashboard/app.py --server.port 8501

volumes:
  influxdb-data:
  influxdb-config:
```

Start services:

```bash
# Set environment variables
export INFLUXDB_PASSWORD="your-secure-password"
export INFLUXDB_TOKEN="your-influxdb-token"

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f monitorx-api
```

### Manual Installation

```bash
# 1. Install InfluxDB
# See: https://docs.influxdata.com/influxdb/v2.7/install/

# 2. Clone and install MonitorX
git clone https://github.com/your-org/monitorx.git
cd monitorx
pip install -e .

# 3. Configure environment
cp .env.example .env
# Edit .env with your settings

# 4. Start API server
python -m monitorx.server

# 5. Start dashboard (in another terminal)
streamlit run src/monitorx/dashboard/app.py
```

---

## Infrastructure Setup

### InfluxDB Configuration

#### Initial Setup

```bash
# Using Docker
docker run -d --name influxdb \
  -p 8086:8086 \
  -e DOCKER_INFLUXDB_INIT_MODE=setup \
  -e DOCKER_INFLUXDB_INIT_USERNAME=admin \
  -e DOCKER_INFLUXDB_INIT_PASSWORD=your-password \
  -e DOCKER_INFLUXDB_INIT_ORG=monitorx \
  -e DOCKER_INFLUXDB_INIT_BUCKET=metrics \
  -e DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=your-token \
  -v influxdb-data:/var/lib/influxdb2 \
  influxdb:2.7
```

#### Create API Token

```bash
# Access InfluxDB UI
open http://localhost:8086

# Or use CLI
influx auth create \
  --org monitorx \
  --all-access \
  --description "MonitorX API Token"
```

#### Data Retention Policy

```bash
# Set retention period (e.g., 30 days)
influx bucket update \
  --name metrics \
  --retention 720h
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name monitorx.yourcompany.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name monitorx.yourcompany.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Dashboard
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # InfluxDB (optional, if exposing)
    location /influxdb {
        proxy_pass http://localhost:8086;
        proxy_set_header Host $host;
    }
}
```

---

## Configuration

### Environment Variables

#### Core Settings

```bash
# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=monitorx
INFLUXDB_BUCKET=metrics

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO

# Dashboard Configuration
DASHBOARD_PORT=8501
```

#### Alert Configuration

```bash
# Email Alerts
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourcompany.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=monitorx@yourcompany.com
ALERT_TO_EMAILS=team@yourcompany.com,oncall@yourcompany.com

# Slack Alerts
ENABLE_SLACK_ALERTS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
SLACK_CHANNEL=#ml-alerts

# Webhook Alerts
ENABLE_WEBHOOK_ALERTS=true
WEBHOOK_URL=https://api.yourcompany.com/alerts
WEBHOOK_API_KEY=your-api-key
```

### Configuration Files

Create `config/production.py`:

```python
from pydantic_settings import BaseSettings

class ProductionConfig(BaseSettings):
    # InfluxDB
    influxdb_url: str
    influxdb_token: str
    influxdb_org: str = "monitorx"
    influxdb_bucket: str = "metrics"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # Security
    api_key_enabled: bool = True
    allowed_origins: list[str] = ["https://yourcompany.com"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    class Config:
        env_file = ".env.production"
```

---

## Security

### API Authentication

#### API Key Authentication

```python
# src/monitorx/auth.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify API key."""
    valid_keys = os.getenv("API_KEYS", "").split(",")
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key
```

Update routes:

```python
from .auth import verify_api_key

@router.post("/metrics/inference", dependencies=[Depends(verify_api_key)])
async def collect_inference_metric(metric_data: InferenceMetricRequest):
    # ...
```

#### JWT Authentication (Advanced)

```python
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourcompany.com",
        "https://dashboard.yourcompany.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
)
```

### HTTPS/TLS

Always use HTTPS in production:

1. **Using Nginx** (recommended): Configure SSL in reverse proxy
2. **Using Uvicorn**:
   ```bash
   uvicorn monitorx.server:app \
     --host 0.0.0.0 \
     --port 8000 \
     --ssl-keyfile /path/to/key.pem \
     --ssl-certfile /path/to/cert.pem
   ```

### Secrets Management

#### Using Environment Variables

```bash
# Never commit .env files
echo ".env*" >> .gitignore

# Use separate files per environment
.env.development
.env.staging
.env.production
```

#### Using Secrets Manager (AWS)

```python
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-west-2')
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e
```

#### Using HashiCorp Vault

```python
import hvac

client = hvac.Client(url='http://vault:8200', token='your-token')
secret = client.secrets.kv.v2.read_secret_version(path='monitorx')
```

---

## Scaling

### Horizontal Scaling

#### API Servers

Run multiple API instances behind a load balancer:

```yaml
# docker-compose.yml
services:
  monitorx-api-1:
    build: .
    environment:
      - INSTANCE_ID=1
    # ...

  monitorx-api-2:
    build: .
    environment:
      - INSTANCE_ID=2
    # ...

  nginx:
    image: nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - monitorx-api-1
      - monitorx-api-2
```

Nginx load balancing:

```nginx
upstream monitorx_api {
    least_conn;
    server monitorx-api-1:8000;
    server monitorx-api-2:8000;
}

server {
    location /api {
        proxy_pass http://monitorx_api;
    }
}
```

### InfluxDB Scaling

#### Clustering

For high-write workloads, use InfluxDB Enterprise or InfluxDB Cloud.

#### Retention Policies

```python
# Downsample old data
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url=url, token=token, org=org)

# Create downsampled bucket for long-term storage
downsampled_query = '''
from(bucket: "metrics")
  |> range(start: -7d, stop: -1d)
  |> aggregateWindow(every: 1h, fn: mean)
  |> to(bucket: "metrics_hourly")
'''
```

### Caching

#### Redis for Metrics Cache

```python
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_metrics(ttl=300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"metrics:{args}:{kwargs}"
            cached = redis_client.get(cache_key)

            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator
```

---

## Monitoring

### Application Monitoring

#### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
requests_total = Counter('monitorx_requests_total', 'Total requests')
request_duration = Histogram('monitorx_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def add_prometheus_metrics(request, call_next):
    with request_duration.time():
        response = await call_next(request)
    requests_total.inc()
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

#### Health Checks

```python
@app.get("/health/liveness")
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}

@app.get("/health/readiness")
async def readiness():
    """Kubernetes readiness probe."""
    try:
        # Check InfluxDB connection
        health = await storage.client.health()
        if health.status != "pass":
            raise HTTPException(status_code=503, detail="InfluxDB unhealthy")
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")
```

### Logging

```python
from loguru import logger
import sys

# Configure structured logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    serialize=True  # JSON output
)

# Log to file with rotation
logger.add(
    "/var/log/monitorx/api.log",
    rotation="100 MB",
    retention="30 days",
    compression="gz"
)
```

---

## Troubleshooting

### Common Issues

#### InfluxDB Connection Failed

**Symptoms:** `Failed to connect to InfluxDB` errors

**Solutions:**
```bash
# Check InfluxDB is running
curl http://localhost:8086/health

# Verify token
influx auth list

# Check network connectivity
docker-compose logs influxdb
```

#### High Memory Usage

**Symptoms:** API server using excessive memory

**Solutions:**
```python
# Limit metrics collector cache size
metrics_collector = MetricsCollector(max_metrics=5000)

# Implement cleanup task
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', hours=1)
def cleanup_old_metrics():
    metrics_collector.cleanup_old_metrics(hours=24)
```

#### Alert Delivery Failures

**Symptoms:** Alerts not being sent

**Solutions:**
```bash
# Test alert channels
python -c "
from monitorx.services.alerting import AlertingService
import asyncio

alerting = AlertingService()
# Configure channels...
results = asyncio.run(alerting.test_channels())
print(results)
"

# Check SMTP settings
# Check Slack webhook URL
# Verify network connectivity
```

### Performance Tuning

```python
# Increase worker processes
uvicorn monitorx.server:app --workers 4

# Adjust timeouts
uvicorn monitorx.server:app --timeout-keep-alive 30

# Enable gzip compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## Production Checklist

- [ ] InfluxDB properly secured and backed up
- [ ] HTTPS/TLS enabled
- [ ] API authentication implemented
- [ ] CORS configured for production domains
- [ ] Secrets stored securely (not in code)
- [ ] Logging configured and rotated
- [ ] Monitoring and alerting set up
- [ ] Health checks configured
- [ ] Backup strategy implemented
- [ ] Rate limiting enabled
- [ ] Load balancer configured (if scaled)
- [ ] Documentation updated

---

## Next Steps

- [API Documentation](API.md)
- [Alerting Guide](ALERTING.md)
- [Architecture Overview](ARCHITECTURE.md)
- [SDK Documentation](SDK.md)
