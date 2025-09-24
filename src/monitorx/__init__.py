"""
MonitorX: ML/AI Infrastructure Observability Platform

The missing piece between ML model deployment and production reliability.
"""

from .types import (
    InferenceMetric,
    DriftMetric,
    Alert,
    ModelConfig,
    Thresholds,
    ResourceUsage,
    SummaryStats
)
from .sdk import MonitorXClient, MonitorXContext, monitor_inference, monitor_drift
from .services import MetricsCollector, AlertingService, EmailChannel, SlackChannel

__version__ = "0.1.0"
__author__ = "MonitorX Team"

__all__ = [
    # Types
    "InferenceMetric",
    "DriftMetric",
    "Alert",
    "ModelConfig",
    "Thresholds",
    "ResourceUsage",
    "SummaryStats",

    # SDK
    "MonitorXClient",
    "MonitorXContext",
    "monitor_inference",
    "monitor_drift",

    # Services
    "MetricsCollector",
    "AlertingService",
    "EmailChannel",
    "SlackChannel",
]