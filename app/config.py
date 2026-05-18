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
    
    # Azure SQL Database
    AZURE_SQL_SERVER: str
    AZURE_SQL_DATABASE: str
    AZURE_SQL_USERNAME: str
    AZURE_SQL_PASSWORD: str
    AZURE_SQL_DRIVER: str = "ODBC Driver 18 for SQL Server"
    
    @property
    def database_url(self) -> str:
        """Construct SQL Server connection string"""
        return (
            f"mssql+pyodbc://{self.AZURE_SQL_USERNAME}:{self.AZURE_SQL_PASSWORD}"
            f"@{self.AZURE_SQL_SERVER}/{self.AZURE_SQL_DATABASE}"
            f"?driver={self.AZURE_SQL_DRIVER.replace(' ', '+')}"
            f"&Encrypt=yes&TrustServerCertificate=no"
        )
    
    # Anthropic Claude API
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 4096
    
    # Qdrant Vector Store
    QDRANT_URL: str
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_INCIDENTS: str = "historical_incidents"
    QDRANT_COLLECTION_STANDARDS: str = "singapore_standards"
    QDRANT_COLLECTION_MANUALS: str = "oem_manuals"
    
    # Image Storage
    IMAGE_UPLOAD_DIR: str = "./app/images"
    MAX_IMAGE_SIZE_MB: int = 10
    
    # Business Logic Thresholds
    HIGH_SEVERITY_COST_THRESHOLD: float = 5000.0
    CRITICAL_FAILURE_PROBABILITY_THRESHOLD: float = 0.30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()