"""
Configuration settings for the Multi-Language Broadcast API
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Configuration
    app_name: str = "Multi-Language Broadcast API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Environment
    environment: str = "development"
    
    # CORS Configuration
    cors_origins: list = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list = ["*"]
    cors_allow_headers: list = ["*"]
    
    # Logging
    log_level: str = "info"
    
    # Database (for future use)
    database_url: Optional[str] = None
    
    # Redis (for future use)
    redis_url: Optional[str] = None
    
    # API Keys
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Google Cloud Translation Configuration
    google_cloud_project_id: Optional[str] = "nama-ai-455515"
    google_cloud_location: str = "us-central1"
    google_application_credentials: str = "credentials.json"  # Path to credentials file from root directory
    
    # Translation Configuration
    default_source_language: str = "en"
    default_target_language: str = "es"
    translation_model: str = "nmt"  # nmt, base, or custom model path
    translation_mime_type: str = "text/plain"  # text/plain or text/html
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
