import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Server configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8501"))

    # InfluxDB configuration
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN: Optional[str] = os.getenv("INFLUXDB_TOKEN")
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "monitorx")
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "metrics")

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Security configuration
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    API_KEYS: str = os.getenv("API_KEYS", "")
    JWT_ENABLED: bool = os.getenv("JWT_ENABLED", "false").lower() == "true"
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

    # Rate limiting configuration
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

    # CORS configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_ALLOW_CREDENTIALS: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"

    # Default thresholds
    DEFAULT_LATENCY_THRESHOLD: float = 1000.0  # ms
    DEFAULT_ERROR_RATE_THRESHOLD: float = 0.05  # 5%
    DEFAULT_GPU_MEMORY_THRESHOLD: float = 0.8  # 80%
    DEFAULT_CPU_USAGE_THRESHOLD: float = 0.8  # 80%
    DEFAULT_MEMORY_USAGE_THRESHOLD: float = 0.8  # 80%


config = Config()