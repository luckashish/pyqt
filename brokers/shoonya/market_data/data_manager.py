"""
Shoonya Market Data Manager
Handles real-time quotes and historical data
"""
from typing import Optional
from data.models import Symbol
from utils.logger import logger
from datetime import datetime


class ShoonyaMarketDataManager:
    """Manages market data retrieval from Shoonya."""
    
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        # Cache symbol tokens to avoid repeated searches
        self.token_cache = {}
    
    def _get_token(self, symbol: str, exchange: str = 'NSE') -> Optional[str]:
        """
        Get token for a symbol by searching.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE-EQ")
            exchange: Exchange
            
        Returns:
            Token string or None
        """
        # Check cache first
        cache_key = f"{exchange}:{symbol}"
        if cache_key in self.token_cache:
            return self.token_cache[cache_key]
        
        api = self.auth_manager.get_api()
        if not api:
            return None
        
        try:
            # Search for the symbol
            result = api.searchscrip(exchange=exchange, searchtext=symbol)
            
            if result and result.get('stat') == 'Ok':
                values = result.get('values', [])
                
                # Find exact match
                for item in values:
                    if item.get('tsym') == symbol:
                        token = item.get('token')
                        # Cache it
                        self.token_cache[cache_key] = token
                        logger.debug(f"Found token {token} for {symbol}")
                        return token
                
                # If no exact match but we have results, log it
                if values:
                    logger.warning(f"No exact match for {symbol}, found {len(values)} similar symbols")
                    
            return None
            
        except Exception as e:
            logger.error(f"Error searching for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str, exchange: str = 'NSE') -> Optional[Symbol]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, etc.)
            
        Returns:
            Symbol with current bid/ask or None
        """
        api = self.auth_manager.get_api()
        if not api:
            logger.error("Cannot get quote - not authenticated")
            return None
        
        try:
            # Step 1: Get token for the symbol
            token = self._get_token(symbol, exchange)
            if not token:
                logger.warning(f"Could not find token for {symbol}")
                return None
            
            # Step 2: Get quote using the token
            result = api.get_quotes(exchange=exchange, token=token)
            
            if result and result.get('stat') == 'Ok':
                # Parse Shoonya response
                bid = float(result.get('bp1', 0))
                ask = float(result.get('sp1', 0))
                ltp = float(result.get('lp', 0))
                
                logger.debug(f"Quote for {symbol}: LTP={ltp}, Bid={bid}, Ask={ask}")
                
                return Symbol(
                    name=symbol,
                    bid=bid if bid > 0 else ltp,
                    ask=ask if ask > 0 else ltp,
                    last_tick_time=datetime.now()
                )
            else:
                error_msg = result.get('emsg', 'Unknown error') if result else 'No response'
                logger.warning(f"Failed to get quote for {symbol}: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: list, exchange: str = 'NSE') -> list:
        """
        Get quotes for multiple symbols.
        
        Args:
            symbols: List of symbols
            exchange: Exchange
            
        Returns:
            List of Symbol objects
        """
        quotes = []
        for symbol in symbols:
            quote = self.get_quote(symbol, exchange)
            if quote:
                quotes.append(quote)
        return quotes
