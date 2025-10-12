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

"""Pytest configuration and fixtures."""
import pytest
import asyncio
from datetime import datetime
from typing import Generator

from monitorx.types import (
    InferenceMetric, DriftMetric, ModelConfig, Thresholds, ResourceUsage
)
from monitorx.services.metrics_collector import MetricsCollector


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Create a fresh MetricsCollector instance."""
    return MetricsCollector()


@pytest.fixture
def sample_model_config() -> ModelConfig:
    """Create a sample model configuration."""
    return ModelConfig(
        id="test-model-1",
        name="Test Model",
        model_type="llm",
        version="1.0.0",
        environment="dev",
        thresholds=Thresholds(
            latency=1000.0,
            error_rate=0.05,
            gpu_memory=0.8,
            cpu_usage=0.8,
            memory_usage=0.8
        )
    )


@pytest.fixture
def sample_inference_metric() -> InferenceMetric:
    """Create a sample inference metric."""
    return InferenceMetric(
        model_id="test-model-1",
        model_type="llm",
        request_id="req-123",
        latency=500.0,
        throughput=10.5,
        error_rate=0.01,
        resource_usage=ResourceUsage(
            gpu_memory=0.5,
            cpu_usage=0.3,
            memory_usage=0.4
        ),
        tags={"version": "1.0.0", "region": "us-west"}
    )


@pytest.fixture
def sample_drift_metric() -> DriftMetric:
    """Create a sample drift metric."""
    return DriftMetric(
        model_id="test-model-1",
        drift_type="data",
        severity="medium",
        confidence=0.85,
        tags={"detector": "ks_test"}
    )


@pytest.fixture
def high_latency_metric() -> InferenceMetric:
    """Create a metric that exceeds latency threshold."""
    return InferenceMetric(
        model_id="test-model-1",
        model_type="llm",
        request_id="req-456",
        latency=2500.0,  # Exceeds 1000ms threshold
        throughput=5.0,
        error_rate=0.0
    )


@pytest.fixture
def high_error_rate_metric() -> InferenceMetric:
    """Create a metric that exceeds error rate threshold."""
    return InferenceMetric(
        model_id="test-model-1",
        model_type="llm",
        request_id="req-789",
        latency=500.0,
        error_rate=0.15  # Exceeds 0.05 threshold
    )
