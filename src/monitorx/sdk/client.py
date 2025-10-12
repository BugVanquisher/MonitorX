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

import httpx
import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import uuid
import time
from collections import deque
from dataclasses import asdict
from loguru import logger

from ..types import InferenceMetric, DriftMetric, ModelConfig, ResourceUsage


class CircuitBreaker:
    """Circuit breaker implementation for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.reset()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise e

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open state")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.reset()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise e

    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"
        logger.info("Circuit breaker reset to CLOSED state")


class MonitorXClient:
    """Python SDK for MonitorX API integration with enhanced error handling."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        enable_circuit_breaker: bool = True,
        buffer_size: int = 1000
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.session = None

        # Circuit breaker
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None

        # Metric buffering for offline scenarios
        self.buffer_size = buffer_size
        self.metric_buffer: deque = deque(maxlen=buffer_size)
        self.buffer_enabled = False

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

    def enable_buffering(self) -> None:
        """Enable metric buffering for offline scenarios."""
        self.buffer_enabled = True
        logger.info("Metric buffering enabled")

    def disable_buffering(self) -> None:
        """Disable metric buffering."""
        self.buffer_enabled = False
        logger.info("Metric buffering disabled")

    def get_buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self.metric_buffer)

    async def flush_buffer(self) -> Dict[str, int]:
        """Flush all buffered metrics to the server."""
        if not self.metric_buffer:
            return {"flushed": 0, "failed": 0}

        flushed = 0
        failed = 0

        # Temporarily disable buffering during flush
        original_buffer_state = self.buffer_enabled
        self.buffer_enabled = False

        try:
            while self.metric_buffer:
                metric_data = self.metric_buffer.popleft()
                metric_type = metric_data.get("type")

                try:
                    if metric_type == "inference":
                        metric = InferenceMetric(**metric_data["data"])
                        if self.session:
                            await self._collect_inference_metric_request(self.session, metric)
                        else:
                            async with httpx.AsyncClient(timeout=self.timeout) as client:
                                await self._collect_inference_metric_request(client, metric)
                        flushed += 1
                    elif metric_type == "drift":
                        drift_metric = DriftMetric(**metric_data["data"])
                        if self.session:
                            await self._collect_drift_metric_request(self.session, drift_metric)
                        else:
                            async with httpx.AsyncClient(timeout=self.timeout) as client:
                                await self._collect_drift_metric_request(client, drift_metric)
                        flushed += 1
                except Exception as e:
                    logger.error(f"Failed to flush metric: {e}")
                    failed += 1

            logger.info(f"Buffer flush complete: {flushed} flushed, {failed} failed")
        finally:
            # Restore original buffer state
            self.buffer_enabled = original_buffer_state

        return {"flushed": flushed, "failed": failed}

    async def _retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute function with exponential backoff retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                if self.circuit_breaker:
                    return await self.circuit_breaker.call_async(func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    # Calculate backoff time with exponential increase
                    backoff_time = self.retry_backoff * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")

        raise last_exception

    async def collect_inference_metrics_batch(
        self,
        metrics: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Collect multiple inference metrics in a single batch request.

        Args:
            metrics: List of metric dictionaries with required fields

        Returns:
            Dictionary with success and failure counts
        """
        if not metrics:
            return {"success": 0, "failed": 0}

        # If buffering is enabled and we're offline, buffer the metrics
        if self.buffer_enabled:
            for metric_data in metrics:
                self.metric_buffer.append({"type": "inference", "data": metric_data})
            logger.debug(f"Buffered {len(metrics)} inference metrics")
            return {"success": len(metrics), "failed": 0}

        success = 0
        failed = 0

        # Process metrics in parallel for better performance
        tasks = []
        for metric_data in metrics:
            # Fill in defaults
            if "request_id" not in metric_data:
                metric_data["request_id"] = str(uuid.uuid4())
            if "tags" not in metric_data:
                metric_data["tags"] = {}

            metric = InferenceMetric(**metric_data)
            if self.session:
                task = self._collect_inference_metric_request_with_retry(self.session, metric)
            else:
                task = self._collect_single_metric_no_session(metric, "inference")
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed += 1
            elif result:
                success += 1
            else:
                failed += 1

        logger.info(f"Batch collection complete: {success} succeeded, {failed} failed")
        return {"success": success, "failed": failed}

    async def _collect_single_metric_no_session(
        self,
        metric: InferenceMetric,
        metric_type: str
    ) -> bool:
        """Helper to collect a single metric without persistent session."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if metric_type == "inference":
                return await self._collect_inference_metric_request_with_retry(client, metric)
            else:
                return await self._collect_drift_metric_request_with_retry(client, metric)

    async def _collect_inference_metric_request_with_retry(
        self,
        client: httpx.AsyncClient,
        metric: InferenceMetric
    ) -> bool:
        """Collect inference metric with retry logic."""
        try:
            return await self._retry_with_backoff(
                self._collect_inference_metric_request,
                client,
                metric
            )
        except Exception as e:
            logger.error(f"Failed to collect inference metric after retries: {e}")
            # If buffering is enabled, add to buffer
            if self.buffer_enabled:
                self.metric_buffer.append({
                    "type": "inference",
                    "data": asdict(metric)
                })
            return False

    async def _collect_drift_metric_request_with_retry(
        self,
        client: httpx.AsyncClient,
        drift_metric: DriftMetric
    ) -> bool:
        """Collect drift metric with retry logic."""
        try:
            return await self._retry_with_backoff(
                self._collect_drift_metric_request,
                client,
                drift_metric
            )
        except Exception as e:
            logger.error(f"Failed to collect drift metric after retries: {e}")
            # If buffering is enabled, add to buffer
            if self.buffer_enabled:
                self.metric_buffer.append({
                    "type": "drift",
                    "data": asdict(drift_metric)
                })
            return False

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
        """Collect an inference metric with automatic retry."""
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

        # If buffering is enabled, buffer immediately
        if self.buffer_enabled:
            self.metric_buffer.append({
                "type": "inference",
                "data": asdict(metric)
            })
            logger.debug(f"Buffered inference metric for model {model_id}")
            return True

        if not self.session:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                return await self._collect_inference_metric_request_with_retry(client, metric)
        else:
            return await self._collect_inference_metric_request_with_retry(self.session, metric)

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
        """Collect a drift detection metric with automatic retry."""
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
                return await self._collect_drift_metric_request_with_retry(client, drift_metric)
        else:
            return await self._collect_drift_metric_request_with_retry(self.session, drift_metric)

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