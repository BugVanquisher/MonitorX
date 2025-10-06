# MonitorX API Documentation

## Overview

MonitorX provides a RESTful API for collecting metrics, managing models, and retrieving alerts. The API is built with FastAPI and includes interactive documentation.

## Base URL

```
http://localhost:8000
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

Currently, the API does not require authentication. For production use, consider implementing:
- API keys
- JWT tokens
- OAuth2

See [Production Readiness](DEPLOYMENT.md#security) for details.

## API Endpoints

### Health Check

#### GET /api/v1/health

Check the health status of the API and connected services.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "0.1.0",
  "services": {
    "api": "healthy",
    "influxdb": "healthy"
  }
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `500 Internal Server Error` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8000/api/v1/health
```

---

### Model Management

#### POST /api/v1/models

Register a new model configuration with monitoring thresholds.

**Request Body:**
```json
{
  "id": "my-llm-v1",
  "name": "My LLM Model",
  "model_type": "llm",
  "version": "1.0.0",
  "environment": "prod",
  "thresholds": {
    "latency": 1000.0,
    "error_rate": 0.05,
    "gpu_memory": 0.8,
    "cpu_usage": 0.8,
    "memory_usage": 0.8
  }
}
```

**Parameters:**
- `id` (string, required): Unique identifier for the model
- `name` (string, required): Human-readable model name
- `model_type` (enum, required): One of `llm`, `cv`, `tabular`
- `version` (string, required): Model version
- `environment` (enum, required): One of `dev`, `staging`, `prod`
- `thresholds` (object, optional): Alert thresholds
  - `latency` (float): Latency threshold in milliseconds (default: 1000)
  - `error_rate` (float): Error rate threshold 0-1 (default: 0.05)
  - `gpu_memory` (float): GPU memory threshold 0-1 (default: 0.8)
  - `cpu_usage` (float): CPU usage threshold 0-1 (default: 0.8)
  - `memory_usage` (float): Memory usage threshold 0-1 (default: 0.8)

**Response:**
```json
{
  "status": "success",
  "message": "Model registered successfully"
}
```

**Status Codes:**
- `201 Created` - Model registered successfully
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/models \
  -H "Content-Type: application/json" \
  -d '{
    "id": "fraud-detector-v1",
    "name": "Fraud Detection Model",
    "model_type": "tabular",
    "version": "1.0.0",
    "environment": "prod",
    "thresholds": {
      "latency": 500.0,
      "error_rate": 0.01
    }
  }'
