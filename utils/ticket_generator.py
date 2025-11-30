"""Ticket number generator for orders."""
import threading


class TicketGenerator:
    """Generate unique ticket numbers for orders."""
    
    _instance = None
    _lock = threading.Lock()
    _counter = 100000000
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def generate(self) -> int:
        """Generate next ticket number."""
        with self._lock:
            self._counter += 1
            return self._counter


# Global ticket generator
ticket_generator = TicketGenerator()
