# Copyright 2025 MonitorX Team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, AsyncMock

from monitorx.server import app
from monitorx.api.routes import metrics_collector, storage


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_metrics_collector():
    """Reset metrics collector before each test."""
    metrics_collector.metrics.clear()
    metrics_collector.drift_metrics.clear()
    metrics_collector.alerts.clear()
    metrics_collector.model_configs.clear()
    yield


@pytest.fixture(autouse=True)
def mock_storage():
    """Mock storage operations."""
    with patch.object(storage, 'write_inference_metric', new_callable=AsyncMock) as mock_write_inference, \
         patch.object(storage, 'write_drift_metric', new_callable=AsyncMock) as mock_write_drift, \
         patch.object(storage, 'get_aggregated_metrics', new_callable=AsyncMock) as mock_get_aggregated:

        mock_write_inference.return_value = None
        mock_write_drift.return_value = None
        mock_get_aggregated.return_value = {}
        yield


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data
        assert data["services"]["api"] == "healthy"


class TestModelEndpoints:
    """Test model registration endpoints."""

    def test_register_model(self, client):
        """Test registering a new model."""
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "model_type": "llm",
            "version": "1.0.0",
            "environment": "dev",
            "thresholds": {
                "latency": 1000.0,
                "error_rate": 0.05,
                "gpu_memory": 0.8,
                "cpu_usage": 0.8,
                "memory_usage": 0.8
            }
        }

        response = client.post("/api/v1/models", json=model_data)
        assert response.status_code == 201

        data = response.json()
        assert data["status"] == "success"

    def test_get_models(self, client):
        """Test getting all registered models."""
        # First register a model
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "model_type": "cv",
            "version": "1.0.0",
            "environment": "prod"
        }
        client.post("/api/v1/models", json=model_data)

        # Get all models
        response = client.get("/api/v1/models")
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert len(data["models"]) == 1
        assert data["models"][0]["id"] == "test-model-1"

    def test_register_model_invalid_type(self, client):
        """Test registering model with invalid type."""
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "model_type": "invalid_type",
            "version": "1.0.0",
            "environment": "dev"
        }

        response = client.post("/api/v1/models", json=model_data)
        assert response.status_code == 422  # Validation error


class TestMetricsEndpoints:
    """Test metrics collection endpoints."""

    def test_collect_inference_metric(self, client):
        """Test collecting an inference metric."""
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": 500.0,
            "throughput": 10.5,
            "error_rate": 0.01,
            "tags": {"version": "1.0.0"}
        }

        response = client.post("/api/v1/metrics/inference", json=metric_data)
        assert response.status_code == 201

        data = response.json()
        assert data["status"] == "success"

    def test_collect_inference_metric_with_resource_usage(self, client):
        """Test collecting metric with resource usage."""
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "cv",
            "request_id": "req-456",
            "latency": 750.0,
            "resource_usage": {
                "gpu_memory": 0.7,
                "cpu_usage": 0.5,
                "memory_usage": 0.6
            }
        }

        response = client.post("/api/v1/metrics/inference", json=metric_data)
        assert response.status_code == 201

    def test_collect_inference_metric_invalid_latency(self, client):
        """Test collecting metric with invalid latency."""
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": -100.0  # Invalid negative latency
        }

        response = client.post("/api/v1/metrics/inference", json=metric_data)
        assert response.status_code == 422

    def test_get_inference_metrics(self, client):
        """Test retrieving inference metrics."""
        # First collect a metric
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": 500.0
        }
        client.post("/api/v1/metrics/inference", json=metric_data)

        # Get metrics
        response = client.get("/api/v1/metrics/inference")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert len(data["metrics"]) >= 1

    def test_get_inference_metrics_filtered_by_model(self, client):
        """Test getting metrics filtered by model_id."""
        # Collect metrics for different models
        for i in range(3):
            metric_data = {
                "model_id": f"model-{i}",
                "model_type": "llm",
                "request_id": f"req-{i}",
                "latency": 500.0
            }
            client.post("/api/v1/metrics/inference", json=metric_data)

        # Filter by specific model
        response = client.get("/api/v1/metrics/inference?model_id=model-1")
        assert response.status_code == 200

        data = response.json()
        assert len(data["metrics"]) == 1
        assert data["metrics"][0]["model_id"] == "model-1"

    def test_get_inference_metrics_with_time_filter(self, client):
        """Test getting metrics with time filter."""
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": 500.0
        }
        client.post("/api/v1/metrics/inference", json=metric_data)

        # Get metrics from last 1 hour
        response = client.get("/api/v1/metrics/inference?since_hours=1")
        assert response.status_code == 200

    def test_collect_drift_metric(self, client):
        """Test collecting a drift metric."""
        drift_data = {
            "model_id": "test-model-1",
            "drift_type": "data",
            "severity": "medium",
            "confidence": 0.85,
            "tags": {"detector": "ks_test"}
        }

        response = client.post("/api/v1/metrics/drift", json=drift_data)
        assert response.status_code == 201

    def test_get_drift_metrics(self, client):
        """Test retrieving drift metrics."""
        # Collect a drift metric
        drift_data = {
            "model_id": "test-model-1",
            "drift_type": "concept",
            "severity": "high",
            "confidence": 0.92
        }
        client.post("/api/v1/metrics/drift", json=drift_data)

        # Get drift metrics
        response = client.get("/api/v1/metrics/drift")
        assert response.status_code == 200

        data = response.json()
        assert "drift_metrics" in data


