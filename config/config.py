import os
import json
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

class TradingConfig:
    def __init__(self, 
                 config_path: str = "config/trading_config.json",
                 cdp_key_path: str = "config/cdp_api_key.json"):
        """Initialize trading configuration"""
        self.config_path = Path(config_path)
        self.cdp_key_path = Path(cdp_key_path)
        self.config: Dict[str, Any] = {}
        self.cdp_credentials: Dict[str, Any] = {}
        self._load_environment()
        self._load_config()
        self._load_cdp_credentials()
        
    def _load_environment(self):
        """Load environment variables from .env file"""
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
            
    def _load_config(self):
        """Load configuration from JSON file"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

    def _load_cdp_credentials(self):
        """Load Coinbase CDP API credentials from JSON file"""
        if self.cdp_key_path.exists():
            with open(self.cdp_key_path, 'r') as f:
                self.cdp_credentials = json.load(f)
        else:
            print(f"Warning: CDP API key file not found at {self.cdp_key_path}")
                
    @property
    def api_credentials(self) -> Dict[str, Any]:
        """Get API credentials from CDP key file"""
        return self.cdp_credentials
        
    @property
    def trading_params(self) -> Dict[str, Any]:
        """Get trading parameters"""
        return self.config.get('trading_params', {})
    
    @property
    def exchange_settings(self) -> Dict[str, Any]:
        """Get exchange settings"""
        return self.config.get('exchange_settings', {})
    
    def validate(self) -> bool:
        """Validate configuration"""
        # Check CDP credentials file exists and is not empty
        if not self.cdp_key_path.exists():
            print(f"Missing CDP API key file: {self.cdp_key_path}")
            return False
            
        if not self.cdp_credentials:
            print("CDP credentials file is empty or invalid")
            return False

        # Check configuration parameters
        required_config = ['trading_params', 'exchange_settings']
        missing_config = [conf for conf in required_config if conf not in self.config]
        if missing_config:
            print(f"Missing configuration sections: {missing_config}")
            return False
            
        return True

# Usage example
if __name__ == "__main__":
    config = TradingConfig()
    if config.validate():
        print("Configuration loaded successfully")
    else:
        print("Configuration validation failed")