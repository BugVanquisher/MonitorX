"""
Basic MonitorX Usage Example

This example demonstrates how to use MonitorX to monitor a simple ML model.
"""

import asyncio
import random
import time
from monitorx.sdk import MonitorXClient, MonitorXContext, monitor_inference
from monitorx.types import ModelConfig, Thresholds, ResourceUsage


async def setup_model():
    """Set up and register a model with MonitorX."""
    client = MonitorXClient("http://localhost:8000")

    # Define model configuration
    config = ModelConfig(
        id="sentiment-analysis-v1",
        name="Sentiment Analysis Model",
        model_type="llm",
        version="1.0.0",
        environment="prod",
        thresholds=Thresholds(
            latency=1000.0,  # 1 second
            error_rate=0.05,  # 5%
            gpu_memory=0.8,   # 80%
            cpu_usage=0.8,    # 80%
            memory_usage=0.8  # 80%
        )
    )

    # Register the model
    success = await client.register_model(config)
    if success:
        print("✅ Model registered successfully!")
    else:
        print("❌ Failed to register model")
        return None

    return client


def simulate_ml_inference(text: str) -> dict:
    """Simulate ML model inference with random latency and occasional errors."""
    # Simulate processing time
    processing_time = random.uniform(0.1, 2.0)
    time.sleep(processing_time)

    # Simulate occasional errors (5% chance)
    if random.random() < 0.05:
        raise Exception("Model inference failed")

    # Return mock result
    return {
        "text": text,
        "sentiment": random.choice(["positive", "negative", "neutral"]),
        "confidence": random.uniform(0.7, 0.99)
    }


@monitor_inference(
    model_id="sentiment-analysis-v1",
    model_type="llm",
    tags={"version": "1.0.0", "endpoint": "/analyze"}
)
async def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment with automatic monitoring."""
    return simulate_ml_inference(text)


async def manual_monitoring_example():
    """Example of manual metrics collection."""
    client = MonitorXClient("http://localhost:8000")

    for i in range(10):
        start_time = time.time()
        error_occurred = False

        try:
            # Simulate model inference
            result = simulate_ml_inference(f"Sample text {i}")

        except Exception as e:
            print(f"❌ Error in inference {i}: {e}")
            error_occurred = True

        finally:
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds

            # Collect metrics manually
            await client.collect_inference_metric(
                model_id="sentiment-analysis-v1",
                model_type="llm",
                latency=latency,
                request_id=f"req-{i}",
                error_rate=1.0 if error_occurred else 0.0,
                resource_usage=ResourceUsage(
                    gpu_memory=random.uniform(0.3, 0.9),
                    cpu_usage=random.uniform(0.2, 0.8),
                    memory_usage=random.uniform(0.4, 0.7)
                ),
                tags={"batch": "manual-example"}
            )

            print(f"📊 Collected metrics for request {i} (latency: {latency:.1f}ms)")

        await asyncio.sleep(0.5)  # Brief pause between requests


async def decorator_monitoring_example():
    """Example of automatic monitoring using decorators."""
    client = MonitorXClient("http://localhost:8000")

    # Use context manager to set up the client for decorators
    async with client:
        with MonitorXContext(client):
            print("\n🎯 Running decorator monitoring example...")

            # Process multiple requests
            sample_texts = [
                "I love this product!",
                "This is terrible.",
                "Not sure how I feel about this.",
                "Amazing quality and fast delivery!",
                "Could be better."
            ]

            for i, text in enumerate(sample_texts):
                try:
                    result = await analyze_sentiment(text)
                    print(f"✅ Request {i+1}: {text[:30]}... -> {result['sentiment']}")

                except Exception as e:
                    print(f"❌ Request {i+1} failed: {e}")

                await asyncio.sleep(0.3)  # Brief pause between requests


async def drift_detection_example():
    """Example of drift detection."""
    client = MonitorXClient("http://localhost:8000")

    # Simulate drift detection results
    drift_scenarios = [
        {"confidence": 0.92, "severity": "critical", "type": "data"},
        {"confidence": 0.78, "severity": "high", "type": "concept"},
        {"confidence": 0.65, "severity": "medium", "type": "data"},
    ]

    for i, scenario in enumerate(drift_scenarios):
        await client.collect_drift_metric(
            model_id="sentiment-analysis-v1",
            drift_type=scenario["type"],
            severity=scenario["severity"],
            confidence=scenario["confidence"],
            tags={"detection_method": "statistical_test", "batch_id": f"batch-{i}"}
        )

        print(f"🚨 Drift detected: {scenario['type']} drift with "
              f"{scenario['severity']} severity (confidence: {scenario['confidence']:.1%})")

        await asyncio.sleep(1)


async def get_statistics_example():
    """Example of retrieving statistics."""
    client = MonitorXClient("http://localhost:8000")

    # Get summary statistics
    stats = await client.get_summary_stats("sentiment-analysis-v1", since_hours=1)

    if stats:
        print("\n📈 Model Statistics (last hour):")
        print(f"  Total requests: {stats.get('total_requests', 0)}")
        print(f"  Average latency: {stats.get('average_latency', 0):.1f}ms")
        print(f"  P95 latency: {stats.get('p95_latency', 0):.1f}ms")
        print(f"  Error rate: {stats.get('error_rate', 0):.1%}")
        print(f"  Active alerts: {stats.get('active_alerts', 0)}")

    # Get recent alerts
    alerts = await client.get_alerts("sentiment-analysis-v1", since_hours=1, resolved=False)

    if alerts:
        print(f"\n🚨 Active alerts: {len(alerts)}")
        for alert in alerts[:3]:  # Show first 3 alerts
            print(f"  • {alert['severity'].upper()}: {alert['message']}")
    else:
        print("\n✅ No active alerts")


async def health_check_example():
    """Example of health check."""
    client = MonitorXClient("http://localhost:8000")

    health = await client.health_check()

    print(f"\n🏥 Health Check:")
    print(f"  Status: {health.get('status', 'unknown')}")
    print(f"  Services: {health.get('services', {})}")


async def main():
    """Main example function."""
    print("🎯 MonitorX Basic Usage Example")
    print("=" * 40)

    # Set up model
    client = await setup_model()
    if not client:
        return

    print("\n1. Manual monitoring example")
    await manual_monitoring_example()

    print("\n2. Decorator monitoring example")
    await decorator_monitoring_example()

    print("\n3. Drift detection example")
    await drift_detection_example()

    print("\n4. Statistics retrieval example")
    await get_statistics_example()

    print("\n5. Health check example")
    await health_check_example()

    print("\n✅ Example completed!")
    print("\n💡 Visit http://localhost:8501 to see the dashboard")
    print("💡 Visit http://localhost:8000/docs for API documentation")


if __name__ == "__main__":
    asyncio.run(main())