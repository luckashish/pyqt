"""
Base Expert Advisor Framework.
Provides lifecycle management and common functionality for all EAs.
"""
from abc import ABCMeta, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

from core.interfaces.plugin import Strategy
from data.models import Symbol, OHLCData, Order, EASignal, EAState, EAConfig
from utils.logger import logger


# Combined metaclass to resolve conflict
class CombinedMeta(type(QObject), ABCMeta):
    pass


class ExpertAdvisor(Strategy, QObject, metaclass=CombinedMeta):
    """
    Base class for Expert Advisors (Automated Trading Strategies).
    Extends the Strategy plugin interface with lifecycle management.
    """
    
    # Signals
    signal_generated = pyqtSignal(object)  # EASignal
    state_changed = pyqtSignal(object)  # EAState
    error_occurred = pyqtSignal(str)  # error message
    order_request = pyqtSignal(object)  # Order request
    
    def __init__(self):
        Strategy.__init__(self)
        QObject.__init__(self)
        
        # EA properties
        self.name = "Base EA"
        self.version = "1.0"
        self.author = "System"
        self.description = "Base Expert Advisor"
        
        # Configuration
        self.config: Optional[EAConfig] = None
        
        # State
        self.state = EAState(name=self.name)
        self.is_running = False
        self.is_paused = False
        
        # Performance tracking
        self.trades_today = 0
        self.daily_profit = 0.0
        self.open_tickets = []  # List of open order tickets
        
        # Market data cache
        self.last_tick: Optional[Symbol] = None
        self.last_bar: Optional[OHLCData] = None
        
    def initialize(self, config: EAConfig):
        """
        Initialize EA with configuration.
        Called before starting the EA.
        
        Args:
            config: EA configuration
        """
        self.config = config
        self.state.symbol = config.symbol
        self.state.timeframe = config.timeframe
        
        # Let subclass do custom initialization
        self.on_init()
        
        logger.info(f"{self.name}: Initialized with config for {config.symbol} {config.timeframe}")
        
    @abstractmethod
    def on_init(self):
        """
        Called after EA initialization.
        Override to perform custom initialization logic.
        """
        pass
        
    def start(self):
        """Start the EA."""
        if not self.config:
            self.emit_error("EA not initialized. Call initialize() first.")
            return
            
        if self.is_running:
            logger.warning(f"{self.name}: Already running")
            return
            
        self.is_running = True
        self.is_paused = False
        self.state.status = "running"
        self.state.enabled = True
        self.state.started_time = datetime.now()
        
        # Reset daily counters if new day
        self._check_new_trading_day()
        
        self.on_start()
        self._emit_state_changed()
        
        logger.info(f"{self.name}: Started on {self.config.symbol} {self.config.timeframe}")
        
    @abstractmethod
    def on_start(self):
        """
        Called when EA starts.
        Override to perform startup logic.
        """
        pass
        
    def stop(self):
        """Stop the EA."""
        if not self.is_running:
            return
            
        self.is_running = False
        self.is_paused = False
        self.state.status = "stopped"
        self.state.enabled = False
        
        self.on_stop()
        self._emit_state_changed()
        
        logger.info(f"{self.name}: Stopped")
        
    @abstractmethod
    def on_stop(self):
        """
        Called when EA stops.
        Override to perform cleanup logic.
        """
        pass
        
    def pause(self):
        """Pause the EA."""
        if not self.is_running or self.is_paused:
            return
            
        self.is_paused = True
        self.state.status = "paused"
        
        self.on_pause()
        self._emit_state_changed()
        
        logger.info(f"{self.name}: Paused")
        
    def on_pause(self):
        """Called when EA is paused. Override if needed."""
        pass
        
    def resume(self):
        """Resume the EA."""
        if not self.is_running or not self.is_paused:
            return
            
        self.is_paused = False
        self.state.status = "running"
        
        self.on_resume()
        self._emit_state_changed()
        
        logger.info(f"{self.name}: Resumed")
        
    def on_resume(self):
        """Called when EA resumes. Override if needed."""
        pass
        
    def on_tick(self, tick: Symbol):
        """
        Called on every price tick.
        
        Args:
            tick: Current tick data
        """
        if not self._can_trade():
            return
            
        self.last_tick = tick
        
        # Update state
        self.state.last_update = datetime.now()
        
        # Let subclass handle tick
        self.handle_tick(tick)
        
    @abstractmethod
    def handle_tick(self, tick: Symbol):
        """
        Handle price tick.
        Override to implement tick-based logic.
        
        Args:
            tick: Current tick data
        """
        pass
        
    def on_bar(self, bar: OHLCData):
        """
        Called when a new candle/bar closes.
        
        Args:
            bar: Closed candle data
        """
        if not self._can_trade():
            return
            
        self.last_bar = bar
        
        # Check new trading day
        self._check_new_trading_day()
        
        # Let subclass handle bar
        self.handle_bar(bar)
        
    @abstractmethod
    def handle_bar(self, bar: OHLCData):
        """
        Handle new bar/candle close.
        Override to implement bar-based logic.
        
        Args:
            bar: Closed candle data
        """
        pass
        
    def on_order_update(self, order: Order):
        """
        Called when an order is updated (filled, closed, etc.).
        
        Args:
            order: Updated order
        """
        # Track open positions
        if order.status.value == "closed":
            if order.ticket in self.open_tickets:
                self.open_tickets.remove(order.ticket)
                
                # Update statistics
                profit = order.calculate_profit(order.close_price or 0)
                self.state.total_trades += 1
                self.state.profit += profit
                self.daily_profit += profit
                self.trades_today += 1
                
                if profit > 0:
                    self.state.winning_trades += 1
                    
                logger.info(f"{self.name}: Order {order.ticket} closed with profit {profit:.2f}")
        elif order.status.value == "active":
            if order.ticket not in self.open_tickets:
                self.open_tickets.append(order.ticket)
                
        self.state.open_positions = len(self.open_tickets)
        self._emit_state_changed()
        
        # Let subclass handle
        self.handle_order_update(order)
        
    def handle_order_update(self, order: Order):
        """
        Handle order update.
        Override to implement custom order handling.
        
        Args:
            order: Updated order
        """
        pass
        
    def generate_signal(
        self,
        signal_type: str,
        price: float,
        stop_loss: float = 0.0,
        take_profit: float = 0.0,
        reason: str = "",
        confidence: float = 1.0
    ):
        """
        Generate a trading signal.
        
        Args:
            signal_type: "BUY", "SELL", "CLOSE_BUY", "CLOSE_SELL"
            price: Signal price
            stop_loss: Stop loss price
            take_profit: Take profit price
            reason: Reason for signal
            confidence: Signal confidence (0-1)
        """
        signal = EASignal(
            ea_name=self.name,
            symbol=self.config.symbol,
            signal_type=signal_type,
            timestamp=datetime.now(),
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            confidence=confidence,
            volume=self.config.lot_size
        )
        
        self.state.last_signal = signal
        self.signal_generated.emit(signal)
        
        logger.info(f"{self.name}: Generated {signal_type} signal at {price:.2f} - {reason}")
        
    def emit_error(self, message: str):
        """
        Emit an error and pause the EA.
        
        Args:
            message: Error message
        """
        self.state.error_message = message
        self.state.status = "error"
        self.error_occurred.emit(message)
        
        if self.is_running:
            self.pause()
            
        logger.error(f"{self.name}: {message}")
        
    def _can_trade(self) -> bool:
        """Check if EA can trade."""
        if not self.is_running or self.is_paused:
            return False
            
        if not self.config:
            return False
            
        # Check time filter
        if self.config.enable_time_filter:
            current_hour = datetime.now().hour
            if not (self.config.trading_start_hour <= current_hour < self.config.trading_end_hour):
                return False
                
        # Check daily loss limit
        if self.daily_profit < 0:
            loss_percent = abs(self.daily_profit / 10000) * 100  # Assuming $10k account
            if loss_percent >= self.config.max_daily_loss:
                self.emit_error(f"Daily loss limit reached: {loss_percent:.2f}%")
                return False
                
        # Check max positions
        if len(self.open_tickets) >= self.config.max_concurrent_positions:
            return False
            
        return True
        
    def _check_new_trading_day(self):
        """Reset daily counters on new day."""
        if self.state.started_time:
            current_date = datetime.now().date()
            started_date = self.state.started_time.date()
            
            if current_date > started_date:
                self.trades_today = 0
                self.daily_profit = 0.0
                self.state.started_time = datetime.now()
                logger.info(f"{self.name}: New trading day - counters reset")
                
    def _emit_state_changed(self):
        """Emit state changed signal."""
        self.state.last_update = datetime.now()
        self.state_changed.emit(self.state)
        
    def get_state(self) -> EAState:
        """Get current EA state."""
        return self.state
        
    def get_config(self) -> Optional[EAConfig]:
        """Get EA configuration."""
        return self.config
        
    def update_config(self, config: EAConfig):
        """
        Update EA configuration.
        Note: EA must be restarted for changes to take effect.
        
        Args:
            config: New configuration
        """
        self.config = config
        logger.info(f"{self.name}: Configuration updated")
