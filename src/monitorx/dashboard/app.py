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

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import httpx
from datetime import datetime, timedelta
import asyncio
from typing import Dict, List, Any
import json
import io
import time

# Support both relative import (when run as package) and absolute import (when run with streamlit)
try:
    from ..config import config
except ImportError:
    from monitorx.config import config


class DashboardAPI:
    """API client for the dashboard."""

    def __init__(self, base_url: str = f"http://{config.API_HOST}:{config.API_PORT}"):
        self.base_url = base_url

    async def get_models(self) -> List[Dict[str, Any]]:
        """Get registered models."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/v1/models")
                response.raise_for_status()
                return response.json().get("models", [])
            except Exception as e:
                st.error(f"Failed to fetch models: {e}")
                return []

    async def get_summary_stats(self, model_id: str = None, since_hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics."""
        async with httpx.AsyncClient() as client:
            try:
                params = {"since_hours": since_hours}
                if model_id:
                    params["model_id"] = model_id

                response = await client.get(f"{self.base_url}/api/v1/summary", params=params)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                st.error(f"Failed to fetch summary stats: {e}")
                return {}

    async def get_metrics(self, model_id: str = None, since_hours: int = 24, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get inference metrics."""
        async with httpx.AsyncClient() as client:
            try:
                params = {"since_hours": since_hours, "limit": limit}
                if model_id:
                    params["model_id"] = model_id

                response = await client.get(f"{self.base_url}/api/v1/metrics/inference", params=params)
                response.raise_for_status()
                return response.json().get("metrics", [])
            except Exception as e:
                st.error(f"Failed to fetch metrics: {e}")
                return []

    async def get_alerts(self, model_id: str = None, since_hours: int = 168, resolved: bool = None) -> List[Dict[str, Any]]:
        """Get alerts."""
        async with httpx.AsyncClient() as client:
            try:
                params = {"since_hours": since_hours}
                if model_id:
                    params["model_id"] = model_id
                if resolved is not None:
                    params["resolved"] = resolved

                response = await client.get(f"{self.base_url}/api/v1/alerts", params=params)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                st.error(f"Failed to fetch alerts: {e}")
                return []

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/alerts/resolve",
                    json={"alert_id": alert_id}
                )
                response.raise_for_status()
                return True
            except Exception as e:
                st.error(f"Failed to resolve alert: {e}")
                return False

    async def get_aggregated_metrics(self, model_id: str = None, since_hours: int = 6, window: str = "5m") -> Dict[str, Any]:
        """Get aggregated metrics."""
        async with httpx.AsyncClient() as client:
            try:
                params = {"since_hours": since_hours, "window": window}
                if model_id:
                    params["model_id"] = model_id

                response = await client.get(f"{self.base_url}/api/v1/metrics/aggregated", params=params)
                response.raise_for_status()
                return response.json().get("aggregated_metrics", {})
            except Exception as e:
                st.error(f"Failed to fetch aggregated metrics: {e}")
                return {}


# Initialize API client
api = DashboardAPI()


def run_async(coro):
    """Helper to run async functions in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def create_metric_charts(metrics_data: Dict[str, List[Dict[str, Any]]]):
    """Create time-series charts for metrics."""
    if not metrics_data:
        st.warning("No aggregated metrics data available")
        return

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Latency (ms)', 'Throughput', 'Error Rate', 'GPU Memory Usage'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"secondary_y": False}]]
    )

    # Latency
    if "latency" in metrics_data and metrics_data["latency"]:
        df = pd.DataFrame(metrics_data["latency"])
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            fig.add_trace(
                go.Scatter(x=df['time'], y=df['value'], name='Latency', mode='lines'),
                row=1, col=1
            )

    # Throughput
    if "throughput" in metrics_data and metrics_data["throughput"]:
        df = pd.DataFrame(metrics_data["throughput"])
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            fig.add_trace(
                go.Scatter(x=df['time'], y=df['value'], name='Throughput', mode='lines'),
                row=1, col=2
            )

    # Error Rate
    if "error_rate" in metrics_data and metrics_data["error_rate"]:
        df = pd.DataFrame(metrics_data["error_rate"])
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            fig.add_trace(
                go.Scatter(x=df['time'], y=df['value'], name='Error Rate', mode='lines'),
                row=2, col=1
            )

    # GPU Memory
    if "gpu_memory" in metrics_data and metrics_data["gpu_memory"]:
        df = pd.DataFrame(metrics_data["gpu_memory"])
        if not df.empty:
            df['time'] = pd.to_datetime(df['time'])
            fig.add_trace(
                go.Scatter(x=df['time'], y=df['value'], name='GPU Memory', mode='lines'),
                row=2, col=2
            )

    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def export_to_csv(data: pd.DataFrame, filename: str) -> bytes:
    """Export DataFrame to CSV bytes."""
    return data.to_csv(index=False).encode('utf-8')


