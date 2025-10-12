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

"""Tests for enhanced SDK features (batch, retry, circuit breaker, buffering)."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx
import asyncio

from monitorx.sdk.client import MonitorXClient, CircuitBreaker
from monitorx.types import InferenceMetric, DriftMetric


@pytest.fixture
def client():
    """Create MonitorX client with enhanced features."""
    return MonitorXClient(
        base_url="http://localhost:8000",
        max_retries=3,
        retry_backoff=0.1,  # Faster for testing
        enable_circuit_breaker=True,
        buffer_size=100
    )


class TestCircuitBreaker:
    """Test Circuit Breaker implementation."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes correctly."""
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3)

        async def failing_func():
            raise Exception("Test failure")

        # Trigger failures
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call_async(failing_func)

        # Circuit should be open now
        assert cb.state == "open"

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects calls when open."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)

        async def failing_func():
            raise Exception("Test failure")

        # Trigger failure to open circuit
        with pytest.raises(Exception):
            await cb.call_async(failing_func)

        # Next call should be rejected
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            await cb.call_async(failing_func)

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker transitions to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        async def failing_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # Open circuit
        with pytest.raises(Exception):
            await cb.call_async(failing_func)

        assert cb.state == "open"

        # Wait for recovery timeout
        await asyncio.sleep(0.2)

        # Next call should transition to half-open and succeed
        result = await cb.call_async(success_func)
        assert result == "success"
        assert cb.state == "closed"


