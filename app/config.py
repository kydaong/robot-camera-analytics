"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Settings
    APP_NAME: str = "Robot Camera Analytics API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Azure SQL Database (matches .env variable names)
    AZURE_SQL_SERVER: str
    AZURE_SQL_DATABASE: str
    AZURE_SQL_USER: str
    AZURE_SQL_PWD: str
    AZURE_DRIVER: str = "ODBC Driver 18 for SQL Server"

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        driver = quote_plus(self.AZURE_DRIVER)
        return (
            f"mssql+pyodbc://{self.AZURE_SQL_USER}:{quote_plus(self.AZURE_SQL_PWD)}"
            f"@{self.AZURE_SQL_SERVER}/{self.AZURE_SQL_DATABASE}"
            f"?driver={driver}&Encrypt=yes&TrustServerCertificate=no"
        )

    # Anthropic Claude API
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 4096

    # Qdrant Vector Store (local: host + port)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_INCIDENTS: str = "historical_incidents"
    QDRANT_COLLECTION_STANDARDS: str = "singapore_standards"
    QDRANT_COLLECTION_MANUALS: str = "oem_manuals"
    QDRANT_COLLECTION_INSPECTION_TASKS: str = "inspection_tasks"

    # Embedding model (sentence-transformers)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Image Storage
    IMAGE_UPLOAD_DIR: str = "./app/images"
    MAX_IMAGE_SIZE_MB: int = 10

    # MLflow Tracing
    MLFLOW_TRACKING_URI: str = "http://localhost:5001"
    MLFLOW_EXPERIMENT_NAME: str = "ai-coworker"

    # Business Logic Thresholds
    HIGH_SEVERITY_COST_THRESHOLD: float = 5000.0
    CRITICAL_FAILURE_PROBABILITY_THRESHOLD: float = 0.30

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Global settings instance
settings = Settings()