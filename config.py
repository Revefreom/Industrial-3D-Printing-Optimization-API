"""
3D Yazıcı Maliyet Hesaplayıcı - Configuration Module
Merkezi konfigürasyon ve logging ayarları
"""

import os
import logging
from functools import lru_cache

# =============================================================================
# ENVIRONMENT VARIABLES
# =============================================================================

class Settings:
    """Uygulama ayarları - Environment variables ile override edilebilir."""
    
    # Database
    DB_FILE: str = os.getenv("DB_FILE", "printer_cost.db")
    SETTINGS_FILE: str = os.getenv("SETTINGS_FILE", "settings.json")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # CORS
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # API
    API_TITLE: str = "3D Yazıcı Maliyet Hesaplayıcı API"
    API_VERSION: str = "2.0.0"


@lru_cache()
def get_settings() -> Settings:
    """Singleton pattern ile settings instance döndürür."""
    return Settings()


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging(log_level: str = None) -> logging.Logger:
    """
    Uygulama için logging yapılandırması.
    
    Args:
        log_level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    level = log_level or settings.LOG_LEVEL
    
    # Root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Application logger
    logger = logging.getLogger("printer_cost_api")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    return logger


# Global logger instance
logger = setup_logging()
