#!/usr/bin/env python3
"""
MonitorX API Server Runner

Simple script to run the FastAPI server.
"""

import subprocess
import sys
import os

def main():
    """Run the MonitorX API server."""
    server_module = "monitorx.server:app"

    print("🎯 Starting MonitorX API Server...")
    print("🔗 API will be available at: http://localhost:8000")
    print("📚 API docs will be available at: http://localhost:8000/docs")
    print("🛑 Press Ctrl+C to stop")
    print()

    try:
        subprocess.run([
            "uvicorn", server_module,
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
            "--log-level", "info"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except FileNotFoundError:
        print("❌ Uvicorn not found! Please install it with:")
        print("   pip install uvicorn")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()