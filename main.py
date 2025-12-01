"""
MT5-Style Trading Platform - Main Entry Point
A comprehensive trading platform built with PyQt5
"""
import sys
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QTabWidget, 
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QMenuBar, QMenu, QAction, 
    QToolBar, QStatusBar, QSplitter, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QModelIndex
from PyQt5.QtGui import QIcon, QColor, QFont

# Import our modules
from utils.config_manager import config
from utils.logger import logger
from core.event_bus import event_bus
from core.feed_manager import feed_manager
from brokers.factory import broker_factory
from brokers.registry import register_builtin_brokers

from data.models import Symbol, Order
from utils.worker_threads import BrokerConnectionWorker, QuoteUpdateWorker, HistoricalDataWorker

# UI Modules
from ui.market_watch import MarketWatch
from ui.navigator import Navigator
from ui.terminal import Terminal
from ui.order_dialog import OrderDialog
from ui.indicator_dialog import IndicatorDialog
from core.plugin_manager import plugin_manager


class MainWindow(QMainWindow):
    """Main application window matching MT5 layout."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT5 Trading Platform - Demo Account")
        self.setGeometry(100, 100, 1400, 900)
        
        # Load configuration FIRST
        try:
            config.load_config("config.yaml")
        except:
            logger.warning("Config file not found, using defaults")
        
        # Register brokers
        register_builtin_brokers()
        
        # Create broker instance (now config is loaded!)
        self.broker = broker_factory.create_broker()  # Uses config.yaml
        
        # Initialize UI
        self._init_ui()
        
        # Connect to broker
        self._connect_broker()
        
        # Load Plugins
        self._load_plugins()
        
        # Setup update timers
        self._setup_timers()
    
    def _init_ui(self):
        """Initialize the user interface."""
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbar
        self._create_toolbar()
        
        # Create central widget (chart area)
        self._create_chart_area()
        
        # Create Market Watch dock (left)
        self.market_watch = MarketWatch(self)
        self.market_watch.symbol_double_clicked.connect(self._fetch_chart_data)
        self.market_watch.symbol_added.connect(self._on_symbol_added)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.market_watch)
        
        # Create Navigator dock (left, below market watch)
        self._create_navigator()
        
        # Create Terminal dock (bottom)
        self.terminal = Terminal(self.broker, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal)
        
        # Create status bar
        self._create_status_bar()
        
        # Apply stylesheet
        self._apply_stylesheet()
        
        logger.info("UI initialized successfully")
    
    def _create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        new_chart_action = QAction("New Chart", self)
        file_menu.addAction(new_chart_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Market Watch")
        view_menu.addAction("Navigator")
        view_menu.addAction("Terminal")
        
        # Insert menu
        insert_menu = menubar.addMenu("Insert")
        insert_menu.addAction("Indicators")
        insert_menu.addAction("Objects")
        
        # Charts menu
        charts_menu = menubar.addMenu("Charts")
        charts_menu.addAction("Templates")
        charts_menu.addAction("Refresh")
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Options")
        tools_menu.addAction("MetaQuotes Language Editor")
        tools_menu.addSeparator()
        
        clear_cache_action = QAction("Clear Cache", self)
        clear_cache_action.setStatusTip("Clear application cache and temporary files")
        clear_cache_action.triggered.connect(self._on_clear_cache)
        tools_menu.addAction(clear_cache_action)
        
        # Window menu
        window_menu = menubar.addMenu("Window")
        window_menu.addAction("Tile Windows")
        window_menu.addAction("Cascade Windows")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Help Topics")
        help_menu.addAction("About")
    
    def _create_toolbar(self):
        """Create main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Add toolbar buttons (using text since we don't have icons)
        new_order_btn = QPushButton("New Order")
        new_order_btn.setToolTip("Open new order dialog")
        new_order_btn.clicked.connect(self._show_new_order_dialog)
        toolbar.addWidget(new_order_btn)
        
        toolbar.addSeparator()
        
        # Timeframe buttons
        for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]:
            btn = QPushButton(tf)
            btn.setFixedWidth(55)
            btn.setToolTip(f"Switch to {tf} timeframe")
            btn.clicked.connect(lambda checked, t=tf: self._change_timeframe(t))
            toolbar.addWidget(btn)
        
        toolbar.addSeparator()
        
        # Chart type buttons
        toolbar.addWidget(QPushButton("Candlestick"))
        toolbar.addWidget(QPushButton("Bar"))
        toolbar.addWidget(QPushButton("Line"))
    
    def _create_chart_area(self):
        """Create central chart area with tabs."""
        # Create tab widget for multiple charts
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setTabsClosable(True)
        self.chart_tabs.setMovable(True)
        self.chart_tabs.tabCloseRequested.connect(self._on_tab_close)
        
        # Add default charts
        for symbol in ["EURUSD.H1", "GBPUSD.H1", "USDJPY.H1", "USDCHF.H1","SBIN-EQ"]:
            chart_widget = self._create_chart_widget(symbol)
            self.chart_tabs.addTab(chart_widget, symbol)
        
        self.setCentralWidget(self.chart_tabs)
    
    def _create_chart_widget(self, symbol_timeframe: str):
        """Create a single chart widget."""
        from ui.charts.chart_widget import ChartWidget
        
        # Create chart widget
        symbol = symbol_timeframe.split('.')[0]
        chart = ChartWidget(symbol)
        
        # Store reference to update later
        if not hasattr(self, 'charts'):
            self.charts = {}
        self.charts[symbol] = chart
        
        # Add one-click trading panel overlay or side widget
        # For now, we'll wrap it in a layout to add the trading panel
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add chart
        layout.addWidget(chart)
        
        # Overlay trading panel (simplified as side widget for now)
        trading_panel = self._create_one_click_trading(symbol)
        # Note: In a real MT5 style, this would be an overlay. 
        # For now, we'll just add it to the layout or keep it separate.
        # Let's add it to the chart layout if possible or just return container
        
        return container
    
    def _create_one_click_trading(self, symbol: str):
        """Create one-click trading widget."""
        panel = QWidget()
        panel.setMaximumWidth(200)
        panel.setStyleSheet("background-color: #2d2d2d; border: 1px solid #3d3d3d; border-radius: 5px;")
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Symbol label
        symbol_label = QLabel(symbol)
        symbol_label.setAlignment(Qt.AlignCenter)
        symbol_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(symbol_label)
        
        # Buy button with price
        buy_btn = QPushButton("BUY\n1.09582")
        buy_btn.setObjectName("buyButton")
        buy_btn.setMinimumHeight(50)
        buy_btn.clicked.connect(lambda: self._place_market_order(symbol, "BUY"))
        layout.addWidget(buy_btn)
        
        # Sell button with price
        sell_btn = QPushButton("SELL\n1.09565")
        sell_btn.setObjectName("sellButton")
        sell_btn.setMinimumHeight(50)
        sell_btn.clicked.connect(lambda: self._place_market_order(symbol, "SELL"))
        layout.addWidget(sell_btn)
        
        # Lot size selector
        lot_label = QLabel("Lot Size: 0.1")
        lot_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(lot_label)
        
        return panel
    
    def _apply_stylesheet(self):
        """Apply dark theme stylesheet."""
        if os.path.exists("resources/styles.qss"):
            with open("resources/styles.qss", "r") as f:
                self.setStyleSheet(f.read())
            logger.info("Stylesheet applied")
        else:
            logger.warning("Stylesheet file not found")
    
    
    def _connect_broker(self):
        """Connect to broker asynchronously."""
        # Connect event handlers
        event_bus.tick_received.connect(self._on_tick_received)
        event_bus.order_placed.connect(self._on_order_placed)
        event_bus.order_closed.connect(self._on_order_closed)
        event_bus.account_updated.connect(self._on_account_updated)
        
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
    
    def _on_connection_progress(self, message):
        """Handle connection progress updates."""
        logger.info(message)
        self.status_bar.showMessage(message)
    
    def _on_connection_success(self, username):
        """Handle successful connection."""
        logger.info("Connected to broker")
        self.status_bar.showMessage(f"Connected as {username}", 5000)
        self.connection_label.setText(f"Connected: {username}")
        self.connection_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        
        # Start market data worker
        # symbols = self.broker.get_symbols()
        # self.quote_worker = QuoteUpdateWorker(self.broker, symbols)
        # self.quote_worker.quotes_updated.connect(self._on_quotes_updated)
        # self.quote_worker.update_failed.connect(lambda err: logger.error(f"Quote worker error: {err}"))
        # self.quote_worker.start()
        
        # Subscribe to default symbols for testing
        # In production, this would be loaded from config or last session
        test_symbols = ["MCX|463007", "NSE|22", "NSE|26000", "NSE|26009"] # NATURALGAS ACC, Nifty 50, Bank Nifty, Reliance
        self.broker.subscribe(test_symbols)
        
        # Setup autocomplete for Market Watch
        if hasattr(self.broker, 'symbol_manager'):
            # Ensure symbols are loaded (might need to download if not cached)
            # For now, we rely on what's in cache/hardcoded
            self.broker.symbol_manager.download_symbol_masters()
            all_symbols = self.broker.symbol_manager.get_all_symbols()
            self.market_watch.set_search_completer(all_symbols)
            logger.info(f"Loaded {len(all_symbols)} symbols for autocomplete")
        
        # Start time timer only (market data handled by worker)
        self._setup_timers()
    
    def _on_connection_failed(self, error):
        """Handle connection failure."""
        logger.error(f"Failed to connect to broker: {error}")
        self.status_bar.showMessage(f"Connection failed: {error}")
        self.connection_label.setText("Connection Failed")
    
    def _setup_timers(self):
        """Setup update timers."""
        # Time update timer
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self._update_time)
        self.time_timer.start(1000)

    @pyqtSlot(list)
    def _on_quotes_updated(self, quotes: list):
        """Handle batch quote updates from worker."""
        self.market_watch.update_quotes(quotes)

    def _fetch_chart_data(self, symbol_name, timeframe="M5"):
        """
        Fetch chart data for a symbol.
        Triggered by double click on symbol table or timeframe change.
        """
        try:
            logger.info(f"Opening chart for {symbol_name} ({timeframe})")
            
            # 1. Check if tab already exists
            tab_index = -1
            for i in range(self.chart_tabs.count()):
                if self.chart_tabs.tabText(i) == symbol_name:
                    tab_index = i
                    break
            
            # 2. Open or focus chart tab
            if tab_index != -1:
                # Tab exists, switch to it
                self.chart_tabs.setCurrentIndex(tab_index)
            else:
                # Tab does not exist, create it
                chart_container = self._create_chart_widget(f"{symbol_name}.{timeframe}")
                self.chart_tabs.addTab(chart_container, symbol_name)
                self.chart_tabs.setCurrentIndex(self.chart_tabs.count() - 1)
            
            # 3. Fetch data
            logger.info(f"Requesting chart data for {symbol_name} {timeframe}")
            
            # Example: Fetch last 7 days of data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            # Keep track of workers to prevent GC
            if not hasattr(self, 'active_workers'):
                self.active_workers = []
                
            # Clean up finished workers
            self.active_workers = [w for w in self.active_workers if w.isRunning()]
            
            worker = HistoricalDataWorker(
                self.broker, 
                symbol_name, 
                timeframe, 
                start_time, 
                end_time
            )
            
            # Connect signal to update specific chart
            chart_widget = self.charts[symbol_name]
            worker.data_received.connect(chart_widget.update_chart)
            
            worker.data_received.connect(
                lambda data: logger.info(f"Received {len(data)} candles for {symbol_name}")
            )
            worker.error_occurred.connect(
                lambda err: logger.error(f"Chart data error for {symbol_name}: {err}")
            )
            
            # Store worker reference
            self.active_workers.append(worker)
            worker.start()
            logger.info(f"Worker started for {symbol_name}")
            
        except Exception as e:
            logger.error(f"Error in _fetch_chart_data: {e}", exc_info=True)
            self.status_bar.showMessage(f"Error opening chart: {e}")

    def _change_timeframe(self, timeframe: str):
        """
        Change timeframe for the currently active chart.
        """
        try:
            # Get current tab index
            current_index = self.chart_tabs.currentIndex()
            if current_index == -1:
                return
                
            # Get symbol from tab text (assuming tab text is the symbol name)
            symbol_name = self.chart_tabs.tabText(current_index)
            
            logger.info(f"Changing timeframe for {symbol_name} to {timeframe}")
            
            # Update chart widget timeframe
            if hasattr(self, 'charts') and symbol_name in self.charts:
                chart_widget = self.charts[symbol_name]
                chart_widget.timeframe = timeframe
                
                # Refresh data
                self._fetch_chart_data(symbol_name, timeframe)
                
        except Exception as e:
            logger.error(f"Error changing timeframe: {e}")
            self.status_bar.showMessage(f"Error changing timeframe: {e}")

    def _on_tab_close(self, index):
        """Handle tab close request."""
        tab_text = self.chart_tabs.tabText(index)
        logger.info(f"Closing tab: {tab_text}")
        
        # Remove from charts dict
        if hasattr(self, 'charts') and tab_text in self.charts:
            del self.charts[tab_text]
            
        self.chart_tabs.removeTab(index)



    @pyqtSlot(Symbol)
    def _on_tick_received(self, symbol: Symbol):
        """Handle tick update."""
        # Update Market Watch incrementally
        self.market_watch.update_tick(symbol)
    
    @pyqtSlot(Order)
    def _on_order_placed(self, order: Order):
        """Handle new order."""
        logger.info(f"Order placed: {order.ticket}")
        self.terminal.update_trade_table()
        self.status_bar.showMessage(f"Order {order.ticket} placed successfully", 3000)
    
    @pyqtSlot(Order)
    def _on_order_closed(self, order: Order):
        """Handle order closed."""
        logger.info(f"Order closed: {order.ticket}")
        self.terminal.update_trade_table()
        self.terminal.update_history_table()
        self.status_bar.showMessage(f"Order {order.ticket} closed", 3000)
    
    @pyqtSlot(dict)
    def _on_account_updated(self, account_info: dict):
        """Handle account info update."""
        self.terminal.update_account_info(account_info)
    
    def _create_navigator(self):
        """Create Navigator dock."""
        self.navigator = Navigator(self)
        self.navigator.plugin_double_clicked.connect(self._on_plugin_double_clicked)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.navigator)

    def _load_plugins(self):
        """Load and initialize plugins."""
        plugin_manager.discover_plugins()
        # Update Navigator with loaded plugins
        self.navigator.update_plugins(plugin_manager.get_all_plugins())

    def _on_plugin_double_clicked(self, plugin_name, plugin_type):
        """Handle plugin activation from Navigator."""
        logger.info(f"Plugin activated: {plugin_name} ({plugin_type})")
        
        try:
            if plugin_type == "Indicator":
                self._apply_indicator(plugin_name)
            elif plugin_type == "Script":
                self._run_script(plugin_name)
            elif plugin_type == "Strategy":
                QMessageBox.information(self, "Strategy", f"Strategy '{plugin_name}' selected. (Not fully implemented)")
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_name}: {e}")
            QMessageBox.critical(self, "Plugin Error", f"Error executing plugin: {e}")

    def _apply_indicator(self, name):
        """Apply an indicator to the active chart."""
        # Get active chart
        current_index = self.chart_tabs.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "No Chart", "Please open a chart first.")
            return
            
        symbol = self.chart_tabs.tabText(current_index)
        if symbol not in self.charts:
            return
            
        chart_widget = self.charts[symbol]
        
        # Get indicator
        indicator = plugin_manager.get_indicator(name)
        if not indicator:
            return
            
        # Get data
        data = chart_widget.get_data()
        if data is None or data.empty:
            QMessageBox.warning(self, "No Data", "Chart has no data to calculate indicator.")
            return
            
        # Configure Indicator
        dialog = IndicatorDialog(indicator, self)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get updated indicator
        indicator = dialog.get_parameters()
        
        # Calculate
        logger.info(f"Calculating {name} for {symbol}...")
        data = indicator.calculate(data)
        
        # Plot
        indicator.plot(chart_widget, data)
        logger.info(f"Applied {name} to {symbol}")

    def _run_script(self, name):
        """Run a script."""
        script = plugin_manager.get_script(name)
        if script:
            script.run(broker=self.broker, parent=self)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.connection_label = QLabel("Not Connected")
        self.connection_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        self.time_label = QLabel("00:00:00")
        self.status_bar.addPermanentWidget(self.time_label)
        
        self.status_bar.showMessage("Ready", 3000)

    def _apply_stylesheet(self):
        """Apply dark theme stylesheet."""
        if os.path.exists("resources/styles.qss"):
            with open("resources/styles.qss", "r") as f:
                self.setStyleSheet(f.read())
            logger.info("Stylesheet applied")
        else:
            logger.warning("Stylesheet file not found")
    
    
    def _connect_broker(self):
        """Connect to broker asynchronously."""
        # Connect event handlers
        event_bus.tick_received.connect(self._on_tick_received)
        event_bus.order_placed.connect(self._on_order_placed)
        event_bus.order_closed.connect(self._on_order_closed)
        event_bus.account_updated.connect(self._on_account_updated)
        
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
    
    def _on_connection_progress(self, message):
        """Handle connection progress updates."""
        logger.info(message)
        self.status_bar.showMessage(message)

    
    def _update_time(self):
        """Update status bar time."""
        from datetime import datetime
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(current_time)
    
    def _on_symbol_double_click(self, index):
        """Handle double-click on symbol in Market Watch."""
        row = index.row()
        symbol_item = self.symbols_table.item(row, 0)
        if symbol_item:
            symbol = symbol_item.text().replace("● ", "")
            logger.info(f"Opening chart for {symbol}")
            QTimer.singleShot(1000, lambda: self._fetch_chart_data(symbol))
            # In full implementation, would open new chart tab
            
    def _on_symbol_added(self, symbol: str):
        """Handle new symbol added from Market Watch."""
        logger.info(f"Adding symbol: {symbol}")
        self.status_bar.showMessage(f"Adding symbol: {symbol}...", 3000)
        # Subscribe to the symbol
        # Note: broker.subscribe handles list, so wrap in list
        self.broker.subscribe([symbol])
    
    def _place_market_order(self, symbol: str, order_type_str: str):
        """Place a market order."""
        from data.models import OrderType
        
        order_type = OrderType.BUY if order_type_str == "BUY" else OrderType.SELL
        volume = 0.1
        
        order = self.broker.place_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            comment="One-click trading"
        )
        
        if order:
            logger.info(f"Market order placed: {order.ticket}")
        else:
            logger.error("Failed to place order")
    
    def _show_new_order_dialog(self):
        """Show the new order dialog."""
        # Get current symbol from active chart or market watch
        symbol = "NSE|26000" # Default
        price = 0.0
        
        # Try to get from active chart
        current_index = self.chart_tabs.currentIndex()
        if current_index != -1:
            symbol = self.chart_tabs.tabText(current_index)
        
        dialog = OrderDialog(symbol, price, self)
        dialog.order_placed.connect(self._place_order_from_dialog)
        dialog.exec_()
        
    def _place_order_from_dialog(self, order_data):
        """Handle order placement from dialog."""
        try:
            logger.info(f"Placing order: {order_data}")
            
            # Map string types to OrderType enum
            from data.models import OrderType
            
            side = order_data['side'] # BUY/SELL
            o_type = order_data['order_type'] # MARKET, LIMIT, SL-L, SL-M
            
            final_order_type = OrderType.BUY
            
            if side == "BUY":
                if o_type == "MARKET": final_order_type = OrderType.BUY
                elif o_type == "LIMIT": final_order_type = OrderType.BUY_LIMIT
                elif o_type in ["SL-L", "SL-M"]: final_order_type = OrderType.BUY_STOP
            else:
                if o_type == "MARKET": final_order_type = OrderType.SELL
                elif o_type == "LIMIT": final_order_type = OrderType.SELL_LIMIT
                elif o_type in ["SL-L", "SL-M"]: final_order_type = OrderType.SELL_STOP
            
            self.broker.place_order(
                symbol=order_data['symbol'],
                order_type=final_order_type,
                volume=order_data['quantity'],
                price=order_data['price'],
                trigger_price=order_data['trigger_price'],
                product_type=order_data['product_type']
            )
            
            self.status_bar.showMessage(f"Order placed for {order_data['symbol']}", 5000)
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            QMessageBox.critical(self, "Order Error", f"Failed to place order: {str(e)}")

    def _on_clear_cache(self):
        """Handle clear cache action."""
        from utils.cache_manager import clear_cache
        
        reply = QMessageBox.question(
            self, 
            "Clear Cache", 
            "Are you sure you want to clear the application cache?\n"
            "This will delete temporary files and may require a restart.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                count = clear_cache(os.getcwd())
                QMessageBox.information(
                    self, 
                    "Cache Cleared", 
                    f"Successfully cleared {count} cache items.\n"
                    "Please restart the application for changes to take full effect."
                )
                logger.info(f"User cleared cache: {count} items deleted")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear cache: {str(e)}")
                logger.error(f"Failed to clear cache: {e}")

    def closeEvent(self, event):
        """Handle application close."""
        logger.info("Application closing...")
        self.broker.disconnect()
        event.accept()


def main():
    """Application entry point."""
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("MT5 Trading Platform")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    logger.info("Application started")
    
    # Run event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
