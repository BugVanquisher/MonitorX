"""
Advanced SDK Features Example

Demonstrates:
1. Batch metric collection
2. Automatic retry with exponential backoff
3. Circuit breaker pattern
4. Metric buffering for offline scenarios
5. Connection pooling with async context manager
"""

import asyncio
from monitorx import MonitorXClient


async def example_batch_collection():
    """Example: Collect multiple metrics in a single batch."""
    print("\n=== Batch Collection Example ===\n")

    async with MonitorXClient(base_url="http://localhost:8000") as client:
        # Prepare batch of metrics
        metrics = [
            {
                "model_id": "gpt-4",
                "model_type": "llm",
                "latency": 245.5,
                "tags": {"endpoint": "/v1/chat", "user": "alice"}
            },
            {
                "model_id": "gpt-4",
                "model_type": "llm",
                "latency": 312.8,
                "tags": {"endpoint": "/v1/chat", "user": "bob"}
            },
            {
                "model_id": "gpt-4",
                "model_type": "llm",
                "latency": 189.3,
                "tags": {"endpoint": "/v1/completion", "user": "charlie"}
            },
        ]

        # Send all metrics in parallel
        result = await client.collect_inference_metrics_batch(metrics)
        print(f"Batch result: {result['success']} succeeded, {result['failed']} failed")


async def example_retry_with_backoff():
    """Example: Automatic retry with exponential backoff."""
    print("\n=== Retry with Backoff Example ===\n")

    # Configure client with retry settings
    client = MonitorXClient(
        base_url="http://localhost:8000",
        max_retries=3,           # Try up to 3 times
        retry_backoff=1.0,       # Start with 1 second, doubles each retry
        enable_circuit_breaker=True
    )

    async with client:
        # If API is temporarily unavailable, this will automatically retry
        success = await client.collect_inference_metric(
            model_id="bert-base",
            model_type="llm",
            latency=156.2
        )
        print(f"Metric collected: {success}")


async def example_circuit_breaker():
    """Example: Circuit breaker prevents cascading failures."""
    print("\n=== Circuit Breaker Example ===\n")

    client = MonitorXClient(
        base_url="http://localhost:8000",
        enable_circuit_breaker=True,
        max_retries=3
    )

    async with client:
        # Simulate multiple requests
        for i in range(10):
            try:
                success = await client.collect_inference_metric(
                    model_id="resnet50",
                    model_type="cv",
                    latency=45.2 + i
                )
                print(f"Request {i+1}: {'✓' if success else '✗'}")
            except Exception as e:
                print(f"Request {i+1}: Circuit breaker OPEN - {e}")
                # Wait for circuit breaker to recover
                await asyncio.sleep(5)


async def example_buffering_offline():
    """Example: Buffer metrics when API is offline, flush when back online."""
    print("\n=== Offline Buffering Example ===\n")

    client = MonitorXClient(
        base_url="http://localhost:8000",
        buffer_size=1000
    )

    # Enable buffering (e.g., when you detect API is down)
    client.enable_buffering()
    print("Buffering enabled - metrics will be stored locally")

    # These metrics will be buffered instead of sent
    for i in range(5):
        await client.collect_inference_metric(
            model_id="vgg16",
            model_type="cv",
            latency=78.3 + i * 10
        )

    print(f"Buffer size: {client.get_buffer_size()} metrics")

    # When API is back online, disable buffering and flush
    client.disable_buffering()
    print("\nBuffering disabled - flushing buffered metrics...")

    async with client:
        result = await client.flush_buffer()
        print(f"Flush result: {result['flushed']} flushed, {result['failed']} failed")


async def example_connection_pooling():
    """Example: Use async context manager for connection pooling."""
    print("\n=== Connection Pooling Example ===\n")

    # Using async context manager keeps connection alive across multiple requests
    async with MonitorXClient(base_url="http://localhost:8000") as client:
        # All these requests reuse the same HTTP connection
        tasks = []
        for i in range(20):
            task = client.collect_inference_metric(
                model_id="efficientnet",
                model_type="cv",
                latency=23.4 + i
            )
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks)
        successes = sum(1 for r in results if r)
        print(f"Collected {successes}/20 metrics using connection pool")


async def example_combined_features():
    """Example: Combine multiple advanced features."""
    print("\n=== Combined Features Example ===\n")

    # Create client with all features enabled
    client = MonitorXClient(
        base_url="http://localhost:8000",
        api_key="your-api-key",  # If authentication is enabled
        timeout=30,
        max_retries=3,
        retry_backoff=1.0,
        enable_circuit_breaker=True,
        buffer_size=1000
    )

    # Enable buffering as fallback
    client.enable_buffering()

    async with client:
        # Batch collection with retry and buffering
        metrics = [
            {"model_id": "model-a", "model_type": "llm", "latency": 100.5},
            {"model_id": "model-b", "model_type": "cv", "latency": 45.2},
            {"model_id": "model-c", "model_type": "tabular", "latency": 12.8},
        ]

        result = await client.collect_inference_metrics_batch(metrics)
        print(f"Batch result: {result}")

        # Check buffer status
        print(f"Buffer size: {client.get_buffer_size()}")

        # Flush if needed
        if client.get_buffer_size() > 0:
            flush_result = await client.flush_buffer()
            print(f"Flush result: {flush_result}")


async def example_production_usage():
    """Example: Production-ready usage pattern."""
    print("\n=== Production Usage Example ===\n")

    # Production configuration
    client = MonitorXClient(
        base_url="https://monitorx.yourcompany.com",
        api_key="prod-api-key-here",
        timeout=10,
        max_retries=3,
        retry_backoff=0.5,
        enable_circuit_breaker=True,
        buffer_size=5000
    )

    # Enable buffering for resilience
    client.enable_buffering()

    try:
        async with client:
            # Your application logic
            for request_id in range(100):
                # Collect metrics during inference
                await client.collect_inference_metric(
                    model_id="production-model",
                    model_type="llm",
                    latency=123.4,
                    request_id=f"req-{request_id}",
                    tags={"env": "production", "region": "us-west-2"}
                )

            # Periodically flush buffer
            if client.get_buffer_size() > 100:
                await client.flush_buffer()

        print("Production metrics collected successfully")

    except Exception as e:
        print(f"Error in production usage: {e}")
        # Metrics are safely buffered and will be retried


async def main():
    """Run all examples."""
    print("=" * 60)
    print("MonitorX SDK - Advanced Features Examples")
    print("=" * 60)

    # Run examples (comment out if API is not available)
    try:
        await example_batch_collection()
        await example_retry_with_backoff()
        # await example_circuit_breaker()  # Uncomment to test
        await example_buffering_offline()
        await example_connection_pooling()
        await example_combined_features()
        await example_production_usage()
    except Exception as e:
        print(f"\nNote: Some examples require a running MonitorX API server")
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
