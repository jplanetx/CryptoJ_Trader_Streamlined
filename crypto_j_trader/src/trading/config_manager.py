"""Standardized configuration management"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import os

class ConfigManager:
    """Centralized configuration management"""
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config_paths = {
            'main': 'config/config.json',
            'test': 'config/test_config.json',
            'production': 'config/production.json',
            'trading': 'config/trading_config.json'
        }
        
    def load_config(self, config_type: str = 'main') -> Dict[str, Any]:
        """Load configuration from specified config file"""
        if config_type in self._config:
            return self._config[config_type]
            
        config_path = self.config_paths.get(config_type)
        if not config_path:
            raise ValueError(f"Unknown config type: {config_type}")
            
        try:
            with open(config_path, 'r') as f:
                self._config[config_type] = json.load(f)
            return self._config[config_type]
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
    def get_api_credentials(self) -> Dict[str, str]:
        """Get API credentials from config"""
        config = self.load_config()
        return {
            'api_key': config.get('api_key', ''),
            'base_url': config.get('base_url', 'https://api.testexchange.com'),
            'timeout': config.get('timeout', 30)
        }
        
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading specific configuration"""
        return self.load_config('trading')
        
    def get_test_config(self) -> Dict[str, Any]:
        """Get test specific configuration"""
        return self.load_config('test')
        
    def get_risk_parameters(self) -> Dict[str, Any]:
        """Get risk management parameters"""
        trading_config = self.get_trading_config()
        return trading_config.get('risk_management', {
            'max_position_size': 5.0,
            'stop_loss_pct': 0.05,
            'max_daily_loss': 500.0
        })

    @staticmethod
    def validate_trading_pair(trading_pair: str) -> bool:
        """Validate trading pair format"""
        if not isinstance(trading_pair, str):
            return False
        parts = trading_pair.split('-')
        return len(parts) == 2 and all(p.isupper() for p in parts)