from PyQt5.QtCore import QTimer
from utils.logger import logger
from utils.worker_threads import BrokerConnectionWorker
from core.event_bus import event_bus
from core.ea_manager import ea_manager

class ConnectionManager:
    """
    Manages broker connection and related events.
    """
    def __init__(self, main_window, broker):
        self.main_window = main_window
        self.broker = broker
        self.connection_worker = None
        self.time_timer = None

    def connect_broker(self):
        """Connect to broker asynchronously."""
        try:
            logger.info("=== connect_broker called ===")
            
            # Connect event handlers
            # Note: These handlers are in MainWindow, so we connect them there
            # or we delegate them. 
            # In main.py:
            # event_bus.tick_received.connect(self._on_tick_received)
            # event_bus.order_placed.connect(self._on_order_placed)
            # event_bus.order_closed.connect(self._on_order_closed)
            # event_bus.account_updated.connect(self._on_account_updated)
            
            # We should probably keep these connections in MainWindow or move the handlers here?
            # The handlers update UI components (MarketWatch, Terminal).
            # So MainWindow is the right place for the handlers, or we pass the UI components to ConnectionManager.
            # But ConnectionManager shouldn't know about UI details if possible.
            # Let's assume MainWindow sets up the event bus connections for UI updates separately, 
            # or we do it here if we have access to main_window methods.
            
            event_bus.tick_received.connect(self.main_window._on_tick_received)
            event_bus.order_placed.connect(self.main_window._on_order_placed)
            event_bus.order_closed.connect(self.main_window._on_order_closed)
            event_bus.account_updated.connect(self.main_window._on_account_updated)
            
            logger.info("About to connect candle_updated to EA Manager...")
            
            # Connect bar close events to EA Manager (CRITICAL for Breakout EAs!)
            event_bus.candle_updated.connect(lambda symbol, bar: ea_manager.on_bar(symbol, bar))
            logger.info("[OK] Connected candle_updated to EA Manager for bar-based strategies")
            
            # Create worker thread for connection
            self.connection_worker = BrokerConnectionWorker(
                self.broker, "Demo Server", "demo_user", "password"
            )
            
            # Connect worker signals
            self.connection_worker.progress_update.connect(self._on_connection_progress)
            self.connection_worker.connection_success.connect(self._on_connection_success)
            self.connection_worker.connection_failed.connect(self._on_connection_failed)
            
            # Start connection in background
            self.connection_worker.start()
            
        except Exception as e:
            logger.error(f"!!! ERROR in connect_broker: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _on_connection_progress(self, message):
        """Handle connection progress updates."""
        logger.info(message)
        if self.main_window.ui.status_bar:
            self.main_window.ui.status_bar.showMessage(message)

    def _on_connection_success(self, username):
        """Handle successful connection."""
        logger.info("Connected to broker")
        if self.main_window.ui.status_bar:
            self.main_window.ui.status_bar.showMessage(f"Connected as {username}", 5000)
        if self.main_window.ui.connection_label:
            self.main_window.ui.connection_label.setText(f"Connected: {username}")
            self.main_window.ui.connection_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        
        # Subscribe to default symbols for testing
        test_symbols = ["MCX|463007", "NSE|22"] # NATURALGAS ACC, Nifty 50, Bank Nifty, Reliance
        self.broker.subscribe(test_symbols)
        
        # Setup autocomplete for Market Watch
        if hasattr(self.broker, 'symbol_manager'):
            self.broker.symbol_manager.download_symbol_masters()
            all_symbols = self.broker.symbol_manager.get_all_symbols()
            if self.main_window.ui.market_watch:
                self.main_window.ui.market_watch.set_search_completer(all_symbols)
            logger.info(f"Loaded {len(all_symbols)} symbols for autocomplete")
        
        # Initialize EA system
        self.main_window._init_ea_system()
        
        # Start time timer
        self.setup_timers()

    def _on_connection_failed(self, error):
        """Handle connection failure."""
        logger.error(f"Failed to connect to broker: {error}")
        if self.main_window.ui.status_bar:
            self.main_window.ui.status_bar.showMessage(f"Connection failed: {error}")
        if self.main_window.ui.connection_label:
            self.main_window.ui.connection_label.setText("Connection Failed")

    def setup_timers(self):
        """Setup update timers."""
        # Time update timer
        self.time_timer = QTimer(self.main_window)
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)

    def _update_time(self):
        """Update status bar time."""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        if self.main_window.ui.time_label:
            self.main_window.ui.time_label.setText(current_time)

    def disconnect(self):
        """Disconnect broker."""
        if self.broker:
            self.broker.disconnect()
