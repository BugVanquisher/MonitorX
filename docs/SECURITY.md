# MonitorX Security Guide

## Overview

This guide covers security features, best practices, and configuration for production deployments of MonitorX.

## Authentication

### API Key Authentication

Simple and effective for machine-to-machine communication.

#### Setup

```bash
# .env
API_KEY_ENABLED=true
API_KEYS=key1-your-secret-key,key2-another-key,key3-third-key
```

#### Usage

```python
# Python SDK
client = MonitorXClient(
    base_url="http://localhost:8000",
    api_key="key1-your-secret-key"
)
```

```bash
# cURL
curl -H "X-API-Key: key1-your-secret-key" \
  http://localhost:8000/api/v1/models
```

#### Generating Secure API Keys

```python
import secrets

# Generate a secure random API key
api_key = secrets.token_urlsafe(32)
print(f"Generated API Key: {api_key}")
```

#### Best Practices

- Use long, random keys (32+ characters)
- Rotate keys regularly (quarterly recommended)
- Use different keys per environment (dev/staging/prod)
- Never commit keys to version control
- Store keys in secrets manager (AWS Secrets Manager, HashiCorp Vault)

### JWT Authentication

Token-based authentication for user-facing applications.

####Setup

```bash
# .env
JWT_ENABLED=true
JWT_SECRET_KEY=your-very-long-random-secret-key-min-32-chars
JWT_EXPIRE_MINUTES=30
```

#### Generating Secret Key

```python
import secrets

# Generate a secure secret key
secret = secrets.token_urlsafe(64)
print(f"JWT Secret: {secret}")
```

#### Usage Example

```python
from monitorx.auth import jwt_auth

# Create token
token = jwt_auth.create_access_token(
    data={"sub": "user@example.com", "scopes": ["read", "write"]}
)

# Use token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8000/api/v1/models", headers=headers)
```

#### Token Scopes

Available scopes:
- `read` - Read access to metrics and models
- `write` - Write access to submit metrics
- `admin` - Full administrative access
- `*` - Wildcard (all scopes)

### Combining Authentication Methods

You can enable both API key and JWT authentication:

```python
# API key for services
API_KEY_ENABLED=true

# JWT for user dashboards
JWT_ENABLED=true
```

---

## Rate Limiting

Protect your API from abuse and ensure fair usage.

### Configuration

```bash
# .env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100    # requests per window
RATE_LIMIT_WINDOW=60       # window in seconds
```

### How It Works

- **Sliding Window**: Tracks requests over a rolling time window
- **Per Client**: Limits applied per API key or IP address
- **Headers**: Returns rate limit info in response headers

### Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1634567890
```

### Rate Limit Exceeded Response

```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "limit": 100,
    "window": "60s",
    "retry_after": 45
  }
}
```

**Status Code**: 429 Too Many Requests
**Retry-After Header**: Seconds until limit resets

### Customizing Rate Limits

Different limits for different clients:

```python
# In production, use Redis for distributed rate limiting
from redis import Redis
from monitorx.middleware import TokenBucketRateLimiter

redis_client = Redis(host='localhost', port=6379)

# Custom rate limiter per API key
rate_limiters = {
    "premium-key": TokenBucketRateLimiter(rate=1000, capacity=1000),
    "standard-key": TokenBucketRateLimiter(rate=100, capacity=100),
}
```

---

## CORS Configuration

Control which domains can access your API.

### Development

```bash
CORS_ORIGINS=*
CORS_ALLOW_CREDENTIALS=true
```

### Production

```bash
CORS_ORIGINS=https://yourcompany.com,https://dashboard.yourcompany.com
CORS_ALLOW_CREDENTIALS=true
```

### Multiple Origins

Separate with commas:
```bash
CORS_ORIGINS=https://app.example.com,https://dashboard.example.com,https://admin.example.com
```

---

## HTTPS/TLS

**REQUIRED** for production deployments.

### Using Reverse Proxy (Recommended)

Configure Nginx with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name monitorx.yourcompany.com;

    ssl_certificate /etc/ssl/certs/monitorx.crt;
    ssl_certificate_key /etc/ssl/private/monitorx.key;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Using Uvicorn Directly

```bash
uvicorn monitorx.server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile /path/to/key.pem \
  --ssl-certfile /path/to/cert.pem
```

### Let's Encrypt (Free SSL)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d monitorx.yourcompany.com

# Auto-renewal (runs twice daily)
sudo systemctl enable certbot.timer
```

---

## Secrets Management

Never store secrets in code or version control.

### Environment Variables

```bash
# Good
export API_KEY=$(cat /run/secrets/monitorx_api_key)

# Bad
export API_KEY="hardcoded-key"  # Never do this!
```

### Docker Secrets

```yaml
# docker-compose.yml
services:
  monitorx-api:
    secrets:
      - influxdb_token
      - jwt_secret
    environment:
      - INFLUXDB_TOKEN_FILE=/run/secrets/influxdb_token

secrets:
  influxdb_token:
    file: ./secrets/influxdb_token.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

### AWS Secrets Manager

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

# Usage
os.environ['INFLUXDB_TOKEN'] = get_secret('monitorx/influxdb_token')
```

### HashiCorp Vault

```python
import hvac

client = hvac.Client(url='http://vault:8200')
client.token = os.getenv('VAULT_TOKEN')

# Read secret
secret = client.secrets.kv.v2.read_secret_version(path='monitorx/config')
influxdb_token = secret['data']['data']['influxdb_token']
```

