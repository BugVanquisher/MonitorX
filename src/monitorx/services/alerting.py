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

import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from loguru import logger

from ..types import Alert


@dataclass
class AlertChannel:
    """Base class for alert channels."""
    name: str
    enabled: bool = True


@dataclass
class EmailChannel(AlertChannel):
    """Email alert channel configuration."""
    smtp_server: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    to_emails: List[str] = field(default_factory=list)
    use_tls: bool = True


@dataclass
class SlackChannel(AlertChannel):
    """Slack alert channel configuration."""
    webhook_url: str = ""
    channel: str = ""
    username: str = "MonitorX"


@dataclass
class WebhookChannel(AlertChannel):
    """Generic webhook alert channel configuration."""
    url: str = ""
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30


class AlertingService:
    """Service for managing alert notifications."""

    def __init__(self):
        self.channels: List[AlertChannel] = []
        self.alert_history: Dict[str, datetime] = {}
        self.rate_limit_window = timedelta(minutes=5)  # Don't spam same alert type
        self.custom_handlers: List[Callable[[Alert], None]] = []

    def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel."""
        self.channels.append(channel)
        logger.info(f"Added alert channel: {channel.name}")

    def add_custom_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a custom alert handler."""
        self.custom_handlers.append(handler)

    async def send_alert(self, alert: Alert) -> None:
        """Send an alert through all configured channels."""
        # Check rate limiting
        rate_limit_key = f"{alert.model_id}:{alert.alert_type}:{alert.severity}"
        last_sent = self.alert_history.get(rate_limit_key)

        if last_sent and (datetime.now() - last_sent) < self.rate_limit_window:
            logger.debug(f"Rate limiting alert: {rate_limit_key}")
            return

        # Update rate limit history
        self.alert_history[rate_limit_key] = datetime.now()

        # Send through all enabled channels
        tasks = []
        for channel in self.channels:
            if channel.enabled:
                tasks.append(self._send_through_channel(alert, channel))

        # Execute custom handlers
        for handler in self.custom_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in custom alert handler: {e}")

        # Send through all channels concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Alert sending failed: {result}")

        logger.info(f"Sent alert: {alert.message}")

    async def _send_through_channel(self, alert: Alert, channel: AlertChannel) -> None:
        """Send alert through a specific channel."""
        try:
            if isinstance(channel, EmailChannel):
                await self._send_email_alert(alert, channel)
            elif isinstance(channel, SlackChannel):
                await self._send_slack_alert(alert, channel)
            elif isinstance(channel, WebhookChannel):
                await self._send_webhook_alert(alert, channel)
            else:
                logger.warning(f"Unknown channel type: {type(channel)}")

        except Exception as e:
            logger.error(f"Failed to send alert through {channel.name}: {e}")

    async def _send_email_alert(self, alert: Alert, channel: EmailChannel) -> None:
        """Send alert via email."""
        if not all([channel.smtp_server, channel.username, channel.password,
                   channel.from_email, channel.to_emails]):
            logger.warning("Email channel not properly configured")
            return

        # Prepare email content
        subject = f"🚨 MonitorX Alert: {alert.alert_type.replace('_', ' ').title()} - {alert.severity.upper()}"

        # Create HTML content
        html_content = f"""
        <html>
        <body>
            <h2 style="color: {'#d32f2f' if alert.severity in ['high', 'critical'] else '#ff9800'};">
                MonitorX Alert
            </h2>

            <table style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Model ID:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{alert.model_id}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Alert Type:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{alert.alert_type.replace('_', ' ').title()}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Severity:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{alert.severity.upper()}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Timestamp:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;"><strong>Message:</strong></td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{alert.message}</td>
                </tr>
            </table>

            <p><em>This alert was generated by MonitorX ML/AI Infrastructure Observability Platform</em></p>
        </body>
        </html>
        """

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = channel.from_email
        msg['To'] = ', '.join(channel.to_emails)

        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send email
        def send_email():
            with smtplib.SMTP(channel.smtp_server, channel.smtp_port) as server:
                if channel.use_tls:
                    server.starttls()
                server.login(channel.username, channel.password)
                server.send_message(msg, to_addrs=channel.to_emails)

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_email)

        logger.info(f"Sent email alert to {len(channel.to_emails)} recipients")

    async def _send_slack_alert(self, alert: Alert, channel: SlackChannel) -> None:
        """Send alert via Slack webhook."""
        if not channel.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return

        # Determine color based on severity
        color_map = {
            'low': '#36a64f',      # green
            'medium': '#ff9800',   # orange
            'high': '#ff5722',     # red
            'critical': '#d32f2f'  # dark red
        }
        color = color_map.get(alert.severity, '#808080')

        # Create Slack payload
        payload = {
            "username": channel.username,
            "channel": channel.channel,
            "attachments": [
                {
                    "color": color,
                    "title": f"🚨 MonitorX Alert - {alert.alert_type.replace('_', ' ').title()}",
                    "fields": [
                        {
                            "title": "Model ID",
                            "value": alert.model_id,
                            "short": True
                        },
                        {
                            "title": "Severity",
                            "value": alert.severity.upper(),
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": True
                        },
                        {
                            "title": "Message",
                            "value": alert.message,
                            "short": False
                        }
                    ],
                    "footer": "MonitorX ML/AI Observability Platform",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(channel.webhook_url, json=payload)
            response.raise_for_status()

        logger.info("Sent Slack alert")

    async def _send_webhook_alert(self, alert: Alert, channel: WebhookChannel) -> None:
        """Send alert via generic webhook."""
        if not channel.url:
            logger.warning("Webhook URL not configured")
            return

        # Prepare payload
        payload = {
            "alert_id": alert.id,
            "model_id": alert.model_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "resolved": alert.resolved
        }

        if alert.resolved_at:
            payload["resolved_at"] = alert.resolved_at.isoformat()

        # Send webhook
        async with httpx.AsyncClient(timeout=channel.timeout) as client:
            if channel.method.upper() == "POST":
                response = await client.post(
                    channel.url,
                    json=payload,
                    headers=channel.headers
                )
            elif channel.method.upper() == "PUT":
                response = await client.put(
                    channel.url,
                    json=payload,
                    headers=channel.headers
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {channel.method}")

            response.raise_for_status()

        logger.info(f"Sent webhook alert to {channel.url}")

    def cleanup_rate_limit_history(self, older_than_hours: int = 24) -> None:
        """Clean up old entries from rate limit history."""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

        # Remove old entries
        keys_to_remove = [
            key for key, timestamp in self.alert_history.items()
            if timestamp < cutoff_time
        ]

        for key in keys_to_remove:
            del self.alert_history[key]

        logger.debug(f"Cleaned up {len(keys_to_remove)} old rate limit entries")

    async def test_channels(self) -> Dict[str, bool]:
        """Test all configured alert channels."""
        test_alert = Alert(
            id="test-alert",
            model_id="test-model",
            alert_type="latency",
            severity="low",
            message="This is a test alert from MonitorX",
            timestamp=datetime.now()
        )

        results = {}

        for channel in self.channels:
            if not channel.enabled:
                results[channel.name] = False
                continue

            try:
                await self._send_through_channel(test_alert, channel)
                results[channel.name] = True
                logger.info(f"Successfully tested channel: {channel.name}")
            except Exception as e:
                results[channel.name] = False
                logger.error(f"Failed to test channel {channel.name}: {e}")

        return results