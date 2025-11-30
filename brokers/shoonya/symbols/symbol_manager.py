"""
Shoonya Symbol Manager
Manages symbol masters and instrument lookups
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from utils.config_manager import config
from utils.logger import logger


class ShoonyaSymbolManager:
    """Manages Shoonya symbol masters (scrip masters)."""
    
    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.cache_dir = config.get('shoonya.symbols.cache_directory', 'cache/symbols')
        self.refresh_hours = config.get('shoonya.symbols.refresh_interval_hours', 24)
        self.exchanges = config.get('shoonya.symbols.exchanges', ['NSE', 'BSE'])
        
        # In-memory symbol cache
        self.symbols: Dict[str, List[Dict]] = {}
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def download_symbol_masters(self, force: bool = False):
        """
        Download symbol masters from Shoonya.
        
        Args:
            force: Force download even if cache is fresh
        """
        api = self.auth_manager.get_api()
        if not api:
            logger.error("Cannot download symbols - not authenticated")
            return
        
        for exchange in self.exchanges:
            cache_file = os.path.join(self.cache_dir, f"{exchange}_symbols.json")
            
            # Check if cache is fresh
            if not force and os.path.exists(cache_file):
                mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
                if datetime.now() - mtime < timedelta(hours=self.refresh_hours):
                    logger.info(f"Using cached symbols for {exchange}")
                    self._load_from_cache(exchange, cache_file)
                    continue
            
            # Download fresh symbol data
            logger.info(f"Downloading symbol master for {exchange}...")
            try:
                # For NSE/BSE, we'll use a simplified approach
                # In production, use api.searchscrip() or get_scrip_info()
                
                # Get common symbols (you can expand this list)
                common_symbols = self._get_common_symbols(exchange)
                
                if common_symbols:
                    # Save to cache
                    with open(cache_file, 'w') as f:
                        json.dump(common_symbols, f, indent=2)
                    
                    self.symbols[exchange] = common_symbols
                    logger.info(f"Cached {len(common_symbols)} symbols for {exchange}")
                    
            except Exception as e:
                logger.error(f"Failed to download symbols for {exchange}: {e}")
    
    def _load_from_cache(self, exchange: str, cache_file: str):
        """Load symbols from cache file."""
        try:
            with open(cache_file, 'r') as f:
                self.symbols[exchange] = json.load(f)
            logger.info(f"Loaded {len(self.symbols[exchange])} symbols from cache")
        except Exception as e:
            logger.error(f"Failed to load cache for {exchange}: {e}")
    
    def _get_common_symbols(self, exchange: str) -> List[Dict]:
        """
        Get common tradeable symbols.
        
        In production, this should call the Shoonya API.
        For now, returns a curated list of popular stocks.
        """
        if exchange == 'NSE':
            return [
                {'symbol': 'RELIANCE-EQ', 'name': 'Reliance Industries', 'exchange': 'NSE'},
                {'symbol': 'TCS-EQ', 'name': 'Tata Consultancy Services', 'exchange': 'NSE'},
                {'symbol': 'INFY-EQ', 'name': 'Infosys', 'exchange': 'NSE'},
                {'symbol': 'HDFCBANK-EQ', 'name': 'HDFC Bank', 'exchange': 'NSE'},
                {'symbol': 'ICICIBANK-EQ', 'name': 'ICICI Bank', 'exchange': 'NSE'},
                {'symbol': 'SBIN-EQ', 'name': 'State Bank of India', 'exchange': 'NSE'},
                {'symbol': 'BHARTIARTL-EQ', 'name': 'Bharti Airtel', 'exchange': 'NSE'},
                {'symbol': 'ITC-EQ', 'name': 'ITC Ltd', 'exchange': 'NSE'},
                {'symbol': 'KOTAKBANK-EQ', 'name': 'Kotak Mahindra Bank', 'exchange': 'NSE'},
                {'symbol': 'LT-EQ', 'name': 'Larsen & Toubro', 'exchange': 'NSE'},
            ]
        elif exchange == 'BSE':
            return [
                {'symbol': 'RELIANCE', 'name': 'Reliance Industries', 'exchange': 'BSE'},
                {'symbol': 'TCS', 'name': 'Tata Consultancy Services', 'exchange': 'BSE'},
                {'symbol': 'INFY', 'name': 'Infosys', 'exchange': 'BSE'},
            ]
        return []
    
    def get_all_symbols(self) -> List[str]:
        """Get all available symbol names."""
        all_symbols = []
        for exchange, symbols in self.symbols.items():
            all_symbols.extend([s['symbol'] for s in symbols])
        return all_symbols
    
    def search_symbol(self, query: str, exchange: str = None) -> List[Dict]:
        """
        Search for symbols by name or code.
        
        Args:
            query: Search query
            exchange: Specific exchange or None for all
            
        Returns:
            List of matching symbols
        """
        query_upper = query.upper()
        results = []
        
        exchanges_to_search = [exchange] if exchange else self.symbols.keys()
        
        for exch in exchanges_to_search:
            if exch not in self.symbols:
                continue
            
            for symbol in self.symbols[exch]:
                if (query_upper in symbol['symbol'].upper() or 
                    query_upper in symbol.get('name', '').upper()):
                    results.append(symbol)
        
        return results[:50]  # Limit results
    
    def get_symbol_info(self, symbol: str, exchange: str = 'NSE') -> Optional[Dict]:
        """Get detailed information for a specific symbol."""
        if exchange not in self.symbols:
            return None
        
        for sym in self.symbols[exchange]:
            if sym['symbol'] == symbol:
                return sym
        
        return None
