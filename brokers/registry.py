"""
Broker Registry
Maintains registry of available broker implementations
"""
from typing import Dict, Type, Optional
from core.broker_interface import BrokerInterface
from utils.logger import logger


class BrokerRegistry:
    """Registry for broker implementations."""
    
    _brokers: Dict[str, Type[BrokerInterface]] = {}
    
    @classmethod
    def register(cls, name: str, broker_class: Type[BrokerInterface]):
        """
        Register a broker implementation.
        
        Args:
            name: Broker identifier (e.g., 'dummy', 'shoonya')
            broker_class: Broker class
        """
        cls._brokers[name] = broker_class
        logger.info(f"Registered broker: {name}")
    
    @classmethod
    def get_broker(cls, name: str) -> Optional[Type[BrokerInterface]]:
        """
        Get a broker class by name.
        
        Args:
            name: Broker identifier
            
        Returns:
            Broker class or None if not found
        """
        return cls._brokers.get(name)
    
    @classmethod
    def list_brokers(cls) -> list:
        """
        List all registered brokers.
        
        Returns:
            List of broker names
        """
        return list(cls._brokers.keys())
    
    @classmethod
    def unregister(cls, name: str):
        """
        Unregister a broker.
        
        Args:
            name: Broker identifier
        """
        if name in cls._brokers:
            del cls._brokers[name]
            logger.info(f"Unregistered broker: {name}")
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a broker is registered."""
        return name in cls._brokers


# Auto-register function to be called after imports
def register_builtin_brokers():
    """Register all built-in brokers."""
    # Import here to avoid circular dependencies
    try:
        from brokers.dummy.dummy_broker import DummyBroker
        BrokerRegistry.register('dummy', DummyBroker)
    except ImportError as e:
        logger.warning(f"Could not register DummyBroker: {e}")
    
    # Conditionally register Shoonya if SDK available
    try:
        from brokers.shoonya.shoonya_broker import ShoonyaBroker
        BrokerRegistry.register('shoonya', ShoonyaBroker)
    except ImportError:
        logger.debug("Shoonya broker not available")
