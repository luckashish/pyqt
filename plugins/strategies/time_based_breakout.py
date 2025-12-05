"""
Time Based Breakout Expert Advisor.
Triggers trades based on price levels after a specific time.
"""
from datetime import datetime, time
from typing import Optional

from core.ea_base import ExpertAdvisor
from data.models import EAConfig, EASignal, Symbol, Order
from utils.logger import logger


class TimeBasedBreakoutEA(ExpertAdvisor):
    """
    Time Based Breakout Expert Advisor.
    
    Strategy Logic:
    - Wait until current time >= target_time.
    - Once time is reached, monitor price:
        - If price > buy_level (and buy_level > 0) -> BUY
        - If price < sell_level (and sell_level > 0) -> SELL
    - One-shot trigger per level.
    """
    
    def __init__(self):
        super().__init__()
        
        # EA Info
        self.name = "Time Based Breakout EA"
        self.version = "1.0"
        self.author = "System"
        self.description = "Triggers trades at price levels after specific time"
        
        # Parameters
        self.target_time_str = "10:33"
        self.enable_buy = True
        self.buy_level = 0.0
        self.enable_sell = True
        self.sell_level = 0.0
        
        # State
        self.buy_triggered = False
        self.sell_triggered = False
        self.time_reached = False
    
    def on_init(self):
        """Called when EA is first initialized."""
        # Get parameters from config
        if self.config and self.config.parameters:
            self.target_time_str = self.config.parameters.get('target_time', "10:33")
            self.enable_buy = self.config.parameters.get('enable_buy', True)
            self.buy_level = self.config.parameters.get('buy_level', 0.0)
            self.enable_sell = self.config.parameters.get('enable_sell', True)
            self.sell_level = self.config.parameters.get('sell_level', 0.0)
        
        logger.info(f"{self.name}: Initializing...")
        logger.info(f"  Symbol: {self.config.symbol}")
        logger.info(f"  Target Time: {self.target_time_str}")
        logger.info(f"  Buy: {'Enabled' if self.enable_buy else 'Disabled'} @ {self.buy_level}")
        logger.info(f"  Sell: {'Enabled' if self.enable_sell else 'Disabled'} @ {self.sell_level}")
    
    def on_start(self):
        """Called when EA is started."""
        self.buy_triggered = False
        self.sell_triggered = False
        self.time_reached = False
        logger.info(f"{self.name}: Started. Waiting for {self.target_time_str}")
    
    def on_stop(self):
        """Called when EA is stopped."""
        logger.info(f"{self.name}: Stopped")
    
    def handle_tick(self, symbol: Symbol):
        """Process incoming tick data."""
        if not self.is_running:
            return
        
        current_price = symbol.last
        if current_price is None or current_price == 0:
            return
            
        # Check Time
        now = datetime.now()
        
        # Parse target time
        try:
            # Handle "10:33 pm" or "22:33" formats
            # Simple parser for HH:MM (24h) or HH:MM am/pm
            t_str = self.target_time_str.lower().strip()
            is_pm = "pm" in t_str
            is_am = "am" in t_str
            t_str = t_str.replace("pm", "").replace("am", "").strip()
            
            parts = t_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0
                
            target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If target time is reached
            if now >= target_dt:
                if not self.time_reached:
                    logger.info(f"{self.name}: Target time {self.target_time_str} reached! Monitoring levels.")
                    self.time_reached = True
                
                # Check Levels
                
                # BUY Logic
                if self.enable_buy and self.buy_level > 0 and not self.buy_triggered:
                    if current_price > self.buy_level:
                        logger.info(f"{self.name}: Price {current_price} > {self.buy_level} -> BUY SIGNAL")
                        self._trigger_trade('BUY', current_price)
                        self.buy_triggered = True
                
                # SELL Logic
                if self.enable_sell and self.sell_level > 0 and not self.sell_triggered:
                    if current_price < self.sell_level:
                        logger.info(f"{self.name}: Price {current_price} < {self.sell_level} -> SELL SIGNAL")
                        self._trigger_trade('SELL', current_price)
                        self.sell_triggered = True
                        
        except Exception as e:
            logger.error(f"{self.name}: Error parsing time or processing: {e}")

    def _trigger_trade(self, signal_type, price):
        """Helper to generate signal."""
        sl_distance = self.config.stop_loss_pips
        tp_distance = self.config.take_profit_pips
        
        if signal_type == 'BUY':
            stop_loss = price - sl_distance
            take_profit = price + tp_distance
        else:
            stop_loss = price + sl_distance
            take_profit = price - tp_distance
            
        self.generate_signal(
            signal_type=signal_type,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=f"Time {self.target_time_str} reached & Level crossed",
            confidence=1.0
        )

    def handle_bar(self, bar):
        pass
    
    def handle_order_update(self, order: Order):
        pass


def create_time_based_ea(
    symbol: str = "NSE|26000",
    target_time: str = "10:33",
    enable_buy: bool = True,
    buy_level: float = 0.0,
    enable_sell: bool = True,
    sell_level: float = 0.0,
    lot_size: float = 1.0,
    stop_loss_pips: float = 10.0,
    take_profit_pips: float = 20.0
) -> TimeBasedBreakoutEA:
    """Factory function to create Time Based EA."""
    ea = TimeBasedBreakoutEA()
    
    config = EAConfig(
        name="Time Based Breakout EA",
        symbol=symbol,
        timeframe="TICK",
        parameters={
            'target_time': target_time,
            'enable_buy': enable_buy,
            'buy_level': buy_level,
            'enable_sell': enable_sell,
            'sell_level': sell_level
        },
        lot_size=lot_size,
        risk_percent=2.0,
        stop_loss_pips=stop_loss_pips,
        take_profit_pips=take_profit_pips,
        use_trailing_stop=True,
        trailing_stop_pips=30.0
    )
    
    ea.initialize(config)
    return ea
