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

import functools
import time
import asyncio
import inspect
from typing import Callable, Optional, Dict, Any
import uuid
from loguru import logger

from .context import MonitorXContext


def monitor_inference(
    model_id: str,
    model_type: str,
    track_errors: bool = True,
    tags: Optional[Dict[str, str]] = None
):
    """
    Decorator to automatically monitor function inference metrics.

    Args:
        model_id: Unique identifier for the model
        model_type: Type of ML model ('llm', 'cv', 'tabular')
        track_errors: Whether to track errors as metrics
        tags: Additional tags to include with metrics
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _monitor_sync_function(
                func, args, kwargs, model_id, model_type, track_errors, tags or {}
            )

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _monitor_async_function(
                func, args, kwargs, model_id, model_type, track_errors, tags or {}
            )

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def monitor_drift(
    model_id: str,
    drift_type: str = "data",
    threshold: float = 0.7,
    tags: Optional[Dict[str, str]] = None
):
    """
    Decorator to automatically monitor drift detection.

    Args:
        model_id: Unique identifier for the model
        drift_type: Type of drift ('data' or 'concept')
        threshold: Confidence threshold to report drift
        tags: Additional tags to include with metrics
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            _handle_drift_detection(result, model_id, drift_type, threshold, tags or {})
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await _handle_drift_detection_async(result, model_id, drift_type, threshold, tags or {})
            return result

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _monitor_sync_function(
    func: Callable,
    args: tuple,
    kwargs: dict,
    model_id: str,
    model_type: str,
    track_errors: bool,
    tags: Dict[str, str]
) -> Any:
    """Monitor synchronous function execution."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    error_occurred = False

    try:
        result = func(*args, **kwargs)
        return result

    except Exception as e:
        error_occurred = True
        if track_errors:
            logger.error(f"Error in monitored function {func.__name__}: {e}")
        raise

    finally:
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds

        # Get client from context
        client = MonitorXContext.get_client()
        if client:
            try:
                # Use asyncio to run the async method in sync context
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                loop.run_until_complete(
                    client.collect_inference_metric(
                        model_id=model_id,
                        model_type=model_type,
                        latency=latency,
                        request_id=request_id,
                        error_rate=1.0 if error_occurred else 0.0,
                        tags={**tags, "function_name": func.__name__}
                    )
                )
            except Exception as e:
                logger.error(f"Failed to collect inference metric: {e}")


async def _monitor_async_function(
    func: Callable,
    args: tuple,
    kwargs: dict,
    model_id: str,
    model_type: str,
    track_errors: bool,
    tags: Dict[str, str]
) -> Any:
    """Monitor asynchronous function execution."""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    error_occurred = False

    try:
        result = await func(*args, **kwargs)
        return result

    except Exception as e:
        error_occurred = True
        if track_errors:
            logger.error(f"Error in monitored async function {func.__name__}: {e}")
        raise

    finally:
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds

        # Get client from context
        client = MonitorXContext.get_client()
        if client:
            try:
                await client.collect_inference_metric(
                    model_id=model_id,
                    model_type=model_type,
                    latency=latency,
                    request_id=request_id,
                    error_rate=1.0 if error_occurred else 0.0,
                    tags={**tags, "function_name": func.__name__}
                )
            except Exception as e:
                logger.error(f"Failed to collect inference metric: {e}")


def _handle_drift_detection(
    result: Any,
    model_id: str,
    drift_type: str,
    threshold: float,
    tags: Dict[str, str]
) -> None:
    """Handle drift detection for synchronous functions."""
    if not _should_report_drift(result, threshold):
        return

    client = MonitorXContext.get_client()
    if client:
        try:
            confidence, severity = _extract_drift_info(result, threshold)

            # Use asyncio to run the async method in sync context
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            loop.run_until_complete(
                client.collect_drift_metric(
                    model_id=model_id,
                    drift_type=drift_type,
                    severity=severity,
                    confidence=confidence,
                    tags=tags
                )
            )
        except Exception as e:
            logger.error(f"Failed to collect drift metric: {e}")


async def _handle_drift_detection_async(
    result: Any,
    model_id: str,
    drift_type: str,
    threshold: float,
    tags: Dict[str, str]
) -> None:
    """Handle drift detection for asynchronous functions."""
    if not _should_report_drift(result, threshold):
        return

    client = MonitorXContext.get_client()
    if client:
        try:
            confidence, severity = _extract_drift_info(result, threshold)

            await client.collect_drift_metric(
                model_id=model_id,
                drift_type=drift_type,
                severity=severity,
                confidence=confidence,
                tags=tags
            )
        except Exception as e:
            logger.error(f"Failed to collect drift metric: {e}")


def _should_report_drift(result: Any, threshold: float) -> bool:
    """Determine if drift should be reported based on result."""
    # Handle different result formats
    if isinstance(result, dict):
        # Look for common drift score keys
        drift_keys = ['drift_score', 'confidence', 'drift_confidence', 'anomaly_score']
        for key in drift_keys:
            if key in result:
                return result[key] >= threshold
    elif isinstance(result, (int, float)):
        # Direct score
        return result >= threshold
    elif hasattr(result, 'drift_score'):
        # Object with drift_score attribute
        return result.drift_score >= threshold

    return False


def _extract_drift_info(result: Any, threshold: float) -> tuple[float, str]:
    """Extract confidence and severity from drift detection result."""
    confidence = 0.0

    # Extract confidence score
    if isinstance(result, dict):
        drift_keys = ['drift_score', 'confidence', 'drift_confidence', 'anomaly_score']
        for key in drift_keys:
            if key in result:
                confidence = result[key]
                break
    elif isinstance(result, (int, float)):
        confidence = result
    elif hasattr(result, 'drift_score'):
        confidence = result.drift_score

    # Determine severity based on confidence
    if confidence >= 0.9:
        severity = "critical"
    elif confidence >= 0.8:
        severity = "high"
    elif confidence >= threshold:
        severity = "medium"
    else:
        severity = "low"

    return confidence, severity