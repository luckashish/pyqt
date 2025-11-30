"""Account Manager - tracks account balance, equity, margin."""
from PyQt5.QtCore import QObject
from typing import List
from data.models import Order, OrderStatus
from core.event_bus import event_bus
from utils.logger import logger


class AccountManager(QObject):
    """Manages account information and calculations."""
    
    def __init__(self, initial_balance: float = 10000.0, leverage: int = 100):
        super().__init__()
        self.balance = initial_balance
        self.leverage = leverage
        self._open_orders: List[Order] = []
        self._closed_orders: List[Order] = []
        
        # Connect to order events
        event_bus.order_placed.connect(self._on_order_placed)
        event_bus.order_closed.connect(self._on_order_closed)
    
    def add_order(self, order: Order):
        """Add an open order."""
        if order.status == OrderStatus.ACTIVE:
            self._open_orders.append(order)
            self._update_account_info()
    
    def close_order(self, order: Order):
        """Move order from open to closed."""
        if order in self._open_orders:
            self._open_orders.remove(order)
        
        order.status = OrderStatus.CLOSED
        self._closed_orders.append(order)
        
        # Update balance with profit/loss
        self.balance += order.calculate_profit(order.close_price or order.open_price)
        self._update_account_info()
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        return self._open_orders.copy()
    
    def get_closed_orders(self) -> List[Order]:
        """Get order history."""
        return self._closed_orders.copy()
    
    def calculate_equity(self, current_prices: dict) -> float:
        """
        Calculate current equity (balance + floating P/L).
        
        Args:
            current_prices: Dict of symbol -> current price
        """
        floating_pl = 0.0
        for order in self._open_orders:
            if order.symbol in current_prices:
                floating_pl += order.calculate_profit(current_prices[order.symbol])
        
        return self.balance + floating_pl
    
    def calculate_margin(self) -> float:
        """Calculate used margin for open positions."""
        margin = 0.0
        for order in self._open_orders:
            # Simplified margin calculation
            # Margin = (Volume * Contract Size * Open Price) / Leverage
            # For forex, contract size = 100,000
            contract_size = 100000
            position_value = order.volume * contract_size * order.open_price
            margin += position_value / self.leverage
        
        return margin
    
    def get_account_info(self, current_prices: dict = None) -> dict:
        """
        Get complete account information.
        
        Args:
            current_prices: Dict of symbol -> current price
            
        Returns:
            Dict with balance, equity, margin, free_margin, margin_level
        """
        if current_prices is None:
            current_prices = {}
        
        equity = self.calculate_equity(current_prices)
        margin = self.calculate_margin()
        free_margin = equity - margin
        margin_level = (equity / margin * 100) if margin > 0 else 0.0
        
        return {
            'balance': round(self.balance, 2),
            'equity': round(equity, 2),
            'margin': round(margin, 2),
            'free_margin': round(free_margin, 2),
            'margin_level': round(margin_level, 2)
        }
    
    def _on_order_placed(self, order: Order):
        """Handle order placed event."""
        self.add_order(order)
    
    def _on_order_closed(self, order: Order):
        """Handle order closed event."""
        self.close_order(order)
    
    def _update_account_info(self):
        """Emit account update event."""
        event_bus.account_updated.emit(self.get_account_info())


# Global account manager (will be initialized by broker)
account_manager = None
