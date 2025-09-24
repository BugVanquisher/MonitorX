from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from datetime import datetime


class ResourceUsageModel(BaseModel):
    gpu_memory: Optional[float] = Field(None, ge=0.0, le=1.0, description="GPU memory usage (0-1)")
    cpu_usage: Optional[float] = Field(None, ge=0.0, le=1.0, description="CPU usage (0-1)")
    memory_usage: Optional[float] = Field(None, ge=0.0, le=1.0, description="Memory usage (0-1)")


class InferenceMetricRequest(BaseModel):
    model_id: str = Field(..., description="Unique identifier for the model")
    model_type: Literal["llm", "cv", "tabular"] = Field(..., description="Type of ML model")
    request_id: str = Field(..., description="Unique identifier for the request")
    latency: float = Field(..., gt=0, description="Request latency in milliseconds")
    throughput: Optional[float] = Field(None, gt=0, description="Requests per second")
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Error rate (0-1)")
    resource_usage: Optional[ResourceUsageModel] = None
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")


class DriftMetricRequest(BaseModel):
    model_id: str = Field(..., description="Unique identifier for the model")
    drift_type: Literal["data", "concept"] = Field(..., description="Type of drift detected")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Drift severity")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    tags: Dict[str, str] = Field(default_factory=dict, description="Custom tags")


class ThresholdsModel(BaseModel):
    latency: float = Field(1000.0, gt=0, description="Latency threshold in milliseconds")
    error_rate: float = Field(0.05, ge=0.0, le=1.0, description="Error rate threshold (0-1)")
    gpu_memory: float = Field(0.8, ge=0.0, le=1.0, description="GPU memory threshold (0-1)")
    cpu_usage: float = Field(0.8, ge=0.0, le=1.0, description="CPU usage threshold (0-1)")
    memory_usage: float = Field(0.8, ge=0.0, le=1.0, description="Memory usage threshold (0-1)")


class ModelConfigRequest(BaseModel):
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable model name")
    model_type: Literal["llm", "cv", "tabular"] = Field(..., description="Type of ML model")
    version: str = Field(..., description="Model version")
    environment: Literal["dev", "staging", "prod"] = Field(..., description="Deployment environment")
    thresholds: ThresholdsModel = Field(default_factory=ThresholdsModel, description="Alert thresholds")


class AlertResponse(BaseModel):
    id: str
    model_id: str
    alert_type: Literal["latency", "error_rate", "drift", "resource_usage"]
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    timestamp: datetime
    resolved: bool
    resolved_at: Optional[datetime] = None


class SummaryStatsResponse(BaseModel):
    total_requests: int
    average_latency: float
    error_rate: float
    p95_latency: float
    p99_latency: float
    active_alerts: int


class MetricsQueryParams(BaseModel):
    model_id: Optional[str] = None
    since_hours: int = Field(24, gt=0, le=168, description="Hours to look back (max 7 days)")
    limit: int = Field(1000, gt=0, le=10000, description="Maximum number of results")


class AlertResolveRequest(BaseModel):
    alert_id: str = Field(..., description="ID of the alert to resolve")


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]