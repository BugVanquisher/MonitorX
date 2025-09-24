import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from .api import router
from .services.storage import InfluxDBStorage
from .config import config


# Global storage instance
storage = InfluxDBStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting MonitorX API server...")
    try:
        await storage.connect()
        logger.info("Successfully connected to InfluxDB")
    except Exception as e:
        logger.warning(f"Failed to connect to InfluxDB: {e}")

    yield

    # Shutdown
    logger.info("Shutting down MonitorX API server...")
    await storage.disconnect()


# Create FastAPI app
app = FastAPI(
    title="MonitorX API",
    description="ML/AI Infrastructure Observability Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic information."""
    return """
    <html>
        <head>
            <title>MonitorX API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { color: #333; }
                .section { margin: 20px 0; }
                .endpoint { background: #f5f5f5; padding: 10px; margin: 5px 0; }
                code { background: #e8e8e8; padding: 2px 4px; }
            </style>
        </head>
        <body>
            <h1 class="header">🎯 MonitorX API</h1>
            <p>ML/AI Infrastructure Observability Platform</p>

            <div class="section">
                <h2>Quick Start</h2>
                <p>Visit <code>/docs</code> for interactive API documentation</p>
                <p>Visit <code>/redoc</code> for alternative documentation</p>
                <p>Check <code>/api/v1/health</code> for system status</p>
            </div>

            <div class="section">
                <h2>Main Endpoints</h2>
                <div class="endpoint">
                    <strong>POST /api/v1/metrics/inference</strong> - Collect inference metrics
                </div>
                <div class="endpoint">
                    <strong>POST /api/v1/metrics/drift</strong> - Report drift detection
                </div>
                <div class="endpoint">
                    <strong>POST /api/v1/models</strong> - Register model configuration
                </div>
                <div class="endpoint">
                    <strong>GET /api/v1/alerts</strong> - Retrieve alerts
                </div>
                <div class="endpoint">
                    <strong>GET /api/v1/summary</strong> - Get summary statistics
                </div>
            </div>

            <div class="section">
                <h2>Features</h2>
                <ul>
                    <li>Real-time inference metrics collection</li>
                    <li>Model drift detection and alerting</li>
                    <li>Resource usage monitoring</li>
                    <li>Configurable thresholds per model</li>
                    <li>Time-series data storage with InfluxDB</li>
                    <li>RESTful API with OpenAPI documentation</li>
                </ul>
            </div>

            <footer style="margin-top: 40px; color: #666; font-size: 14px;">
                MonitorX v0.1.0 - The missing piece between ML model deployment and production reliability
            </footer>
        </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting MonitorX API server on {config.API_HOST}:{config.API_PORT}")
    uvicorn.run(
        "monitorx.server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower()
    )