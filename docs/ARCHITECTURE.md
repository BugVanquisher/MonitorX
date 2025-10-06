# MonitorX Architecture

## System Overview

MonitorX is a comprehensive ML/AI infrastructure observability platform designed to monitor production ML systems at scale. The architecture follows a modular, microservices-inspired design that can scale from single-server deployments to distributed systems.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  ML Models   │  │  Python SDK  │  │  REST API    │                 │
│  │              │  │              │  │   Clients    │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        MonitorX API Layer                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI Application                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │   │
│  │  │  /api/v1     │  │  WebSocket   │  │   Health     │         │   │
│  │  │  Endpoints   │  │  Support     │  │   Checks     │         │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Business Logic Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │  Metrics     │  │  Alerting    │  │  Model       │                 │
│  │  Collector   │  │  Service     │  │  Registry    │                 │
│  └──────────────┘  └──────────────┘  └──────────────┘                 │
└───────────────────────────┬──────────────────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                ▼                        ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Storage Layer          │  │   External Services      │
│  ┌──────────────┐       │  │  ┌──────────────┐       │
│  │  InfluxDB    │       │  │  │  Email/SMTP  │       │
│  │  Time-Series │       │  │  │  Slack       │       │
│  │  Database    │       │  │  │  Webhooks    │       │
│  └──────────────┘       │  │  └──────────────┘       │
└──────────────────────────┘  └──────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Presentation Layer                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Streamlit Dashboard                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │   │
│  │  │  Real-time   │  │  Historical  │  │    Alert     │         │   │
│  │  │  Metrics     │  │  Analysis    │  │  Management  │         │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. API Layer (FastAPI)

**Location:** `src/monitorx/server.py`, `src/monitorx/api/`

**Responsibilities:**
- HTTP request handling
- Request validation (Pydantic models)
- Route management
- CORS configuration
- Error handling
- API documentation (OpenAPI/Swagger)

**Key Features:**
- Async/await support for high concurrency
- Automatic request validation
- Interactive documentation at `/docs`
- Health check endpoints
- Middleware for logging, metrics, CORS

**Endpoints:**
- `/api/v1/models` - Model registration
- `/api/v1/metrics/*` - Metric collection and retrieval
- `/api/v1/alerts` - Alert management
- `/api/v1/summary` - Aggregated statistics
- `/api/v1/health` - Health checks

### 2. Metrics Collector

**Location:** `src/monitorx/services/metrics_collector.py`

**Responsibilities:**
- Metric collection and storage
- Threshold monitoring
- Alert generation
- Summary statistics calculation
- Model configuration management

**Design Patterns:**
- Observer pattern for callbacks
- Singleton for global instance
- Circular buffer (deque) for in-memory cache

**Key Features:**
- Real-time threshold checking
- Automatic alert generation
- Configurable per-model thresholds
- Severity calculation based on threshold ratios
- Time-based and model-based filtering

**Data Flow:**
```
Metric Received → Validate → Store in Memory Cache → Check Thresholds
                                     ↓                      ↓
                                Store in InfluxDB    Generate Alerts
                                                           ↓
                                                  Trigger Callbacks
```

### 3. Alerting Service

**Location:** `src/monitorx/services/alerting.py`

**Responsibilities:**
- Multi-channel alert delivery
- Rate limiting
- Custom alert handlers
- Alert formatting

**Supported Channels:**
- **Email (SMTP):** HTML formatted emails with severity-based colors
- **Slack:** Rich attachments with structured fields
- **Webhooks:** Generic HTTP POST/PUT to custom endpoints

**Design Patterns:**
- Strategy pattern for different channels
- Template method for alert formatting
- Rate limiting with sliding window

**Key Features:**
- Concurrent channel sending
- Automatic rate limiting (5-minute window)
- Custom handler support
- Channel enable/disable toggles
- Test mode for validation

### 4. Storage Layer (InfluxDB)

**Location:** `src/monitorx/services/storage.py`

**Responsibilities:**
- Time-series data persistence
- Metric aggregation
- Query optimization
- Data retention management

**Schema:**
```
Measurement: inference_metrics
├── Tags: model_id, model_type, environment, custom_tags
├── Fields: latency, throughput, error_rate, gpu_memory, cpu_usage
└── Timestamp: nanosecond precision

Measurement: drift_metrics
├── Tags: model_id, drift_type, severity
├── Fields: confidence
└── Timestamp: nanosecond precision
```

