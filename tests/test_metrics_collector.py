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

"""Tests for MetricsCollector."""
import pytest
from datetime import datetime, timedelta

from monitorx.services.metrics_collector import MetricsCollector
from monitorx.types import InferenceMetric, DriftMetric, ModelConfig, Alert


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_register_model(self, metrics_collector, sample_model_config):
        """Test model registration."""
        metrics_collector.register_model(sample_model_config)

        configs = metrics_collector.get_model_configs()
        assert len(configs) == 1
        assert configs[0].id == "test-model-1"
        assert configs[0].name == "Test Model"

    @pytest.mark.asyncio
    async def test_collect_inference_metric(self, metrics_collector, sample_inference_metric):
        """Test collecting an inference metric."""
        await metrics_collector.collect_inference_metric(sample_inference_metric)

        metrics = metrics_collector.get_metrics()
        assert len(metrics) == 1
        assert metrics[0].model_id == "test-model-1"
        assert metrics[0].latency == 500.0

    @pytest.mark.asyncio
    async def test_collect_drift_metric(self, metrics_collector, sample_drift_metric):
        """Test collecting a drift metric."""
        await metrics_collector.collect_drift_metric(sample_drift_metric)

        drift_metrics = metrics_collector.get_drift_metrics()
        assert len(drift_metrics) == 1
        assert drift_metrics[0].model_id == "test-model-1"
        assert drift_metrics[0].drift_type == "data"

    @pytest.mark.asyncio
    async def test_latency_threshold_alert(
        self, metrics_collector, sample_model_config, high_latency_metric
    ):
        """Test that high latency generates an alert."""
        metrics_collector.register_model(sample_model_config)
        await metrics_collector.collect_inference_metric(high_latency_metric)

        alerts = metrics_collector.get_alerts()
        assert len(alerts) >= 1

        latency_alerts = [a for a in alerts if a.alert_type == "latency"]
        assert len(latency_alerts) == 1
        assert latency_alerts[0].model_id == "test-model-1"
        assert latency_alerts[0].severity in ["medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_error_rate_threshold_alert(
        self, metrics_collector, sample_model_config, high_error_rate_metric
    ):
        """Test that high error rate generates an alert."""
        metrics_collector.register_model(sample_model_config)
        await metrics_collector.collect_inference_metric(high_error_rate_metric)

        alerts = metrics_collector.get_alerts()
        error_alerts = [a for a in alerts if a.alert_type == "error_rate"]
        assert len(error_alerts) == 1
        assert error_alerts[0].severity in ["medium", "high", "critical"]

    @pytest.mark.asyncio
    async def test_high_severity_drift_alert(self, metrics_collector):
        """Test that high/critical drift generates alerts."""
        high_drift = DriftMetric(
            model_id="test-model-1",
            drift_type="concept",
            severity="critical",
            confidence=0.95
        )

        await metrics_collector.collect_drift_metric(high_drift)

        alerts = metrics_collector.get_alerts()
        drift_alerts = [a for a in alerts if a.alert_type == "drift"]
        assert len(drift_alerts) == 1
        assert drift_alerts[0].severity == "critical"

    def test_get_metrics_filtered_by_model(self, metrics_collector):
        """Test filtering metrics by model_id."""
        metric1 = InferenceMetric(
            model_id="model-1", model_type="llm", request_id="req-1", latency=100.0
        )
        metric2 = InferenceMetric(
            model_id="model-2", model_type="cv", request_id="req-2", latency=200.0
        )

        metrics_collector.metrics.append(metric1)
        metrics_collector.metrics.append(metric2)

        filtered = metrics_collector.get_metrics(model_id="model-1")
        assert len(filtered) == 1
        assert filtered[0].model_id == "model-1"

    def test_get_metrics_filtered_by_time(self, metrics_collector):
        """Test filtering metrics by timestamp."""
        old_metric = InferenceMetric(
            model_id="model-1",
            model_type="llm",
            request_id="req-1",
            latency=100.0,
            timestamp=datetime.now() - timedelta(hours=48)
        )
        recent_metric = InferenceMetric(
            model_id="model-1",
            model_type="llm",
            request_id="req-2",
            latency=200.0,
            timestamp=datetime.now()
        )

        metrics_collector.metrics.append(old_metric)
        metrics_collector.metrics.append(recent_metric)

        since = datetime.now() - timedelta(hours=24)
        filtered = metrics_collector.get_metrics(since=since)
        assert len(filtered) == 1
        assert filtered[0].request_id == "req-2"

    def test_get_alerts_filtered_by_resolved_status(self, metrics_collector):
        """Test filtering alerts by resolved status."""
        alert1 = Alert(
            model_id="model-1",
            alert_type="latency",
            severity="high",
            message="High latency",
            resolved=False
        )
        alert2 = Alert(
            model_id="model-1",
            alert_type="error_rate",
            severity="medium",
            message="High error rate",
            resolved=True
        )

        metrics_collector.alerts.append(alert1)
        metrics_collector.alerts.append(alert2)

        unresolved = metrics_collector.get_alerts(resolved=False)
        assert len(unresolved) == 1
        assert unresolved[0].alert_type == "latency"

        resolved = metrics_collector.get_alerts(resolved=True)
        assert len(resolved) == 1
        assert resolved[0].alert_type == "error_rate"

    def test_calculate_severity(self, metrics_collector):
        """Test severity calculation based on threshold ratio."""
        # Low severity (1.0-1.2x threshold)
        assert metrics_collector._calculate_severity(110.0, 100.0) == "low"

        # Medium severity (1.2-1.5x threshold)
        assert metrics_collector._calculate_severity(130.0, 100.0) == "medium"

        # High severity (1.5-2.0x threshold)
        assert metrics_collector._calculate_severity(175.0, 100.0) == "high"

        # Critical severity (>=2.0x threshold)
        assert metrics_collector._calculate_severity(250.0, 100.0) == "critical"

    def test_get_summary_stats(self, metrics_collector):
        """Test summary statistics calculation."""
        # Add multiple metrics
        for i in range(10):
            metric = InferenceMetric(
                model_id="model-1",
                model_type="llm",
                request_id=f"req-{i}",
                latency=100.0 + (i * 50),
                error_rate=0.01
            )
            metrics_collector.metrics.append(metric)

        stats = metrics_collector.get_summary_stats()
        assert stats.total_requests == 10
        assert stats.average_latency > 0
        assert stats.p95_latency > stats.average_latency
        assert stats.p99_latency >= stats.p95_latency

    def test_get_summary_stats_empty(self, metrics_collector):
        """Test summary stats with no metrics."""
        stats = metrics_collector.get_summary_stats()
        assert stats.total_requests == 0
        assert stats.average_latency == 0.0
        assert stats.error_rate == 0.0

    @pytest.mark.asyncio
    async def test_resolve_alert(self, metrics_collector):
        """Test resolving an alert."""
        alert = Alert(
            model_id="model-1",
            alert_type="latency",
            severity="high",
            message="High latency",
            resolved=False
        )
        metrics_collector.alerts.append(alert)

        success = await metrics_collector.resolve_alert(alert.id)
        assert success is True
        assert alert.resolved is True
        assert alert.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self, metrics_collector):
        """Test resolving a non-existent alert."""
        success = await metrics_collector.resolve_alert("fake-alert-id")
        assert success is False

    def test_alert_callbacks(self, metrics_collector, sample_model_config):
        """Test that alert callbacks are called."""
        callback_called = []

        def alert_callback(alert: Alert):
            callback_called.append(alert)

        metrics_collector.add_alert_callback(alert_callback)
        metrics_collector.register_model(sample_model_config)

        # This should trigger an alert due to high latency
        high_latency = InferenceMetric(
            model_id="test-model-1",
            model_type="llm",
            request_id="req-999",
            latency=3000.0
        )

        import asyncio
        asyncio.run(metrics_collector.collect_inference_metric(high_latency))

        assert len(callback_called) >= 1

    def test_metric_callbacks(self, metrics_collector, sample_inference_metric):
        """Test that metric callbacks are called."""
        callback_called = []

        def metric_callback(metric: InferenceMetric):
            callback_called.append(metric)

        metrics_collector.add_metric_callback(metric_callback)

        import asyncio
        asyncio.run(metrics_collector.collect_inference_metric(sample_inference_metric))

        assert len(callback_called) == 1
        assert callback_called[0].model_id == "test-model-1"

    def test_max_metrics_limit(self):
        """Test that metrics deque respects maxlen."""
        collector = MetricsCollector(max_metrics=5)

        # Add more metrics than the limit
        for i in range(10):
            metric = InferenceMetric(
                model_id="model-1",
                model_type="llm",
                request_id=f"req-{i}",
                latency=100.0
            )
            collector.metrics.append(metric)

        # Should only keep the last 5
        assert len(collector.metrics) == 5
