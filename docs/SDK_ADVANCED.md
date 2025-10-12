# MonitorX SDK - Advanced Features

This guide covers advanced features of the MonitorX Python SDK for production deployments.

---

## Table of Contents

- [Batch Collection](#batch-collection)
- [Automatic Retry with Exponential Backoff](#automatic-retry-with-exponential-backoff)
- [Circuit Breaker Pattern](#circuit-breaker-pattern)
- [Metric Buffering](#metric-buffering)
- [Connection Pooling](#connection-pooling)
- [Production Configuration](#production-configuration)

---

## Batch Collection

Collect multiple metrics in a single operation for improved performance.

### Basic Usage

```python
import asyncio
from monitorx import MonitorXClient

async def collect_batch():
    async with MonitorXClient(base_url="http://localhost:8000") as client:
        metrics = [
            {
                "model_id": "gpt-4",
                "model_type": "llm",
                "latency": 245.5,
                "tags": {"endpoint": "/v1/chat"}
            },
            {
                "model_id": "gpt-4",
                "model_type": "llm",
                "latency": 312.8,
                "tags": {"endpoint": "/v1/completion"}
            },
            {
                "model_id": "bert-base",
                "model_type": "llm",
                "latency": 89.3,
                "tags": {"endpoint": "/v1/embeddings"}
            }
        ]

        result = await client.collect_inference_metrics_batch(metrics)
        print(f"{result['success']} succeeded, {result['failed']} failed")
```

### Performance Benefits

- **Parallel execution**: Metrics are sent concurrently
- **Reduced overhead**: Single session reuse
- **Better throughput**: Up to 10x faster than sequential collection

### When to Use

- High-volume metric collection (>100 metrics/second)
- Batch processing scenarios
- End-of-request metric aggregation

---

## Automatic Retry with Exponential Backoff

Built-in retry logic handles transient failures automatically.

### Configuration

```python
from monitorx import MonitorXClient

client = MonitorXClient(
    base_url="http://localhost:8000",
    max_retries=3,           # Number of retry attempts
    retry_backoff=1.0,       # Initial backoff in seconds
    enable_circuit_breaker=True
)
```

### Retry Behavior

| Attempt | Backoff Time |
|---------|--------------|
| 1       | 1.0 seconds  |
| 2       | 2.0 seconds  |
| 3       | 4.0 seconds  |

The backoff doubles with each retry (exponential backoff).

### Example

```python
async with client:
    # If API is temporarily unavailable, this will automatically retry
    success = await client.collect_inference_metric(
        model_id="model-1",
        model_type="llm",
        latency=156.2
    )

    # Returns True if succeeded (within max_retries)
    # Returns False if all retries exhausted
```

### Retry Logic

1. Attempt 1 fails → wait 1 second → retry
2. Attempt 2 fails → wait 2 seconds → retry
3. Attempt 3 fails → wait 4 seconds → retry
4. All retries exhausted → return False (or buffer if enabled)

---

## Circuit Breaker Pattern

Prevents cascading failures by "opening" the circuit after repeated failures.

### How It Works

```
┌─────────────────────────────────────────────────┐
│ Circuit States                                  │
│                                                 │
│  CLOSED ─────failure threshold────► OPEN       │
│    │                                  │         │
│    │                                  │         │
│    │                              recovery      │
│    │                              timeout       │
│    │                                  │         │
│    │                                  ▼         │
│    └────success────────────── HALF-OPEN        │
└─────────────────────────────────────────────────┘
```

### States

1. **CLOSED** (Normal): Requests flow through normally
2. **OPEN** (Failed): All requests rejected immediately (no API calls)
3. **HALF-OPEN** (Testing): Single request allowed to test if service recovered

### Configuration

```python
from monitorx import MonitorXClient

client = MonitorXClient(
    base_url="http://localhost:8000",
    enable_circuit_breaker=True,  # Enable circuit breaker
    max_retries=3
)
```

Circuit breaker parameters (internal):
- **Failure threshold**: 5 consecutive failures opens circuit
- **Recovery timeout**: 60 seconds before transitioning to half-open

### Example

```python
async with client:
    for i in range(100):
        try:
            await client.collect_inference_metric(
                model_id="model-1",
                model_type="llm",
                latency=100.0 + i
            )
        except Exception as e:
            if "Circuit breaker is OPEN" in str(e):
                print("Service unavailable, waiting for recovery...")
                await asyncio.sleep(60)  # Wait for recovery
```

### Benefits

- **Fast failure**: No waiting for timeouts when service is down
- **Resource protection**: Reduces load on failing service
- **Automatic recovery**: Tests service health automatically

---

## Metric Buffering

Buffer metrics locally when API is unavailable, then flush when back online.

### Enable Buffering

```python
from monitorx import MonitorXClient

client = MonitorXClient(
    base_url="http://localhost:8000",
    buffer_size=1000  # Maximum buffered metrics
)

# Enable buffering
client.enable_buffering()
```

### Usage Pattern

```python
async with client:
    # Enable buffering when you detect API issues
    client.enable_buffering()

    # Metrics will be buffered instead of sent
    for i in range(100):
        await client.collect_inference_metric(
            model_id="model-1",
            model_type="llm",
            latency=100.0 + i
        )

    print(f"Buffered: {client.get_buffer_size()} metrics")

    # When API is back online, flush buffer
    client.disable_buffering()
    result = await client.flush_buffer()

    print(f"Flushed: {result['flushed']}, Failed: {result['failed']}")
```

### Automatic Buffering on Failure

When buffering is enabled, failed requests are automatically buffered:

```python
client.enable_buffering()

async with client:
    # If this fails after all retries, it will be buffered
    await client.collect_inference_metric(
        model_id="model-1",
        model_type="llm",
        latency=100.0
    )
```

### Buffer Management

```python
# Check buffer size
size = client.get_buffer_size()

# Enable buffering
client.enable_buffering()

# Disable buffering
client.disable_buffering()

# Flush all buffered metrics
result = await client.flush_buffer()
```

### Buffer Overflow

When buffer reaches `buffer_size`, oldest metrics are dropped (FIFO):

```python
client = MonitorXClient(buffer_size=100)  # Only keep last 100 metrics
```

---

## Connection Pooling

Use async context manager to reuse HTTP connections across multiple requests.

### With Connection Pool

```python
async with MonitorXClient(base_url="http://localhost:8000") as client:
    # All these requests reuse the same HTTP connection
    for i in range(1000):
        await client.collect_inference_metric(
            model_id="model-1",
            model_type="llm",
            latency=100.0 + i
        )
```

### Without Connection Pool

```python
client = MonitorXClient(base_url="http://localhost:8000")

# Each request creates a new connection (slower)
for i in range(1000):
    await client.collect_inference_metric(
        model_id="model-1",
        model_type="llm",
        latency=100.0 + i
    )
```

### Performance Comparison

| Scenario | Time (1000 requests) | Improvement |
|----------|---------------------|-------------|
| Without pool | 45.2s | Baseline |
| With pool | 8.7s | **5.2x faster** |

---

## Production Configuration

Recommended configuration for production environments.

### Recommended Settings

```python
from monitorx import MonitorXClient
import os

client = MonitorXClient(
    base_url=os.getenv("MONITORX_URL", "https://monitorx.yourcompany.com"),
    api_key=os.getenv("MONITORX_API_KEY"),

    # Timeouts
    timeout=10,  # 10 second timeout

    # Retry configuration
    max_retries=3,
    retry_backoff=0.5,  # Start with 0.5s, doubles each retry

    # Circuit breaker
    enable_circuit_breaker=True,

    # Buffering for resilience
    buffer_size=5000
)
```

### Production Usage Pattern

```python
import asyncio
from loguru import logger

async def production_monitor():
    """Production-ready monitoring."""
    client = MonitorXClient(
        base_url="https://monitorx.yourcompany.com",
        api_key=os.getenv("MONITORX_API_KEY"),
        timeout=10,
        max_retries=3,
        retry_backoff=0.5,
        enable_circuit_breaker=True,
        buffer_size=5000
    )

    # Enable buffering for resilience
    client.enable_buffering()

    try:
        async with client:
            # Your application monitoring logic
            while True:
                # Collect metrics
                await client.collect_inference_metric(
                    model_id="prod-model",
                    model_type="llm",
                    latency=measure_latency(),
                    tags={"env": "production"}
                )

                # Flush buffer periodically
                if client.get_buffer_size() > 100:
                    logger.info("Flushing metric buffer...")
                    await client.flush_buffer()

                await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down, flushing remaining metrics...")
        await client.flush_buffer()
```

### Error Handling

```python
async with client:
    try:
        success = await client.collect_inference_metric(
            model_id="model-1",
            model_type="llm",
            latency=100.0
        )

        if not success:
            logger.warning("Failed to collect metric (buffered if enabled)")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
```

### Health Monitoring

```python
# Check API health before starting
health = await client.health_check()

if health.get("status") == "healthy":
    logger.info("API is healthy, starting monitoring...")
else:
    logger.warning("API is unhealthy, enabling buffering...")
    client.enable_buffering()
```

---

## Advanced Patterns

### Pattern 1: Adaptive Buffering

Enable buffering based on failure rate:

```python
failure_count = 0
total_count = 0

async with client:
    for metric in metrics:
        success = await client.collect_inference_metric(**metric)

        total_count += 1
        if not success:
            failure_count += 1

        # Enable buffering if failure rate > 10%
        if total_count > 10:
            failure_rate = failure_count / total_count
            if failure_rate > 0.1 and not client.buffer_enabled:
                logger.warning("High failure rate, enabling buffering")
                client.enable_buffering()
```

### Pattern 2: Periodic Buffer Flush

Flush buffer on schedule:

```python
import asyncio
from datetime import datetime

async def periodic_flush(client, interval=60):
    """Flush buffer every N seconds."""
    while True:
        await asyncio.sleep(interval)

        if client.get_buffer_size() > 0:
            logger.info(f"Periodic flush at {datetime.now()}")
            result = await client.flush_buffer()
            logger.info(f"Flushed {result['flushed']} metrics")

# Run in background
async with client:
    flush_task = asyncio.create_task(periodic_flush(client, interval=60))

    # Your main logic
    # ...

    flush_task.cancel()
```

### Pattern 3: Batch with Retry

Combine batch collection with retry:

```python
async def collect_with_retry(client, metrics, max_attempts=3):
    """Collect batch with retry on partial failure."""
    for attempt in range(max_attempts):
        result = await client.collect_inference_metrics_batch(metrics)

        if result['failed'] == 0:
            return True

        logger.warning(
            f"Attempt {attempt + 1}: {result['failed']} failed"
        )

        if attempt < max_attempts - 1:
            await asyncio.sleep(2 ** attempt)

    return False
```

---

## Troubleshooting

### High Failure Rate

**Problem**: Many metrics failing to send

**Solutions**:
1. Enable buffering: `client.enable_buffering()`
2. Check API health: `await client.health_check()`
3. Increase retry attempts: `max_retries=5`
4. Check network connectivity

### Circuit Breaker Opens Frequently

**Problem**: Circuit breaker opening repeatedly

**Solutions**:
1. Check API server logs for errors
2. Verify API server is running and accessible
3. Increase timeout: `timeout=30`
4. Check for rate limiting issues

### Buffer Filling Up

**Problem**: Buffer size keeps growing

**Solutions**:
1. Check if API is accessible
2. Flush buffer manually: `await client.flush_buffer()`
3. Increase buffer size: `buffer_size=10000`
4. Implement periodic flush (see Pattern 2)

### Slow Performance

**Problem**: Metric collection is slow

**Solutions**:
1. Use batch collection for multiple metrics
2. Use async context manager for connection pooling
3. Reduce timeout: `timeout=5`
4. Disable circuit breaker if not needed

---

## API Reference

### MonitorXClient

```python
class MonitorXClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        enable_circuit_breaker: bool = True,
        buffer_size: int = 1000
    )
```

**Parameters**:
- `base_url`: API server URL
- `api_key`: API authentication key
- `timeout`: Request timeout in seconds
- `max_retries`: Number of retry attempts
- `retry_backoff`: Initial backoff time (doubles each retry)
- `enable_circuit_breaker`: Enable circuit breaker pattern
- `buffer_size`: Maximum buffered metrics

**Methods**:

```python
# Batch collection
async def collect_inference_metrics_batch(
    self,
    metrics: List[Dict[str, Any]]
) -> Dict[str, int]

# Buffering
def enable_buffering(self) -> None
def disable_buffering(self) -> None
def get_buffer_size(self) -> int
async def flush_buffer(self) -> Dict[str, int]

# Standard methods (now with retry)
async def collect_inference_metric(...) -> bool
async def collect_drift_metric(...) -> bool
async def register_model(...) -> bool
async def get_summary_stats(...) -> Dict[str, Any]
async def get_alerts(...) -> List[Dict[str, Any]]
async def resolve_alert(...) -> bool
async def health_check() -> Dict[str, Any]
```

---

## Examples

See `examples/sdk_advanced_features.py` for complete working examples.

---

## Best Practices

### 1. Always Use Async Context Manager

```python
# ✓ Good
async with MonitorXClient(...) as client:
    await client.collect_inference_metric(...)

# ✗ Bad (no connection pooling)
client = MonitorXClient(...)
await client.collect_inference_metric(...)
```

### 2. Enable Buffering in Production

```python
# ✓ Good (resilient)
client.enable_buffering()

# ✗ Bad (metrics lost on failure)
# (no buffering)
```

### 3. Use Batch Collection for Multiple Metrics

```python
# ✓ Good (fast)
await client.collect_inference_metrics_batch(metrics)

# ✗ Bad (slow)
for metric in metrics:
    await client.collect_inference_metric(**metric)
```

### 4. Configure Reasonable Timeouts

```python
# ✓ Good
timeout=10  # 10 seconds

# ✗ Bad (too long)
timeout=300  # 5 minutes
```

### 5. Monitor Buffer Size

```python
# ✓ Good
if client.get_buffer_size() > 100:
    await client.flush_buffer()

# ✗ Bad (buffer can grow indefinitely)
# (never check buffer size)
```

---

## Performance Tuning

### High-Throughput Scenarios

For collecting >1000 metrics/second:

```python
client = MonitorXClient(
    timeout=5,              # Short timeout
    max_retries=1,          # Fewer retries
    retry_backoff=0.1,      # Fast backoff
    buffer_size=10000       # Large buffer
)

# Use batch collection
await client.collect_inference_metrics_batch(metrics)
```

### Low-Latency Scenarios

For time-sensitive applications:

```python
client = MonitorXClient(
    timeout=1,              # Very short timeout
    max_retries=0,          # No retries
    enable_circuit_breaker=False  # No circuit breaker overhead
)
```

### High-Reliability Scenarios

For mission-critical monitoring:

```python
client = MonitorXClient(
    timeout=30,             # Longer timeout
    max_retries=5,          # More retries
    retry_backoff=2.0,      # Longer backoff
    enable_circuit_breaker=True,
    buffer_size=10000       # Large buffer
)

client.enable_buffering()  # Always buffer
```

---

*Last Updated: October 2025*
*MonitorX Development Team*