class TestBatchCollection:
    """Test batch metric collection."""

    @pytest.mark.asyncio
    async def test_batch_inference_metrics_success(self, client):
        """Test successful batch metric collection."""
        metrics = [
            {"model_id": "model-1", "model_type": "llm", "latency": 100.0},
            {"model_id": "model-2", "model_type": "cv", "latency": 50.0},
            {"model_id": "model-3", "model_type": "tabular", "latency": 25.0},
        ]

        with patch.object(client, '_collect_inference_metric_request_with_retry',
                         new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = True

            async with client:
                result = await client.collect_inference_metrics_batch(metrics)

            assert result["success"] == 3
            assert result["failed"] == 0
            assert mock_collect.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_empty_list(self, client):
        """Test batch collection with empty list."""
        result = await client.collect_inference_metrics_batch([])

        assert result["success"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_with_failures(self, client):
        """Test batch collection with some failures."""
        metrics = [
            {"model_id": "model-1", "model_type": "llm", "latency": 100.0},
            {"model_id": "model-2", "model_type": "cv", "latency": 50.0},
        ]

        with patch.object(client, '_collect_inference_metric_request_with_retry',
                         new_callable=AsyncMock) as mock_collect:
            # First succeeds, second fails
            mock_collect.side_effect = [True, False]

            async with client:
                result = await client.collect_inference_metrics_batch(metrics)

            assert result["success"] == 1
            assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_batch_generates_request_ids(self, client):
        """Test batch collection auto-generates request IDs."""
        metrics = [
            {"model_id": "model-1", "model_type": "llm", "latency": 100.0},
        ]

        with patch.object(client, '_collect_inference_metric_request_with_retry',
                         new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = True

            async with client:
                await client.collect_inference_metrics_batch(metrics)

            # Check that metric has request_id
            call_args = mock_collect.call_args[0]
            metric = call_args[1]  # Second argument is the metric
            assert metric.request_id is not None


class TestRetryWithBackoff:
    """Test retry with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self, client):
        """Test retry logic when first attempt succeeds."""
        with patch.object(client, '_collect_inference_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = True

            async with client:
                success = await client.collect_inference_metric(
                    model_id="test-model",
                    model_type="llm",
                    latency=100.0
                )

            assert success is True
            assert mock_collect.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self, client):
        """Test retry logic succeeds after initial failures."""
        with patch.object(client, '_collect_inference_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            # Fail twice, then succeed
            mock_collect.side_effect = [
                Exception("Network error"),
                Exception("Network error"),
                True
            ]

            async with client:
                success = await client.collect_inference_metric(
                    model_id="test-model",
                    model_type="llm",
                    latency=100.0
                )

            assert success is True
            assert mock_collect.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self, client):
        """Test retry logic fails after max attempts."""
        with patch.object(client, '_collect_inference_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            # Always fail
            mock_collect.side_effect = Exception("Network error")

            async with client:
                success = await client.collect_inference_metric(
                    model_id="test-model",
                    model_type="llm",
                    latency=100.0
                )

            # Should return False after all retries
            assert success is False
            assert mock_collect.call_count == client.max_retries


class TestBuffering:
    """Test metric buffering for offline scenarios."""

    @pytest.mark.asyncio
    async def test_buffering_enable_disable(self, client):
        """Test enabling and disabling buffering."""
        assert client.buffer_enabled is False

        client.enable_buffering()
        assert client.buffer_enabled is True

        client.disable_buffering()
        assert client.buffer_enabled is False

    @pytest.mark.asyncio
    async def test_metrics_buffered_when_enabled(self, client):
        """Test metrics are buffered when buffering is enabled."""
        client.enable_buffering()

        async with client:
            await client.collect_inference_metric(
                model_id="test-model",
                model_type="llm",
                latency=100.0
            )

        # Metric should be in buffer
        assert client.get_buffer_size() == 1

    @pytest.mark.asyncio
    async def test_batch_buffering(self, client):
        """Test batch metrics are buffered when enabled."""
        client.enable_buffering()

        metrics = [
            {"model_id": "model-1", "model_type": "llm", "latency": 100.0},
            {"model_id": "model-2", "model_type": "cv", "latency": 50.0},
        ]

        result = await client.collect_inference_metrics_batch(metrics)

        assert result["success"] == 2  # All "successful" (buffered)
        assert client.get_buffer_size() == 2

    @pytest.mark.asyncio
    async def test_buffer_flush(self, client):
        """Test flushing buffered metrics."""
        client.enable_buffering()

        # Buffer some metrics
        async with client:
            await client.collect_inference_metric(
                model_id="test-model",
                model_type="llm",
                latency=100.0
            )

        assert client.get_buffer_size() == 1

        # Mock the collection to succeed
        with patch.object(client, '_collect_inference_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = True

            client.disable_buffering()
            async with client:
                result = await client.flush_buffer()

        assert result["flushed"] == 1
        assert result["failed"] == 0
        assert client.get_buffer_size() == 0

    @pytest.mark.asyncio
    async def test_buffer_max_size(self):
        """Test buffer respects max size."""
        client = MonitorXClient(buffer_size=5)
        client.enable_buffering()

        # Add more than max
        for i in range(10):
            await client.collect_inference_metric(
                model_id="test-model",
                model_type="llm",
                latency=100.0 + i
            )

        # Should only keep last 5
        assert client.get_buffer_size() == 5

    @pytest.mark.asyncio
    async def test_failed_request_auto_buffers(self, client):
        """Test failed requests are auto-buffered when buffering enabled."""
        client.enable_buffering()

        with patch.object(client, '_collect_inference_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            # Simulate network failure
            mock_collect.side_effect = Exception("Network error")

            async with client:
                # This should fail and buffer
                await client.collect_inference_metric(
                    model_id="test-model",
                    model_type="llm",
                    latency=100.0
                )

        # Failed metric should be in buffer
        assert client.get_buffer_size() > 0


class TestEnhancedClientIntegration:
    """Integration tests for enhanced client features."""

    @pytest.mark.asyncio
    async def test_client_with_all_features(self):
        """Test client with all features enabled."""
        client = MonitorXClient(
            base_url="http://localhost:8000",
            api_key="test-key",
            max_retries=3,
            retry_backoff=0.1,
            enable_circuit_breaker=True,
            buffer_size=100
        )

        assert client.max_retries == 3
        assert client.circuit_breaker is not None
        assert client.buffer_size == 100

    @pytest.mark.asyncio
    async def test_circuit_breaker_can_be_disabled(self):
        """Test circuit breaker can be disabled."""
        client = MonitorXClient(
            base_url="http://localhost:8000",
            enable_circuit_breaker=False
        )

        assert client.circuit_breaker is None

    @pytest.mark.asyncio
    async def test_drift_metric_retry(self, client):
        """Test drift metrics also use retry logic."""
        with patch.object(client, '_collect_drift_metric_request',
                         new_callable=AsyncMock) as mock_collect:
            # Fail once, then succeed
            mock_collect.side_effect = [
                Exception("Network error"),
                True
            ]

            async with client:
                success = await client.collect_drift_metric(
                    model_id="test-model",
                    drift_type="data",
                    severity="high",
                    confidence=0.85
                )

            assert success is True
            assert mock_collect.call_count == 2
