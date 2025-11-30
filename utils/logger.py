"""Logging utility for the trading application."""
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:
    """Centralized logging system."""
    
    _instance: Optional[logging.Logger] = None
    
    @classmethod
    def get_logger(cls, name: str = "TradingApp") -> logging.Logger:
        """Get or create logger instance."""
        if cls._instance is None:
            cls._instance = logging.getLogger(name)
            cls._instance.setLevel(logging.INFO)
            
            # Create logs directory if it doesn't exist
            os.makedirs("logs", exist_ok=True)
            
            # File handler with rotation
            file_handler = RotatingFileHandler(
                "logs/trading_app.log",
                maxBytes=10485760,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers
            cls._instance.addHandler(file_handler)
            cls._instance.addHandler(console_handler)
        
        return cls._instance


# Global logger instance
logger = Logger.get_logger()