---

## Security Headers

Add security headers to all responses:

```python
# Add to server.py
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# Force HTTPS in production
if os.getenv('ENV') == 'production':
    app.add_middleware(HTTPSRedirectMiddleware)

# Trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["monitorx.yourcompany.com", "*.yourcompany.com"]
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    return response
```

---

## Input Validation

FastAPI/Pydantic handle most validation, but additional checks:

```python
from pydantic import BaseModel, validator

class InferenceMetricRequest(BaseModel):
    model_id: str
    latency: float

    @validator('model_id')
    def validate_model_id(cls, v):
        # Prevent injection attacks
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Model ID must be alphanumeric')
        if len(v) > 100:
            raise ValueError('Model ID too long')
        return v

    @validator('latency')
    def validate_latency(cls, v):
        if v > 1_000_000:  # 1000 seconds
            raise ValueError('Latency value unrealistic')
        return v
```

---

## Audit Logging

Track all API access for security monitoring:

```python
import json
from datetime import datetime
from loguru import logger

@app.middleware("http")
async def audit_log(request, call_next):
    start_time = datetime.utcnow()

    # Get user/API key
    api_key = request.headers.get("X-API-Key", "anonymous")
    client_ip = request.client.host if request.client else "unknown"

    # Process request
    response = await call_next(request)

    # Log audit trail
    audit_data = {
        "timestamp": start_time.isoformat(),
        "method": request.method,
        "path": request.url.path,
        "client_ip": client_ip,
        "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "status_code": response.status_code,
        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
    }

    logger.info(f"AUDIT: {json.dumps(audit_data)}")

    return response
```

---

## Database Security

### InfluxDB

1. **Authentication**: Always enable auth in production
2. **Tokens**: Use read/write specific tokens
3. **Network**: Restrict to private network
4. **Encryption**: Enable TLS for connections

```bash
# Create limited token
influx auth create \
  --org monitorx \
  --read-bucket metrics \
  --write-bucket metrics \
  --description "MonitorX API Token"
```

### Connection Security

```python
from influxdb_client import InfluxDBClient

client = InfluxDBClient(
    url="https://influxdb:8086",  # Use HTTPS
    token=os.getenv("INFLUXDB_TOKEN"),
    org="monitorx",
    verify_ssl=True  # Verify SSL certificates
)
```

---

## Network Security

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct API access (use reverse proxy)
sudo ufw deny 8086/tcp   # Block direct InfluxDB access
sudo ufw enable
```

### VPC/Subnet Isolation

- Place InfluxDB in private subnet
- Only API server in public subnet
- Use security groups to restrict traffic

### Docker Network Isolation

```yaml
# docker-compose.yml
services:
  influxdb:
    networks:
      - backend  # Private network

  monitorx-api:
    networks:
      - backend
      - frontend  # Public network

networks:
  frontend:
  backend:
    internal: true  # No external access
```

---

## Vulnerability Scanning

### Dependency Scanning

```bash
# Install safety
pip install safety

# Check for known vulnerabilities
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

### Container Scanning

```bash
# Scan Docker image
docker scan monitorx:latest

# Or use Trivy
trivy image monitorx:latest
```

### Regular Updates

```bash
# Update dependencies
pip list --outdated
pip install --upgrade -r requirements.txt

# Rebuild Docker images
docker-compose build --no-cache
```

---

## Security Checklist

### Pre-Production
- [ ] API authentication enabled
- [ ] HTTPS/TLS configured
- [ ] Secrets in environment variables or secrets manager
- [ ] CORS configured for specific domains
- [ ] Rate limiting enabled
- [ ] Security headers added
- [ ] Audit logging configured
- [ ] InfluxDB authentication enabled
- [ ] Firewall rules configured
- [ ] Dependency vulnerabilities checked

### Production
- [ ] Strong JWT secret key (64+ chars)
- [ ] API keys rotated regularly
- [ ] SSL certificates valid and auto-renewing
- [ ] Monitoring for failed auth attempts
- [ ] Backup strategy for secrets
- [ ] Incident response plan
- [ ] Regular security audits
- [ ] Penetration testing completed

### Ongoing
- [ ] Monthly dependency updates
- [ ] Quarterly API key rotation
- [ ] Annual security review
- [ ] Monitor security advisories
- [ ] Review audit logs weekly

---

## Incident Response

### Suspected Compromise

1. **Immediate Actions**:
   - Disable compromised API keys
   - Review audit logs
   - Check for unauthorized access
   - Notify security team

2. **Investigation**:
   - Identify scope of breach
   - Review all access logs
   - Check for data exfiltration
   - Document timeline

3. **Remediation**:
   - Rotate all secrets
   - Patch vulnerabilities
   - Update security rules
   - Enhance monitoring

4. **Post-Incident**:
   - Conduct post-mortem
   - Update procedures
   - Improve detection
   - Train team

### Contact

For security issues, email: security@yourcompany.com

**Do not** report security issues via public GitHub issues.

---

## Compliance

### GDPR Considerations

- Implement data retention policies
- Provide data export functionality
- Enable data deletion
- Document data processing

### SOC 2 / ISO 27001

- Enable audit logging
- Implement access controls
- Regular security reviews
- Incident response procedures

---

## Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

*Last Updated: October 2025*
*MonitorX Security Team*
