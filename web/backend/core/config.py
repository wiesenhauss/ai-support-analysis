"""
Configuration settings for the web backend.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    app_name: str = "AI Support Analyzer"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # OpenAI API Key
    openai_api_key: Optional[str] = None
    
    # CORS Settings
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # File Upload Settings
    max_upload_size_mb: int = 100
    upload_dir: str = "/tmp/ai-support-analyzer/uploads"
    
    # Database Settings (use existing data store path)
    db_path: Optional[str] = None
    
    # Analysis Settings
    max_concurrent_analyses: int = 2
    analysis_timeout_seconds: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Project root directory (for importing existing modules)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
