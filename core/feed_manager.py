"""Feed Manager - normalizes and distributes market data."""
from PyQt5.QtCore import QObject
from typing import Dict, List
from data.models import Symbol, OHLCData
from core.event_bus import event_bus
from core.candle_builder import candle_builder
from utils.symbol_normalizer import symbol_normalizer
from utils.logger import logger
from datetime import datetime, timedelta


class FeedManager(QObject):
    """Manages market data feeds and distribution."""
    
    def __init__(self):
        super().__init__()
        self._symbols: Dict[str, Symbol] = {}
        self._candles: Dict[str, List[OHLCData]] = {}  # symbol -> candles
        self._subscribers: Dict[str, int] = {}  # symbol -> subscriber count
        
        # Listen to candle_updated events to auto-store candles
        event_bus.candle_updated.connect(self._on_candle_updated)
    
    def _on_candle_updated(self, symbol: str, candle: OHLCData):
        """
        Auto-store candles when they close (from candle builder or external).
        
        Args:
            symbol: Symbol name
            candle: Closed candle
        """
        if symbol not in self._candles:
            self._candles[symbol] = []
        
        candles = self._candles[symbol]
        
        # Check if this is a new candle or update
        if candles and candles[-1].timestamp == candle.timestamp:
            candles[-1] = candle  # Update existing
        else:
            candles.append(candle)  # New candle
            
            # Keep only last 1000 candles
            if len(candles) > 1000:
                candles.pop(0)
    
    def update_tick(self, symbol_data: Symbol):
        """
        Process incoming tick data and emit events.
        
        Args:
            symbol_data: Updated symbol information
        """
        self._symbols[symbol_data.name] = symbol_data
        
        # Debug: Log symbol formats
        if symbol_data.display_name and symbol_data.display_name != symbol_data.name:
            logger.debug(f"Symbol formats: {symbol_data.name} <-> {symbol_data.display_name}")
        
        # Auto-register symbol format mapping
        symbol_normalizer.auto_register_from_symbol(symbol_data)
        
        event_bus.tick_received.emit(symbol_data)
        
        # Build candles from ticks (emits candle_updated on close)
        candle_builder.process_tick(symbol_data)
    
    def update_candle(self, symbol: str, candle: OHLCData):
        """
        Process new/updated candle data.
        
        Args:
            symbol: Symbol name
            candle: OHLC candle data
        """
        if symbol not in self._candles:
            self._candles[symbol] = []
        
        # Update or append candle
        candles = self._candles[symbol]
        if candles and candles[-1].timestamp == candle.timestamp:
            candles[-1] = candle  # Update existing candle
        else:
            candles.append(candle)  # New candle
            
            # Keep only last 1000 candles
            if len(candles) > 1000:
                candles.pop(0)
        
        event_bus.candle_updated.emit(symbol, candle)
    
    def get_symbol(self, name: str) -> Symbol:
        """Get latest symbol data."""
        return self._symbols.get(name)
    
    def get_candles(self, symbol: str, count: int = 200) -> List[OHLCData]:
        """
        Get recent candles for a symbol.
        
        Args:
            symbol: Symbol name
            count: Number of candles to return
            
        Returns:
            List of recent candles
        """
        candles = self._candles.get(symbol, [])
        return candles[-count:] if len(candles) > count else candles
    
    def subscribe(self, symbol: str):
        """Subscribe to a symbol's data feed."""
        self._subscribers[symbol] = self._subscribers.get(symbol, 0) + 1
    
    def unsubscribe(self, symbol: str):
        """Unsubscribe from a symbol's data feed."""
        if symbol in self._subscribers:
            self._subscribers[symbol] -= 1
            if self._subscribers[symbol] <= 0:
                del self._subscribers[symbol]
    
    def get_subscribed_symbols(self) -> List[str]:
        """Get list of currently subscribed symbols."""
        return list(self._subscribers.keys())


# Global feed manager instance
feed_manager = FeedManager()
