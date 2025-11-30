"""
Broker Factory
Creates broker instances based on configuration
"""
from typing import Optional
from core.broker_interface import BrokerInterface
from brokers.registry import BrokerRegistry
from utils.config_manager import config
from utils.logger import logger


class BrokerFactory:
    """Factory for creating broker instances."""
    
    _instance = None
    _current_broker: Optional[BrokerInterface] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_broker(self, broker_type: str = None) -> BrokerInterface:
        """
        Create a broker instance.
        
        Args:
            broker_type: Type of broker ('dummy', 'shoonya', etc.)
                        If None, uses config setting
        
        Returns:
            Broker instance
            
        Raises:
            ValueError: If broker type is invalid
        """
        if broker_type is None:
            broker_type = config.get('broker.type', 'dummy')
        
        broker_class = BrokerRegistry.get_broker(broker_type)
        
        if broker_class is None:
            logger.error(f"Unknown broker type: {broker_type}")
            logger.info(f"Available brokers: {BrokerRegistry.list_brokers()}")
            
            # Fallback to dummy
            logger.warning("Falling back to dummy broker")
            broker_class = BrokerRegistry.get_broker('dummy')
            
            if broker_class is None:
                raise ValueError(f"No brokers available. Cannot create {broker_type}")
        
        logger.info(f"Creating broker: {broker_type}")
        self._current_broker = broker_class()
        
        return self._current_broker
    
    def get_current_broker(self) -> Optional[BrokerInterface]:
        """
        Get the currently active broker.
        
        Returns:
            Current broker instance or None
        """
        return self._current_broker
    
    def switch_broker(self, broker_type: str) -> BrokerInterface:
        """
        Switch to a different broker.
        
        Args:
            broker_type: Type of broker to switch to
            
        Returns:
            New broker instance
        """
        # Disconnect current broker if connected
        if self._current_broker:
            if self._current_broker.is_connected():
                logger.info("Disconnecting current broker before switching")
                self._current_broker.disconnect()
        
        return self.create_broker(broker_type)
    
    def list_available_brokers(self) -> list:
        """
        List all registered brokers.
        
        Returns:
            List of broker names
        """
        return BrokerRegistry.list_brokers()


# Global factory instance
broker_factory = BrokerFactory()
