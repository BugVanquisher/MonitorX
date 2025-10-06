# MonitorX Alerting System

## Overview

MonitorX provides a comprehensive alerting system that sends notifications when ML model metrics exceed configured thresholds. The system supports multiple alert channels and includes intelligent features like rate limiting and custom handlers.

## Supported Alert Channels

### 1. Email Alerts

Send alerts via SMTP email to your team.

**Configuration:**
```python
from monitorx.services.alerting import AlertingService, EmailChannel

alerting = AlertingService()

email_channel = EmailChannel(
    name="email-alerts",
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-app-password",  # Use app-specific password
    from_email="alerts@yourcompany.com",
    to_emails=["team@yourcompany.com", "oncall@yourcompany.com"],
    use_tls=True
)

alerting.add_channel(email_channel)
```

**Gmail Setup:**
1. Enable 2-factor authentication
2. Generate an app-specific password
3. Use the app password in the configuration

**Email Alert Format:**
- Subject: `🚨 MonitorX Alert: [Alert Type] - [SEVERITY]`
- HTML formatted body with alert details
- Color-coded based on severity

### 2. Slack Alerts

Send alerts to Slack channels using incoming webhooks.

**Configuration:**
```python
from monitorx.services.alerting import SlackChannel

slack_channel = SlackChannel(
    name="slack-alerts",
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    channel="#ml-alerts",
    username="MonitorX Bot"
)

alerting.add_channel(slack_channel)
```

**Slack Setup:**
1. Go to your Slack workspace settings
2. Create a new incoming webhook
3. Select the channel for alerts
4. Copy the webhook URL

