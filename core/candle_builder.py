"""
Tick to Candle Converter.
Builds OHLC candles from incoming ticks and emits candle close events.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
from PyQt5.QtCore import QObject

from data.models import Symbol, OHLCData
from core.event_bus import event_bus
from utils.logger import logger


class CandleBuilder(QObject):
    """
    Builds candles from ticks and emits candle close events.
    Supports multiple timeframes simultaneously.
    """
    
    def __init__(self):
        super().__init__()
        
        # Current candles being built: symbol -> timeframe -> candle
        self.current_candles: Dict[str, Dict[str, OHLCData]] = {}
        
        # Track last candle time to detect closes
        self.last_candle_time: Dict[str, Dict[str, datetime]] = {}
        
        # Timeframe settings (in minutes)
        self.timeframes = {
            'M1': 1,
            'M5': 5,
            'M15': 15,
            'M30': 30,
            'H1': 60,
            'H4': 240,
            'D1': 1440
        }
        
    def process_tick(self, symbol: Symbol):
        """
        Process incoming tick and build candles.
        
        Args:
            symbol: Symbol with latest tick data
        """
        if not symbol.last or symbol.last == 0:
            return
            
        symbol_name = symbol.name
        current_time = datetime.now()
        
        # Initialize symbol if needed
        if symbol_name not in self.current_candles:
            self.current_candles[symbol_name] = {}
            self.last_candle_time[symbol_name] = {}
        
        # Update candles for each timeframe
        for tf, minutes in self.timeframes.items():
            candle_time = self._get_candle_start_time(current_time, minutes)
            
            # Check if we need to close the previous candle
            if symbol_name in self.last_candle_time and tf in self.last_candle_time[symbol_name]:
                last_time = self.last_candle_time[symbol_name][tf]
                
                if candle_time > last_time:
                    # New candle started - close the previous one
                    if tf in self.current_candles[symbol_name]:
                        closed_candle = self.current_candles[symbol_name][tf]
                        self._emit_candle_close(symbol_name, closed_candle)
                        logger.debug(f"Candle closed: {symbol_name} {tf} at {closed_candle.timestamp}")
            
            # Update or create current candle
            if tf not in self.current_candles[symbol_name] or candle_time > self.last_candle_time[symbol_name].get(tf, datetime.min):
                # Start new candle
                self.current_candles[symbol_name][tf] = OHLCData(
                    timestamp=candle_time,
                    open=symbol.last,
                    high=symbol.last,
                    low=symbol.last,
                    close=symbol.last,
                    volume=0
                )
                self.last_candle_time[symbol_name][tf] = candle_time
            else:
                # Update existing candle
                candle = self.current_candles[symbol_name][tf]
                candle.high = max(candle.high, symbol.last)
                candle.low = min(candle.low, symbol.last)
                candle.close = symbol.last
    
    def _get_candle_start_time(self, current_time: datetime, minutes: int) -> datetime:
        """
        Get the start time of the candle for given timeframe.
        
        Args:
            current_time: Current datetime
            minutes: Timeframe in minutes
            
        Returns:
            Start time of current candle
        """
        # Round down to candle boundary
        if minutes < 60:
            # Minute-based
            candle_minute = (current_time.minute // minutes) * minutes
            return current_time.replace(minute=candle_minute, second=0, microsecond=0)
        elif minutes < 1440:
            # Hour-based
            hours = minutes // 60
            candle_hour = (current_time.hour // hours) * hours
            return current_time.replace(hour=candle_hour, minute=0, second=0, microsecond=0)
        else:
            # Daily
            return current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _emit_candle_close(self, symbol: str, candle: OHLCData):
        """
        Emit candle close event via event bus.
        
        Args:
            symbol: Symbol name
            candle: Closed candle
        """
        event_bus.candle_updated.emit(symbol, candle)
        logger.info(f"Candle close: {symbol} O:{candle.open:.2f} H:{candle.high:.2f} L:{candle.low:.2f} C:{candle.close:.2f} @ {candle.timestamp}")
    
    def get_current_candle(self, symbol: str, timeframe: str = 'M1') -> Optional[OHLCData]:
        """
        Get current candle being built.
        
        Args:
            symbol: Symbol name
            timeframe: Timeframe (M1, M5, etc.)
            
        Returns:
            Current candle or None
        """
        if symbol in self.current_candles and timeframe in self.current_candles[symbol]:
            return self.current_candles[symbol][timeframe]
        return None


# Global candle builder instance
candle_builder = CandleBuilder()
