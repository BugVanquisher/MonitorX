#!/usr/bin/env python3
"""
MonitorX Dashboard Runner

Simple script to run the Streamlit dashboard.
"""

import subprocess
import sys
import os

def main():
    """Run the MonitorX dashboard."""
    dashboard_path = os.path.join("src", "monitorx", "dashboard", "app.py")

    if not os.path.exists(dashboard_path):
        print("❌ Dashboard app not found!")
        print(f"Expected path: {dashboard_path}")
        sys.exit(1)

    print("🎯 Starting MonitorX Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop")
    print()

    try:
        subprocess.run([
            "streamlit", "run", dashboard_path,
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except FileNotFoundError:
        print("❌ Streamlit not found! Please install it with:")
        print("   pip install streamlit")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()