"""
Configuration Management Module

This module handles loading and validation of configuration settings,
ensuring proper separation between different environments and secure
handling of sensitive data.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import os
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required fields."""
    pass

class BaseConfig:
    """Base configuration class with common validation logic."""
    
    def __init__(self, config_path: Path):
        """
        Initialize configuration from file.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse configuration file."""
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {self.config_path}: {str(e)}")
    
    def _validate_config(self) -> None:
        """Validate configuration has required fields."""
        required_fields = {
            "trading_pairs",
            "risk_management",
            "websocket"
        }
        
        missing = required_fields - set(self.config.keys())
        if missing:
            raise ConfigurationError(f"Missing required configuration fields: {missing}")
    
    def get_api_credentials(self) -> Dict[str, str]:
        """Load API credentials from separate secure file."""
        try:
            creds_path = self.config_path.parent / "cdp_api_key.json"
            with open(creds_path) as f:
                creds = json.load(f)
                required = {"api_key", "api_secret"}
                if not all(k in creds for k in required):
                    raise ConfigurationError("Missing required API credentials")
                return creds
        except Exception as e:
            raise ConfigurationError(f"Failed to load API credentials: {str(e)}")
    
    def get_risk_limits(self) -> Dict[str, Decimal]:
        """Get risk management limits with proper decimal conversion."""
        limits = self.config.get("risk_management", {})
        return {
            k: Decimal(str(v)) for k, v in limits.items()
        }
    
    def get_trading_pairs(self) -> list:
        """Get configured trading pairs."""
        return self.config.get("trading_pairs", [])
    
    def is_paper_trading(self) -> bool:
        """Check if paper trading is enabled."""
        return bool(self.config.get("paper_trading", True))

class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""
    
    def _validate_config(self) -> None:
        """Additional validation for development environment."""
        super()._validate_config()
        
        if not self.is_paper_trading():
            logger.warning("Paper trading disabled in development environment")

class ProductionConfig(BaseConfig):
    """Production environment configuration with stricter validation."""
    
    def _validate_config(self) -> None:
        """Additional validation for production environment."""
        super()._validate_config()
        
        if self.is_paper_trading():
            raise ConfigurationError("Paper trading must be disabled in production")
        
        # Validate risk management settings
        risk = self.config.get("risk_management", {})
        if not all(k in risk for k in ["daily_loss_limit", "position_size_limit"]):
            raise ConfigurationError("Production requires all risk management settings")
        
        # Validate max positions are set
        if "max_positions" not in self.config:
            raise ConfigurationError("Production requires maximum position limits")

class TestConfig(BaseConfig):
    """Test environment configuration."""
    
    def _validate_config(self) -> None:
        """Validation for test environment."""
        # Basic validation is sufficient for tests
        if not self.is_paper_trading():
            raise ConfigurationError("Tests must use paper trading")

def load_config(environment: Optional[str] = None) -> BaseConfig:
    """
    Factory function to load appropriate configuration based on environment.
    
    Args:
        environment: Optional environment name. If not provided, reads from ENV var.
    
    Returns:
        Configuration instance for specified environment
    """
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development").lower()
    
    config_dir = Path("config")
    
    config_map = {
        "development": (DevelopmentConfig, "config.json"),
        "production": (ProductionConfig, "production.json"),
        "test": (TestConfig, "test_config.json")
    }
    
    if environment not in config_map:
        raise ConfigurationError(f"Invalid environment: {environment}")
    
    ConfigClass, filename = config_map[environment]
    config_path = config_dir / filename
    
    if not config_path.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    
    return ConfigClass(config_path)