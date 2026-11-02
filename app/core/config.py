"""
Configuration management for the Browser Use Agent
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application Configuration
    app_name: str = "Browser Use Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Database Configuration
    database_url: str = "postgresql://user:password@localhost:5432/bua_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    
    # LLM Configuration
    bua_llm_provider: str = "openai"  # "openai" or "gemini"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.1
    
    # Google Gemini
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Alternative name for Google API key
    google_model: str = "gemini-1.5-pro"
    google_max_tokens: int = 4000
    google_temperature: float = 0.1
    
    # Browser Configuration
    browser_type: str = "chromium"
    browser_headless: bool = True
    browser_timeout: int = 30000
    browser_viewport_width: int = 1920
    browser_viewport_height: int = 1080
    
    # Security
    secret_key: str = "your_secret_key_here_change_in_production"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # Task Queue
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_task_serializer: str = "json"
    celery_result_serializer: str = "json"
    celery_accept_content: str = "json"
    celery_timezone: str = "UTC"
    celery_enable_utc: bool = True
    
    # Logging
    log_file: str = "logs/bua.log"
    log_max_size: str = "10MB"
    log_backup_count: int = 5
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    enable_health_checks: bool = True
    
    # CORS and Security
    allowed_origins: List[str] = ["*"]
    allowed_hosts: List[str] = ["*"]
    
    @validator("allowed_origins", "allowed_hosts", pre=True)
    def parse_list(cls, v):
        """Parse comma-separated strings into lists"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @validator("browser_type")
    def validate_browser_type(cls, v):
        """Validate browser type"""
        valid_browsers = ["chromium", "firefox", "webkit"]
        if v.lower() not in valid_browsers:
            raise ValueError(f"BROWSER_TYPE must be one of {valid_browsers}")
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        alias_generator = lambda string: string.upper()


# Create global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
