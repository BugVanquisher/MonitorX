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

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta

from .models import (
    InferenceMetricRequest, DriftMetricRequest, ModelConfigRequest,
    AlertResponse, SummaryStatsResponse, MetricsQueryParams,
    AlertResolveRequest, HealthResponse
)
from ..services.metrics_collector import MetricsCollector
from ..services.storage import InfluxDBStorage
from ..types import InferenceMetric, DriftMetric, ModelConfig, ResourceUsage, Thresholds

# Global instances (will be properly injected in production)
metrics_collector = MetricsCollector()

# Import storage from server to use the connected instance
def get_storage():
    from ..server import storage
    return storage

router = APIRouter(prefix="/api/v1")


@router.post("/metrics/inference", status_code=201)
async def collect_inference_metric(metric_data: InferenceMetricRequest):
    """Collect an inference metric."""
    try:
        # Convert request model to internal model
        resource_usage = None
        if metric_data.resource_usage:
            resource_usage = ResourceUsage(
                gpu_memory=metric_data.resource_usage.gpu_memory,
                cpu_usage=metric_data.resource_usage.cpu_usage,
                memory_usage=metric_data.resource_usage.memory_usage
            )

        metric = InferenceMetric(
            model_id=metric_data.model_id,
            model_type=metric_data.model_type,
            request_id=metric_data.request_id,
            latency=metric_data.latency,
            throughput=metric_data.throughput,
            error_rate=metric_data.error_rate,
            resource_usage=resource_usage,
            tags=metric_data.tags
        )

        # Collect metric
        await metrics_collector.collect_inference_metric(metric)

        # Store in InfluxDB
        await get_storage().write_inference_metric(metric)

        return {"status": "success", "message": "Metric collected successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect metric: {str(e)}")


@router.post("/metrics/drift", status_code=201)
async def collect_drift_metric(drift_data: DriftMetricRequest):
    """Collect a drift detection metric."""
    try:
        drift_metric = DriftMetric(
            model_id=drift_data.model_id,
            drift_type=drift_data.drift_type,
            severity=drift_data.severity,
            confidence=drift_data.confidence,
            tags=drift_data.tags
        )

        # Collect drift metric
        await metrics_collector.collect_drift_metric(drift_metric)

        # Store in InfluxDB
        await get_storage().write_drift_metric(drift_metric)

        return {"status": "success", "message": "Drift metric collected successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect drift metric: {str(e)}")


@router.post("/models", status_code=201)
async def register_model(model_data: ModelConfigRequest):
    """Register a new model configuration."""
    try:
        thresholds = Thresholds(
            latency=model_data.thresholds.latency,
            error_rate=model_data.thresholds.error_rate,
            gpu_memory=model_data.thresholds.gpu_memory,
            cpu_usage=model_data.thresholds.cpu_usage,
            memory_usage=model_data.thresholds.memory_usage
        )

        model_config = ModelConfig(
            id=model_data.id,
            name=model_data.name,
            model_type=model_data.model_type,
            version=model_data.version,
            environment=model_data.environment,
            thresholds=thresholds
        )

        metrics_collector.register_model(model_config)

        return {"status": "success", "message": "Model registered successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register model: {str(e)}")


@router.get("/models")
async def get_models():
    """Get all registered models."""
    try:
        models = metrics_collector.get_model_configs()
        return {"models": models}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")


@router.get("/metrics/inference")
async def get_inference_metrics(
    model_id: Optional[str] = Query(None),
    since_hours: int = Query(24, gt=0, le=168),
    limit: int = Query(1000, gt=0, le=10000)
):
    """Get inference metrics."""
    try:
        since = datetime.now() - timedelta(hours=since_hours) if since_hours else None
        metrics = metrics_collector.get_metrics(model_id=model_id, since=since)

        # Limit results
        metrics = metrics[:limit]

        return {"metrics": metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.get("/metrics/drift")
async def get_drift_metrics(
    model_id: Optional[str] = Query(None),
    since_hours: int = Query(168, gt=0, le=168),  # Default 7 days
    limit: int = Query(100, gt=0, le=1000)
):
    """Get drift detection metrics."""
    try:
        since = datetime.now() - timedelta(hours=since_hours)
        drift_metrics = metrics_collector.get_drift_metrics(model_id=model_id, since=since)

        # Limit results
        drift_metrics = drift_metrics[:limit]

        return {"drift_metrics": drift_metrics}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get drift metrics: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    model_id: Optional[str] = Query(None),
    since_hours: int = Query(168, gt=0, le=168),  # Default 7 days
    resolved: Optional[bool] = Query(None),
    limit: int = Query(100, gt=0, le=1000)
):
    """Get alerts."""
    try:
        since = datetime.now() - timedelta(hours=since_hours)
        alerts = metrics_collector.get_alerts(
            model_id=model_id,
            since=since,
            resolved=resolved
        )

        # Limit results and convert to response model
        alerts = alerts[:limit]
        return [
            AlertResponse(
                id=alert.id,
                model_id=alert.model_id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=alert.message,
                timestamp=alert.timestamp,
                resolved=alert.resolved,
                resolved_at=alert.resolved_at
            ) for alert in alerts
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


@router.post("/alerts/resolve")
async def resolve_alert(request: AlertResolveRequest):
    """Mark an alert as resolved."""
    try:
        success = await metrics_collector.resolve_alert(request.alert_id)
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {"status": "success", "message": "Alert resolved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}")


@router.get("/summary", response_model=SummaryStatsResponse)
async def get_summary_stats(
    model_id: Optional[str] = Query(None),
    since_hours: int = Query(24, gt=0, le=168)
):
    """Get summary statistics."""
    try:
        since = datetime.now() - timedelta(hours=since_hours)
        stats = metrics_collector.get_summary_stats(model_id=model_id, since=since)

        return SummaryStatsResponse(
            total_requests=stats.total_requests,
            average_latency=stats.average_latency,
            error_rate=stats.error_rate,
            p95_latency=stats.p95_latency,
            p99_latency=stats.p99_latency,
            active_alerts=stats.active_alerts
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary stats: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        services = {"api": "healthy"}

        # Check InfluxDB connection
        try:
            if storage.client:
                health = storage.client.health()
                services["influxdb"] = "healthy" if health.status == "pass" else "unhealthy"
            else:
                services["influxdb"] = "not_connected"
        except Exception:
            services["influxdb"] = "unhealthy"

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(),
            version="0.1.0",
            services=services
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    model_id: Optional[str] = Query(None),
    since_hours: int = Query(6, gt=0, le=168),
    window: str = Query("5m", regex="^[0-9]+[smh]$")
):
    """Get aggregated metrics over time windows."""
    try:
        since = datetime.now() - timedelta(hours=since_hours)
        end_time = datetime.now()

        aggregated = await get_storage().get_aggregated_metrics(
            model_id=model_id,
            start_time=since,
            end_time=end_time,
            window=window
        )

        return {"aggregated_metrics": aggregated}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get aggregated metrics: {str(e)}")