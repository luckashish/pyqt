"""
Base Broker Implementation
Provides common functionality for all brokers
"""
from abc import ABC
from core.broker_interface import BrokerInterface
from brokers.base.exceptions import ConnectionError
from utils.logger import logger


class BrokerBase(BrokerInterface, ABC):
    """Base class for broker implementations with common functionality."""
    
    def __init__(self, name: str):
        """
        Initialize base broker.
        
        Args:
            name: Broker name (e.g., 'Dummy', 'Shoonya')
        """
        self.name = name
        self._connected = False
        
        logger.debug(f"Initializing {name} broker")
    
    def is_connected(self) -> bool:
        """
        Check connection status.
        
        Returns:
            True if connected to broker
        """
        return self._connected
    
    def _validate_connection(self):
        """
        Ensure broker is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self._connected:
            raise ConnectionError(f"{self.name} broker not connected. Please connect first.")
    
    def _log_operation(self, operation: str, **kwargs):
        """
        Log broker operations for debugging.
        
        Args:
            operation: Operation name
            **kwargs: Operation parameters
        """
        logger.debug(f"[{self.name}] {operation}: {kwargs}")
    
    def _log_error(self, operation: str, error: Exception):
        """
        Log broker errors.
        
        Args:
            operation: Operation that failed
            error: Exception that occurred
        """
        logger.error(f"[{self.name}] {operation} failed: {error}")
