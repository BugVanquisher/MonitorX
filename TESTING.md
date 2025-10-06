# MonitorX Test Suite

## Overview

This document describes the comprehensive test suite for MonitorX, covering all core functionality including types, metrics collection, API endpoints, and SDK client operations.

## Test Coverage

**Total Tests: 75**

### Test Breakdown

#### 1. Type Tests (`test_types.py`) - 16 tests
Tests for core data structures:
- `InferenceMetric` - basic metrics, resource usage, custom tags
- `DriftMetric` - data drift and concept drift
- `Alert` - alert creation, unique IDs, resolution
- `Thresholds` - default and custom threshold values
- `ModelConfig` - model configuration with thresholds
- `SummaryStats` - summary statistics calculation
- `ResourceUsage` - GPU/CPU/memory tracking

#### 2. Metrics Collector Tests (`test_metrics_collector.py`) - 17 tests
Tests for the core metrics collection service:
- Model registration
- Inference metric collection
- Drift metric collection
- Threshold breach detection and alerting
- Latency threshold alerts
- Error rate threshold alerts
- Drift severity alerts
- Metric filtering (by model, by time)
- Alert filtering (by resolved status)
- Severity calculation logic
- Summary statistics aggregation
- Alert resolution
- Callback mechanisms
- Deque size limits

#### 3. API Endpoint Tests (`test_api.py`) - 22 tests
Tests for FastAPI REST API endpoints:
- **Health Endpoint**: Health check status
- **Model Endpoints**: Register models, get models, validation
- **Metrics Endpoints**: Collect inference metrics, collect drift metrics, get metrics with filters
- **Alert Endpoints**: Get alerts, filter by status, resolve alerts
- **Summary Endpoints**: Get summary stats, model-specific stats
- **Aggregated Metrics**: Time-window aggregations

#### 4. SDK Client Tests (`test_sdk.py`) - 20 tests
Tests for the Python SDK client:
- Client initialization and configuration
- Header management with/without API keys
- Async context manager usage
- Model registration (success/failure)
- Inference metric collection with auto-generated request IDs
- Drift metric collection
- Resource usage tracking
- Summary statistics retrieval
- Alert retrieval with filters
- Alert resolution
- Health check operations
- Session management

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_api.py -v
pytest tests/test_types.py -v
pytest tests/test_metrics_collector.py -v
pytest tests/test_sdk.py -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=monitorx --cov-report=html
```

### Run Tests in Parallel
```bash
pytest tests/ -n auto
```

## Test Configuration

Tests are configured via `pytest.ini`:
- Async support enabled via `pytest-asyncio`
- Test discovery patterns defined
- Warning suppression enabled
- Verbose output by default

## Fixtures

### Global Fixtures (`conftest.py`)
- `metrics_collector`: Fresh MetricsCollector instance
- `sample_model_config`: Pre-configured model for testing
- `sample_inference_metric`: Sample metric data
- `sample_drift_metric`: Sample drift data
- `high_latency_metric`: Metric exceeding latency threshold
- `high_error_rate_metric`: Metric exceeding error threshold

### Test-Specific Fixtures
- `client`: FastAPI test client
- `reset_metrics_collector`: Auto-reset before each test
- `mock_storage`: Mock InfluxDB storage operations

## Mocking Strategy

### Storage Mocking
All InfluxDB storage operations are mocked to avoid external dependencies:
- `write_inference_metric`
- `write_drift_metric`
- `get_aggregated_metrics`

This ensures tests run quickly and don't require a running InfluxDB instance.

### HTTP Client Mocking
SDK tests mock `httpx.AsyncClient` to test client behavior without hitting real endpoints.

## Test Patterns

### Async Tests
Tests using async/await are marked with `@pytest.mark.asyncio` (handled automatically by `pytest.ini`).

### Parametrized Tests
Consider adding parametrized tests for:
- Different model types (llm, cv, tabular)
- Different severity levels
- Different time ranges

### Integration Tests
Current tests are primarily unit tests. Consider adding:
- End-to-end tests with real InfluxDB
- Load tests for metrics collection
- Concurrency tests for alert generation

## Test Best Practices

1. **Isolation**: Each test resets state via fixtures
2. **Clarity**: Test names describe what they test
3. **Completeness**: Both success and failure cases covered
4. **Speed**: Mocking ensures fast execution
5. **Maintainability**: Shared fixtures reduce duplication

## Future Test Additions

### Recommended Areas for Expansion:
1. **Storage Layer**: Tests for InfluxDB integration
2. **Dashboard**: Tests for Streamlit UI components
3. **Decorators**: Tests for `@monitor_inference` decorator
4. **Context Management**: Tests for `MonitorXContext`
5. **Alerting Service**: Tests for email/Slack/webhook channels
6. **Performance**: Load tests and benchmarks
7. **Security**: Auth and validation tests

## Continuous Integration

Tests should be run on every commit via CI/CD:
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v
```

## Test Results

Latest test run results:
```
========== 75 passed, 5 warnings in 0.39s ==========
```

All tests passing with 100% success rate.
