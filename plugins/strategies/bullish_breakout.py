"""
Bullish Breakout Expert Advisor.
Buys on specific candlestick pattern:
- Current candle low < previous candle low
- Current candle high > previous candle high
- Current candle close > previous candle close
Entry at previous-to-previous candle high (candle[2].high)
Stop loss at previous candle low with buffer
"""
import pandas as pd
import numpy as np
from datetime import datetime

from core.ea_base import ExpertAdvisor
from core.feed_manager import feed_manager
from core.execution_service import execution_service
from core.risk_manager import risk_manager
from data.models import Symbol, OHLCData, Order, EAConfig, OrderType
from utils.logger import logger


class BullishBreakoutEA(ExpertAdvisor):
    """
    Bullish Breakout Expert Advisor.
    
    Strategy:
    - Detects when current candle makes lower low but higher high and higher close
    - This indicates strength after a pullback
    - Enters at previous-to-previous candle high
    - Stop loss at previous candle low with buffer
    """
    
    def __init__(self):
        super().__init__()
        
        # EA Info
        self.name = "Bullish Breakout EA"
        self.version = "1.0"
        self.author = "System"
        self.description = "Price action pattern EA - Bullish breakout after pullback"
        
        # State tracking
        self.last_signal_time = None
        
        # Candle tracking
        self.candles_buffer = []
        self.max_candles = 50
        
    def on_init(self):
        """Initialize EA."""
        logger.info(f"{self.name}: Initializing...")
        
        # Log configuration
        params = self.config.parameters
        logger.info(f"  Symbol: {self.config.symbol}")
        logger.info(f"  Timeframe: {self.config.timeframe}")
        logger.info(f"  SL Buffer: {params.get('sl_buffer_pips', 5)} pips")
        logger.info(f"  Lot Size: {self.config.lot_size}")
        
    def on_start(self):
        """Called when EA starts."""
        logger.info(f"{self.name}: Started")
        
        # Reset state
        self.last_signal_time = None
        self.candles_buffer = []
        
        # Load initial candles
        self._load_initial_candles()
        
    def on_stop(self):
        """Called when EA stops."""
        logger.info(f"{self.name}: Stopped")
        
    def handle_tick(self, tick: Symbol):
        """
        Handle price tick.
        For this strategy, we mainly work with closed candles.
        """
        # Update trailing stops if enabled
        if self.config.use_trailing_stop and self.state.open_positions > 0:
            from core.position_tracker import position_tracker
            
            updates = position_tracker.update_trailing_stops(self.config.symbol, tick.last)
            
            # Apply updates via execution service
            for ticket, new_sl in updates:
                execution_service.modify_position(ticket, sl=new_sl)
                
    def handle_bar(self, bar: OHLCData):
        """
        Handle new candle close.
        This is where the main strategy logic runs.
        """
        # Add to buffer
        self._add_candle(bar)
        
        # Need at least 3 candles for the pattern
        if len(self.candles_buffer) < 3:
            logger.info(f"{self.name}: Waiting for more candles ({len(self.candles_buffer)}/3)")
            return
            
        # Check for pattern
        self._check_pattern(bar.close)
        
    def handle_order_update(self, order: Order):
        """Handle order updates."""
        # Base class already handles position tracking
        pass
        
    def _load_initial_candles(self):
        """Load initial candles from feed manager or broker."""
        try:
            # Try feed manager first
            candles = feed_manager.get_candles(self.config.symbol, count=10)
            
            if candles:
                self.candles_buffer = candles[-self.max_candles:]
                logger.info(f"{self.name}: Loaded {len(self.candles_buffer)} candles from feed manager")
            else:
                # No candles in feed manager - will need to wait for live candles
                logger.warning(
                    f"{self.name}: No historical candles available. "
                    f"EA will start detecting patterns after {3} candles close."
                )
                self.candles_buffer = []
                
        except Exception as e:
            logger.error(f"{self.name}: Error loading candles: {e}")
            self.candles_buffer = []
            
    def _add_candle(self, bar: OHLCData):
        """Add candle to buffer."""
        self.candles_buffer.append(bar)
        
        # Keep buffer size limited
        if len(self.candles_buffer) > self.max_candles:
            self.candles_buffer.pop(0)
            
    def _check_pattern(self, current_price: float):
        """
        Check for bullish breakout pattern.
        
        Pattern:
        - candle[0] (current): low < candle[1].low, high > candle[1].high, close > candle[1].close
        - Entry: candle[2].high
        - SL: candle[1].low - buffer
        """
        if len(self.candles_buffer) < 3:
            return
            
        # Get last 3 candles
        candle_0 = self.candles_buffer[-1]  # Current (just closed)
        candle_1 = self.candles_buffer[-2]  # Previous
        candle_2 = self.candles_buffer[-3]  # Previous to previous
        
        # Check pattern conditions
        lower_low = candle_0.low < candle_1.low
        higher_high = candle_0.high > candle_1.high
        higher_close = candle_0.close > candle_1.close
        
        if lower_low and higher_high and higher_close:
            # Pattern detected!
            logger.info(
                f"{self.name}: PATTERN DETECTED! "
                f"Candle[0]: L={candle_0.low:.2f} H={candle_0.high:.2f} C={candle_0.close:.2f}, "
                f"Candle[1]: L={candle_1.low:.2f} H={candle_1.high:.2f} C={candle_1.close:.2f}"
            )
            
            # Avoid duplicate signals (one per candle)
            if self.last_signal_time and self.last_signal_time >= candle_0.timestamp:
                logger.debug(f"{self.name}: Signal already generated for this candle")
                return
            
            # Generate buy signal
            self._generate_buy_signal(candle_0, candle_1, candle_2, current_price)
            self.last_signal_time = candle_0.timestamp
            
    def _generate_buy_signal(
        self,
        current_candle: OHLCData,
        prev_candle: OHLCData,
        prev_prev_candle: OHLCData,
        current_price: float
    ):
        """
        Generate buy signal with entry and stop loss.
        
        Args:
            current_candle: Current closed candle
            prev_candle: Previous candle
            prev_prev_candle: Previous to previous candle
            current_price: Current market price
        """
        # Apply filters
        if not self._check_filters(current_price, is_buy=True):
            return
            
        # Check if we can open position
        can_open, reason = risk_manager.can_open_position(
            self.name,
            self.config.risk_percent,
            self.config.lot_size
        )
        
        if not can_open:
            logger.warning(f"{self.name}: Cannot open BUY - {reason}")
            return
            
        # Calculate entry and stop loss
        entry_price = prev_prev_candle.high  # Enter at candle[2] high
        
        # Stop loss: previous candle low - buffer
        sl_buffer_pips = self.config.parameters.get('sl_buffer_pips', 5)
        pip_value = 0.0001  # For 4-digit quote
        
        sl_price = prev_candle.low - (sl_buffer_pips * pip_value)
        
        # Calculate take profit based on risk:reward
        risk_pips = abs(entry_price - sl_price) * 10000
        tp_pips = risk_pips * 2  # 1:2 risk:reward
        tp_price = entry_price + (tp_pips * pip_value)
        
        # Override with config TP if specified
        if self.config.take_profit_pips > 0:
            tp_price = risk_manager.calculate_take_profit(entry_price, True, self.config.take_profit_pips)
        
        # Calculate position size
        lot_size = risk_manager.calculate_position_size(
            self.config,
            entry_price,
            sl_price,
            None
        )
        
        logger.info(
            f"{self.name}: BUY SIGNAL - "
            f"Entry: {entry_price:.2f}, SL: {sl_price:.2f}, TP: {tp_price:.2f}, "
            f"Risk: {risk_pips:.1f} pips, Lot: {lot_size}"
        )
        
        # Generate signal
        self.generate_signal(
            signal_type="BUY",
            price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            reason=(
                f"Bullish Breakout Pattern: "
                f"Lower Low ({current_candle.low:.2f} < {prev_candle.low:.2f}), "
                f"Higher High ({current_candle.high:.2f} > {prev_candle.high:.2f}), "
                f"Higher Close ({current_candle.close:.2f} > {prev_candle.close:.2f}). "
                f"Entry at candle[2] high: {entry_price:.2f}"
            ),
            confidence=0.75
        )
        
        # Execute via execution service (if connected)
        if execution_service.broker:
            signal = self.state.last_signal
            signal.volume = lot_size
            
            order = execution_service.execute_signal(signal)
            
            if order and self.config.use_trailing_stop:
                # Enable trailing stop
                from core.position_tracker import position_tracker
                position_tracker.enable_trailing_stop(
                    order.ticket,
                    self.config.trailing_stop_pips,
                    current_price
                )
                
    def _check_filters(self, price: float, is_buy: bool) -> bool:
        """
        Apply trade filters.
        
        Args:
            price: Current price
            is_buy: True if buy signal
            
        Returns:
            True if filters pass
        """
        # Time filter (already checked in base class _can_trade)
        
        # Spread filter
        if self.last_tick:
            spread_pips = (self.last_tick.ask - self.last_tick.bid) * 10000
            
            if spread_pips > self.config.max_spread_pips:
                logger.warning(f"{self.name}: Spread too high: {spread_pips:.1f} pips")
                return False
                
        # Max positions filter (already checked in base class _can_trade)
        
        return True