**Query Patterns:**
- Time-window aggregations
- Downsampling for historical data
- Multi-tag filtering
- Percentile calculations (p95, p99)

### 5. Python SDK

**Location:** `src/monitorx/sdk/`

**Responsibilities:**
- Simplified API client
- Async context management
- Error handling and retries
- Decorator-based metric collection

**Components:**
- `client.py` - HTTP client wrapper
- `decorators.py` - Function decorators for automatic tracking
- `context.py` - Context manager for scoped operations

**Usage Patterns:**
```python
# Context manager pattern
async with MonitorXClient() as client:
    await client.collect_metric(...)

# Decorator pattern
@monitor_inference(model_id="my-model")
async def my_inference_function():
    pass
```

### 6. Dashboard (Streamlit)

**Location:** `src/monitorx/dashboard/app.py`

**Responsibilities:**
- Real-time metrics visualization
- Alert management UI
- Model configuration display
- Historical analysis

**Features:**
- Auto-refresh capability
- Interactive charts (Plotly)
- Filterable views (model, time range)
- Alert resolution interface

**Architecture:**
- Single-page app with tabs
- API client for data fetching
- Cached data for performance
- Responsive layout

---

## Data Types

### Core Types

**Location:** `src/monitorx/types/__init__.py`

```python
@dataclass
class InferenceMetric:
    model_id: str
    model_type: Literal["llm", "cv", "tabular"]
    request_id: str
    latency: float
    throughput: Optional[float]
    error_rate: Optional[float]
    resource_usage: Optional[ResourceUsage]
    tags: Dict[str, str]
    timestamp: datetime

@dataclass
class Alert:
    id: str
    model_id: str
    alert_type: Literal["latency", "error_rate", "drift", "resource_usage"]
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    timestamp: datetime
    resolved: bool
    resolved_at: Optional[datetime]

@dataclass
class ModelConfig:
    id: str
    name: str
    model_type: Literal["llm", "cv", "tabular"]
    version: str
    environment: Literal["dev", "staging", "prod"]
    thresholds: Thresholds
```

---

## Design Decisions

### 1. Why FastAPI?

**Pros:**
- Native async/await support (crucial for I/O-bound operations)
- Automatic request validation with Pydantic
- Built-in OpenAPI documentation
- High performance (comparable to Node.js/Go)
- Type hints and IDE support

**Trade-offs:**
- Smaller ecosystem than Flask/Django
- Newer framework (less mature)

### 2. Why InfluxDB?

**Pros:**
- Purpose-built for time-series data
- Efficient compression (10-100x over relational DBs)
- Native downsampling and retention policies
- Powerful query language (Flux)
- Horizontal scalability

**Trade-offs:**
- Eventual consistency (not ACID)
- Learning curve for Flux query language
- Requires separate service

**Alternatives Considered:**
- **Prometheus:** Great for infrastructure, less suited for custom ML metrics
- **TimescaleDB:** PostgreSQL extension, more familiar SQL, but less optimized for time-series
- **Elasticsearch:** More general-purpose, higher resource requirements

### 3. Why In-Memory Cache + InfluxDB?

**Rationale:**
- **Fast access** for recent metrics (no DB queries)
- **Circular buffer** (deque) prevents unbounded memory growth
- **Write-through** ensures persistence
- **Hybrid approach** balances speed and durability

**Trade-offs:**
- Metrics in deque lost on crash (acceptable for recent data)
- Higher memory usage
- Complexity in synchronization

### 4. Why Dataclasses over Pydantic?

**Internal Types (dataclasses):**
- Simpler, lighter weight
- No validation overhead
- Better performance for internal use

**API Models (Pydantic):**
- Automatic validation
- JSON schema generation
- OpenAPI integration

### 5. Async Architecture

**Benefits:**
- Handle thousands of concurrent requests
- Non-blocking I/O for InfluxDB writes
- Concurrent alert channel sending
- Efficient resource utilization

**Considerations:**
- More complex error handling
- Requires async-aware libraries
- Debugging can be harder

---

## Scalability Considerations

### Horizontal Scaling

**API Servers:**
- Stateless design (no server-side sessions)
- Load balancer distributes requests
- Shared InfluxDB backend

**Challenges:**
- In-memory cache not shared across instances
- Rate limiting per-instance (can use Redis)

