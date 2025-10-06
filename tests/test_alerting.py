"""Tests for alerting service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from datetime import datetime, timedelta
import smtplib
import httpx

from monitorx.services.alerting import (
    AlertingService, EmailChannel, SlackChannel, WebhookChannel
)
from monitorx.types import Alert


@pytest.fixture
def alerting_service():
    """Create alerting service instance."""
    return AlertingService()


@pytest.fixture
def sample_alert():
    """Create a sample alert."""
    return Alert(
        id="test-alert-123",
        model_id="test-model-1",
        alert_type="latency",
        severity="high",
        message="High latency detected: 2500ms (threshold: 1000ms)",
        timestamp=datetime.now()
    )


@pytest.fixture
def email_channel():
    """Create email channel configuration."""
    return EmailChannel(
        name="test-email",
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        username="test@example.com",
        password="password123",
        from_email="alerts@example.com",
        to_emails=["team@example.com", "oncall@example.com"]
    )


@pytest.fixture
def slack_channel():
    """Create Slack channel configuration."""
    return SlackChannel(
        name="test-slack",
        webhook_url="https://hooks.slack.com/services/TEST/WEBHOOK/URL",
        channel="#ml-alerts",
        username="MonitorX Bot"
    )


@pytest.fixture
def webhook_channel():
    """Create webhook channel configuration."""
    return WebhookChannel(
        name="test-webhook",
        url="https://api.example.com/alerts",
        method="POST",
        headers={"Authorization": "Bearer test-token"},
        timeout=30
    )


class TestAlertingService:
    """Test AlertingService functionality."""

    def test_add_channel(self, alerting_service, email_channel):
        """Test adding an alert channel."""
        alerting_service.add_channel(email_channel)

        assert len(alerting_service.channels) == 1
        assert alerting_service.channels[0].name == "test-email"

    def test_add_multiple_channels(self, alerting_service, email_channel, slack_channel):
        """Test adding multiple channels."""
        alerting_service.add_channel(email_channel)
        alerting_service.add_channel(slack_channel)

        assert len(alerting_service.channels) == 2

    def test_add_custom_handler(self, alerting_service):
        """Test adding custom alert handler."""
        handler = Mock()
        alerting_service.add_custom_handler(handler)

        assert len(alerting_service.custom_handlers) == 1

    @pytest.mark.asyncio
    async def test_send_alert_rate_limiting(self, alerting_service, sample_alert):
        """Test that rate limiting prevents duplicate alerts."""
        # Send alert first time
        await alerting_service.send_alert(sample_alert)

        # Try to send same alert type immediately
        alert2 = Alert(
            model_id="test-model-1",
            alert_type="latency",
            severity="high",
            message="Another latency alert"
        )

        # Mock to verify it's rate limited
        with patch.object(alerting_service, '_send_through_channel') as mock_send:
            await alerting_service.send_alert(alert2)
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_alert_custom_handlers(self, alerting_service, sample_alert):
        """Test that custom handlers are called."""
        handler1 = Mock()
        handler2 = Mock()

        alerting_service.add_custom_handler(handler1)
        alerting_service.add_custom_handler(handler2)

        await alerting_service.send_alert(sample_alert)

        handler1.assert_called_once_with(sample_alert)
        handler2.assert_called_once_with(sample_alert)

    @pytest.mark.asyncio
    async def test_send_alert_handler_error_handling(self, alerting_service, sample_alert):
        """Test that handler errors don't break alert sending."""
        failing_handler = Mock(side_effect=Exception("Handler error"))
        working_handler = Mock()

        alerting_service.add_custom_handler(failing_handler)
        alerting_service.add_custom_handler(working_handler)

        # Should not raise exception
        await alerting_service.send_alert(sample_alert)

        # Working handler should still be called
        working_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_alert(self, alerting_service, sample_alert, email_channel):
        """Test sending email alert."""
        alerting_service.add_channel(email_channel)

        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            await alerting_service.send_alert(sample_alert)

            # Verify SMTP was called correctly
            mock_smtp.assert_called_with('smtp.gmail.com', 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_with('test@example.com', 'password123')
            mock_server.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_alert_incomplete_config(self, alerting_service, sample_alert):
        """Test email alert with incomplete configuration."""
        incomplete_channel = EmailChannel(
            name="incomplete-email",
            smtp_server="smtp.gmail.com"
            # Missing other required fields
        )

        alerting_service.add_channel(incomplete_channel)

        with patch('smtplib.SMTP') as mock_smtp:
            # Should not raise error, just log warning
            await alerting_service.send_alert(sample_alert)

            # SMTP should not be called
            mock_smtp.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_slack_alert(self, alerting_service, sample_alert, slack_channel):
        """Test sending Slack alert."""
        alerting_service.add_channel(slack_channel)

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await alerting_service.send_alert(sample_alert)

            # Verify webhook was called
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args

            # Check webhook URL
            assert call_args[0][0] == slack_channel.webhook_url

            # Check payload structure
            payload = call_args[1]['json']
            assert 'attachments' in payload
            assert payload['username'] == 'MonitorX Bot'
            assert payload['channel'] == '#ml-alerts'

    @pytest.mark.asyncio
    async def test_send_slack_alert_severity_colors(self, alerting_service, slack_channel):
        """Test that Slack alerts use correct colors for severity."""
        alerting_service.add_channel(slack_channel)

        severity_colors = {
            'low': '#36a64f',
            'medium': '#ff9800',
            'high': '#ff5722',
            'critical': '#d32f2f'
        }

        for severity, expected_color in severity_colors.items():
            alert = Alert(
                model_id="test-model",
                alert_type="latency",
                severity=severity,
                message=f"Test {severity} alert"
            )

            # Reset rate limiting for this test
            alerting_service.alert_history.clear()

            with patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()

                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                await alerting_service.send_alert(alert)

                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                payload = call_args[1]['json']

                assert payload['attachments'][0]['color'] == expected_color

    @pytest.mark.asyncio
    async def test_send_webhook_alert_post(self, alerting_service, sample_alert, webhook_channel):
        """Test sending webhook alert with POST method."""
        alerting_service.add_channel(webhook_channel)

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await alerting_service.send_alert(sample_alert)

            # Verify webhook was called
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args

            # Check URL and payload
            assert call_args[0][0] == webhook_channel.url

            payload = call_args[1]['json']
            assert payload['alert_id'] == sample_alert.id
            assert payload['model_id'] == sample_alert.model_id
            assert payload['alert_type'] == sample_alert.alert_type
            assert payload['severity'] == sample_alert.severity

            # Check headers
            assert call_args[1]['headers'] == {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_send_webhook_alert_put(self, alerting_service, sample_alert):
        """Test sending webhook alert with PUT method."""
        webhook = WebhookChannel(
            name="put-webhook",
            url="https://api.example.com/alerts",
            method="PUT"
        )

        alerting_service.add_channel(webhook)

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()

            mock_client.return_value.__aenter__.return_value.put = AsyncMock(
                return_value=mock_response
            )

            await alerting_service.send_alert(sample_alert)

            # Verify PUT was called
            mock_client.return_value.__aenter__.return_value.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_channel_not_used(self, alerting_service, sample_alert, email_channel):
        """Test that disabled channels are not used."""
        email_channel.enabled = False
        alerting_service.add_channel(email_channel)

        with patch('smtplib.SMTP') as mock_smtp:
            await alerting_service.send_alert(sample_alert)

            # SMTP should not be called for disabled channel
            mock_smtp.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_channels_concurrent(
        self, alerting_service, sample_alert, email_channel, slack_channel
    ):
        """Test that multiple channels send alerts concurrently."""
        alerting_service.add_channel(email_channel)
        alerting_service.add_channel(slack_channel)

        with patch('smtplib.SMTP') as mock_smtp, \
             patch('httpx.AsyncClient') as mock_http:

            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_http.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await alerting_service.send_alert(sample_alert)

            # Both channels should have been used
            mock_smtp.assert_called_once()
            mock_http.return_value.__aenter__.return_value.post.assert_called_once()

    def test_cleanup_rate_limit_history(self, alerting_service):
        """Test cleaning up old rate limit entries."""
        # Add some old and new entries
        old_time = datetime.now() - timedelta(hours=48)
        new_time = datetime.now()

        alerting_service.alert_history["old:alert:high"] = old_time
        alerting_service.alert_history["new:alert:high"] = new_time

        # Cleanup entries older than 24 hours
        alerting_service.cleanup_rate_limit_history(older_than_hours=24)

        # Old entry should be removed, new one kept
        assert "old:alert:high" not in alerting_service.alert_history
        assert "new:alert:high" in alerting_service.alert_history

    @pytest.mark.asyncio
    async def test_test_channels(self, alerting_service, email_channel, slack_channel):
        """Test the test_channels functionality."""
        # Add channels
        alerting_service.add_channel(email_channel)
        slack_channel.enabled = False  # Disable one channel
        alerting_service.add_channel(slack_channel)

        with patch.object(alerting_service, '_send_through_channel', new_callable=AsyncMock) as mock_send:
            # Make email succeed, slack disabled
            mock_send.return_value = None

            results = await alerting_service.test_channels()

            # Email should succeed
            assert results["test-email"] is True
            # Slack is disabled
            assert results["test-slack"] is False

    @pytest.mark.asyncio
    async def test_test_channels_with_failures(self, alerting_service, email_channel):
        """Test test_channels handles failures gracefully."""
        alerting_service.add_channel(email_channel)

        with patch.object(
            alerting_service, '_send_through_channel',
            new_callable=AsyncMock
        ) as mock_send:
            mock_send.side_effect = Exception("Connection failed")

            results = await alerting_service.test_channels()

            assert results["test-email"] is False

    @pytest.mark.asyncio
    async def test_channel_error_handling(self, alerting_service, sample_alert, email_channel):
        """Test that channel errors are handled gracefully."""
        alerting_service.add_channel(email_channel)

        with patch('smtplib.SMTP', side_effect=Exception("SMTP connection failed")):
            # Should not raise exception
            await alerting_service.send_alert(sample_alert)

            # Alert should still be logged despite failure
            assert len(alerting_service.alert_history) > 0


class TestEmailChannel:
    """Test EmailChannel configuration."""

    def test_email_channel_defaults(self):
        """Test email channel default values."""
        channel = EmailChannel(name="test")

        assert channel.smtp_port == 587
        assert channel.use_tls is True
        assert channel.to_emails == []

    def test_email_channel_custom_config(self):
        """Test email channel custom configuration."""
        channel = EmailChannel(
            name="custom-email",
            smtp_server="smtp.custom.com",
            smtp_port=465,
            use_tls=False,
            to_emails=["test@example.com"]
        )

        assert channel.smtp_server == "smtp.custom.com"
        assert channel.smtp_port == 465
        assert channel.use_tls is False


class TestSlackChannel:
    """Test SlackChannel configuration."""

    def test_slack_channel_defaults(self):
        """Test Slack channel default values."""
        channel = SlackChannel(name="test")

        assert channel.username == "MonitorX"
        assert channel.webhook_url == ""

    def test_slack_channel_custom_config(self):
        """Test Slack channel custom configuration."""
        channel = SlackChannel(
            name="custom-slack",
            webhook_url="https://hooks.slack.com/test",
            channel="#custom-alerts",
            username="Custom Bot"
        )

        assert channel.webhook_url == "https://hooks.slack.com/test"
        assert channel.channel == "#custom-alerts"
        assert channel.username == "Custom Bot"


class TestWebhookChannel:
    """Test WebhookChannel configuration."""

    def test_webhook_channel_defaults(self):
        """Test webhook channel default values."""
        channel = WebhookChannel(name="test")

        assert channel.method == "POST"
        assert channel.timeout == 30
        assert channel.headers == {}

    def test_webhook_channel_custom_config(self):
        """Test webhook channel custom configuration."""
        channel = WebhookChannel(
            name="custom-webhook",
            url="https://api.example.com/alerts",
            method="PUT",
            timeout=60,
            headers={"X-API-Key": "secret"}
        )

        assert channel.url == "https://api.example.com/alerts"
        assert channel.method == "PUT"
        assert channel.timeout == 60
        assert channel.headers == {"X-API-Key": "secret"}
