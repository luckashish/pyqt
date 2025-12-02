"""
Symbol Normalizer.
Handles conversion between different symbol formats (colon vs pipe).
"""
from typing import Optional, Dict
from utils.logger import logger


class SymbolNormalizer:
    """
    Normalizes symbol names between different formats.
    
    Supports:
    - MCX:NATURALGAS26DEC25 <-> MCX|467741
    - NSE:SBIN-EQ <-> NSE|123
    """
    
    def __init__(self):
        # Cache for symbol mappings
        self._colon_to_pipe: Dict[str, str] = {}
        self._pipe_to_colon: Dict[str, str] = {}
        
    def register_mapping(self, colon_format: str, pipe_format: str):
        """
        Register a symbol mapping.
        
        Args:
            colon_format: Symbol in colon format (e.g., MCX:NATURALGAS26DEC25)
            pipe_format: Symbol in pipe format (e.g., MCX|467741)
        """
        self._colon_to_pipe[colon_format] = pipe_format
        self._pipe_to_colon[pipe_format] = colon_format
        logger.debug(f"Registered symbol mapping: {colon_format} <-> {pipe_format}")
    
    def auto_register_from_symbol(self, symbol_obj):
        """
        Auto-register mapping from Symbol object if it has both formats.
        
        Args:
            symbol_obj: Symbol object with name and possibly display_name
        """
        if not hasattr(symbol_obj, 'name'):
            return
            
        # If symbol has both formats, register them
        if '|' in symbol_obj.name and hasattr(symbol_obj, 'display_name'):
            pipe_format = symbol_obj.name
            colon_format = symbol_obj.display_name or symbol_obj.name
            
            if ':' in colon_format:
                self.register_mapping(colon_format, pipe_format)
    
    def normalize(self, symbol: str) -> str:
        """
        Normalize symbol to a canonical format.
        Returns the symbol unchanged if no mapping exists.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Normalized symbol
        """
        # If it's already in our mapping, return as-is
        if symbol in self._colon_to_pipe or symbol in self._pipe_to_colon:
            return symbol
            
        # Otherwise return unchanged
        return symbol
    
    def match(self, symbol1: str, symbol2: str) -> bool:
        """
        Check if two symbols match (same underlying instrument).
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            
        Returns:
            True if they represent the same instrument
        """
        if symbol1 == symbol2:
            return True
            
        # Check if they map to each other
        if self._colon_to_pipe.get(symbol1) == symbol2:
            return True
        if self._pipe_to_colon.get(symbol1) == symbol2:
            return True
            
        # Extract exchange and check if base symbols match
        exchange1, base1 = self._extract_parts(symbol1)
        exchange2, base2 = self._extract_parts(symbol2)
        
        # Same exchange is required
        if exchange1 != exchange2:
            return False
        
        # For token format (pipe), we can't match easily
        # Require explicit mapping
        return False
    
    def get_all_formats(self, symbol: str) -> list:
        """
        Get all known formats for a symbol.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            List of all equivalent symbol formats
        """
        formats = [symbol]
        
        # Add mapped format if exists
        if symbol in self._colon_to_pipe:
            formats.append(self._colon_to_pipe[symbol])
        elif symbol in self._pipe_to_colon:
            formats.append(self._pipe_to_colon[symbol])
            
        return formats
    
    def _extract_parts(self, symbol: str) -> tuple:
        """
        Extract exchange and base symbol.
        
        Args:
            symbol: Symbol string
            
        Returns:
            Tuple of (exchange, base)
        """
        if ':' in symbol:
            parts = symbol.split(':', 1)
            return parts[0], parts[1] if len(parts) > 1 else ''
        elif '|' in symbol:
            parts = symbol.split('|', 1)
            return parts[0], parts[1] if len(parts) > 1 else ''
        else:
            return '', symbol
    
    def to_pipe_format(self, symbol: str) -> Optional[str]:
        """
        Convert symbol to pipe format if possible.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Symbol in pipe format or None
        """
        if '|' in symbol:
            return symbol
        
        return self._colon_to_pipe.get(symbol)
    
    def to_colon_format(self, symbol: str) -> Optional[str]:
        """
        Convert symbol to colon format if possible.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Symbol in colon format or None
        """
        if ':' in symbol:
            return symbol
            
        return self._pipe_to_colon.get(symbol)


# Global symbol normalizer instance
symbol_normalizer = SymbolNormalizer()