**Slack Alert Format:**
- Rich attachments with color coding
- Structured fields for model ID, severity, timestamp
- Automatic severity color mapping:
  - Low: Green (#36a64f)
  - Medium: Orange (#ff9800)
  - High: Red (#ff5722)
  - Critical: Dark Red (#d32f2f)

### 3. Generic Webhooks

Send alerts to any HTTP endpoint.

**Configuration:**
```python
from monitorx.services.alerting import WebhookChannel

webhook_channel = WebhookChannel(
    name="custom-webhook",
    url="https://api.yourcompany.com/alerts",
    method="POST",  # or "PUT"
    headers={
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    },
    timeout=30
)

alerting.add_channel(webhook_channel)
```

**Webhook Payload:**
```json
{
    "alert_id": "uuid-here",
    "model_id": "your-model-id",
    "alert_type": "latency",
    "severity": "high",
    "message": "High latency detected: 2500ms (threshold: 1000ms)",
    "timestamp": "2024-01-01T12:00:00Z",
    "resolved": false
}
```

## Alert Types

MonitorX generates alerts for the following conditions:

### 1. Latency Alerts
Triggered when request latency exceeds threshold.

**Severity Calculation:**
- Low: 1.0-1.2x threshold
- Medium: 1.2-1.5x threshold
- High: 1.5-2.0x threshold
- Critical: ≥2.0x threshold

### 2. Error Rate Alerts
Triggered when error rate exceeds threshold.

### 3. Resource Usage Alerts
Triggered when GPU/CPU/memory usage exceeds threshold.

### 4. Drift Alerts
Triggered when model drift is detected with high/critical severity.

## Features

### Rate Limiting

Prevents alert spam by rate limiting duplicate alerts.

- Default window: 5 minutes
- Alerts are rate-limited by: `model_id:alert_type:severity`
- Prevents sending duplicate alerts within the window

**Cleanup:**
```python
# Clean up rate limit history older than 24 hours
alerting.cleanup_rate_limit_history(older_than_hours=24)
```

### Custom Alert Handlers

Add custom logic for alert processing.

```python
def custom_handler(alert):
    """Custom alert handling logic."""
    # Write to database
    db.alerts.insert(alert)

    # Trigger other workflows
    if alert.severity == "critical":
        trigger_incident_response(alert)

alerting.add_custom_handler(custom_handler)
```

### Multiple Channels

Send alerts to multiple channels simultaneously.

```python
# Add multiple channels
alerting.add_channel(email_channel)
alerting.add_channel(slack_channel)
alerting.add_channel(webhook_channel)

# Alerts will be sent to all enabled channels concurrently
```

### Channel Management

Enable/disable channels dynamically.

```python
# Disable a channel
email_channel.enabled = False

# Re-enable
email_channel.enabled = True
```

## Integration with Metrics Collector

Connect alerting to the metrics collector to automatically send alerts.

```python
from monitorx.services.metrics_collector import MetricsCollector
from monitorx.services.alerting import AlertingService

metrics_collector = MetricsCollector()
alerting = AlertingService()

# Configure channels...

# Register alert callback
async def alert_callback(alert):
    await alerting.send_alert(alert)

metrics_collector.add_alert_callback(
    lambda alert: asyncio.create_task(alert_callback(alert))
)
```

## Testing Alert Channels

Test all configured channels before going live.

```python
# Test all channels
results = await alerting.test_channels()

for channel_name, success in results.items():
    if success:
        print(f"✓ {channel_name} is working")
    else:
        print(f"✗ {channel_name} failed")
```

## Environment Variables

Configure alerts using environment variables:

```bash
# Email Alerts
ENABLE_EMAIL_ALERTS=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_FROM_EMAIL=alerts@yourcompany.com
ALERT_TO_EMAILS=team@yourcompany.com,oncall@yourcompany.com

# Slack Alerts
ENABLE_SLACK_ALERTS=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK
SLACK_CHANNEL=#ml-alerts

# Webhook Alerts
ENABLE_WEBHOOK_ALERTS=true
WEBHOOK_URL=https://api.yourcompany.com/alerts
WEBHOOK_API_KEY=your-api-key
```

## Complete Example

See `examples/alerting_setup.py` for a complete working example.

```bash
# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run example
python examples/alerting_setup.py
```

## Best Practices

### 1. Security
- Use app-specific passwords for email
- Store credentials in environment variables
- Never commit credentials to version control
- Use HTTPS for webhook URLs

### 2. Alert Fatigue Prevention
- Set appropriate thresholds to avoid noise
- Use rate limiting (enabled by default)
- Route critical alerts to on-call, low/medium to Slack
- Implement alert aggregation for multiple related issues

### 3. Testing
- Always test channels before production use
- Use test mode for initial setup
- Monitor alert delivery logs

### 4. Monitoring
- Track alert delivery success/failure
- Monitor rate limit hits
- Review alert history periodically

## Troubleshooting

### Email Alerts Not Sending

**Issue:** SMTP authentication fails

**Solutions:**
- Verify SMTP credentials
- Enable "Less secure app access" (Gmail)
- Use app-specific password
- Check firewall/network settings

### Slack Alerts Not Appearing

**Issue:** Webhook returns 400/404

**Solutions:**
- Verify webhook URL is correct
- Check webhook is still active in Slack
- Ensure channel exists and webhook has access
- Validate payload format

### Rate Limiting Too Aggressive

**Issue:** Important alerts are being suppressed

**Solutions:**
- Adjust rate_limit_window
- Use different alert types for different issues
- Implement severity-based rate limiting

```python
# Custom rate limit window
alerting.rate_limit_window = timedelta(minutes=10)
```

## API Reference

### AlertingService

```python
class AlertingService:
    def add_channel(self, channel: AlertChannel) -> None
    def add_custom_handler(self, handler: Callable[[Alert], None]) -> None
    async def send_alert(self, alert: Alert) -> None
    async def test_channels(self) -> Dict[str, bool]
    def cleanup_rate_limit_history(self, older_than_hours: int = 24) -> None
```

### Channel Classes

```python
@dataclass
class EmailChannel(AlertChannel):
    smtp_server: str
    smtp_port: int = 587
    username: str
    password: str
    from_email: str
    to_emails: List[str]
    use_tls: bool = True

@dataclass
class SlackChannel(AlertChannel):
    webhook_url: str
    channel: str
    username: str = "MonitorX"

@dataclass
class WebhookChannel(AlertChannel):
    url: str
    method: str = "POST"
    headers: Dict[str, str]
    timeout: int = 30
```

## Next Steps

- [API Documentation](API.md)
- [Metrics Collection Guide](METRICS.md)
- [Dashboard Setup](DASHBOARD.md)
- [Deployment Guide](DEPLOYMENT.md)
