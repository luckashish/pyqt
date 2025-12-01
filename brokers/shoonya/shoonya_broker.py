"""
Shoonya Broker Implementation  
Main broker class coordinating all sub-modules
"""
from typing import List, Optional
from datetime import datetime

from brokers.base.broker_base import BrokerBase
from data.models import Symbol, Order, OHLCData, OrderType
from core.event_bus import event_bus
from utils.logger import logger


class ShoonyaBroker(BrokerBase):
    """
    Shoonya/Finvasia broker implementation.
    
    Modular implementation with separate managers for:
    - Authentication, Orders, Market Data, Symbols
    """
    
    def __init__(self):
        super().__init__("Shoonya")
        
        # Initialize auth manager
        try:
            from brokers.shoonya.auth.auth_manager import ShoonyaAuthManager
            self.auth_manager = ShoonyaAuthManager()
            logger.info("Shoonya auth manager initialized")
            
            # Other managers initialized after login
            self.symbol_manager = None
            self.market_data_manager = None
            self.order_manager = None
            
        except ImportError as e:
            logger.error(f"Failed to import Shoonya SDK: {e}")
            logger.error("Install: pip install git+https://github.com/Shoonya-Dev/ShoonyaApi-py.git")
            self.auth_manager = None
    
    def connect(self, server: str, username: str, password: str) -> bool:
        """Connect to Shoonya broker."""
        if not self.auth_manager:
            logger.error("Shoonya auth manager not available")
            return False
        
        try:
            logger.info("Connecting to Shoonya...")
            
            # Login
            success = self.auth_manager.login({'username': username, 'password': password})
            
            if success:
                self._connected = True
                user_info = self.auth_manager.get_user_info()
                
                logger.info("[OK] Connected to Shoonya")
                logger.info(f"   User: {user_info.get('user_name')}")
                logger.info(f"   Account: {user_info.get('account_id')}")
                
                # Initialize managers
                from brokers.shoonya.symbols.symbol_manager import ShoonyaSymbolManager
                from brokers.shoonya.market_data.data_manager import ShoonyaMarketDataManager
                from brokers.shoonya.orders.order_manager import ShoonyaOrderManager
                
                self.symbol_manager = ShoonyaSymbolManager(self.auth_manager)
                self.market_data_manager = ShoonyaMarketDataManager(self.auth_manager)
                self.order_manager = ShoonyaOrderManager(self.auth_manager)
                
                # Initialize WebSocket Client
                from brokers.shoonya.websocket.client import ShoonyaWebSocketClient
                self.ws_client = ShoonyaWebSocketClient(self.auth_manager.get_api())
                self.ws_client.connect()
                
                logger.info("Downloading symbols...")
                # self.symbol_manager.download_symbol_masters() # Can be slow, maybe skip or async
                logger.info("[OK] All managers initialized")
                
                event_bus.connected.emit(self.name)
                return True
            else:
                logger.error("Shoonya login failed - check config.yaml")
                return False
                
        except Exception as e:
            logger.error(f"Shoonya connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Shoonya."""
        if hasattr(self, 'ws_client') and self.ws_client:
            self.ws_client.disconnect()
            
        if self.auth_manager:
            self.auth_manager.logout()
        self._connected = False
        event_bus.disconnected.emit("User disconnect")
    
    def get_symbols(self) -> List[str]:
        """Get available symbols."""
        if self.symbol_manager:
            return self.symbol_manager.get_all_symbols()
        return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Symbol]:
        """Get symbol information."""
        if self.market_data_manager:
            return self.market_data_manager.get_quote(symbol)
        return None
    
    def subscribe(self, symbols):
        """
        Subscribe to symbol updates.
        
        Args:
            symbols: Single symbol string or list of symbol strings
        """
        if isinstance(symbols, str):
            symbols = [symbols]
            
        final_symbols = []
        
        for symbol in symbols:
            if "|" in symbol:
                final_symbols.append(symbol)
            else:
                # Try to resolve symbol
                # Check for exchange prefix (e.g. NSE:SBIN)
                exchange = 'NSE'
                clean_symbol = symbol
                
                if ':' in symbol:
                    parts = symbol.split(':')
                    if len(parts) == 2:
                        exchange = parts[0]
                        clean_symbol = parts[1]
                elif 'BSE' in symbol: # Heuristic
                    exchange = 'BSE'
                
                # Lookup token
                token = self.market_data_manager.get_token(clean_symbol, exchange)
                if token:
                    final_symbols.append(f"{exchange}|{token}")
                    logger.info(f"Resolved {symbol} to {exchange}|{token}")
                else:
                    logger.warning(f"Could not resolve symbol: {symbol}")
        
        if final_symbols:
            if hasattr(self, 'ws_client') and self.ws_client:
                self.ws_client.subscribe(final_symbols)
            else:
                logger.warning("WebSocket client not initialized, cannot subscribe")
    
    def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol."""
        if "|" in symbol:
            if hasattr(self, 'ws_client') and self.ws_client:
                self.ws_client.unsubscribe([symbol])
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[OHLCData]:
        """Get historical data."""
        if self.market_data_manager:
            return self.market_data_manager.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time
            )
        return []
    
    def place_order(
        self,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: Optional[float] = None,
        sl: float = 0.0,
        tp: float = 0.0,
        comment: str = "",
        trigger_price: Optional[float] = None,
        product_type: str = 'I'
    ) -> Optional[Order]:
        """Place an order."""
        if self.order_manager:
            # Parse symbol and exchange
            exchange = 'NSE' # Default
            trading_symbol = symbol
            
            # Handle EXCHANGE:SYMBOL format
            if ':' in symbol:
                parts = symbol.split(':')
                if len(parts) == 2:
                    exchange = parts[0]
                    trading_symbol = parts[1]
            # Handle EXCHANGE|TOKEN format (less likely for placement but possible)
            elif '|' in symbol:
                 parts = symbol.split('|')
                 if len(parts) == 2:
                    exchange = parts[0]
                    trading_symbol = parts[1]

            return self.order_manager.place_order(
                symbol=trading_symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                trigger_price=trigger_price,
                product=product_type,
                exchange=exchange
            )
        return None
    
    def modify_order(
        self,
        ticket: int,
        symbol: str,
        order_type: OrderType,
        volume: float,
        price: float = 0.0,
        trigger_price: float = 0.0
    ) -> bool:
        """Modify an existing order."""
        if self.order_manager:
            return self.order_manager.modify_order(
                ticket=ticket,
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                trigger_price=trigger_price
            )
        return False

    def cancel_order(self, ticket: int) -> bool:
        """Cancel an order."""
        if self.order_manager:
            return self.order_manager.cancel_order(ticket)
        return False
    
    def close_order(self, ticket: int) -> bool:
        """Close order (alias for cancel)."""
        return self.cancel_order(ticket)
    
    def get_open_orders(self) -> List[Order]:
        """Get open orders."""
        if self.order_manager:
            return self.order_manager.get_open_orders()
        return []
    
    def get_order_history(self) -> List[Order]:
        """Get order history."""
        if self.order_manager:
            return self.order_manager.get_order_history()
        return []
    
    def get_order_book(self) -> List[Order]:
        """Get full order book."""
        if self.order_manager:
            return self.order_manager.get_order_book()
        return []
    
    def get_positions(self) -> List[dict]:
        """Get position book."""
        if self.order_manager:
            return self.order_manager.get_positions()
        return []
    
    def get_account_info(self) -> dict:
        """Get account information."""
        # TODO: Implement account manager
        return {
            'balance': 0.0,
            'equity': 0.0,
            'margin': 0.0,
            'free_margin': 0.0,
            'margin_level': 0.0
        }
