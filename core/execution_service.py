"""
Order Execution Service.
Handles order placement, validation, and execution for Expert Advisors.
"""
from typing import Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

from core.broker_interface import BrokerInterface
from data.models import Order, OrderType, OrderStatus, EASignal
from utils.logger import logger


class ExecutionService(QObject):
    """
    Centralized order execution for EAs.
    Handles validation, risk checks, and broker communication.
    """
    
    # Signals
    order_placed = pyqtSignal(object)  # Order
    order_rejected = pyqtSignal(str, str)  # EA name, reason
    order_filled = pyqtSignal(object)  # Order
    
    _instance = None
    
    def __new__(cls, broker: Optional[BrokerInterface] = None):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
        
    def __init__(self, broker: Optional[BrokerInterface] = None):
        """
        Initialize Execution Service.
        
        Args:
            broker: Broker interface instance
        """
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        self.broker = broker
        self.paper_trading = True  # Safety mode
        
        # Execution settings
        self.max_slippage_pips = 5.0
        self.max_retries = 3
        
        logger.info("Execution Service initialized")
        
    def set_broker(self, broker: BrokerInterface):
        """Set broker interface."""
        self.broker = broker
        logger.info(f"Broker set: {broker.__class__.__name__}")
        
    def set_paper_trading(self, enabled: bool):
        """Enable/disable paper trading mode."""
        self.paper_trading = enabled
        mode = "ENABLED" if enabled else "DISABLED"
        logger.warning(f"Paper trading {mode}")
        
    def execute_signal(self, signal: EASignal) -> Optional[Order]:
        """
        Execute a trading signal.
        
        Args:
            signal: EA signal to execute
            
        Returns:
            Order object if successful, None otherwise
        """
        if not self.broker:
            logger.error("No broker connection")
            self.order_rejected.emit(signal.ea_name, "No broker connection")
            return None
            
        # Validate signal
        if not self._validate_signal(signal):
            return None
            
        # Convert signal to order
        order = self._signal_to_order(signal)
        
        if self.paper_trading:
            # Simulated execution
            logger.info(f"[PAPER] Executing {signal.signal_type} {signal.symbol} @ {signal.price}")
            order.status = OrderStatus.ACTIVE
            self.order_placed.emit(order)
            return order
        else:
            # Real execution
            try:
                placed_order = self._place_order_with_retry(order)
                
                if placed_order:
                    self.order_placed.emit(placed_order)
                    logger.info(f"Order placed: {placed_order.ticket} {placed_order.order_type.value} {placed_order.symbol}")
                    return placed_order
                else:
                    self.order_rejected.emit(signal.ea_name, "Order placement failed")
                    return None
                    
            except Exception as e:
                logger.error(f"Order execution error: {e}")
                self.order_rejected.emit(signal.ea_name, str(e))
                return None
                
    def _validate_signal(self, signal: EASignal) -> bool:
        """
        Validate trading signal.
        
        Args:
            signal: Signal to validate
            
        Returns:
            True if valid
        """
        # Check signal type
        if signal.signal_type not in ["BUY", "SELL", "CLOSE_BUY", "CLOSE_SELL"]:
            logger.error(f"Invalid signal type: {signal.signal_type}")
            self.order_rejected.emit(signal.ea_name, f"Invalid signal type: {signal.signal_type}")
            return False
            
        # Check symbol
        if not signal.symbol:
            logger.error("Signal has no symbol")
            self.order_rejected.emit(signal.ea_name, "No symbol specified")
            return False
            
        # Check volume
        if signal.volume <= 0:
            logger.error(f"Invalid volume: {signal.volume}")
            self.order_rejected.emit(signal.ea_name, f"Invalid volume: {signal.volume}")
            return False
            
        # Check price
        if signal.price <= 0:
            logger.error(f"Invalid price: {signal.price}")
            self.order_rejected.emit(signal.ea_name, f"Invalid price: {signal.price}")
            return False
            
        return True
        
    def _signal_to_order(self, signal: EASignal) -> Order:
        """
        Convert signal to order.
        
        Args:
            signal: EA signal
            
        Returns:
            Order object
        """
        # Map signal type to order type
        order_type_map = {
            "BUY": OrderType.BUY,
            "SELL": OrderType.SELL,
            "CLOSE_BUY": OrderType.SELL,  # Close buy = sell
            "CLOSE_SELL": OrderType.BUY   # Close sell = buy
        }
        
        order_type = order_type_map.get(signal.signal_type, OrderType.BUY)
        
        # Create order
        order = Order(
            ticket=self._generate_ticket(),
            symbol=signal.symbol,
            order_type=order_type,
            volume=signal.volume,
            open_price=signal.price,
            open_time=datetime.now(),
            sl=signal.stop_loss,
            tp=signal.take_profit,
            comment=f"{signal.ea_name} - {signal.reason}",
            status=OrderStatus.PENDING
        )
        
        return order
        
    def _place_order_with_retry(self, order: Order) -> Optional[Order]:
        """
        Place order with retry logic.
        
        Args:
            order: Order to place
            
        Returns:
            Placed order or None
        """
        for attempt in range(self.max_retries):
            try:
                placed_order = self.broker.place_order(
                    symbol=order.symbol,
                    order_type=order.order_type,
                    volume=order.volume,
                    price=order.open_price,
                    sl=order.sl,
                    tp=order.tp,
                    comment=order.comment
                )
                
                if placed_order:
                    return placed_order
                    
                logger.warning(f"Order placement attempt {attempt + 1} failed")
                
            except Exception as e:
                logger.error(f"Order placement attempt {attempt + 1} error: {e}")
                
        return None
        
    def _generate_ticket(self) -> int:
        """Generate unique ticket number."""
        # Simple implementation - use timestamp
        return int(datetime.now().timestamp() * 1000)
        
    def close_position(
        self,
        ticket: int,
        ea_name: str = "Manual"
    ) -> bool:
        """
        Close a position.
        
        Args:
            ticket: Order ticket
            ea_name: EA name requesting close
            
        Returns:
            True if successful
        """
        if not self.broker:
            logger.error("No broker connection")
            return False
            
        if self.paper_trading:
            logger.info(f"[PAPER] Closing position {ticket}")
            return True
        else:
            try:
                success = self.broker.close_order(ticket)
                
                if success:
                    logger.info(f"Position {ticket} closed by {ea_name}")
                else:
                    logger.error(f"Failed to close position {ticket}")
                    
                return success
                
            except Exception as e:
                logger.error(f"Error closing position {ticket}: {e}")
                return False
                
    def modify_position(
        self,
        ticket: int,
        sl: float = 0.0,
        tp: float = 0.0
    ) -> bool:
        """
        Modify position SL/TP.
        
        Args:
            ticket: Order ticket
            sl: New stop loss
            tp: New take profit
            
        Returns:
            True if successful
        """
        if not self.broker:
            logger.error("No broker connection")
            return False
            
        if self.paper_trading:
            logger.info(f"[PAPER] Modifying position {ticket}: SL={sl}, TP={tp}")
            return True
        else:
            try:
                success = self.broker.modify_order(ticket, sl, tp)
                
                if success:
                    logger.info(f"Position {ticket} modified: SL={sl}, TP={tp}")
                else:
                    logger.error(f"Failed to modify position {ticket}")
                    
                return success
                
            except Exception as e:
                logger.error(f"Error modifying position {ticket}: {e}")
                return False


# Global execution service (will be initialized with broker later)
execution_service = ExecutionService()
