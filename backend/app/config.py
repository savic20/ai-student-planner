"""
Application Configuration
-------------------------
Loads settings from environment variables using Pydantic.

EXPLANATION FOR BEGINNERS:
- Pydantic validates that environment variables have the correct types
- If a required variable is missing, the app won't start (fail-fast principle)
- Settings are loaded once at startup and cached
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    WHAT THIS DOES:
    - Reads .env file automatically
    - Validates all settings on startup
    - Provides type-safe access to configuration
    """
    
    # -------------------------------------------------------------------------
    # DATABASE
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql://planner_user:planner_pass@localhost:5432/student_planner",
        description="PostgreSQL connection string"
    )
    
    # -------------------------------------------------------------------------
    # JWT AUTHENTICATION
    # -------------------------------------------------------------------------
    SECRET_KEY: str = Field(
        ...,  # ... means required (no default)
        description="Secret key for JWT encoding (NEVER share this!)"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token validity period"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token validity period"
    )
    
    # -------------------------------------------------------------------------
    # LLM PROVIDERS
    # -------------------------------------------------------------------------
    # Groq (Primary)
    GROQ_API_KEY: str = Field(
        ...,  # Required
        description="Groq API key from console.groq.com"
    )
    GROQ_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default Groq model to use"
    )
    
    # Ollama (Fallback)
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    OLLAMA_MODEL: str = Field(
        default="llama2",
        description="Ollama model name"
    )
    
    # LLM Gateway
    LLM_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")
    LLM_MAX_RETRIES: int = Field(default=3, description="Max retry attempts")
    LLM_FALLBACK_ENABLED: bool = Field(default=True, description="Enable Ollama fallback")
    
    # -------------------------------------------------------------------------
    # BACKEND API
    # -------------------------------------------------------------------------
    BACKEND_HOST: str = Field(default="0.0.0.0")
    BACKEND_PORT: int = Field(default=8000)
    BACKEND_RELOAD: bool = Field(default=True, description="Auto-reload on code changes")
    
    # CORS (Cross-Origin Resource Sharing)
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed origins"
    )
    
    @validator("CORS_ORIGINS")
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Convert comma-separated string to list"""
        return [origin.strip() for origin in v.split(",")]
    
    # -------------------------------------------------------------------------
    # FILE STORAGE
    # -------------------------------------------------------------------------
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10)
    ALLOWED_EXTENSIONS: str = Field(default="pdf,docx,txt")
    
    @validator("ALLOWED_EXTENSIONS")
    def parse_extensions(cls, v: str) -> List[str]:
        """Convert comma-separated string to list"""
        return [ext.strip() for ext in v.split(",")]
    
    # -------------------------------------------------------------------------
    # LOGGING
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR")
    
    # -------------------------------------------------------------------------
    # ENVIRONMENT
    # -------------------------------------------------------------------------
    ENVIRONMENT: str = Field(default="development", description="development or production")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    # -------------------------------------------------------------------------
    # COMPUTED PROPERTIES
    # -------------------------------------------------------------------------
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes for file upload validation"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    
    # -------------------------------------------------------------------------
    # PYDANTIC CONFIG
    # -------------------------------------------------------------------------
    class Config:
        env_file = ".env"  # Automatically load .env file
        env_file_encoding = "utf-8"
        case_sensitive = True  # DATABASE_URL != database_url


# ============================================================================
# GLOBAL SETTINGS INSTANCE
# ============================================================================
# This is loaded once at startup and reused everywhere
settings = Settings()


# ============================================================================
# HELPER FUNCTION TO PRINT CONFIG (FOR DEBUGGING)
# ============================================================================
def print_config():
    """Print current configuration (hides secrets)"""
    print("\n" + "="*70)
    print("APPLICATION CONFIGURATION")
    print("="*70)
    
    for field, value in settings.dict().items():
        # Hide sensitive values
        if any(secret in field.upper() for secret in ["KEY", "PASSWORD", "SECRET"]):
            display_value = "***HIDDEN***"
        else:
            display_value = value
        
        print(f"{field:30} = {display_value}")
    
    print("="*70 + "\n")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================
if __name__ == "__main__":
    # Run this file directly to test configuration
    print_config()
    
    # Example: Access settings
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"Is production? {settings.is_production}")
    print(f"Max upload size: {settings.max_upload_size_bytes} bytes")