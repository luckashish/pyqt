"""
Enhanced MA Crossover Expert Advisor.
Complete implementation with risk management, filters, and trailing stops.
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


class MACrossoverEA(ExpertAdvisor):
    """
    Moving Average Crossover Expert Advisor.
    
    Strategy:
    - BUY when Fast MA crosses above Slow MA (Golden Cross)
    - SELL when Fast MA crosses below Slow MA (Death Cross)
    - Supports SMA and EMA
    - Includes risk management and trade filters
    """
    
    def __init__(self):
        super().__init__()
        
        # EA Info
        self.name = "MA Crossover EA"
        self.version = "2.0"
        self.author = "System"
        self.description = "Enhanced MA Crossover with risk management and filters"
        
        # State tracking
        self.last_cross = None  # 'golden' or 'death'
        self.last_fast_ma = None
        self.last_slow_ma = None
        
        # Candle tracking
        self.candles_buffer = []
        self.max_candles = 100
        
    def on_init(self):
        """Initialize EA."""
        logger.info(f"{self.name}: Initializing...")
        
        # Log configuration
        params = self.config.parameters
        logger.info(f"  Symbol: {self.config.symbol}")
        logger.info(f"  Timeframe: {self.config.timeframe}")
        logger.info(f"  Fast MA: {params.get('fast_period', 10)}")
        logger.info(f"  Slow MA: {params.get('slow_period', 20)}")
        logger.info(f"  MA Type: {params.get('ma_type', 'SMA')}")
        logger.info(f"  Lot Size: {self.config.lot_size}")
        logger.info(f"  Stop Loss: {self.config.stop_loss_pips} pips")
        logger.info(f"  Take Profit: {self.config.take_profit_pips} pips")
        
        if self.config.use_trailing_stop:
            logger.info(f"  Trailing Stop: {self.config.trailing_stop_pips} pips")
            
    def on_start(self):
        """Called when EA starts."""
        logger.info(f"{self.name}: Started")
        
        # Reset state
        self.last_cross = None
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
        
        # Need enough candles for calculation
        slow_period = self.config.parameters.get('slow_period', 20)
        
        if len(self.candles_buffer) < slow_period + 1:
            logger.debug(f"{self.name}: Waiting for more candles ({len(self.candles_buffer)}/{slow_period + 1})")
            return
            
        # Calculate MAs
        fast_ma, slow_ma = self._calculate_mas()
        
        if fast_ma is None or slow_ma is None:
            return
            
        # Check for crossover
        self._check_crossover(fast_ma, slow_ma, bar.close)
        
        # Update state
        self.last_fast_ma = fast_ma
        self.last_slow_ma = slow_ma
        
    def handle_order_update(self, order: Order):
        """Handle order updates."""
        # Base class already handles position tracking
        pass
        
    def _load_initial_candles(self):
        """Load initial candles from feed manager."""
        try:
            slow_period = self.config.parameters.get('slow_period', 20)
            candles = feed_manager.get_candles(self.config.symbol, count=slow_period + 10)
            
            if candles:
                self.candles_buffer = candles[-self.max_candles:]
                logger.info(f"{self.name}: Loaded {len(self.candles_buffer)} candles")
            else:
                logger.warning(f"{self.name}: No candles available")
                
        except Exception as e:
            logger.error(f"{self.name}: Error loading candles: {e}")
            
    def _add_candle(self, bar: OHLCData):
        """Add candle to buffer."""
        self.candles_buffer.append(bar)
        
        # Keep buffer size limited
        if len(self.candles_buffer) > self.max_candles:
            self.candles_buffer.pop(0)
            
    def _calculate_mas(self) -> tuple:
        """
        Calculate moving averages.
        
        Returns:
            (fast_ma, slow_ma) tuple of current values
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': c.timestamp,
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume
            } for c in self.candles_buffer])
            
            # Get parameters
            fast_period = self.config.parameters.get('fast_period', 10)
            slow_period = self.config.parameters.get('slow_period', 20)
            ma_type = self.config.parameters.get('ma_type', 'SMA')
            
            # Calculate MAs
            if ma_type == 'SMA':
                fast_ma = df['close'].rolling(window=fast_period).mean()
                slow_ma = df['close'].rolling(window=slow_period).mean()
            else:  # EMA
                fast_ma = df['close'].ewm(span=fast_period, adjust=False).mean()
                slow_ma = df['close'].ewm(span=slow_period, adjust=False).mean()
                
            # Return last values
            return fast_ma.iloc[-1], slow_ma.iloc[-1]
            
        except Exception as e:
            logger.error(f"{self.name}: Error calculating MAs: {e}")
            return None, None
            
    def _check_crossover(self, current_fast: float, current_slow: float, current_price: float):
        """
        Check for MA crossover and generate signals.
        
        Args:
            current_fast: Current fast MA value
            current_slow: Current slow MA value
            current_price: Current close price
        """
        # Need previous values
        if self.last_fast_ma is None or self.last_slow_ma is None:
            return
            
        # Golden Cross: Fast crosses above Slow
        if self.last_fast_ma <= self.last_slow_ma and current_fast > current_slow:
            if self.last_cross != 'golden':
                self._on_golden_cross(current_price)
                self.last_cross = 'golden'
                
        # Death Cross: Fast crosses below Slow
        elif self.last_fast_ma >= self.last_slow_ma and current_fast < current_slow:
            if self.last_cross != 'death':
                self._on_death_cross(current_price)
                self.last_cross = 'death'
                
    def _on_golden_cross(self, price: float):
        """
        Handle Golden Cross signal.
        
        Args:
            price: Current price
        """
        logger.info(f"{self.name}: GOLDEN CROSS detected at {price}")
        
        # Apply filters
        if not self._check_filters(price, is_buy=True):
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
            
        # Close any existing SELL positions first
        self._close_opposite_positions(is_buy=True)
        
        # Calculate SL and TP
        sl = risk_manager.calculate_stop_loss(price, True, self.config.stop_loss_pips)
        tp = risk_manager.calculate_take_profit(price, True, self.config.take_profit_pips)
        
        # Calculate position size
        lot_size = risk_manager.calculate_position_size(
            self.config,
            price,
            sl,
            None
        )
        
        # Generate BUY signal
        self.generate_signal(
            signal_type="BUY",
            price=price,
            stop_loss=sl,
            take_profit=tp,
            reason=f"Golden Cross (Fast MA: {self.last_fast_ma:.2f}, Slow MA: {self.last_slow_ma:.2f})",
            confidence=0.8
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
                    price
                )
                
    def _on_death_cross(self, price: float):
        """
        Handle Death Cross signal.
        
        Args:
            price: Current price
        """
        logger.info(f"{self.name}: DEATH CROSS detected at {price}")
        
        # Apply filters
        if not self._check_filters(price, is_buy=False):
            return
            
        # Check if we can open position
        can_open, reason = risk_manager.can_open_position(
            self.name,
            self.config.risk_percent,
            self.config.lot_size
        )
        
        if not can_open:
            logger.warning(f"{self.name}: Cannot open SELL - {reason}")
            return
            
        # Close any existing BUY positions first
        self._close_opposite_positions(is_buy=False)
        
        # Calculate SL and TP
        sl = risk_manager.calculate_stop_loss(price, False, self.config.stop_loss_pips)
        tp = risk_manager.calculate_take_profit(price, False, self.config.take_profit_pips)
        
        # Calculate position size
        lot_size = risk_manager.calculate_position_size(
            self.config,
            price,
            sl,
            None
        )
        
        # Generate SELL signal
        self.generate_signal(
            signal_type="SELL",
            price=price,
            stop_loss=sl,
            take_profit=tp,
            reason=f"Death Cross (Fast MA: {self.last_fast_ma:.2f}, Slow MA: {self.last_slow_ma:.2f})",
            confidence=0.8
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
                    price
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
        
    def _close_opposite_positions(self, is_buy: bool):
        """
        Close positions in opposite direction.
        
        Args:
            is_buy: True if opening buy (close sells)
        """
        from core.position_tracker import position_tracker
        
        positions = position_tracker.get_positions_for_symbol(self.config.symbol)
        
        for order in positions:
            # Close opposite direction
            if is_buy and not order.is_buy:
                logger.info(f"{self.name}: Closing SELL position {order.ticket}")
                execution_service.close_position(order.ticket, self.name)
            elif not is_buy and order.is_buy:
                logger.info(f"{self.name}: Closing BUY position {order.ticket}")
                execution_service.close_position(order.ticket, self.name)


# Factory function to create and configure EA
def create_ma_crossover_ea(
    symbol: str = "NSE|26000",
    timeframe: str = "M5",
    fast_period: int = 10,
    slow_period: int = 20,
    ma_type: str = "SMA",
    lot_size: float = 0.1,
    stop_loss_pips: float = 50.0,
    take_profit_pips: float = 100.0,
    use_trailing_stop: bool = False,
    trailing_stop_pips: float = 30.0
) -> MACrossoverEA:
    """
    Create and configure MA Crossover EA.
    
    Args:
        symbol: Trading symbol
        timeframe: Chart timeframe
        fast_period: Fast MA period
        slow_period: Slow MA period
        ma_type: MA type ("SMA" or "EMA")
        lot_size: Lot size
        stop_loss_pips: Stop loss in pips
        take_profit_pips: Take profit in pips
        use_trailing_stop: Enable trailing stop
        trailing_stop_pips: Trailing stop distance
        
    Returns:
        Configured EA instance
    """
    ea = MACrossoverEA()
    
    config = EAConfig(
        name=ea.name,
        symbol=symbol,
        timeframe=timeframe,
        parameters={
            'fast_period': fast_period,
            'slow_period': slow_period,
            'ma_type': ma_type
        },
        lot_size=lot_size,
        stop_loss_pips=stop_loss_pips,
        take_profit_pips=take_profit_pips,
        use_trailing_stop=use_trailing_stop,
        trailing_stop_pips=trailing_stop_pips
    )
    
    ea.initialize(config)
    
    return ea
