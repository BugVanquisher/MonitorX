"""Tests for type definitions."""
import pytest
from datetime import datetime

from monitorx.types import (
    InferenceMetric, DriftMetric, Alert, ModelConfig,
    Thresholds, ResourceUsage, SummaryStats
)


class TestInferenceMetric:
    """Test InferenceMetric dataclass."""

    def test_create_basic_metric(self):
        """Test creating a basic inference metric."""
        metric = InferenceMetric(
            model_id="test-model",
            model_type="llm",
            request_id="req-123",
            latency=500.0
        )

        assert metric.model_id == "test-model"
        assert metric.model_type == "llm"
        assert metric.latency == 500.0
        assert isinstance(metric.timestamp, datetime)

    def test_create_metric_with_resource_usage(self):
        """Test creating metric with resource usage."""
        resource_usage = ResourceUsage(
            gpu_memory=0.7,
            cpu_usage=0.5,
            memory_usage=0.6
        )

        metric = InferenceMetric(
            model_id="test-model",
            model_type="cv",
            request_id="req-456",
            latency=750.0,
            resource_usage=resource_usage
        )

        assert metric.resource_usage.gpu_memory == 0.7
        assert metric.resource_usage.cpu_usage == 0.5

    def test_create_metric_with_tags(self):
        """Test creating metric with custom tags."""
        metric = InferenceMetric(
            model_id="test-model",
            model_type="tabular",
            request_id="req-789",
            latency=200.0,
            tags={"version": "1.0.0", "region": "us-east"}
        )

        assert metric.tags["version"] == "1.0.0"
        assert metric.tags["region"] == "us-east"


class TestDriftMetric:
    """Test DriftMetric dataclass."""

    def test_create_data_drift(self):
        """Test creating a data drift metric."""
        drift = DriftMetric(
            model_id="test-model",
            drift_type="data",
            severity="medium",
            confidence=0.85
        )

        assert drift.drift_type == "data"
        assert drift.severity == "medium"
        assert drift.confidence == 0.85

    def test_create_concept_drift(self):
        """Test creating a concept drift metric."""
        drift = DriftMetric(
            model_id="test-model",
            drift_type="concept",
            severity="critical",
            confidence=0.95
        )

        assert drift.drift_type == "concept"
        assert drift.severity == "critical"


class TestAlert:
    """Test Alert dataclass."""

    def test_create_alert(self):
        """Test creating an alert."""
        alert = Alert(
            model_id="test-model",
            alert_type="latency",
            severity="high",
            message="High latency detected"
        )

        assert alert.model_id == "test-model"
        assert alert.alert_type == "latency"
        assert alert.severity == "high"
        assert alert.resolved is False
        assert alert.resolved_at is None

    def test_alert_has_unique_id(self):
        """Test that alerts get unique IDs."""
        alert1 = Alert(
            model_id="test-model",
            alert_type="latency",
            severity="high",
            message="Alert 1"
        )
        alert2 = Alert(
            model_id="test-model",
            alert_type="latency",
            severity="high",
            message="Alert 2"
        )

        assert alert1.id != alert2.id

    def test_resolve_alert(self):
        """Test resolving an alert."""
        alert = Alert(
            model_id="test-model",
            alert_type="error_rate",
            severity="medium",
            message="High error rate"
        )

        assert alert.resolved is False

        alert.resolved = True
        alert.resolved_at = datetime.now()

        assert alert.resolved is True
        assert isinstance(alert.resolved_at, datetime)


class TestThresholds:
    """Test Thresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = Thresholds()

        assert thresholds.latency == 1000.0
        assert thresholds.error_rate == 0.05
        assert thresholds.gpu_memory == 0.8
        assert thresholds.cpu_usage == 0.8

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = Thresholds(
            latency=500.0,
            error_rate=0.01,
            gpu_memory=0.9
        )

        assert thresholds.latency == 500.0
        assert thresholds.error_rate == 0.01
        assert thresholds.gpu_memory == 0.9


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_create_model_config(self):
        """Test creating a model configuration."""
        config = ModelConfig(
            id="model-1",
            name="Test Model",
            model_type="llm",
            version="1.0.0",
            environment="prod"
        )

        assert config.id == "model-1"
        assert config.name == "Test Model"
        assert config.model_type == "llm"
        assert config.environment == "prod"

    def test_model_config_with_custom_thresholds(self):
        """Test model config with custom thresholds."""
        thresholds = Thresholds(latency=2000.0, error_rate=0.02)
        config = ModelConfig(
            id="model-1",
            name="Test Model",
            model_type="cv",
            version="2.0.0",
            environment="dev",
            thresholds=thresholds
        )

        assert config.thresholds.latency == 2000.0
        assert config.thresholds.error_rate == 0.02


class TestSummaryStats:
    """Test SummaryStats dataclass."""

    def test_default_summary_stats(self):
        """Test default summary stats."""
        stats = SummaryStats()

        assert stats.total_requests == 0
        assert stats.average_latency == 0.0
        assert stats.error_rate == 0.0
        assert stats.active_alerts == 0

    def test_custom_summary_stats(self):
        """Test custom summary stats."""
        stats = SummaryStats(
            total_requests=1000,
            average_latency=450.5,
            error_rate=0.015,
            p95_latency=850.0,
            p99_latency=1200.0,
            active_alerts=3
        )

        assert stats.total_requests == 1000
        assert stats.average_latency == 450.5
        assert stats.p95_latency == 850.0
        assert stats.active_alerts == 3


class TestResourceUsage:
    """Test ResourceUsage dataclass."""

    def test_create_resource_usage(self):
        """Test creating resource usage."""
        usage = ResourceUsage(
            gpu_memory=0.75,
            cpu_usage=0.45,
            memory_usage=0.60
        )

        assert usage.gpu_memory == 0.75
        assert usage.cpu_usage == 0.45
        assert usage.memory_usage == 0.60

    def test_partial_resource_usage(self):
        """Test creating partial resource usage."""
        usage = ResourceUsage(gpu_memory=0.8)

        assert usage.gpu_memory == 0.8
        assert usage.cpu_usage is None
        assert usage.memory_usage is None
