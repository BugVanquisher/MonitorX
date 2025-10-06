"""Tests for SDK client."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx

from monitorx.sdk.client import MonitorXClient
from monitorx.types import ModelConfig, Thresholds, ResourceUsage


@pytest.fixture
def client():
    """Create MonitorX client."""
    return MonitorXClient(base_url="http://localhost:8000")


@pytest.fixture
def sample_model_config():
    """Create sample model config."""
    return ModelConfig(
        id="test-model",
        name="Test Model",
        model_type="llm",
        version="1.0.0",
        environment="dev",
        thresholds=Thresholds(latency=1000.0, error_rate=0.05)
    )


class TestMonitorXClient:
    """Test MonitorXClient SDK."""

    def test_client_initialization(self):
        """Test client initialization."""
        client = MonitorXClient(
            base_url="http://api.example.com",
            api_key="test-key",
            timeout=60
        )

        assert client.base_url == "http://api.example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 60

    def test_client_strips_trailing_slash(self):
        """Test that base_url trailing slash is stripped."""
        client = MonitorXClient(base_url="http://api.example.com/")
        assert client.base_url == "http://api.example.com"

    def test_get_headers_without_api_key(self, client):
        """Test headers without API key."""
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    def test_get_headers_with_api_key(self):
        """Test headers with API key."""
        client = MonitorXClient(api_key="test-key")
        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        client = MonitorXClient()

        async with client as c:
            assert c.session is not None
            assert isinstance(c.session, httpx.AsyncClient)

        # Session should be closed after context
        assert client.session is not None  # Reference still exists

    @pytest.mark.asyncio
    async def test_register_model_success(self, client, sample_model_config):
        """Test successful model registration."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = await client.register_model(sample_model_config)

            assert result is True
            mock_post.assert_called_once()

            # Check payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['id'] == "test-model"
            assert payload['name'] == "Test Model"

    @pytest.mark.asyncio
    async def test_register_model_failure(self, client, sample_model_config):
        """Test failed model registration."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Network error")

            result = await client.register_model(sample_model_config)

            assert result is False

    @pytest.mark.asyncio
    async def test_collect_inference_metric_success(self, client):
        """Test successful inference metric collection."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = await client.collect_inference_metric(
                model_id="test-model",
                model_type="llm",
                latency=500.0,
                throughput=10.5,
                error_rate=0.01
            )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_inference_metric_auto_request_id(self, client):
        """Test that request_id is auto-generated if not provided."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = await client.collect_inference_metric(
                model_id="test-model",
                model_type="llm",
                latency=500.0
            )

            assert result is True

            # Check that request_id was generated
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert 'request_id' in payload
            assert len(payload['request_id']) > 0

    @pytest.mark.asyncio
    async def test_collect_inference_metric_with_resource_usage(self, client):
        """Test collecting metric with resource usage."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            resource_usage = ResourceUsage(
                gpu_memory=0.7,
                cpu_usage=0.5,
                memory_usage=0.6
            )

            result = await client.collect_inference_metric(
                model_id="test-model",
                model_type="cv",
                latency=750.0,
                resource_usage=resource_usage
            )

            assert result is True

            # Check payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert 'resource_usage' in payload
            assert payload['resource_usage']['gpu_memory'] == 0.7

    @pytest.mark.asyncio
    async def test_collect_drift_metric_success(self, client):
        """Test successful drift metric collection."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = await client.collect_drift_metric(
                model_id="test-model",
                drift_type="data",
                severity="medium",
                confidence=0.85,
                tags={"detector": "ks_test"}
            )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_summary_stats_success(self, client):
        """Test getting summary stats."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "total_requests": 100,
                "average_latency": 500.0,
                "error_rate": 0.02
            }
            mock_get.return_value = mock_response

            stats = await client.get_summary_stats(model_id="test-model", since_hours=24)

            assert stats["total_requests"] == 100
            assert stats["average_latency"] == 500.0
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_summary_stats_failure(self, client):
        """Test get summary stats failure returns empty dict."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")

            stats = await client.get_summary_stats()

            assert stats == {}

    @pytest.mark.asyncio
    async def test_get_alerts_success(self, client):
        """Test getting alerts."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = [
                {
                    "id": "alert-1",
                    "model_id": "test-model",
                    "alert_type": "latency",
                    "severity": "high",
                    "message": "High latency",
                    "resolved": False
                }
            ]
            mock_get.return_value = mock_response

            alerts = await client.get_alerts(model_id="test-model", resolved=False)

            assert len(alerts) == 1
            assert alerts[0]["id"] == "alert-1"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self, client):
        """Test getting alerts with filters."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            await client.get_alerts(
                model_id="test-model",
                since_hours=48,
                resolved=True
            )

            # Check that params were passed correctly
            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['model_id'] == "test-model"
            assert params['since_hours'] == 48
            assert params['resolved'] is True

    @pytest.mark.asyncio
    async def test_resolve_alert_success(self, client):
        """Test resolving an alert."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = await client.resolve_alert("alert-123")

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_resolve_alert_failure(self, client):
        """Test failed alert resolution."""
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Not found")

            result = await client.resolve_alert("fake-alert-id")

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test health check."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_response.json.return_value = {
                "status": "healthy",
                "version": "0.1.0",
                "services": {"api": "healthy"}
            }
            mock_get.return_value = mock_response

            health = await client.health_check()

            assert health["status"] == "healthy"
            assert health["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test health check failure."""
        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection failed")

            health = await client.health_check()

            assert health["status"] == "unhealthy"
            assert "error" in health

    @pytest.mark.asyncio
    async def test_client_with_session(self):
        """Test client operations using context manager session."""
        client = MonitorXClient()

        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            async with client:
                # Operations within context use the same session
                await client.collect_inference_metric(
                    model_id="model-1",
                    model_type="llm",
                    latency=500.0
                )
                await client.collect_inference_metric(
                    model_id="model-2",
                    model_type="cv",
                    latency=600.0
                )

            # Both calls should use the session
            assert mock_post.call_count == 2