# Factory function to create and configure EA
def create_bullish_breakout_ea(
    symbol: str = "NSE|26000",
    timeframe: str = "M5",
    sl_buffer_pips: float = 5.0,
    lot_size: float = 0.1,
    stop_loss_pips: float = 0.0,  # Calculated from pattern
    take_profit_pips: float = 0.0,  # Calculated as 2x risk
    use_trailing_stop: bool = False,
    trailing_stop_pips: float = 30.0
) -> BullishBreakoutEA:
    """
    Create and configure Bullish Breakout EA.
    
    Args:
        symbol: Trading symbol
        timeframe: Chart timeframe
        sl_buffer_pips: Buffer to add to SL (below prev candle low)
        lot_size: Lot size
        stop_loss_pips: Override SL calculation (0 = use pattern)
        take_profit_pips: Override TP calculation (0 = use 2x risk)
        use_trailing_stop: Enable trailing stop
        trailing_stop_pips: Trailing stop distance
        
    Returns:
        Configured EA instance
    """
    ea = BullishBreakoutEA()
    
    config = EAConfig(
        name=ea.name,
        symbol=symbol,
        timeframe=timeframe,
        parameters={
            'sl_buffer_pips': sl_buffer_pips
        },
        lot_size=lot_size,
        stop_loss_pips=stop_loss_pips,
        take_profit_pips=take_profit_pips,
        use_trailing_stop=use_trailing_stop,
        trailing_stop_pips=trailing_stop_pips
    )
    
    ea.initialize(config)
    
    return ea
