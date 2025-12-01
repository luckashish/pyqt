"""
Sample MA Crossover Strategy.
Buys when Fast MA crosses above Slow MA.
Sells when Fast MA crosses below Slow MA.
"""
from core.interfaces.plugin import Strategy
from data.models import OrderType
from utils.logger import logger
from core.event_bus import event_bus

class MACrossoverStrategy(Strategy):
    """
    Simple Moving Average Crossover Strategy.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "MA Crossover EA"
        self.version = "1.0"
        self.author = "System"
        self.description = "Buys on Golden Cross, Sells on Death Cross."
        
        # Parameters
        self.fast_period = 10
        self.slow_period = 20
        self.symbol = "NSE|26000" # Nifty 50
        self.volume = 1
        
        # State
        self.last_cross = None # 'above' or 'below'
        
    def on_tick(self, tick):
        """
        Called on every tick.
        For this strategy, we mainly care about candle closes, 
        but we could implement real-time checks here.
        """
        pass
        
    def on_bar(self, bar):
        """
        Called when a candle closes.
        """
        # We need historical data to calculate MA
        # This requires access to the FeedManager or DataManager
        # For this sample, we'll assume we can get data via a global or passed reference
        
        from core.feed_manager import feed_manager
        import pandas as pd
        import pandas_ta as ta
        
        # Get candles for the symbol
        candles = feed_manager.get_candles(self.symbol, count=self.slow_period + 5)
        if len(candles) < self.slow_period:
            return
            
        # Convert to DataFrame
        df = pd.DataFrame([c.__dict__ for c in candles])
        
        # Calculate MAs
        fast_ma = ta.sma(df['close'], length=self.fast_period)
        slow_ma = ta.sma(df['close'], length=self.slow_period)
        
        # Check crossover on last closed candle (index -1)
        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]
        
        # Logic
        if prev_fast <= prev_slow and current_fast > current_slow:
            # Golden Cross (Buy)
            if self.last_cross != 'above':
                logger.info(f"{self.name}: Golden Cross detected on {self.symbol}")
                self._place_order(OrderType.BUY)
                self.last_cross = 'above'
                
        elif prev_fast >= prev_slow and current_fast < current_slow:
            # Death Cross (Sell)
            if self.last_cross != 'below':
                logger.info(f"{self.name}: Death Cross detected on {self.symbol}")
                self._place_order(OrderType.SELL)
                self.last_cross = 'below'
                
    def _place_order(self, order_type):
        """Helper to place order."""
        # We need access to the broker. 
        # Ideally, the Strategy class should have a reference to the broker or an execution service.
        # For now, we'll emit a signal or use a global reference if available.
        # Let's use EventBus to request order placement? 
        # Or better, let the PluginManager inject the broker.
        
        # For this sample, we'll just log it as we don't have direct broker access here yet.
        logger.info(f"STRATEGY SIGNAL: {order_type} {self.volume} {self.symbol}")
