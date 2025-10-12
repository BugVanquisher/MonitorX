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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
from datetime import datetime
import uuid


@dataclass
class MetricPoint:
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    gpu_memory: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


@dataclass
class InferenceMetric:
    model_id: str
    model_type: Literal["llm", "cv", "tabular"]
    request_id: str
    latency: float
    timestamp: datetime = field(default_factory=datetime.now)
    throughput: Optional[float] = None
    error_rate: Optional[float] = None
    resource_usage: Optional[ResourceUsage] = None
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DriftMetric:
    model_id: str
    drift_type: Literal["data", "concept"]
    severity: Literal["low", "medium", "high", "critical"]
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = ""
    alert_type: Literal["latency", "error_rate", "drift", "resource_usage"] = "latency"
    severity: Literal["low", "medium", "high", "critical"] = "low"
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class Thresholds:
    latency: float = 1000.0
    error_rate: float = 0.05
    gpu_memory: float = 0.8
    cpu_usage: float = 0.8
    memory_usage: float = 0.8


@dataclass
class ModelConfig:
    id: str
    name: str
    model_type: Literal["llm", "cv", "tabular"]
    version: str
    environment: Literal["dev", "staging", "prod"]
    thresholds: Thresholds = field(default_factory=Thresholds)


@dataclass
class SummaryStats:
    total_requests: int = 0
    average_latency: float = 0.0
    error_rate: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    active_alerts: int = 0


@dataclass
class DashboardData:
    models: List[ModelConfig] = field(default_factory=list)
    metrics: List[InferenceMetric] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    summary: SummaryStats = field(default_factory=SummaryStats)