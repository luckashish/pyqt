"""Abstract Broker Interface - defines the contract for broker connectors."""
from abc import ABC, abstractmethod
from typing import List, Optional
from data.models import Symbol, Order, OHLCData, OrderType
from datetime import datetime


class BrokerInterface(ABC):
    """Abstract base class for broker connections."""
    
    @abstractmethod
    def connect(self, server: str, username: str, password: str) -> bool:
        """
        Connect to broker server.
        
        Args:
            server: Broker server address
            username: Account username
            password: Account password
            
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from broker."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected to broker."""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get list of available trading symbols."""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Symbol]:
        """Get current symbol information (bid, ask, etc.)."""
        pass
    
    @abstractmethod
    def subscribe(self, symbol: str):
        """Subscribe to real-time price updates for a symbol."""
        pass
    
    @abstractmethod
    def unsubscribe(self, symbol: str):
        """Unsubscribe from price updates for a symbol."""
        pass
    
    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[OHLCData]:
        """
        Get historical OHLC data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, etc.)
            start_time: Start date/time
            end_time: End date/time
            
        Returns:
            List of OHLC candles
        """
        pass
    
    @abstractmethod
    def place_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = ""
    ) -> Optional[Order]:
        """
        Place a new order.
        
        Args:
            symbol: Trading symbol
            order_type: Type of order (BUY, SELL, etc.)
            volume: Lot size
            price: Entry price (None for market orders)
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment
            
        Returns:
            Order object if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def modify_order(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """
        Modify an existing order's SL/TP.
        
        Args:
            ticket: Order ticket number
            sl: New stop loss
            tp: New take profit
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def close_order(self, ticket: int) -> bool:
        """
        Close an order.
        
        Args:
            ticket: Order ticket number
            
        Returns:
            True if successful
        """
        pass
    
    @abstractmethod
    def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        pass
    
    @abstractmethod
    def get_order_history(self) -> List[Order]:
        """Get closed orders history."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> dict:
        """
        Get account information.
        
        Returns:
            Dict with balance, equity, margin, free_margin, margin_level
        """
        pass
