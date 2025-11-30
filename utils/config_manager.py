"""Configuration Manager for loading and accessing app settings."""
import yaml
import os
from typing import Any, Dict


class ConfigManager:
    """Manages application configuration from YAML file."""
    
    _instance = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_config(self, config_path: str = "config.yaml"):
        """Load configuration from YAML file."""
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        Example: config.get('broker.server')
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation."""
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, config_path: str = "config.yaml"):
        """Save current configuration to file."""
        with open(config_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)
    
    @property
    def all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._config


# Global config instance
config = ConfigManager()
