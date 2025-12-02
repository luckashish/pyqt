"""
Fixed Price Trigger Expert Advisor.
Simple EA that triggers trades based on a fixed price threshold.
"""
from datetime import datetime
from typing import Optional

from core.ea_base import ExpertAdvisor
from data.models import EAConfig, EASignal, Symbol, Order
from utils.logger import logger


class FixedPriceTriggerEA(ExpertAdvisor):
    """
    Fixed Price Trigger Expert Advisor.
    
    Strategy Logic:
    - If current price > trigger_price → place BUY order
    - If current price < trigger_price → place SELL order
    
    Simple threshold-based trading.
    """
    
    def __init__(self, config: EAConfig):
        super().__init__(config)
        
        # Get trigger price from parameters
        self.trigger_price = config.parameters.get('trigger_price', 100.0)
        
        # Track current position state
        self.current_position = None  # None, 'BUY', or 'SELL'
        
        logger.info(f"{self.name}: Initialized with trigger price {self.trigger_price}")
    
    def on_init(self):
        """Called when EA is first initialized."""
        logger.info(f"{self.name}: Initializing...")
        logger.info(f"  Symbol: {self.config.symbol}")
        logger.info(f"  Trigger Price: {self.trigger_price}")
        logger.info(f"  Lot Size: {self.config.lot_size}")
    
    def on_start(self):
        """Called when EA is started."""
        self.current_position = None
        logger.info(f"{self.name}: Started on {self.config.symbol}")
        logger.info(f"  Watching for price crosses at {self.trigger_price}")
    
    def on_stop(self):
        """Called when EA is stopped."""
        logger.info(f"{self.name}: Stopped")
    
    def handle_tick(self, symbol: Symbol):
        """
        Process incoming tick data.
        
        Args:
            symbol: Current tick data
        """
        if not self.is_running():
            return
        
        # Get current price
        current_price = symbol.last
        
        if current_price is None or current_price == 0:
            return
        
        # Check for signal based on trigger price
        signal = None
        
        # Price above trigger → BUY signal
        if current_price > self.trigger_price:
            if self.current_position != 'BUY':
                logger.info(f"{self.name}: Price {current_price} > {self.trigger_price} → BUY SIGNAL")
                signal = self._create_buy_signal(symbol, current_price)
                self.current_position = 'BUY'
        
        # Price below trigger → SELL signal
        elif current_price < self.trigger_price:
            if self.current_position != 'SELL':
                logger.info(f"{self.name}: Price {current_price} < {self.trigger_price} → SELL SIGNAL")
                signal = self._create_sell_signal(symbol, current_price)
                self.current_position = 'SELL'
        
        # Emit signal if generated
        if signal:
            self.emit_signal(signal)
    
    def handle_bar(self, bar):
        """
        Process bar close events.
        
        Not used by this EA - uses tick data for instant triggers.
        """
        pass
    
    def handle_order_update(self, order: Order):
        """
        Handle order status updates.
        
        Args:
            order: Updated order
        """
        logger.info(f"{self.name}: Order update - {order.ticket} {order.status}")
    
    def _create_buy_signal(self, symbol: Symbol, price: float) -> EASignal:
        """
        Create a BUY signal.
        
        Args:
            symbol: Current symbol data
            price: Entry price
            
        Returns:
            EASignal for BUY
        """
        # Calculate SL/TP
        sl_distance = self.config.stop_loss_pips
        tp_distance = self.config.take_profit_pips or (sl_distance * 2)  # Default 1:2 R:R
        
        stop_loss = price - sl_distance
        take_profit = price + tp_distance
        
        return EASignal(
            ea_name=self.name,
            symbol=self.config.symbol,
            signal_type='BUY',
            timestamp=datetime.now(),
            price=price,
            volume=self.config.lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=f"Price {price} crossed above trigger {self.trigger_price}",
            confidence=1.0
        )
    
    def _create_sell_signal(self, symbol: Symbol, price: float) -> EASignal:
        """
        Create a SELL signal.
        
        Args:
            symbol: Current symbol data
            price: Entry price
            
        Returns:
            EASignal for SELL
        """
        # Calculate SL/TP
        sl_distance = self.config.stop_loss_pips
        tp_distance = self.config.take_profit_pips or (sl_distance * 2)  # Default 1:2 R:R
        
        stop_loss = price + sl_distance
        take_profit = price - tp_distance
        
        return EASignal(
            ea_name=self.name,
            symbol=self.config.symbol,
            signal_type='SELL',
            timestamp=datetime.now(),
            price=price,
            volume=self.config.lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=f"Price {price} crossed below trigger {self.trigger_price}",
            confidence=1.0
        )


def create_fixed_price_trigger_ea(
    symbol: str = "NSE|26000",
    trigger_price: float = 100.0,
    lot_size: float = 1.0,
    stop_loss_pips: float = 10.0,
    take_profit_pips: float = 20.0
) -> FixedPriceTriggerEA:
    """
    Factory function to create a Fixed Price Trigger EA.
    
    Args:
        symbol: Trading symbol
        trigger_price: Price threshold for triggering trades
        lot_size: Position size
        stop_loss_pips: Stop loss distance in pips
        take_profit_pips: Take profit distance in pips (0 for 2x SL)
        
    Returns:
        Configured FixedPriceTriggerEA instance
    """
    config = EAConfig(
        name="Fixed Price Trigger EA",
        symbol=symbol,
        timeframe="TICK",  # Tick-based EA
        parameters={
            'trigger_price': trigger_price
        },
        lot_size=lot_size,
        risk_percent=2.0,
        stop_loss_pips=stop_loss_pips,
        take_profit_pips=take_profit_pips,
        use_trailing_stop=False,
        trailing_stop_pips=0,
        enable_time_filter=False,
        trading_start_hour=0,
        trading_end_hour=24,
        max_spread_pips=10.0
    )
    
    return FixedPriceTriggerEA(config)
