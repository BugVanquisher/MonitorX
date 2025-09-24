import asyncio
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import uuid
import statistics

from ..types import (
    InferenceMetric, DriftMetric, Alert, ModelConfig,
    SummaryStats, Thresholds
)
from loguru import logger


class MetricsCollector:
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics)
        self.drift_metrics: deque = deque(maxlen=max_metrics)
        self.alerts: deque = deque(maxlen=1000)
        self.model_configs: Dict[str, ModelConfig] = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.metric_callbacks: List[Callable[[InferenceMetric], None]] = []

    def register_model(self, config: ModelConfig) -> None:
        """Register a new model configuration."""
        self.model_configs[config.id] = config
        logger.info(f"Registered model: {config.name} ({config.id})")

    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add callback to be called when alerts are generated."""
        self.alert_callbacks.append(callback)

    def add_metric_callback(self, callback: Callable[[InferenceMetric], None]) -> None:
        """Add callback to be called when metrics are collected."""
        self.metric_callbacks.append(callback)

    async def collect_inference_metric(self, metric: InferenceMetric) -> None:
        """Collect an inference metric and check thresholds."""
        self.metrics.append(metric)
        logger.debug(f"Collected metric for model {metric.model_id}")

        # Call callbacks
        for callback in self.metric_callbacks:
            try:
                callback(metric)
            except Exception as e:
                logger.error(f"Error in metric callback: {e}")

        # Check thresholds and generate alerts
        await self._check_thresholds(metric)

    async def collect_drift_metric(self, metric: DriftMetric) -> None:
        """Collect a drift detection metric."""
        self.drift_metrics.append(metric)
        logger.info(f"Drift detected for model {metric.model_id}: {metric.drift_type} "
                   f"({metric.severity}, confidence: {metric.confidence:.2%})")

        # Generate alert for high/critical drift
        if metric.severity in ["high", "critical"]:
            alert = Alert(
                model_id=metric.model_id,
                alert_type="drift",
                severity=metric.severity,
                message=f"{metric.drift_type.title()} drift detected with {metric.severity} "
                       f"severity (confidence: {metric.confidence:.1%})",
                timestamp=metric.timestamp
            )
            await self._generate_alert(alert)

    async def _check_thresholds(self, metric: InferenceMetric) -> None:
        """Check if metric exceeds configured thresholds."""
        model_config = self.model_configs.get(metric.model_id)
        if not model_config:
            logger.warning(f"No configuration found for model {metric.model_id}")
            return

        thresholds = model_config.thresholds
        alerts = []

        # Check latency threshold
        if metric.latency > thresholds.latency:
            severity = self._calculate_severity(metric.latency, thresholds.latency)
            alerts.append(Alert(
                model_id=metric.model_id,
                alert_type="latency",
                severity=severity,
                message=f"High latency detected: {metric.latency:.1f}ms "
                       f"(threshold: {thresholds.latency:.1f}ms)"
            ))

        # Check error rate threshold
        if metric.error_rate and metric.error_rate > thresholds.error_rate:
            severity = self._calculate_severity(metric.error_rate, thresholds.error_rate)
            alerts.append(Alert(
                model_id=metric.model_id,
                alert_type="error_rate",
                severity=severity,
                message=f"High error rate detected: {metric.error_rate:.1%} "
                       f"(threshold: {thresholds.error_rate:.1%})"
            ))

        # Check resource usage thresholds
        if metric.resource_usage:
            ru = metric.resource_usage

            if ru.gpu_memory and ru.gpu_memory > thresholds.gpu_memory:
                severity = self._calculate_severity(ru.gpu_memory, thresholds.gpu_memory)
                alerts.append(Alert(
                    model_id=metric.model_id,
                    alert_type="resource_usage",
                    severity=severity,
                    message=f"High GPU memory usage: {ru.gpu_memory:.1%} "
                           f"(threshold: {thresholds.gpu_memory:.1%})"
                ))

            if ru.cpu_usage and ru.cpu_usage > thresholds.cpu_usage:
                severity = self._calculate_severity(ru.cpu_usage, thresholds.cpu_usage)
                alerts.append(Alert(
                    model_id=metric.model_id,
                    alert_type="resource_usage",
                    severity=severity,
                    message=f"High CPU usage: {ru.cpu_usage:.1%} "
                           f"(threshold: {thresholds.cpu_usage:.1%})"
                ))

        # Generate all alerts
        for alert in alerts:
            await self._generate_alert(alert)

    async def _generate_alert(self, alert: Alert) -> None:
        """Generate and store an alert."""
        self.alerts.append(alert)
        logger.warning(f"Alert generated: {alert.message}")

        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _calculate_severity(self, value: float, threshold: float) -> str:
        """Calculate alert severity based on how much value exceeds threshold."""
        ratio = value / threshold
        if ratio >= 2.0:
            return "critical"
        elif ratio >= 1.5:
            return "high"
        elif ratio >= 1.2:
            return "medium"
        else:
            return "low"

    def get_metrics(self, model_id: Optional[str] = None,
                   since: Optional[datetime] = None) -> List[InferenceMetric]:
        """Get metrics with optional filtering."""
        filtered_metrics = list(self.metrics)

        if model_id:
            filtered_metrics = [m for m in filtered_metrics if m.model_id == model_id]

        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]

        return sorted(filtered_metrics, key=lambda x: x.timestamp, reverse=True)

    def get_drift_metrics(self, model_id: Optional[str] = None,
                         since: Optional[datetime] = None) -> List[DriftMetric]:
        """Get drift metrics with optional filtering."""
        filtered_metrics = list(self.drift_metrics)

        if model_id:
            filtered_metrics = [m for m in filtered_metrics if m.model_id == model_id]

        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp >= since]

        return sorted(filtered_metrics, key=lambda x: x.timestamp, reverse=True)

    def get_alerts(self, model_id: Optional[str] = None,
                  since: Optional[datetime] = None,
                  resolved: Optional[bool] = None) -> List[Alert]:
        """Get alerts with optional filtering."""
        filtered_alerts = list(self.alerts)

        if model_id:
            filtered_alerts = [a for a in filtered_alerts if a.model_id == model_id]

        if since:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= since]

        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]

        return sorted(filtered_alerts, key=lambda x: x.timestamp, reverse=True)

    def get_model_configs(self) -> List[ModelConfig]:
        """Get all registered model configurations."""
        return list(self.model_configs.values())

    def get_summary_stats(self, model_id: Optional[str] = None,
                         since: Optional[datetime] = None) -> SummaryStats:
        """Get summary statistics for metrics."""
        metrics = self.get_metrics(model_id, since)

        if not metrics:
            return SummaryStats()

        # Calculate basic stats
        total_requests = len(metrics)
        latencies = [m.latency for m in metrics]
        average_latency = statistics.mean(latencies) if latencies else 0.0

        # Calculate error rate
        error_metrics = [m for m in metrics if m.error_rate and m.error_rate > 0]
        error_rate = (
            statistics.mean([m.error_rate for m in error_metrics])
            if error_metrics else 0.0
        )

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p95_latency = (
            sorted_latencies[int(len(sorted_latencies) * 0.95)]
            if sorted_latencies else 0.0
        )
        p99_latency = (
            sorted_latencies[int(len(sorted_latencies) * 0.99)]
            if sorted_latencies else 0.0
        )

        # Count active alerts
        active_alerts = len([a for a in self.get_alerts(model_id, since) if not a.resolved])

        return SummaryStats(
            total_requests=total_requests,
            average_latency=average_latency,
            error_rate=error_rate,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            active_alerts=active_alerts
        )

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"Alert {alert_id} resolved")
                return True
        return False