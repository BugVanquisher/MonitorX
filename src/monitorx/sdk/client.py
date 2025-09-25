import httpx
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
from loguru import logger

from ..types import InferenceMetric, DriftMetric, ModelConfig, ResourceUsage


class MonitorXClient:
    """Python SDK for MonitorX API integration."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def register_model(self, config: ModelConfig) -> bool:
        """Register a model configuration."""
        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._register_model_request(client, config)
        else:
            return await self._register_model_request(self.session, config)

    async def _register_model_request(self, client: httpx.AsyncClient, config: ModelConfig) -> bool:
        """Internal method to make register model request."""
        try:
            payload = {
                "id": config.id,
                "name": config.name,
                "model_type": config.model_type,
                "version": config.version,
                "environment": config.environment,
                "thresholds": {
                    "latency": config.thresholds.latency,
                    "error_rate": config.thresholds.error_rate,
                    "gpu_memory": config.thresholds.gpu_memory,
                    "cpu_usage": config.thresholds.cpu_usage,
                    "memory_usage": config.thresholds.memory_usage,
                }
            }

            response = await client.post(
                f"{self.base_url}/api/v1/models",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            logger.info(f"Successfully registered model: {config.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to register model {config.name}: {e}")
            return False

    async def collect_inference_metric(
        self,
        model_id: str,
        model_type: str,
        latency: float,
        request_id: Optional[str] = None,
        throughput: Optional[float] = None,
        error_rate: Optional[float] = None,
        resource_usage: Optional[ResourceUsage] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """Collect an inference metric."""
        if not request_id:
            request_id = str(uuid.uuid4())

        if not tags:
            tags = {}

        metric = InferenceMetric(
            model_id=model_id,
            model_type=model_type,  # type: ignore
            request_id=request_id,
            latency=latency,
            throughput=throughput,
            error_rate=error_rate,
            resource_usage=resource_usage,
            tags=tags
        )

        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._collect_inference_metric_request(client, metric)
        else:
            return await self._collect_inference_metric_request(self.session, metric)

    async def _collect_inference_metric_request(
        self, client: httpx.AsyncClient, metric: InferenceMetric
    ) -> bool:
        """Internal method to make collect inference metric request."""
        try:
            payload = {
                "model_id": metric.model_id,
                "model_type": metric.model_type,
                "request_id": metric.request_id,
                "latency": metric.latency,
                "tags": metric.tags
            }

            if metric.throughput is not None:
                payload["throughput"] = metric.throughput

            if metric.error_rate is not None:
                payload["error_rate"] = metric.error_rate

            if metric.resource_usage:
                payload["resource_usage"] = {
                    "gpu_memory": metric.resource_usage.gpu_memory,
                    "cpu_usage": metric.resource_usage.cpu_usage,
                    "memory_usage": metric.resource_usage.memory_usage,
                }

            response = await client.post(
                f"{self.base_url}/api/v1/metrics/inference",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            logger.debug(f"Successfully collected metric for model {metric.model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect metric for model {metric.model_id}: {e}")
            return False

    async def collect_drift_metric(
        self,
        model_id: str,
        drift_type: str,
        severity: str,
        confidence: float,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """Collect a drift detection metric."""
        if not tags:
            tags = {}

        drift_metric = DriftMetric(
            model_id=model_id,
            drift_type=drift_type,  # type: ignore
            severity=severity,  # type: ignore
            confidence=confidence,
            tags=tags
        )

        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._collect_drift_metric_request(client, drift_metric)
        else:
            return await self._collect_drift_metric_request(self.session, drift_metric)

    async def _collect_drift_metric_request(
        self, client: httpx.AsyncClient, drift_metric: DriftMetric
    ) -> bool:
        """Internal method to make collect drift metric request."""
        try:
            payload = {
                "model_id": drift_metric.model_id,
                "drift_type": drift_metric.drift_type,
                "severity": drift_metric.severity,
                "confidence": drift_metric.confidence,
                "tags": drift_metric.tags
            }

            response = await client.post(
                f"{self.base_url}/api/v1/metrics/drift",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            logger.info(f"Successfully collected drift metric for model {drift_metric.model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect drift metric for model {drift_metric.model_id}: {e}")
            return False

    async def get_summary_stats(
        self,
        model_id: Optional[str] = None,
        since_hours: int = 24
    ) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._get_summary_stats_request(client, model_id, since_hours)
        else:
            return await self._get_summary_stats_request(self.session, model_id, since_hours)

    async def _get_summary_stats_request(
        self, client: httpx.AsyncClient, model_id: Optional[str], since_hours: int
    ) -> Dict[str, Any]:
        """Internal method to get summary stats."""
        try:
            params = {"since_hours": since_hours}
            if model_id:
                params["model_id"] = model_id

            response = await client.get(
                f"{self.base_url}/api/v1/summary",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            return {}

    async def get_alerts(
        self,
        model_id: Optional[str] = None,
        since_hours: int = 168,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts."""
        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._get_alerts_request(client, model_id, since_hours, resolved)
        else:
            return await self._get_alerts_request(self.session, model_id, since_hours, resolved)

    async def _get_alerts_request(
        self,
        client: httpx.AsyncClient,
        model_id: Optional[str],
        since_hours: int,
        resolved: Optional[bool]
    ) -> List[Dict[str, Any]]:
        """Internal method to get alerts."""
        try:
            params = {"since_hours": since_hours}
            if model_id:
                params["model_id"] = model_id
            if resolved is not None:
                params["resolved"] = resolved

            response = await client.get(
                f"{self.base_url}/api/v1/alerts",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []

    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._resolve_alert_request(client, alert_id)
        else:
            return await self._resolve_alert_request(self.session, alert_id)

    async def _resolve_alert_request(self, client: httpx.AsyncClient, alert_id: str) -> bool:
        """Internal method to resolve alert."""
        try:
            payload = {"alert_id": alert_id}

            response = await client.post(
                f"{self.base_url}/api/v1/alerts/resolve",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()
            logger.info(f"Successfully resolved alert {alert_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._health_check_request(client)
        else:
            return await self._health_check_request(self.session)

    async def _health_check_request(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Internal method to check health."""
        try:
            response = await client.get(
                f"{self.base_url}/api/v1/health",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}