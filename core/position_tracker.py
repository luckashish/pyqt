"""
Position Tracker.
Tracks open positions, calculates P&L, and manages trailing stops.
"""
from typing import Dict, List, Optional
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

from data.models import Order, OrderStatus, Position, OHLCData
from core.event_bus import event_bus
from utils.logger import logger


class PositionTracker(QObject):
    """
    Tracks open positions and manages position-level logic.
    """
    
    # Signals
    position_opened = pyqtSignal(object)  # Position
    position_closed = pyqtSignal(object)  # Position
    position_updated = pyqtSignal(object)  # Position
    trailing_stop_updated = pyqtSignal(int, float)  # ticket, new_sl
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
        
    def __init__(self):
        """Initialize Position Tracker."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Storage
        self.open_positions: Dict[int, Order] = {}  # ticket -> Order
        self.closed_positions: List[Order] = []
        
        # Price cache for P&L calculation
        self.current_prices: Dict[str, float] = {}  # symbol -> latest price
        
        # Trailing stop settings
        self.trailing_stops: Dict[int, dict] = {}  # ticket -> {pips, highest/lowest}
        
        logger.info("Position Tracker initialized")
        
    def add_position(self, order: Order):
        """
        Add an open position.
        
        Args:
            order: Order object
        """
        if order.ticket in self.open_positions:
            logger.warning(f"Position {order.ticket} already tracked")
            return
            
        self.open_positions[order.ticket] = order
        
        # Create position object
        position = self._order_to_position(order)
        self.position_opened.emit(position)
        
        logger.info(f"Position opened: {order.ticket} {order.order_type.value} {order.symbol} {order.volume} @ {order.open_price}")
        
    def update_position(self, order: Order):
        """
        Update a position.
        
        Args:
            order: Updated order
        """
        if order.ticket not in self.open_positions:
            # New position
            if order.status == OrderStatus.ACTIVE:
                self.add_position(order)
            return
            
        # Update existing position
        self.open_positions[order.ticket] = order
        
        position = self._order_to_position(order)
        self.position_updated.emit(position)
        
    def close_position(self, ticket: int, close_price: float, close_time: datetime = None):
        """
        Close a position.
        
        Args:
            ticket: Order ticket
            close_price: Close price
            close_time: Close time
        """
        if ticket not in self.open_positions:
            logger.warning(f"Position {ticket} not found")
            return
            
        order = self.open_positions.pop(ticket)
        order.close_price = close_price
        order.close_time = close_time or datetime.now()
        order.status = OrderStatus.CLOSED
        
        # Remove trailing stop if exists
        if ticket in self.trailing_stops:
            del self.trailing_stops[ticket]
            
        # Store in history
        self.closed_positions.append(order)
        
        # Create position object
        position = self._order_to_position(order)
        self.position_closed.emit(position)
        
        # Emit order closed event for EAs
        event_bus.order_closed.emit(order)
        
        profit = order.calculate_profit(close_price)
        logger.info(f"Position closed: {ticket} @ {close_price}, Profit: {profit:.2f}")
        
    def get_position(self, ticket: int) -> Optional[Order]:
        """Get position by ticket."""
        return self.open_positions.get(ticket)
        
    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return [self._order_to_position(order) for order in self.open_positions.values()]
        
    def get_positions_for_symbol(self, symbol: str) -> List[Order]:
        """Get all positions for a symbol."""
        return [order for order in self.open_positions.values() if order.symbol == symbol]
        
    def get_position_count(self) -> int:
        """Get count of open positions."""
        return len(self.open_positions)
        
    def calculate_total_pnl(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate total unrealized P&L.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            Total P&L
        """
        total_pnl = 0.0
        
        for order in self.open_positions.values():
            current_price = current_prices.get(order.symbol, order.open_price)
            pnl = order.calculate_profit(current_price)
            total_pnl += pnl
            
        return total_pnl
    
    def get_unrealized_pnl_for_ea(self, ea_name: str) -> float:
        """
        Calculate unrealized P&L for a specific EA.
        
        Args:
            ea_name: Name of the EA
            
        Returns:
            Total unrealized P&L for this EA's open positions
        """
        total_pnl = 0.0
        
        for order in self.open_positions.values():
            # Check if this order belongs to the EA (by comment)
            if order.comment and order.comment.startswith(ea_name):
                # Get current price from cache
                current_price = self.current_prices.get(order.symbol, order.open_price)
                pnl = order.calculate_profit(current_price)
                total_pnl += pnl
                
        return total_pnl
        
    def enable_trailing_stop(
        self,
        ticket: int,
        trailing_pips: float,
        current_price: float
    ):
        """
        Enable trailing stop for a position.
        
        Args:
            ticket: Order ticket
            trailing_pips: Trailing distance in pips
            current_price: Current market price
        """
        if ticket not in self.open_positions:
            logger.warning(f"Position {ticket} not found")
            return
            
        order = self.open_positions[ticket]
        
        # Initialize trailing stop
        self.trailing_stops[ticket] = {
            "pips": trailing_pips,
            "best_price": current_price,
            "is_buy": order.is_buy
        }
        
        logger.info(f"Trailing stop enabled for {ticket}: {trailing_pips} pips")
        
    def update_trailing_stops(self, symbol: str, current_price: float) -> List[tuple]:
        """
        Update trailing stops for a symbol.
        
        Args:
            symbol: Symbol name
            current_price: Current price
            
        Returns:
            List of (ticket, new_sl) tuples that need updating
        """
        updates = []
        
        for ticket, trail_data in self.trailing_stops.items():
            order = self.open_positions.get(ticket)
            
            if not order or order.symbol != symbol:
                continue
                
            is_buy = trail_data["is_buy"]
            trailing_pips = trail_data["pips"]
            best_price = trail_data["best_price"]
            
            # Update best price
            if is_buy:
                if current_price > best_price:
                    trail_data["best_price"] = current_price
                    best_price = current_price
                    
                # Calculate new SL
                pip_value = 0.0001
                new_sl = best_price - (trailing_pips * pip_value)
                
                # Only update if new SL is higher than current SL
                if new_sl > order.sl:
                    updates.append((ticket, new_sl))
                    self.trailing_stop_updated.emit(ticket, new_sl)
                    logger.info(f"Trailing stop updated for {ticket}: {new_sl:.5f}")
            else:
                if current_price < best_price:
                    trail_data["best_price"] = current_price
                    best_price = current_price
                    
                # Calculate new SL
                pip_value = 0.0001
                new_sl = best_price + (trailing_pips * pip_value)
                
                # Only update if new SL is lower than current SL
                if new_sl < order.sl or order.sl == 0:
                    updates.append((ticket, new_sl))
                    self.trailing_stop_updated.emit(ticket, new_sl)
                    logger.info(f"Trailing stop updated for {ticket}: {new_sl:.5f}")
                    
        return updates
        
    def get_statistics(self) -> dict:
        """Get position statistics."""
        total_trades = len(self.closed_positions)
        
        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0
            }
            
        wins = [o for o in self.closed_positions if o.calculate_profit(o.close_price) > 0]
        losses = [o for o in self.closed_positions if o.calculate_profit(o.close_price) <= 0]
        
        total_profit = sum(o.calculate_profit(o.close_price) for o in self.closed_positions)
        gross_profit = sum(o.calculate_profit(o.close_price) for o in wins) if wins else 0
        gross_loss = abs(sum(o.calculate_profit(o.close_price) for o in losses)) if losses else 0
        
        return {
            "total_trades": total_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round((len(wins) / total_trades) * 100, 2),
            "total_profit": round(total_profit, 2),
            "avg_win": round(gross_profit / len(wins), 2) if wins else 0.0,
            "avg_loss": round(gross_loss / len(losses), 2) if losses else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0
        }
        
    def _order_to_position(self, order: Order) -> Position:
        """Convert Order to Position."""
        current_price = order.close_price if order.close_price else order.open_price
        profit = order.calculate_profit(current_price)
        
        return Position(
            symbol=order.symbol,
            volume=order.volume,
            entry_price=order.open_price,
            current_price=current_price,
            profit=profit,
            is_long=order.is_buy
        )

    def on_tick(self, symbol: object):
        """
        Process tick for client-side SL/TP monitoring.
        """
        current_price = symbol.last
        if not current_price:
            return
        
        # Cache current price for P&L calculation
        self.current_prices[symbol.name] = current_price
            
        # logger.debug(f"Tick received for {symbol.name}: {current_price}")

        # Check all open positions for this symbol
        # Create a copy to avoid modification during iteration
        for ticket, order in list(self.open_positions.items()):
            logger.info(f"Checking {ticket} {order.symbol} vs {symbol.name} @ {current_price}")
            if order.symbol == symbol.name:
                self._check_sl_tp(order, current_price)
                
                # Also update trailing stops
                self.update_trailing_stops(symbol.name, current_price)

    def on_bar(self, bar: OHLCData, symbol_name: str):
        """
        Process bar for client-side SL/TP monitoring (Backup check).
        Checks if High/Low hit SL/TP during the bar.
        """
        logger.info(f"PositionTracker: Received bar for {symbol_name} H:{bar.high} L:{bar.low}")
        
        # Check all open positions for this symbol
        for ticket, order in list(self.open_positions.items()):
            if order.symbol == symbol_name:
                logger.info(f"Checking Bar SL/TP for {ticket} (SL:{order.sl} TP:{order.tp})")
                self._check_sl_tp_bar(order, bar)
                
    def _check_sl_tp_bar(self, order: Order, bar: OHLCData):
        """Check SL/TP against bar High/Low."""
        from core.execution_service import execution_service
        
        # Check Stop Loss
        if order.sl > 0:
            # For BUY: Low <= SL
            if order.is_buy and bar.low <= order.sl:
                logger.info(f"SL HIT (Bar) for {order.ticket}: Low {bar.low} <= SL {order.sl}")
                execution_service.close_position(order.ticket, "SL_HIT_BAR")
                return
            # For SELL: High >= SL
            elif not order.is_buy and bar.high >= order.sl:
                logger.info(f"SL HIT (Bar) for {order.ticket}: High {bar.high} >= SL {order.sl}")
                execution_service.close_position(order.ticket, "SL_HIT_BAR")
                return

        # Check Take Profit
        if order.tp > 0:
            # For BUY: High >= TP
            if order.is_buy and bar.high >= order.tp:
                logger.info(f"TP HIT (Bar) for {order.ticket}: High {bar.high} >= TP {order.tp}")
                execution_service.close_position(order.ticket, "TP_HIT_BAR")
                return
            # For SELL: Low <= TP
            elif not order.is_buy and bar.low <= order.tp:
                logger.info(f"TP HIT (Bar) for {order.ticket}: Low {bar.low} <= TP {order.tp}")
                execution_service.close_position(order.ticket, "TP_HIT_BAR")
                return

    def _check_sl_tp(self, order: Order, current_price: float):
        """Check if SL or TP is hit."""
        from core.execution_service import execution_service
        
        # Check Stop Loss
        if order.sl > 0:
            if (order.is_buy and current_price <= order.sl) or \
               (not order.is_buy and current_price >= order.sl):
                logger.info(f"SL HIT for {order.ticket}: {current_price} (SL {order.sl})")
                execution_service.close_position(order.ticket, "SL_HIT")
                return

        # Check Take Profit
        if order.tp > 0:
            logger.info(f"Checking TP {order.tp} for {order.ticket} (Sell={not order.is_buy}) @ {current_price}")
            if (order.is_buy and current_price >= order.tp) or \
               (not order.is_buy and current_price <= order.tp):
                logger.info(f"TP HIT for {order.ticket}: {current_price} (TP {order.tp})")
                execution_service.close_position(order.ticket, "TP_HIT")
                return


# Global position tracker instance
position_tracker = PositionTracker()
