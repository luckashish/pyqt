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
    
    def __init__(self):
        super().__init__()
        
        # EA Info
        self.name = "Fixed Price Trigger EA"
        self.version = "1.0"
        self.author = "System"
        self.description = "Simple price threshold trigger EA"
        
        # Default trigger price (will be set from config)
        self.trigger_price = 100.0
        
        # Track current position state
        self.current_position = None  # None, 'BUY', or 'SELL'
    
    def on_init(self):
        """Called when EA is first initialized."""
        # Get trigger price from config parameters
        if self.config and self.config.parameters:
            self.trigger_price = self.config.parameters.get('trigger_price', 100.0)
        
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
        if not self.is_running:
            return
        
        # Get current price
        current_price = symbol.last
        
        if current_price is None or current_price == 0:
            return
        
        # Check for signal based on trigger price
        
        # Price above trigger -> BUY signal
        if current_price > self.trigger_price:
            if self.current_position != 'BUY':
                logger.info(f"{self.name}: Price {current_price} > {self.trigger_price} -> BUY SIGNAL")
                
                # Calculate SL/TP
                sl_distance = self.config.stop_loss_pips
                tp_distance = self.config.take_profit_pips or (sl_distance * 2)
                
                stop_loss = current_price - sl_distance
                take_profit = current_price + tp_distance
                
                # Generate signal
                self.generate_signal(
                    signal_type='BUY',
                    price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=f"Price {current_price} crossed above trigger {self.trigger_price}",
                    confidence=1.0
                )
                
                self.current_position = 'BUY'
        
        # Price below trigger -> SELL signal
        elif current_price < self.trigger_price:
            if self.current_position != 'SELL':
                logger.info(f"{self.name}: Price {current_price} < {self.trigger_price} -> SELL SIGNAL")
                
                # Calculate SL/TP
                sl_distance = self.config.stop_loss_pips
                tp_distance = self.config.take_profit_pips or (sl_distance * 2)
                
                stop_loss = current_price + sl_distance
                take_profit = current_price - tp_distance
                
                # Generate signal
                self.generate_signal(
                    signal_type='SELL',
                    price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reason=f"Price {current_price} crossed below trigger {self.trigger_price}",
                    confidence=1.0
                )
                
                self.current_position = 'SELL'
    
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
    # Create EA instance (no args)
    ea = FixedPriceTriggerEA()
    
    # Create config
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
    
    # Initialize EA with config
    ea.initialize(config)
    
    return ea

