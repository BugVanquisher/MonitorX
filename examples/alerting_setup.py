"""Example: Setting up alert channels for MonitorX."""
import asyncio
import os
from dotenv import load_dotenv

from monitorx.services.alerting import (
    AlertingService, EmailChannel, SlackChannel, WebhookChannel
)
from monitorx.services.metrics_collector import MetricsCollector
from monitorx.types import ModelConfig, Thresholds, InferenceMetric

# Load environment variables
load_dotenv()


async def main():
    """Demonstrate alert channel configuration."""

    # 1. Create alerting service
    alerting = AlertingService()

    # 2. Configure Email Alerts
    if os.getenv("ENABLE_EMAIL_ALERTS") == "true":
        email_channel = EmailChannel(
            name="email-alerts",
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
            from_email=os.getenv("ALERT_FROM_EMAIL"),
            to_emails=os.getenv("ALERT_TO_EMAILS", "").split(","),
            use_tls=True
        )
        alerting.add_channel(email_channel)
        print("✓ Email alerts configured")

    # 3. Configure Slack Alerts
    if os.getenv("ENABLE_SLACK_ALERTS") == "true":
        slack_channel = SlackChannel(
            name="slack-alerts",
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            channel=os.getenv("SLACK_CHANNEL", "#ml-alerts"),
            username="MonitorX Bot"
        )
        alerting.add_channel(slack_channel)
        print("✓ Slack alerts configured")

    # 4. Configure Custom Webhook
    if os.getenv("ENABLE_WEBHOOK_ALERTS") == "true":
        webhook_channel = WebhookChannel(
            name="custom-webhook",
            url=os.getenv("WEBHOOK_URL"),
            method="POST",
            headers={
                "Authorization": f"Bearer {os.getenv('WEBHOOK_API_KEY')}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        alerting.add_channel(webhook_channel)
        print("✓ Custom webhook configured")

    # 5. Add custom alert handler (optional)
    def custom_alert_handler(alert):
        """Custom logic for alert handling."""
        # For example, write to a database, trigger other workflows, etc.
        print(f"Custom handler received alert: {alert.message}")

    alerting.add_custom_handler(custom_alert_handler)

    # 6. Test all channels
    print("\nTesting alert channels...")
    test_results = await alerting.test_channels()

    for channel_name, success in test_results.items():
        status = "✓" if success else "✗"
        print(f"{status} {channel_name}: {'OK' if success else 'FAILED'}")

    # 7. Integrate with metrics collector
    metrics_collector = MetricsCollector()

    # Register alerting callback
    async def alert_callback(alert):
        await alerting.send_alert(alert)

    metrics_collector.add_alert_callback(lambda alert: asyncio.create_task(alert_callback(alert)))

    # 8. Register a model
    model_config = ModelConfig(
        id="example-llm-v1",
        name="Example LLM Model",
        model_type="llm",
        version="1.0.0",
        environment="prod",
        thresholds=Thresholds(
            latency=1000.0,  # 1 second
            error_rate=0.01,  # 1%
            gpu_memory=0.85,  # 85%
        )
    )
    metrics_collector.register_model(model_config)

    # 9. Simulate a threshold breach (will trigger alerts)
    print("\nSimulating high latency (will trigger alerts)...")

    high_latency_metric = InferenceMetric(
        model_id="example-llm-v1",
        model_type="llm",
        request_id="req-test-001",
        latency=2500.0,  # Exceeds 1000ms threshold
        throughput=5.0,
        error_rate=0.0,
        tags={"test": "true"}
    )

    await metrics_collector.collect_inference_metric(high_latency_metric)

    # Wait for async alert sending
    await asyncio.sleep(1)

    print("\n✓ Alert demonstration complete!")
    print("\nCheck your configured channels for the test alerts.")

    # 10. Cleanup old rate limit history (run periodically)
    alerting.cleanup_rate_limit_history(older_than_hours=24)


if __name__ == "__main__":
    print("MonitorX Alert Channel Configuration\n" + "="*50 + "\n")
    asyncio.run(main())