```

#### GET /api/v1/models

Retrieve all registered models.

**Response:**
```json
{
  "models": [
    {
      "id": "my-llm-v1",
      "name": "My LLM Model",
      "model_type": "llm",
      "version": "1.0.0",
      "environment": "prod",
      "thresholds": {
        "latency": 1000.0,
        "error_rate": 0.05,
        "gpu_memory": 0.8,
        "cpu_usage": 0.8,
        "memory_usage": 0.8
      }
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/v1/models
```

---

### Metrics Collection

#### POST /api/v1/metrics/inference

Collect an inference metric for a model.

**Request Body:**
```json
{
  "model_id": "my-llm-v1",
  "model_type": "llm",
  "request_id": "req-123456",
  "latency": 850.5,
  "throughput": 12.3,
  "error_rate": 0.01,
  "resource_usage": {
    "gpu_memory": 0.65,
    "cpu_usage": 0.45,
    "memory_usage": 0.55
  },
  "tags": {
    "region": "us-west",
    "version": "1.0.0"
  }
}
```

**Parameters:**
- `model_id` (string, required): ID of the model
- `model_type` (enum, required): One of `llm`, `cv`, `tabular`
- `request_id` (string, required): Unique request identifier
- `latency` (float, required): Latency in milliseconds (> 0)
- `throughput` (float, optional): Requests per second (> 0)
- `error_rate` (float, optional): Error rate 0-1
- `resource_usage` (object, optional): Resource utilization metrics
  - `gpu_memory` (float): GPU memory usage 0-1
  - `cpu_usage` (float): CPU usage 0-1
  - `memory_usage` (float): Memory usage 0-1
- `tags` (object, optional): Custom key-value tags

**Response:**
```json
{
  "status": "success",
  "message": "Metric collected successfully"
}
```

**Status Codes:**
- `201 Created` - Metric collected
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/metrics/inference \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "my-llm-v1",
    "model_type": "llm",
    "request_id": "req-001",
    "latency": 850.5,
    "error_rate": 0.01
  }'
```

#### GET /api/v1/metrics/inference

Retrieve inference metrics with optional filtering.

**Query Parameters:**
- `model_id` (string, optional): Filter by model ID
- `since_hours` (int, optional): Hours to look back (default: 24, max: 168)
- `limit` (int, optional): Maximum results (default: 1000, max: 10000)

**Response:**
```json
{
  "metrics": [
    {
      "model_id": "my-llm-v1",
      "model_type": "llm",
      "request_id": "req-123",
      "latency": 850.5,
      "throughput": 12.3,
      "error_rate": 0.01,
      "timestamp": "2024-01-01T12:00:00Z",
      "tags": {}
    }
  ]
}
```

**Example:**
```bash
# Get all metrics from last 24 hours
curl http://localhost:8000/api/v1/metrics/inference

# Filter by model
curl "http://localhost:8000/api/v1/metrics/inference?model_id=my-llm-v1&since_hours=6"
```

#### POST /api/v1/metrics/drift

Report model drift detection.

**Request Body:**
```json
{
  "model_id": "my-llm-v1",
  "drift_type": "data",
  "severity": "medium",
  "confidence": 0.85,
  "tags": {
    "detector": "ks_test",
    "feature": "input_length"
  }
}
```

**Parameters:**
- `model_id` (string, required): ID of the model
- `drift_type` (enum, required): One of `data`, `concept`
- `severity` (enum, required): One of `low`, `medium`, `high`, `critical`
- `confidence` (float, required): Detection confidence 0-1
- `tags` (object, optional): Custom tags

**Response:**
```json
{
  "status": "success",
  "message": "Drift metric collected successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/metrics/drift \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "my-llm-v1",
    "drift_type": "concept",
    "severity": "high",
    "confidence": 0.92
  }'
```

#### GET /api/v1/metrics/drift

Retrieve drift metrics.

**Query Parameters:**
- `model_id` (string, optional): Filter by model ID
- `since_hours` (int, optional): Hours to look back (default: 168, max: 168)
- `limit` (int, optional): Maximum results (default: 100, max: 1000)

**Response:**
```json
{
  "drift_metrics": [
    {
      "model_id": "my-llm-v1",
      "drift_type": "data",
      "severity": "medium",
      "confidence": 0.85,
      "timestamp": "2024-01-01T12:00:00Z",
      "tags": {}
    }
  ]
}
```

#### GET /api/v1/metrics/aggregated

Get aggregated metrics over time windows.

**Query Parameters:**
- `model_id` (string, optional): Filter by model ID
- `since_hours` (int, optional): Hours to look back (default: 6, max: 168)
- `window` (string, optional): Aggregation window (default: "5m")
  - Valid formats: `Xs` (seconds), `Xm` (minutes), `Xh` (hours)
  - Examples: "30s", "5m", "1h"

**Response:**
```json
{
  "aggregated_metrics": {
    "latency": [
      {
        "time": "2024-01-01T12:00:00Z",
        "value": 850.5
      }
    ],
    "throughput": [...],
    "error_rate": [...],
    "gpu_memory": [...]
  }
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/metrics/aggregated?since_hours=1&window=5m"
```

---

### Alerts

#### GET /api/v1/alerts

Retrieve alerts with optional filtering.

**Query Parameters:**
- `model_id` (string, optional): Filter by model ID
- `since_hours` (int, optional): Hours to look back (default: 168, max: 168)
- `resolved` (boolean, optional): Filter by resolution status
- `limit` (int, optional): Maximum results (default: 100, max: 1000)

**Response:**
```json
[
  {
    "id": "alert-uuid",
    "model_id": "my-llm-v1",
    "alert_type": "latency",
    "severity": "high",
    "message": "High latency detected: 2500ms (threshold: 1000ms)",
    "timestamp": "2024-01-01T12:00:00Z",
    "resolved": false,
    "resolved_at": null
  }
]
```

**Alert Types:**
- `latency` - High request latency
- `error_rate` - High error rate
- `resource_usage` - High resource utilization
- `drift` - Model drift detected

**Severity Levels:**
- `low` - 1.0-1.2x threshold
- `medium` - 1.2-1.5x threshold
- `high` - 1.5-2.0x threshold
- `critical` - ≥2.0x threshold

**Example:**
```bash
# Get unresolved alerts
curl "http://localhost:8000/api/v1/alerts?resolved=false"

# Get all alerts for a model
curl "http://localhost:8000/api/v1/alerts?model_id=my-llm-v1&since_hours=24"
```

#### POST /api/v1/alerts/resolve

Mark an alert as resolved.

**Request Body:**
```json
{
  "alert_id": "alert-uuid"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Alert resolved successfully"
}
```

**Status Codes:**
- `200 OK` - Alert resolved
- `404 Not Found` - Alert not found
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/alerts/resolve \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "alert-uuid"}'
```

---

### Summary Statistics

#### GET /api/v1/summary

Get aggregated summary statistics for metrics.

**Query Parameters:**
- `model_id` (string, optional): Filter by model ID
- `since_hours` (int, optional): Hours to look back (default: 24, max: 168)

**Response:**
```json
{
  "total_requests": 10000,
  "average_latency": 845.3,
  "error_rate": 0.015,
  "p95_latency": 1250.0,
  "p99_latency": 1850.0,
  "active_alerts": 3
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/summary?model_id=my-llm-v1&since_hours=24"
```

---

## Error Responses

All endpoints return errors in a consistent format:

```json
{
  "detail": "Error message description"
}
```

### Common Error Codes

- `400 Bad Request` - Invalid request format
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "latency"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider:
- Request-based rate limiting
- IP-based throttling
- Model-specific quotas

---

## Best Practices

### 1. Model Registration
- Register models before sending metrics
- Use semantic versioning for model versions
- Set appropriate thresholds based on SLOs

### 2. Metric Collection
- Include unique request IDs for tracing
- Use consistent tag naming conventions
- Send metrics asynchronously to avoid blocking
- Batch metrics when possible (future feature)

### 3. Error Handling
- Implement retry logic with exponential backoff
- Log failed metric submissions
- Monitor API health endpoint

### 4. Alert Management
- Regularly resolve processed alerts
- Monitor alert trends
- Adjust thresholds based on alert frequency

---

## Code Examples

### Python SDK

```python
import asyncio
from monitorx.sdk import MonitorXClient
from monitorx.types import ModelConfig, Thresholds

async def main():
    client = MonitorXClient("http://localhost:8000")

    # Register model
    config = ModelConfig(
        id="my-model",
        name="My Model",
        model_type="llm",
        version="1.0.0",
        environment="prod"
    )
    await client.register_model(config)

    # Collect metric
    await client.collect_inference_metric(
        model_id="my-model",
        model_type="llm",
        latency=850.5,
        error_rate=0.01
    )

    # Get summary
    stats = await client.get_summary_stats("my-model", since_hours=24)
    print(stats)

asyncio.run(main())
```

### cURL

```bash
# Register model
curl -X POST http://localhost:8000/api/v1/models \
  -H "Content-Type: application/json" \
  -d '{"id":"my-model","name":"My Model","model_type":"llm","version":"1.0.0","environment":"prod"}'

# Collect metric
curl -X POST http://localhost:8000/api/v1/metrics/inference \
  -H "Content-Type: application/json" \
  -d '{"model_id":"my-model","model_type":"llm","request_id":"req-001","latency":850.5}'

# Get summary
curl "http://localhost:8000/api/v1/summary?model_id=my-model&since_hours=24"
```

### JavaScript/TypeScript

```javascript
const API_BASE = 'http://localhost:8000';

// Register model
async function registerModel() {
  const response = await fetch(`${API_BASE}/api/v1/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id: 'my-model',
      name: 'My Model',
      model_type: 'llm',
      version: '1.0.0',
      environment: 'prod'
    })
  });
  return response.json();
}

// Collect metric
async function collectMetric() {
  const response = await fetch(`${API_BASE}/api/v1/metrics/inference`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model_id: 'my-model',
      model_type: 'llm',
      request_id: 'req-001',
      latency: 850.5
    })
  });
  return response.json();
}
```

---

## Next Steps

- [Alerting Guide](ALERTING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [SDK Documentation](SDK.md)
- [Dashboard Guide](DASHBOARD.md)
