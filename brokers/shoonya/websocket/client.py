"""
Shoonya WebSocket Client
Handles real-time market data and order updates via WebSocket.
"""
import threading
import time
from typing import List, Dict, Callable, Optional
from NorenRestApiPy.NorenApi import NorenApi
from utils.logger import logger
from data.models import Symbol, Order, OrderStatus, OrderType
from core.feed_manager import feed_manager
from core.event_bus import event_bus
from datetime import datetime

class ShoonyaWebSocketClient:
    """
    WebSocket client for Shoonya API.
    Manages connection, subscriptions, and data processing.
    """
    
    def __init__(self, api: NorenApi):
        self.api = api
        self.is_connected = False
        self.subscribed_symbols: List[str] = []
        self._stop_event = threading.Event()
        
    def connect(self):
        """Start the WebSocket connection."""
        if self.is_connected:
            logger.warning("WebSocket already connected")
            return

        logger.info("Starting WebSocket connection...")
        
        try:
            # Start WebSocket with callbacks
            self.api.start_websocket(
                subscribe_callback=self._on_feed_update,
                order_update_callback=self._on_order_update,
                socket_open_callback=self._on_open,
                socket_close_callback=self._on_close,
                socket_error_callback=self._on_error
            )
            
            # Wait for connection (with timeout)
            # Note: NorenApi starts a separate thread for WS
            # We wait for _on_open to set is_connected
            timeout = 10
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            if self.is_connected:
                logger.info("WebSocket connected successfully")
            else:
                logger.error("WebSocket connection timed out")
                
        except Exception as e:
            logger.error(f"Failed to start WebSocket: {e}")

    def disconnect(self):
        """Disconnect WebSocket."""
        # NorenApi doesn't have a clean stop_websocket method exposed publicly 
        # in some versions, but usually closing the app handles it.
        # We'll rely on the API's internal handling or just stop tracking.
        self.is_connected = False
        logger.info("WebSocket disconnected")

    def subscribe(self, symbols: List[str]):
        """
        Subscribe to market data for symbols.
        Args:
            symbols: List of symbols in format 'EXCHANGE|TOKEN'
        """
        if not self.is_connected:
            logger.warning("Cannot subscribe: WebSocket not connected")
            return
            
        if not symbols:
            return

        logger.info(f"Subscribing to {len(symbols)} symbols: {symbols[:5]}...")
        self.api.subscribe(symbols)
        
        # Track subscriptions
        for s in symbols:
            if s not in self.subscribed_symbols:
                self.subscribed_symbols.append(s)

    def unsubscribe(self, symbols: List[str]):
        """Unsubscribe from symbols."""
        if not self.is_connected:
            return
            
        logger.info(f"Unsubscribing from {len(symbols)} symbols")
        self.api.unsubscribe(symbols)
        
        for s in symbols:
            if s in self.subscribed_symbols:
                self.subscribed_symbols.remove(s)

    def _on_open(self):
        """Callback when socket opens."""
        logger.info("WebSocket connection opened")
        self.is_connected = True
        
        # Resubscribe if we have stored symbols (reconnection scenario)
        if self.subscribed_symbols:
            logger.info(f"Resubscribing to {len(self.subscribed_symbols)} symbols")
            self.api.subscribe(self.subscribed_symbols)

    def _on_close(self):
        """Callback when socket closes."""
        logger.warning("WebSocket connection closed")
        self.is_connected = False

    def _on_error(self, error):
        """Callback for WebSocket errors."""
        logger.error(f"WebSocket error: {error}")

    def _on_feed_update(self, tick_data: Dict):
        """
        Handle market data update.
        
        Data types:
        t='tk' : Full touchline (sent on subscribe)
        t='tf' : Touchline update (changes only)
        """
        try:
            msg_type = tick_data.get('t')
            logger.debug(f"WS Message: {tick_data}")
            if msg_type not in ['tk', 'tf']:
                return

            # Extract basic info
            token = tick_data.get('tk')
            exchange = tick_data.get('e')
            
            if not token or not exchange:
                return
                
            # We need to reconstruct the symbol name to look it up
            # Since we don't have a global Token -> Name map easily accessible here without passing it in,
            # we will rely on the fact that we subscribed with "EXCHANGE|TOKEN".
            # Ideally, we should pass a token_map to this client.
            # For now, let's create a partial Symbol object and let FeedManager handle the rest if possible,
            # OR we emit the raw data and let Broker/FeedManager enrich it.
            
            # Better approach: The 'tk' message usually contains 'ts' (Trading Symbol)
            # We can cache it.
            
            # Construct symbol name with exchange to avoid ambiguity
            # e.g. "NSE:RELIANCE-EQ"
            ts = tick_data.get('ts')
            symbol_name = f"{exchange}:{ts}" if ts else None
            
            # Create a Symbol object with available data
            # Note: 'tf' messages might NOT have 'ts', so we need to handle that.
            # For this implementation, we'll assume we can find the symbol in FeedManager by token if needed,
            # but FeedManager uses names.
            
            # Let's try to get the symbol name from the tick if available, or construct a unique ID
            # If 'ts' is missing (common in 'tf'), we might have issues identifying the symbol 
            # unless we maintain a map.
            
            if not hasattr(self, 'token_map'):
                self.token_map = {} # Token -> Symbol Name
                
            if symbol_name:
                self.token_map[token] = symbol_name
            elif token in self.token_map:
                symbol_name = self.token_map[token]
            else:
                # Fallback: try to construct it or ignore
                logger.debug(f"Unknown token {token} in tick. Map keys: {list(self.token_map.keys())}")
                return

            # Parse fields
            # Shoonya sends strings for numbers often
            try:
                bid = float(tick_data.get('bp1', 0.0))
                ask = float(tick_data.get('sp1', 0.0))
                last = float(tick_data.get('lp', 0.0))
                volume = int(tick_data.get('v', 0))
                high = float(tick_data.get('h', 0.0))
                low = float(tick_data.get('l', 0.0))
                close = float(tick_data.get('c', 0.0)) # Previous close
                open_price = float(tick_data.get('o', 0.0))
                change = float(tick_data.get('pc', 0.0)) # Percent change
            except ValueError:
                return # Bad data

            # Create Symbol object
            # We might not have all fields in 'tf', so we should ideally merge with previous state.
            # However, FeedManager.update_tick usually expects a full object or we need a partial update mechanism.
            # For now, we'll create a Symbol with what we have.
            
            symbol = Symbol(
                name=symbol_name,
                bid=bid,
                ask=ask,
                last=last,
                high=high,
                low=low,
                close=close,
                volume=volume,
                description="" # We don't have this in tick
            )
            
            # Push to Feed Manager
            feed_manager.update_tick(symbol)
            
        except Exception as e:
            logger.error(f"Error processing tick: {e}")

    def _on_order_update(self, order_data: Dict):
        """
        Handle order update.
        t='om'
        """
        try:
            if order_data.get('t') != 'om':
                return
                
            logger.info(f"Order update: {order_data.get('norenordno')} {order_data.get('status')}")
            
            # Map status
            status_map = {
                'OPEN': OrderStatus.ACTIVE,
                'PENDING': OrderStatus.ACTIVE,
                'COMPLETE': OrderStatus.FILLED,
                'REJECTED': OrderStatus.REJECTED,
                'CANCELED': OrderStatus.CANCELLED,
                'TRIGGER_PENDING': OrderStatus.ACTIVE
            }
            
            api_status = order_data.get('status', '').upper()
            status = status_map.get(api_status, OrderStatus.PENDING)
            
            # Create Order object
            # We need to be careful about fields availability
            order = Order(
                ticket=order_data.get('norenordno', ''),
                symbol=order_data.get('tsym', ''),
                order_type=OrderType.BUY if order_data.get('trantype') == 'B' else OrderType.SELL,
                volume=float(order_data.get('qty', 0)),
                open_price=float(order_data.get('prc', 0.0)),
                open_time=datetime.now(), # API might provide 'norentm'
                status=status,
                rejection_reason=order_data.get('rejreason', '')
            )
            
            # Emit event
            if status == OrderStatus.FILLED:
                # For filled, we might want close_price/time
                order.close_price = float(order_data.get('flprc', 0.0))
                event_bus.order_closed.emit(order) # Or order_filled
            elif status == OrderStatus.ACTIVE:
                event_bus.order_placed.emit(order)
            elif status in [OrderStatus.REJECTED, OrderStatus.CANCELLED]:
                event_bus.order_closed.emit(order) # Treat as closed for UI purposes
                
        except Exception as e:
            logger.error(f"Error processing order update: {e}")