def export_to_json(data: List[Dict[str, Any]], filename: str) -> bytes:
    """Export data to JSON bytes."""
    return json.dumps(data, indent=2, default=str).encode('utf-8')


def display_alerts(alerts: List[Dict[str, Any]]):
    """Display alerts in a formatted way with resolution capability."""
    if not alerts:
        st.success("No active alerts")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(alerts)
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Color code by severity
    severity_colors = {
        'low': '🟢',
        'medium': '🟡',
        'high': '🟠',
        'critical': '🔴'
    }

    for _, alert in df.iterrows():
        severity_icon = severity_colors.get(alert['severity'], '⚪')
        status_icon = '✅' if alert['resolved'] else '❌'

        with st.expander(f"{severity_icon} {alert['alert_type'].title()} Alert - {alert['model_id']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Severity:** {alert['severity'].title()}")
                st.write(f"**Type:** {alert['alert_type'].replace('_', ' ').title()}")
            with col2:
                st.write(f"**Status:** {'Resolved' if alert['resolved'] else 'Active'} {status_icon}")
                st.write(f"**Timestamp:** {alert['timestamp']}")
            with col3:
                st.write(f"**Model:** {alert['model_id']}")

            st.write(f"**Message:** {alert['message']}")

            if not alert['resolved']:
                if st.button(f"✓ Resolve Alert", key=f"resolve_{alert['id']}", type="primary"):
                    # Resolve alert via API
                    success = run_async(api.resolve_alert(alert['id']))
                    if success:
                        st.success(f"✅ Alert {alert['id']} resolved successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to resolve alert. Please try again.")


