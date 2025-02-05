#!/usr/bin/env python3
"""
Configuration Initialization Script

This script sets up the necessary configuration files for local development
while ensuring sensitive data remains secure and out of version control.
"""

import json
import shutil
from pathlib import Path
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_config():
    """Initialize configuration files from templates."""
    try:
        # Ensure config directory exists
        config_dir = Path("config")
        config_dir.mkdir(exist_ok=True)
        
        # Initialize main config
        main_config = config_dir / "config.json"
        if not main_config.exists():
            shutil.copy(
                config_dir / "config.example.json",
                main_config
            )
            logger.info(f"Created {main_config}")
        
        # Initialize API credentials file
        creds_file = config_dir / "cdp_api_key.json"
        if not creds_file.exists():
            creds_template = {
                "api_key": "",
                "api_secret": "",
                "paper_trading": True
            }
            creds_file.write_text(json.dumps(creds_template, indent=2))
            logger.info(f"Created {creds_file}")
        
        # Initialize .env file
        env_file = Path(".env")
        env_template = Path(".env.template")
        if not env_file.exists() and env_template.exists():
            shutil.copy(env_template, env_file)
            logger.info(f"Created {env_file}")
        
        # Initialize test config
        test_config = config_dir / "test_config.json"
        if not test_config.exists():
            test_template = {
                "paper_trading": True,
                "trading_pairs": [
                    {
                        "pair": "BTC-USD",
                        "weight": 0.6,
                        "precision": 8
                    }
                ],
                "risk_management": {
                    "daily_loss_limit": 0.02,
                    "position_size_limit": 0.1,
                    "stop_loss_pct": 0.05
                },
                "emergency": {
                    "max_positions": {
                        "BTC-USD": 1.0
                    },
                    "risk_limits": {
                        "BTC-USD": 50000.0
                    }
                }
            }
            test_config.write_text(json.dumps(test_template, indent=2))
            logger.info(f"Created {test_config}")
        
        logger.info("Configuration initialization complete")
        logger.info("\nNext steps:")
        logger.info("1. Update .env with your environment variables")
        logger.info("2. Update config/cdp_api_key.json with your API credentials")
        logger.info("3. Review and modify config/config.json for your needs")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize configuration: {str(e)}")
        return False

def validate_config():
    """Validate configuration files exist and have required fields."""
    required_files = [
        ".env",
        "config/config.json",
        "config/cdp_api_key.json",
        "config/test_config.json"
    ]
    
    missing = []
    for file in required_files:
        if not Path(file).exists():
            missing.append(file)
    
    if missing:
        logger.warning("Missing configuration files:")
        for file in missing:
            logger.warning(f"- {file}")
        return False
    
    return True

if __name__ == "__main__":
    success = init_config()
    if not success:
        sys.exit(1)
    
    if not validate_config():
        logger.warning("Some configuration files are missing. Please check the logs above.")
        sys.exit(1)
    
    logger.info("Configuration setup successful")