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
    
    def get_token(self, symbol: str, exchange: str = 'NSE') -> Optional[str]:
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
                
                # 1. Try exact match
                for item in values:
                    if item.get('tsym') == symbol:
                        token = item.get('token')
                        self.token_cache[cache_key] = token
                        logger.debug(f"Found token {token} for {symbol} (Exact match)")
                        return token
                
                # 2. Try match with -EQ suffix (common for NSE)
                symbol_eq = f"{symbol}-EQ"
                for item in values:
                    if item.get('tsym') == symbol_eq:
                        token = item.get('token')
                        self.token_cache[cache_key] = token
                        logger.debug(f"Found token {token} for {symbol} (Suffix match)")
                        return token

                # 3. Try match where result starts with symbol (e.g. RELIANCE vs RELIANCE-EQ)
                for item in values:
                    tsym = item.get('tsym', '')
                    if tsym.startswith(symbol) and (tsym == symbol or tsym == f"{symbol}-EQ"):
                         token = item.get('token')
                         self.token_cache[cache_key] = token
                         logger.debug(f"Found token {token} for {symbol} (Prefix match)")
                         return token
                
                # 4. If still no match but we have results, take the first one if it looks reasonable
                # This is risky but better than failing for simple cases
                if values:
                    first_match = values[0]
                    token = first_match.get('token')
                    tsym = first_match.get('tsym')
                    logger.warning(f"No exact match for {symbol}, using first result: {tsym}")
                    self.token_cache[cache_key] = token
                    return token
                    
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
            # Step 1: Parse exchange and get token
            exchange = 'NSE'  # Default
            token = None
            clean_symbol = symbol
            
            # Handle pipe format: MCX|463007 (exchange|token)
            if '|' in symbol:
                parts = symbol.split('|', 1)
                exchange = parts[0]
                token = parts[1]  # Token already provided
                
            # Handle colon format: MCX:SYMBOL (exchange:symbol name)  
            elif ':' in symbol:
                parts = symbol.split(':', 1)
                exchange = parts[0]
                clean_symbol = parts[1]
                token = self.get_token(clean_symbol, exchange)
            else:
                token = self.get_token(clean_symbol, exchange)
                
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
        return quotes

    def get_historical_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> list:
        """
        Get historical OHLC data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, D1, etc.)
            start_time: Start datetime
            end_time: End datetime
            
        Returns:
            List of OHLCData objects
        """
        from data.models import OHLCData
        
        api = self.auth_manager.get_api()
        if not api:
            logger.error("Cannot get historical data - not authenticated")
            return []
            
        try:
            # 1. Get token
            # Parse exchange and token from symbol
            exchange = 'NSE'  # Default
            token = None
            clean_symbol = symbol
            
            # Handle pipe format: MCX|463007 (exchange|token)
            if '|' in symbol:
                parts = symbol.split('|', 1)
                exchange = parts[0]
                token = parts[1]  # Token is already provided!
                logger.info(f"Using token from symbol: {exchange}|{token}")
                
            # Handle colon format: MCX:NATURALGAS26DEC25 (exchange:symbol name)
            elif ':' in symbol:
                parts = symbol.split(':', 1)
                exchange = parts[0]
                clean_symbol = parts[1]
                token = self.get_token(clean_symbol, exchange)
                
            # No format specified - try to get token
            else:
                if 'BSE' in symbol:
                    exchange = 'BSE'
                token = self.get_token(clean_symbol, exchange)
                
            if not token:
                logger.warning(f"Could not find token for {symbol}")
                return []
            
            # 2. Map timeframe to interval
            # M1->1, M5->5, M15->15, M30->30, H1->60, H4->240
            interval_map = {
                'M1': '1', 'M5': '5', 'M15': '15', 'M30': '30',
                'H1': '60', 'H4': '240'
            }
            
            data = []
            
            # 3. Fetch data based on timeframe
            if timeframe == 'D1':
                # Daily data
                # Format: DD-MM-YYYY (e.g., 01-01-2023) - Wait, API doc says "457401600" (timestamp) in example?
                # Actually doc says: startdate="457401600" (seconds since 1970)
                # But example response has "time":"21-SEP-2022"
                
                # Let's try passing timestamps as strings as per user snippet/doc
                start_ts = str(int(start_time.timestamp()))
                end_ts = str(int(end_time.timestamp()))
                
                logger.info(f"Fetching daily data for {symbol} ({start_ts} to {end_ts})")
                
                # Note: API method signature might vary, checking user snippet...
                # User snippet for daily: api.get_daily_price_series(exchange="NSE",tradingsymbol="PAYTM-EQ",startdate="...",enddate="...")
                
                result = api.get_daily_price_series(
                    exchange=exchange,
                    tradingsymbol=symbol,
                    startdate=start_ts,
                    enddate=end_ts
                )
                
            else:
                # Intraday data
                interval = interval_map.get(timeframe, '1')
                start_ts = start_time.timestamp()
                end_ts = end_time.timestamp()
                
                logger.info(f"Fetching {timeframe} data for {symbol} (Interval: {interval})")
                
                # User snippet: api.get_time_price_series(exchange='NSE', token=tok, starttime=lastBusDay.timestamp(), interval=5)
                # Note: user snippet passes float timestamp
                
                result = api.get_time_price_series(
                    exchange=exchange,
                    token=token,
                    starttime=start_ts,
                    endtime=end_ts,
                    interval=interval
                )
            
            # 4. Process results
            if result:
                # Check for failure response which is a list with one dict or just a dict
                if isinstance(result, dict) and result.get('stat') == 'Not_Ok':
                    logger.error(f"API Error: {result.get('emsg')}")
                    return []
                
                # Result is usually a list of dicts
                for candle in result:
                    if candle.get('stat') != 'Ok':
                        continue
                        
                    # Parse timestamp
                    # Intraday: "02-06-2020 15:46:23"
                    # Daily: "21-SEP-2022" or "DD-MM-YYYY HH:MM:SS" depending on response
                    time_str = candle.get('time')
                    try:
                        if timeframe == 'D1':
                            # Try multiple formats for daily
                            try:
                                dt = datetime.strptime(time_str, "%d-%b-%Y") # 21-SEP-2022
                            except ValueError:
                                dt = datetime.strptime(time_str, "%d-%m-%Y %H:%M:%S")
                        else:
                            dt = datetime.strptime(time_str, "%d-%m-%Y %H:%M:%S")
                    except ValueError as e:
                        logger.warning(f"Could not parse date {time_str}: {e}")
                        continue
                        
                    ohlc = OHLCData(
                        timestamp=dt,
                        open=float(candle.get('into', 0)),
                        high=float(candle.get('inth', 0)),
                        low=float(candle.get('intl', 0)),
                        close=float(candle.get('intc', 0)),
                        volume=float(candle.get('v', 0) or candle.get('intv', 0))
                    )
                    data.append(ohlc)
                    
                # Sort by time
                data.sort(key=lambda x: x.timestamp)
                logger.info(f"Retrieved {len(data)} candles for {symbol}")
                
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
