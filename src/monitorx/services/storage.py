from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import asyncio
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from loguru import logger

from ..types import InferenceMetric, DriftMetric, Alert
from ..config import config


class InfluxDBStorage:
    def __init__(self):
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None
        self.bucket = config.INFLUXDB_BUCKET
        self.org = config.INFLUXDB_ORG

    async def connect(self):
        """Connect to InfluxDB."""
        try:
            self.client = InfluxDBClient(
                url=config.INFLUXDB_URL,
                token=config.INFLUXDB_TOKEN,
                org=self.org
            )
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()

            # Test connection
            health = self.client.health()
            if health.status == "pass":
                logger.info("Successfully connected to InfluxDB")
            else:
                raise Exception(f"InfluxDB health check failed: {health.message}")

        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from InfluxDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from InfluxDB")

    async def write_inference_metric(self, metric: InferenceMetric) -> None:
        """Write inference metric to InfluxDB."""
        if not self.write_api:
            raise RuntimeError("Not connected to InfluxDB")

        try:
            point = (
                Point("inference_metrics")
                .tag("model_id", metric.model_id)
                .tag("model_type", metric.model_type)
                .tag("request_id", metric.request_id)
                .field("latency", metric.latency)
                .time(metric.timestamp)
            )

            # Add optional fields
            if metric.throughput is not None:
                point = point.field("throughput", metric.throughput)

            if metric.error_rate is not None:
                point = point.field("error_rate", metric.error_rate)

            # Add resource usage fields
            if metric.resource_usage:
                if metric.resource_usage.gpu_memory is not None:
                    point = point.field("gpu_memory", metric.resource_usage.gpu_memory)
                if metric.resource_usage.cpu_usage is not None:
                    point = point.field("cpu_usage", metric.resource_usage.cpu_usage)
                if metric.resource_usage.memory_usage is not None:
                    point = point.field("memory_usage", metric.resource_usage.memory_usage)

            # Add custom tags
            for key, value in metric.tags.items():
                point = point.tag(key, value)

            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Wrote inference metric for model {metric.model_id}")

        except Exception as e:
            logger.error(f"Failed to write inference metric: {e}")

    async def write_drift_metric(self, metric: DriftMetric) -> None:
        """Write drift metric to InfluxDB."""
        if not self.write_api:
            raise RuntimeError("Not connected to InfluxDB")

        try:
            point = (
                Point("drift_metrics")
                .tag("model_id", metric.model_id)
                .tag("drift_type", metric.drift_type)
                .tag("severity", metric.severity)
                .field("confidence", metric.confidence)
                .time(metric.timestamp)
            )

            # Add custom tags
            for key, value in metric.tags.items():
                point = point.tag(key, value)

            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Wrote drift metric for model {metric.model_id}")

        except Exception as e:
            logger.error(f"Failed to write drift metric: {e}")

    async def write_alert(self, alert: Alert) -> None:
        """Write alert to InfluxDB."""
        if not self.write_api:
            raise RuntimeError("Not connected to InfluxDB")

        try:
            point = (
                Point("alerts")
                .tag("alert_id", alert.id)
                .tag("model_id", alert.model_id)
                .tag("alert_type", alert.alert_type)
                .tag("severity", alert.severity)
                .field("message", alert.message)
                .field("resolved", alert.resolved)
                .time(alert.timestamp)
            )

            if alert.resolved_at:
                point = point.field("resolved_at", alert.resolved_at.isoformat())

            self.write_api.write(bucket=self.bucket, record=point)
            logger.debug(f"Wrote alert {alert.id}")

        except Exception as e:
            logger.error(f"Failed to write alert: {e}")

    async def query_inference_metrics(
        self,
        model_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query inference metrics from InfluxDB."""
        if not self.query_api:
            raise RuntimeError("Not connected to InfluxDB")

        # Default to last 24 hours
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.now()

        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "inference_metrics")
        '''

        if model_id:
            query += f'|> filter(fn: (r) => r.model_id == "{model_id}")\n'

        query += f'|> limit(n: {limit})\n'

        try:
            tables = self.query_api.query(query)
            results = []

            for table in tables:
                for record in table.records:
                    results.append({
                        'time': record.get_time(),
                        'model_id': record.values.get('model_id'),
                        'model_type': record.values.get('model_type'),
                        'field': record.get_field(),
                        'value': record.get_value(),
                        **{k: v for k, v in record.values.items()
                           if k.startswith('tag_') or k in ['request_id']}
                    })

            logger.debug(f"Queried {len(results)} inference metric records")
            return results

        except Exception as e:
            logger.error(f"Failed to query inference metrics: {e}")
            return []

    async def query_drift_metrics(
        self,
        model_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query drift metrics from InfluxDB."""
        if not self.query_api:
            raise RuntimeError("Not connected to InfluxDB")

        # Default to last 7 days
        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()

        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "drift_metrics")
        '''

        if model_id:
            query += f'|> filter(fn: (r) => r.model_id == "{model_id}")\n'

        query += f'|> limit(n: {limit})\n'

        try:
            tables = self.query_api.query(query)
            results = []

            for table in tables:
                for record in table.records:
                    results.append({
                        'time': record.get_time(),
                        'model_id': record.values.get('model_id'),
                        'drift_type': record.values.get('drift_type'),
                        'severity': record.values.get('severity'),
                        'confidence': record.get_value(),
                    })

            logger.debug(f"Queried {len(results)} drift metric records")
            return results

        except Exception as e:
            logger.error(f"Failed to query drift metrics: {e}")
            return []

    async def query_alerts(
        self,
        model_id: Optional[str] = None,
        resolved: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query alerts from InfluxDB."""
        if not self.query_api:
            raise RuntimeError("Not connected to InfluxDB")

        # Default to last 7 days
        if not start_time:
            start_time = datetime.now() - timedelta(days=7)
        if not end_time:
            end_time = datetime.now()

        query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "alerts")
        '''

        if model_id:
            query += f'|> filter(fn: (r) => r.model_id == "{model_id}")\n'

        if resolved is not None:
            query += f'|> filter(fn: (r) => r.resolved == {str(resolved).lower()})\n'

        query += f'|> limit(n: {limit})\n'

        try:
            tables = self.query_api.query(query)
            results = []

            for table in tables:
                for record in table.records:
                    if record.get_field() == "message":  # Use message field as primary
                        results.append({
                            'time': record.get_time(),
                            'alert_id': record.values.get('alert_id'),
                            'model_id': record.values.get('model_id'),
                            'alert_type': record.values.get('alert_type'),
                            'severity': record.values.get('severity'),
                            'message': record.get_value(),
                            'resolved': record.values.get('resolved', False)
                        })

            logger.debug(f"Queried {len(results)} alert records")
            return results

        except Exception as e:
            logger.error(f"Failed to query alerts: {e}")
            return []

    async def get_aggregated_metrics(
        self,
        model_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        window: str = "5m"
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get aggregated metrics (average, min, max) over time windows."""
        if not self.query_api:
            raise RuntimeError("Not connected to InfluxDB")

        # Default to last 6 hours
        if not start_time:
            start_time = datetime.now() - timedelta(hours=6)
        if not end_time:
            end_time = datetime.now()

        base_query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
            |> filter(fn: (r) => r._measurement == "inference_metrics")
        '''

        if model_id:
            base_query += f'|> filter(fn: (r) => r.model_id == "{model_id}")\n'

        results = {}

        # Query different metrics
        metrics = ["latency", "throughput", "error_rate", "gpu_memory", "cpu_usage"]

        for metric in metrics:
            query = base_query + f'''
                |> filter(fn: (r) => r._field == "{metric}")
                |> aggregateWindow(every: {window}, fn: mean)
                |> yield(name: "mean")
            '''

            try:
                tables = self.query_api.query(query)
                metric_data = []

                for table in tables:
                    for record in table.records:
                        metric_data.append({
                            'time': record.get_time(),
                            'value': record.get_value(),
                        })

                results[metric] = metric_data

            except Exception as e:
                logger.error(f"Failed to query aggregated {metric} metrics: {e}")
                results[metric] = []

        return results