class TestAlertEndpoints:
    """Test alert management endpoints."""

    def test_get_alerts_empty(self, client):
        """Test getting alerts when none exist."""
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_alerts_after_threshold_breach(self, client):
        """Test that alerts are generated when thresholds are breached."""
        # Register model with thresholds
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "model_type": "llm",
            "version": "1.0.0",
            "environment": "dev",
            "thresholds": {
                "latency": 1000.0,
                "error_rate": 0.05
            }
        }
        client.post("/api/v1/models", json=model_data)

        # Send metric that exceeds latency threshold
        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": 2500.0  # Exceeds 1000ms threshold
        }
        client.post("/api/v1/metrics/inference", json=metric_data)

        # Get alerts
        response = client.get("/api/v1/alerts")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1
        assert data[0]["alert_type"] == "latency"
        assert data[0]["model_id"] == "test-model-1"

    def test_get_alerts_filtered_by_resolved(self, client):
        """Test filtering alerts by resolved status."""
        response = client.get("/api/v1/alerts?resolved=false")
        assert response.status_code == 200

    def test_resolve_alert(self, client):
        """Test resolving an alert."""
        # First generate an alert
        model_data = {
            "id": "test-model-1",
            "name": "Test Model",
            "model_type": "llm",
            "version": "1.0.0",
            "environment": "dev",
            "thresholds": {"latency": 500.0}
        }
        client.post("/api/v1/models", json=model_data)

        metric_data = {
            "model_id": "test-model-1",
            "model_type": "llm",
            "request_id": "req-123",
            "latency": 2000.0
        }
        client.post("/api/v1/metrics/inference", json=metric_data)

        # Get the alert
        alerts_response = client.get("/api/v1/alerts")
        alerts = alerts_response.json()

        if len(alerts) > 0:
            alert_id = alerts[0]["id"]

            # Resolve it
            resolve_data = {"alert_id": alert_id}
            response = client.post("/api/v1/alerts/resolve", json=resolve_data)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"

    def test_resolve_nonexistent_alert(self, client):
        """Test resolving a non-existent alert."""
        resolve_data = {"alert_id": "fake-alert-id"}
        response = client.post("/api/v1/alerts/resolve", json=resolve_data)
        assert response.status_code == 404


class TestSummaryEndpoints:
    """Test summary statistics endpoints."""

    def test_get_summary_stats_empty(self, client):
        """Test getting summary stats with no metrics."""
        response = client.get("/api/v1/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["total_requests"] == 0
        assert data["average_latency"] == 0.0

    def test_get_summary_stats_with_metrics(self, client):
        """Test getting summary stats with metrics."""
        # Collect multiple metrics
        for i in range(5):
            metric_data = {
                "model_id": "test-model-1",
                "model_type": "llm",
                "request_id": f"req-{i}",
                "latency": 500.0 + (i * 100),
                "error_rate": 0.01
            }
            client.post("/api/v1/metrics/inference", json=metric_data)

        # Get summary
        response = client.get("/api/v1/summary")
        assert response.status_code == 200

        data = response.json()
        assert data["total_requests"] == 5
        assert data["average_latency"] > 0
        assert data["p95_latency"] > 0

    def test_get_summary_stats_filtered_by_model(self, client):
        """Test getting summary stats for specific model."""
        # Collect metrics for different models
        for model_num in [1, 2]:
            metric_data = {
                "model_id": f"model-{model_num}",
                "model_type": "llm",
                "request_id": f"req-{model_num}",
                "latency": 500.0
            }
            client.post("/api/v1/metrics/inference", json=metric_data)

        # Get summary for specific model
        response = client.get("/api/v1/summary?model_id=model-1")
        assert response.status_code == 200

        data = response.json()
        assert data["total_requests"] == 1


class TestAggregatedMetrics:
    """Test aggregated metrics endpoint."""

    def test_get_aggregated_metrics(self, client):
        """Test getting aggregated metrics."""
        response = client.get("/api/v1/metrics/aggregated?since_hours=1&window=5m")
        assert response.status_code == 200

        data = response.json()
        assert "aggregated_metrics" in data

    def test_get_aggregated_metrics_invalid_window(self, client):
        """Test getting aggregated metrics with invalid window."""
        response = client.get("/api/v1/metrics/aggregated?window=invalid")
        assert response.status_code == 422