**Solution:**
```python
# Use Redis for shared state
import redis

redis_client = redis.Redis(host='localhost', port=6379)

# Distributed rate limiting
def check_rate_limit(key: str, window: int, max_requests: int):
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    return current <= max_requests
```

### Vertical Scaling

**InfluxDB:**
- Increase IOPS for disk (SSD recommended)
- More RAM for query cache
- CPU for query processing

**API:**
- More workers (`--workers N`)
- Larger worker class (`--worker-class uvicorn.workers.UvicornWorker`)

### Data Partitioning

**By Model:**
```python
# Separate buckets per model or environment
bucket_name = f"metrics_{model.environment}_{model.id}"
```

**By Time:**
```python
# Use InfluxDB retention policies
# Hot data: 7 days, full resolution
# Warm data: 30 days, 1-hour aggregation
# Cold data: 1 year, 1-day aggregation
```

---

## Security Architecture

### Defense in Depth

**Layer 1: Network**
- Firewall rules
- VPC/subnet isolation
- TLS/SSL encryption

**Layer 2: API**
- API key authentication
- Rate limiting
- Input validation (Pydantic)

**Layer 3: Application**
- Least privilege principle
- Secure secret storage
- Audit logging

**Layer 4: Data**
- Encrypted at rest (InfluxDB)
- Encrypted in transit (TLS)
- Access control lists

---

## Performance Characteristics

### Latency Targets

- **Metric ingestion:** < 50ms (p99)
- **Query (recent data):** < 100ms (p99)
- **Aggregations:** < 500ms (p99)
- **Alert delivery:** < 2s (p99)

### Throughput

- **Single instance:** ~1000 metrics/sec
- **With InfluxDB optimization:** ~10,000 metrics/sec
- **Clustered:** 100,000+ metrics/sec

### Resource Usage

**Single Instance (Typical):**
- CPU: 10-20% (idle), 50-70% (busy)
- RAM: 500MB (base) + 100MB per 10k cached metrics
- Disk: Depends on retention (1GB/day for 1k metrics/sec)

---

## Monitoring the Monitor

### Self-Monitoring

MonitorX should monitor itself:

```python
# Expose Prometheus metrics
from prometheus_client import Counter, Histogram

metrics_received = Counter('monitorx_metrics_received_total', 'Metrics received')
api_latency = Histogram('monitorx_api_latency_seconds', 'API latency')
influxdb_writes = Counter('monitorx_influxdb_writes_total', 'InfluxDB writes')
alert_sends = Counter('monitorx_alerts_sent_total', 'Alerts sent', ['channel'])
```

### Health Checks

- **Liveness:** Is the process running?
- **Readiness:** Can it serve requests?
- **Dependency checks:** InfluxDB, SMTP, etc.

---

## Future Architecture Enhancements

### 1. Event Streaming (Kafka)

For very high throughput:
```
ML Models → Kafka → MonitorX Consumers → InfluxDB
```

**Benefits:**
- Decouple ingestion from processing
- Replay capability
- Backpressure handling

### 2. Distributed Tracing

Integrate OpenTelemetry:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("collect_metric"):
    await metrics_collector.collect_inference_metric(metric)
```

### 3. ML Pipeline Integration

Direct integration with:
- Kubeflow Pipelines
- MLflow
- Airflow DAGs

### 4. Advanced Analytics

- Anomaly detection on metrics
- Predictive alerting
- Automated root cause analysis
- Cost optimization recommendations

---

## Technology Stack

### Core
- **Python 3.9+**: Main language
- **FastAPI**: Web framework
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### Storage
- **InfluxDB 2.7+**: Time-series database

### Dashboard
- **Streamlit**: UI framework
- **Plotly**: Interactive charts
- **Pandas**: Data manipulation

### Utilities
- **httpx**: Async HTTP client
- **loguru**: Logging
- **APScheduler**: Task scheduling

### Testing
- **pytest**: Test framework
- **pytest-asyncio**: Async test support

### Deployment
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy

---

## Conclusion

MonitorX's architecture prioritizes:
1. **Scalability** - Horizontal and vertical scaling paths
2. **Performance** - Async I/O, efficient storage
3. **Reliability** - Health checks, error handling
4. **Extensibility** - Plugin architecture for channels, modular design
5. **Usability** - Clean APIs, comprehensive documentation

The modular design allows components to evolve independently while maintaining backward compatibility through versioned APIs.

---

## Related Documentation

- [API Documentation](API.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Alerting Guide](ALERTING.md)
- [Testing Guide](../TESTING.md)
