"""
Worker Threads for Non-Blocking Operations
Prevents UI freeze during broker operations
"""
from PyQt5.QtCore import QThread, pyqtSignal
from utils.logger import logger


class BrokerConnectionWorker(QThread):
    """Background worker for broker connection."""
    
    # Signals
    connection_success = pyqtSignal(str)  # username
    connection_failed = pyqtSignal(str)   # error message
    progress_update = pyqtSignal(str)     # status message
    
    def __init__(self, broker, server, username, password):
        super().__init__()
        self.broker = broker
        self.server = server
        self.username = username
        self.password = password
    
    def run(self):
        """Execute connection in background thread."""
        try:
            self.progress_update.emit("Connecting to broker...")
            
            success = self.broker.connect(self.server, self.username, self.password)
            
            if success:
                self.connection_success.emit(self.username)
            else:
                self.connection_failed.emit("Connection failed")
                
        except Exception as e:
            logger.error(f"Connection worker error: {e}")
            self.connection_failed.emit(str(e))


class QuoteUpdateWorker(QThread):
    """Background worker for quote updates."""
    
    # Signals
    quotes_updated = pyqtSignal(list)  # List of Symbol objects
    update_failed = pyqtSignal(str)    # Error message
    
    def __init__(self, broker, symbols):
        super().__init__()
        self.broker = broker
        self.symbols = symbols
        self.running = True
    
    def run(self):
        """Periodically fetch quotes in background."""
        while self.running:
            try:
                quotes = []
                for symbol in self.symbols:
                    if not self.running:
                        break
                    
                    quote = self.broker.get_symbol_info(symbol)
                    if quote:
                        quotes.append(quote)
                
                if quotes:
                    self.quotes_updated.emit(quotes)
                
                # Wait 1 second between updates
                self.msleep(1000)
                
            except Exception as e:
                logger.error(f"Quote update worker error: {e}")
                self.update_failed.emit(str(e))
                self.msleep(5000)  # Wait 5s before retry
    
    def stop(self):
        """Stop the worker thread."""
        self.running = False


class OrderPlacementWorker(QThread):
    """Background worker for placing orders."""
    
    # Signals
    order_placed = pyqtSignal(object)  # Order object
    order_failed = pyqtSignal(str)     # Error message
    
    def __init__(self, broker, symbol, order_type, volume, price=None, sl=0, tp=0):
        super().__init__()
        self.broker = broker
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume
        self.price = price
        self.sl = sl
        self.tp = tp
    
    def run(self):
        """Place order in background thread."""
        try:
            order = self.broker.place_order(
                symbol=self.symbol,
                order_type=self.order_type,
                volume=self.volume,
                price=self.price,
                sl=self.sl,
                tp=self.tp
            )
            
            if order:
                self.order_placed.emit(order)
            else:
                self.order_failed.emit("Order placement failed")
                
        except Exception as e:
            logger.error(f"Order placement worker error: {e}")
            self.order_failed.emit(str(e))


class HistoricalDataWorker(QThread):
    """Background worker for fetching historical data."""
    
    # Signals
    data_received = pyqtSignal(list)   # List of OHLCData
    error_occurred = pyqtSignal(str)   # Error message
    
    def __init__(self, broker, symbol, timeframe, start_time, end_time):
        super().__init__()
        self.broker = broker
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.end_time = end_time
    
    def run(self):
        """Fetch data in background."""
        try:
            data = self.broker.get_historical_data(
                self.symbol,
                self.timeframe,
                self.start_time,
                self.end_time
            )
            
            if data:
                self.data_received.emit(data)
            else:
                self.error_occurred.emit(f"No data received for {self.symbol}")
                
        except Exception as e:
            logger.error(f"Historical data worker error: {e}")
            self.error_occurred.emit(str(e))


class OrderBookWorker(QThread):
    """Background worker for fetching order book."""
    
    # Signals
    data_received = pyqtSignal(list)   # List of Order objects
    error_occurred = pyqtSignal(str)   # Error message
    
    def __init__(self, broker):
        super().__init__()
        self.broker = broker
    
    def run(self):
        """Fetch order book in background."""
        try:
            orders = self.broker.get_order_book()
            self.data_received.emit(orders)
        except Exception as e:
            logger.error(f"Order book worker error: {e}")
            self.error_occurred.emit(str(e))