def main():
    """Main dashboard application."""
    st.set_page_config(
        page_title="MonitorX Dashboard",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🎯 MonitorX Dashboard")
    st.markdown("ML/AI Infrastructure Observability Platform")

    # Sidebar for model selection and time range
    st.sidebar.header("Filters")

    # Get models
    models = run_async(api.get_models())
    model_options = ["All Models"] + [f"{m['name']} ({m['id']})" for m in models]
    selected_model = st.sidebar.selectbox("Select Model", model_options)

    # Extract model ID
    model_id = None
    if selected_model != "All Models":
        model_id = selected_model.split("(")[-1].rstrip(")")

    # Time range selection
    time_ranges = {
        "Last Hour": 1,
        "Last 6 Hours": 6,
        "Last 24 Hours": 24,
        "Last 7 Days": 168
    }
    selected_range = st.sidebar.selectbox("Time Range", list(time_ranges.keys()), index=2)
    since_hours = time_ranges[selected_range]

    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto Refresh (30s)", value=False)
    refresh_interval = st.sidebar.slider("Refresh Interval (seconds)", 5, 120, 30, 5, disabled=not auto_refresh)

    if auto_refresh:
        # Use session state to track last refresh time
        if 'last_refresh' not in st.session_state:
            st.session_state.last_refresh = time.time()

        current_time = time.time()
        elapsed = current_time - st.session_state.last_refresh

        if elapsed >= refresh_interval:
            st.session_state.last_refresh = current_time
            st.rerun()

        # Show countdown
        remaining = int(refresh_interval - elapsed)
        st.sidebar.info(f"⏱️ Next refresh in {remaining}s")
        time.sleep(1)
        st.rerun()

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Metrics", "🚨 Alerts", "🔧 Models"])

    with tab1:
        st.header("System Overview")

        # Get summary stats
        summary = run_async(api.get_summary_stats(model_id, since_hours))

        if summary:
            # KPI metrics
            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                st.metric(
                    label="Total Requests",
                    value=f"{summary.get('total_requests', 0):,}"
                )

            with col2:
                avg_latency = summary.get('average_latency', 0)
                st.metric(
                    label="Avg Latency",
                    value=f"{avg_latency:.1f}ms"
                )

            with col3:
                error_rate = summary.get('error_rate', 0)
                st.metric(
                    label="Error Rate",
                    value=f"{error_rate:.2%}"
                )

            with col4:
                p95_latency = summary.get('p95_latency', 0)
                st.metric(
                    label="P95 Latency",
                    value=f"{p95_latency:.1f}ms"
                )

            with col5:
                active_alerts = summary.get('active_alerts', 0)
                st.metric(
                    label="Active Alerts",
                    value=active_alerts,
                    delta=None if active_alerts == 0 else f"⚠️"
                )

        # Time series charts
        st.subheader("Performance Trends")
        aggregated_data = run_async(api.get_aggregated_metrics(model_id, min(since_hours, 24), "5m"))
        create_metric_charts(aggregated_data)

    with tab2:
        st.header("Detailed Metrics")

        # Get recent metrics
        metrics = run_async(api.get_metrics(model_id, since_hours, 500))

        if metrics:
            df = pd.DataFrame(metrics)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Export buttons
            col1, col2, col3 = st.columns([6, 1, 1])
            with col1:
                st.subheader("Recent Metrics")
            with col2:
                # CSV export
                csv_data = export_to_csv(df, f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download metrics as CSV"
                )
            with col3:
                # JSON export
                json_data = export_to_json(metrics, f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                st.download_button(
                    label="📥 JSON",
                    data=json_data,
                    file_name=f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    help="Download metrics as JSON"
                )

            # Latest metrics table
            display_df = df[['timestamp', 'model_id', 'model_type', 'latency', 'error_rate']].head(20)
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(display_df, use_container_width=True)

            # Latency distribution
            st.subheader("Latency Distribution")
            fig = px.histogram(df, x='latency', nbins=30, title="Latency Distribution")
            fig.update_layout(xaxis_title="Latency (ms)", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

            # Model performance comparison (if multiple models)
            if not model_id and len(df['model_id'].unique()) > 1:
                st.subheader("Model Performance Comparison")
                model_stats = df.groupby('model_id').agg({
                    'latency': ['mean', 'median'],
                    'error_rate': 'mean'
                }).round(2)
                st.dataframe(model_stats)

        else:
            st.info("No metrics data available for the selected time range")

    with tab3:
        col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
        with col1:
            st.header("Alerts")
        with col2:
            pass  # Spacer
        with col3:
            export_alerts_csv = st.button("📥 CSV", help="Export alerts to CSV", disabled=True, key="alerts_csv_btn")
        with col4:
            export_alerts_json = st.button("📥 JSON", help="Export alerts to JSON", disabled=True, key="alerts_json_btn")

        # Alert filters
        col1, col2 = st.columns(2)
        with col1:
            show_resolved = st.checkbox("Include Resolved Alerts", value=False)
        with col2:
            alert_time_range = st.selectbox("Alert Time Range", ["Last 24 Hours", "Last 7 Days"], index=1)

        alert_hours = 24 if alert_time_range == "Last 24 Hours" else 168

        # Get alerts
        alerts = run_async(api.get_alerts(model_id, alert_hours, None if show_resolved else False))

        # Enable export buttons if we have alerts
        if alerts:
            # Re-render export buttons with actual data
            col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
            with col1:
                pass
            with col2:
                pass
            with col3:
                # CSV export
                alerts_df = pd.DataFrame(alerts)
                csv_data = export_to_csv(alerts_df, f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                st.download_button(
                    label="📥 CSV",
                    data=csv_data,
                    file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    help="Download alerts as CSV",
                    key="alerts_csv_download"
                )
            with col4:
                # JSON export
                json_data = export_to_json(alerts, f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                st.download_button(
                    label="📥 JSON",
                    data=json_data,
                    file_name=f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    help="Download alerts as JSON",
                    key="alerts_json_download"
                )

        # Display alerts
        display_alerts(alerts)

        # Alert statistics
        if alerts:
            st.subheader("Alert Summary")
            df = pd.DataFrame(alerts)

            col1, col2 = st.columns(2)
            with col1:
                # Alert count by severity
                severity_counts = df['severity'].value_counts()
                fig = px.pie(
                    values=severity_counts.values,
                    names=severity_counts.index,
                    title="Alerts by Severity"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                # Alert count by type
                type_counts = df['alert_type'].value_counts()
                fig = px.bar(
                    x=type_counts.index,
                    y=type_counts.values,
                    title="Alerts by Type"
                )
                fig.update_layout(xaxis_title="Alert Type", yaxis_title="Count")
                st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.header("Registered Models")

        if models:
            for model in models:
                with st.expander(f"📋 {model['name']} ({model['model_type'].upper()})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**ID:** {model['id']}")
                        st.write(f"**Version:** {model['version']}")
                        st.write(f"**Environment:** {model['environment']}")
                        st.write(f"**Type:** {model['model_type']}")

                    with col2:
                        st.write("**Thresholds:**")
                        thresholds = model.get('thresholds', {})
                        st.write(f"- Latency: {thresholds.get('latency', 'N/A')}ms")
                        st.write(f"- Error Rate: {thresholds.get('error_rate', 'N/A')}")
                        st.write(f"- GPU Memory: {thresholds.get('gpu_memory', 'N/A')}")
                        st.write(f"- CPU Usage: {thresholds.get('cpu_usage', 'N/A')}")

        else:
            st.info("No models registered yet")

    # Footer
    st.markdown("---")
    st.markdown(
        "MonitorX v0.1.0 - The missing piece between ML model deployment and production reliability"
    )


if __name__ == "__main__":
    main()