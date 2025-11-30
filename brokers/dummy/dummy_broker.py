"""Dummy Broker - simulates a trading broker for testing."""
import random
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from PyQt5.QtCore import QTimer

from core.broker_interface import BrokerInterface
from core.event_bus import event_bus
from core.feed_manager import feed_manager
from core.account_manager import AccountManager
from data.models import Symbol, Order, OHLCData, OrderType, OrderStatus
from utils.ticket_generator import ticket_generator
from utils.logger import logger


class DummyBroker(BrokerInterface):
    """Simulated broker for demo/testing purposes."""
    
    def __init__(self):
        self._connected = False
        self._symbols: Dict[str, Symbol] = {}
        self._open_orders: List[Order] = []
        self._closed_orders: List[Order] = []
        self._account_manager: Optional[AccountManager] = None
        self._update_timer: Optional[QTimer] = None
        
        # Initialize default symbols
        self._init_symbols()
    
    def _init_symbols(self):
        """Initialize default trading symbols with starting prices."""
        symbol_prices = {
            'EURUSD': 1.10000,
            'GBPUSD': 1.28000,
            'USDJPY': 148.500,
            'USDCHF': 0.88000,
            'AUDUSD': 0.65000,
            'USDCAD': 1.35000,
            'EURJPY': 163.000,
            'EURGBP': 0.86000
        }
        
        for name, price in symbol_prices.items():
            spread = 0.0002 if 'JPY' not in name else 0.02
            self._symbols[name] = Symbol(
                name=name,
                bid=price,
                ask=price + spread,
                last_tick_time=datetime.now()
            )
    
    def connect(self, server: str, username: str, password: str) -> bool:
        """Simulate connection to broker."""
        logger.info(f"Connecting to {server} as {username}...")
        
        # Simulate connection delay
        self._connected = True
        
        # Initialize account manager
        self._account_manager = AccountManager(initial_balance=10000.0)
        
        # Start price updates
        self._start_price_updates()
        
        # Generate some historical data
        for symbol in self._symbols.keys():
            self._generate_historical_data(symbol)
        
        event_bus.connected.emit(server)
        logger.info("Connected successfully")
        return True
    
    def disconnect(self):
        """Disconnect from broker."""
        if self._update_timer:
            self._update_timer.stop()
        
        self._connected = False
        event_bus.disconnected.emit("User disconnect")
        logger.info("Disconnected from broker")
    
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected
    
    def get_symbols(self) -> List[str]:
        """Get available symbols."""
        return list(self._symbols.keys())
    
    def get_symbol_info(self, symbol: str) -> Optional[Symbol]:
        """Get symbol information."""
        return self._symbols.get(symbol)
    
    def subscribe(self, symbol: str):
        """Subscribe to symbol updates."""
        feed_manager.subscribe(symbol)
        logger.info(f"Subscribed to {symbol}")
    
    def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol updates."""
        feed_manager.unsubscribe(symbol)
        logger.info(f"Unsubscribed from {symbol}")
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[OHLCData]:
        """Get historical candle data."""
        # Return cached candles from feed manager
        return feed_manager.get_candles(symbol, 200)
    
    def place_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = ""
    ) -> Optional[Order]:
        """Place a new order."""
        if not self._connected:
            logger.error("Not connected to broker")
            return None
        
        symbol_info = self._symbols.get(symbol)
        if not symbol_info:
            logger.error(f"Symbol {symbol} not found")
            return None
        
        # Determine execution price
        if price is None:
            # Market order
            if order_type in [OrderType.BUY]:
                exec_price = symbol_info.ask
            else:
                exec_price = symbol_info.bid
        else:
            exec_price = price
        
        # Create order
        order = Order(
            ticket=ticket_generator.generate(),
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            open_price=exec_price,
            open_time=datetime.now(),
            sl=sl,
            tp=tp,
            status=OrderStatus.ACTIVE,
            comment=comment
        )
        
        self._open_orders.append(order)
        event_bus.order_placed.emit(order)
        logger.info(f"Order placed: {order.ticket} {order_type.value} {volume} {symbol} @ {exec_price}")
        
        return order
    
    def modify_order(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """Modify order SL/TP."""
        for order in self._open_orders:
            if order.ticket == ticket:
                order.sl = sl
                order.tp = tp
                event_bus.order_modified.emit(order)
                logger.info(f"Order modified: {ticket} SL={sl} TP={tp}")
                return True
        
        logger.error(f"Order {ticket} not found")
        return False
    
    def close_order(self, ticket: int) -> bool:
        """Close an order."""
        for order in self._open_orders:
            if order.ticket == ticket:
                symbol_info = self._symbols.get(order.symbol)
                if not symbol_info:
                    return False
                
                # Determine close price
                if order.is_buy:
                    close_price = symbol_info.bid
                else:
                    close_price = symbol_info.ask
                
                order.close_price = close_price
                order.close_time = datetime.now()
                order.status = OrderStatus.CLOSED
                
                self._open_orders.remove(order)
                self._closed_orders.append(order)
                
                event_bus.order_closed.emit(order)
                logger.info(f"Order closed: {ticket} @ {close_price}")
                return True
        
        logger.error(f"Order {ticket} not found")
        return False
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders."""
        return self._open_orders.copy()
    
    def get_order_history(self) -> List[Order]:
        """Get closed orders."""
        return self._closed_orders.copy()
    
    def get_account_info(self) -> dict:
        """Get account information."""
        if self._account_manager:
            # Get current prices
            current_prices = {s.name: s.bid for s in self._symbols.values()}
            return self._account_manager.get_account_info(current_prices)
        
        return {
            'balance': 10000.0,
            'equity': 10000.0,
            'margin': 0.0,
            'free_margin': 10000.0,
            'margin_level': 0.0
        }
    
    def _start_price_updates(self):
        """Start timer for price updates."""
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_prices)
        self._update_timer.start(1000)  # Update every 1 second
    
    def _update_prices(self):
        """Simulate price movement."""
        for symbol in self._symbols.values():
            # Random walk for price updates
            change = random.gauss(0, 0.0001)  # Small random change
            if 'JPY' in symbol.name:
                change *= 100  # JPY has different pip value
            
            symbol.bid += change
            symbol.ask = symbol.bid + (0.02 if 'JPY' in symbol.name else 0.0002)
            symbol.last_tick_time = datetime.now()
            
            # Emit tick update
            feed_manager.update_tick(symbol)
        
        # Check SL/TP for open orders
        self._check_sl_tp()
        
        # Update account info
        if self._account_manager:
            current_prices = {s.name: s.bid for s in self._symbols.values()}
            event_bus.account_updated.emit(
                self._account_manager.get_account_info(current_prices)
            )
    
    def _check_sl_tp(self):
        """Check if any orders hit SL or TP."""
        for order in self._open_orders.copy():
            symbol_info = self._symbols.get(order.symbol)
            if not symbol_info:
                continue
            
            current_price = symbol_info.bid if order.is_buy else symbol_info.ask
            
            # Check stop loss
            if order.sl > 0:
                if (order.is_buy and current_price <= order.sl) or \
                   (not order.is_buy and current_price >= order.sl):
                    logger.info(f"Order {order.ticket} hit SL at {current_price}")
                    self.close_order(order.ticket)
                    continue
            
            # Check take profit
            if order.tp > 0:
                if (order.is_buy and current_price >= order.tp) or \
                   (not order.is_buy and current_price <= order.tp):
                    logger.info(f"Order {order.ticket} hit TP at {current_price}")
                    self.close_order(order.ticket)
    
    def _generate_historical_data(self, symbol: str, count: int = 200):
        """Generate dummy historical candles for a symbol."""
        symbol_info = self._symbols.get(symbol)
        if not symbol_info:
            return
        
        # Start from 200 hours ago
        start_time = datetime.now() - timedelta(hours=count)
        base_price = symbol_info.bid
        
        for i in range(count):
            timestamp = start_time + timedelta(hours=i)
            
            # Random walk
            change = random.gauss(0, 0.002)
            if 'JPY' in symbol:
                change *= 100
            
            open_price = base_price
            close_price = base_price + change
            high_price = max(open_price, close_price) + abs(random.gauss(0, 0.0005))
            low_price = min(open_price, close_price) - abs(random.gauss(0, 0.0005))
            volume = random.randint(100, 10000)
            
            if 'JPY' in symbol:
                high_price = max(open_price, close_price) + abs(random.gauss(0, 0.05))
                low_price = min(open_price, close_price) - abs(random.gauss(0, 0.05))
            
            candle = OHLCData(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            )
            
            feed_manager.update_candle(symbol, candle)
            base_price = close_price


# Global broker instance
dummy_broker = DummyBroker()
