"""
MT5-Style Trading Platform - Main Entry Point
A comprehensive trading platform built with PyQt5
"""
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDockWidget, QTabWidget, 
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QPushButton,
    QMenuBar, QMenu,QAction, QToolBar, QStatusBar, QSplitter,
    QMessageBox
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
from utils.worker_threads import BrokerConnectionWorker, QuoteUpdateWorker


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
        self._create_market_watch()
        
        # Create Navigator dock (left, below market watch)
        self._create_navigator()
        
        # Create Terminal dock (bottom)
        self._create_terminal()
        
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
            btn.setFixedWidth(35)
            btn.setToolTip(f"Switch to {tf} timeframe")
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
    
    def _create_market_watch(self):
        """Create Market Watch dock."""
        self.market_watch_dock = QDockWidget("Market Watch", self)
        self.market_watch_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create tab widget for Market Watch tabs
        mw_tabs = QTabWidget()
        
        # Symbols tab
        self.symbols_table = QTableWidget(0, 3)
        self.symbols_table.setHorizontalHeaderLabels(["Symbol", "Bid", "Ask"])
        self.symbols_table.horizontalHeader().setStretchLastSection(True)
        self.symbols_table.setAlternatingRowColors(True)
        self.symbols_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.symbols_table.setEditTriggers(QTableWidget.NoEditTriggers)  # Disable editing
        self.symbols_table.doubleClicked.connect(self._on_symbol_double_click)
        
        mw_tabs.addTab(self.symbols_table, "Symbols")
        mw_tabs.addTab(QLabel("Details view"), "Details")
        mw_tabs.addTab(QLabel("Trading view"), "Trading")
        mw_tabs.addTab(QLabel("Ticks view"), "Ticks")
        
        self.market_watch_dock.setWidget(mw_tabs)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.market_watch_dock)
    
    def _create_navigator(self):
        """Create Navigator dock."""
        self.navigator_dock = QDockWidget("Navigator", self)
        self.navigator_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Create tree widget
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        
        # Add folders
        accounts_item = QTreeWidgetItem(tree, ["Accounts"])
        QTreeWidgetItem(accounts_item, ["Demo Account - 1000000"])
        
        indicators_item = QTreeWidgetItem(tree, ["Indicators"])
        trend_item = QTreeWidgetItem(indicators_item, ["Trend"])
        QTreeWidgetItem(trend_item, ["Moving Average"])
        QTreeWidgetItem(trend_item, ["Bollinger Bands"])
        oscillators_item = QTreeWidgetItem(indicators_item, ["Oscillators"])
        QTreeWidgetItem(oscillators_item, ["RSI"])
        QTreeWidgetItem(oscillators_item, ["MACD"])
        
        ea_item = QTreeWidgetItem(tree, ["Expert Advisors"])
        QTreeWidgetItem(ea_item, ["Sample EA"])
        
        scripts_item = QTreeWidgetItem(tree, ["Scripts"])
        QTreeWidgetItem(scripts_item, ["Close All"])
        
        examples_item = QTreeWidgetItem(tree, ["Examples"])
        
        # Expand all
        tree.expandAll()
        
        self.navigator_dock.setWidget(tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.navigator_dock)
    
    def _create_terminal(self):
        """Create Terminal dock with tabs."""
        self.terminal_dock = QDockWidget("Terminal", self)
        self.terminal_dock.setAllowedAreas(Qt.BottomDockWidgetArea)
        
        # Create container widget
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Account info bar
        self.account_info_bar = self._create_account_info_bar()
        terminal_layout.addWidget(self.account_info_bar)
        
        # Create tab widget for terminal tabs
        terminal_tabs = QTabWidget()
        
        # Trade tab
        self.trade_table = QTableWidget(0, 9)
        self.trade_table.setHorizontalHeaderLabels([
            "Symbol", "Ticket", "Time", "Type", "Volume", "Price", "S/L", "T/P", "Profit"
        ])
        self.trade_table.horizontalHeader().setStretchLastSection(True)
        self.trade_table.setAlternatingRowColors(True)
        terminal_tabs.addTab(self.trade_table, "Trade")
        
        # History tab
        self.history_table = QTableWidget(0, 10)
        self.history_table.setHorizontalHeaderLabels([
            "Symbol", "Ticket", "Time", "Type", "Volume", "Price", "S/L", "T/P", "Close Price", "Profit"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        terminal_tabs.addTab(self.history_table, "History")
        
        # News tab
        news_widget = QLabel("Market News Feed\n\nFed Holds Interest Rates Steady - Reuters\nECB Signals Potential Rate Cut - Bloomberg\n...")
        news_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        news_widget.setWordWrap(True)
        terminal_tabs.addTab(news_widget, "News")
        
        # Calendar tab
        calendar_widget = QLabel("Economic Calendar\n\n2025-11-30 14:30 USD Non-Farm Payrolls (High Impact)\n...")
        calendar_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        calendar_widget.setWordWrap(True)
        terminal_tabs.addTab(calendar_widget, "Calendar")
        
        # Alerts tab
        alerts_widget = QLabel("Price Alerts\n\nNo active alerts")
        alerts_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        terminal_tabs.addTab(alerts_widget, "Alerts")
        
        # Journal tab
        journal_widget = QLabel("System Journal\n\n[INFO] Application started\n[INFO] Connected to Demo Server\n...")
        journal_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        journal_widget.setWordWrap(True)
        journal_widget.setStyleSheet("font-family: monospace;")
        terminal_tabs.addTab(journal_widget, "Journal")
        
        terminal_layout.addWidget(terminal_tabs)
        
        self.terminal_dock.setWidget(terminal_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.terminal_dock)
    
    def _create_account_info_bar(self):
        """Create account information bar."""
        bar = QWidget()
        bar.setStyleSheet("background-color: #2d2d2d; padding: 5px;")
        bar.setMaximumHeight(35)
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 2, 10, 2)
        
        self.balance_label = QLabel("Balance: 10,000.00 USD")
        self.balance_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.balance_label)
        
        self.equity_label = QLabel("Equity: 10,000.00")
        layout.addWidget(self.equity_label)
        
        self.margin_label = QLabel("Margin: 0.00")
        layout.addWidget(self.margin_label)
        
        self.free_margin_label = QLabel("Free Margin: 10,000.00")
        layout.addWidget(self.free_margin_label)
        
        self.margin_level_label = QLabel("Margin Level: 0.00 %")
        layout.addWidget(self.margin_level_label)
        
        layout.addStretch()
        
        return bar
    
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
    
    def _on_connection_success(self, username):
        """Handle successful connection."""
        logger.info("Connected to broker")
        self.status_bar.showMessage(f"Connected as {username}", 5000)
        self.connection_label.setText(f"Connected: {username}")
        self.connection_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        
        # Start market data worker
        symbols = self.broker.get_symbols()
        self.quote_worker = QuoteUpdateWorker(self.broker, symbols)
        self.quote_worker.quotes_updated.connect(self._on_quotes_updated)
        self.quote_worker.update_failed.connect(lambda err: logger.error(f"Quote worker error: {err}"))
        self.quote_worker.start()
        
        # TEST: Auto-fetch chart data for first symbol
        if symbols:
            QTimer.singleShot(2000, lambda: self._fetch_chart_data(symbols[0]))
            QTimer.singleShot(2000, lambda: self._fetch_chart_data(symbols[1]))
            QTimer.singleShot(2000, lambda: self._fetch_chart_data(symbols[2]))
        
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
        self.symbols_table.setRowCount(len(quotes))
        
        for row, symbol in enumerate(quotes):
            # Symbol name with color indicator
            symbol_item = QTableWidgetItem(f"● {symbol.name}")
            symbol_item.setForeground(QColor("#4caf50") if symbol.trend == "up" else QColor("#f44336"))
            self.symbols_table.setItem(row, 0, symbol_item)
            
            # Bid price
            bid_item = QTableWidgetItem(f"{symbol.bid:.5f}")
            bid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.symbols_table.setItem(row, 1, bid_item)
            
            # Ask price
            ask_item = QTableWidgetItem(f"{symbol.ask:.5f}")
            ask_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.symbols_table.setItem(row, 2, ask_item)

    def _fetch_chart_data(self, symbol_name):
        """
        Fetch chart data for a symbol.
        Triggered by double click on symbol table.
        """
        from utils.worker_threads import HistoricalDataWorker
        from datetime import timedelta
        
        try:
            logger.info(f"Opening chart for {symbol_name}")
            
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
                chart_container = self._create_chart_widget(f"{symbol_name}.M5")
                self.chart_tabs.addTab(chart_container, symbol_name)
                self.chart_tabs.setCurrentIndex(self.chart_tabs.count() - 1)
            
            # 3. Fetch data
            logger.info(f"Requesting chart data for {symbol_name}")
            
            # Example: Fetch last 7 days of M5 data
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
                "M5", 
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

    def _on_tab_close(self, index):
        """Handle tab close request."""
        tab_text = self.chart_tabs.tabText(index)
        logger.info(f"Closing tab: {tab_text}")
        
        # Remove from charts dict
        if hasattr(self, 'charts') and tab_text in self.charts:
            del self.charts[tab_text]
            
        self.chart_tabs.removeTab(index)

    """@pyqtSlot(QModelIndex)
    def _on_symbol_double_click(self, index):
        """Handle symbol double click."""
        print("ashish")
        row = index.row()
        symbol_item = self.symbols_table.item(row, 0)
        if symbol_item:
            # Extract symbol name (remove the "● " prefix)
            symbol_text = symbol_item.text()
            symbol_name = symbol_text.replace("● ", "")
            
            # Fetch chart data
            self._fetch_chart_data(symbol_name)
            
            # Also show order dialog (existing functionality)
            # self._show_new_order_dialog()"""

    @pyqtSlot(Symbol)
    def _on_tick_received(self, symbol: Symbol):
        """Handle tick update."""
        # Update will happen in bulk via timer
        pass
    
    @pyqtSlot(Order)
    def _on_order_placed(self, order: Order):
        """Handle new order."""
        logger.info(f"Order placed: {order.ticket}")
        self._update_trade_table()
        self.status_bar.showMessage(f"Order {order.ticket} placed successfully", 3000)
    
    @pyqtSlot(Order)
    def _on_order_closed(self, order: Order):
        """Handle order closed."""
        logger.info(f"Order closed: {order.ticket}")
        self._update_trade_table()
        self._update_history_table()
        self.status_bar.showMessage(f"Order {order.ticket} closed", 3000)
    
    @pyqtSlot(dict)
    def _on_account_updated(self, account_info: dict):
        """Handle account info update."""
        self.balance_label.setText(f"Balance: {account_info['balance']:,.2f} USD")
        self.equity_label.setText(f"Equity: {account_info['equity']:,.2f}")
        self.margin_label.setText(f"Margin: {account_info['margin']:,.2f}")
        self.free_margin_label.setText(f"Free Margin: {account_info['free_margin']:,.2f}")
        self.margin_level_label.setText(f"Margin Level: {account_info['margin_level']:.2f} %")
        
        # Color code margin level
        if account_info['margin_level'] < 100 and account_info['margin'] > 0:
            self.margin_level_label.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.margin_level_label.setStyleSheet("")
    
    def _update_market_watch(self):
        """Update Market Watch table."""
        symbols = self.broker.get_symbols()
        self.symbols_table.setRowCount(len(symbols))
        
        for row, symbol_name in enumerate(symbols):
            symbol = self.broker.get_symbol_info(symbol_name)
            if not symbol:
                continue
            
            # Symbol name with color indicator
            symbol_item = QTableWidgetItem(f"● {symbol.name}")
            symbol_item.setForeground(QColor("#4caf50") if symbol.trend == "up" else QColor("#f44336"))
            self.symbols_table.setItem(row, 0, symbol_item)
            
            # Bid price
            bid_item = QTableWidgetItem(f"{symbol.bid:.5f}")
            bid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.symbols_table.setItem(row, 1, bid_item)
            
            # Ask price
            ask_item = QTableWidgetItem(f"{symbol.ask:.5f}")
            ask_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.symbols_table.setItem(row, 2, ask_item)
    
    def _update_trade_table(self):
        """Update Trade (open positions) table."""
        orders = self.broker.get_open_orders()
        self.trade_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            symbol_info = self.broker.get_symbol_info(order.symbol)
            current_price = symbol_info.bid if symbol_info else order.open_price
            profit = order.calculate_profit(current_price)
            
            self.trade_table.setItem(row, 0, QTableWidgetItem(order.symbol))
            self.trade_table.setItem(row, 1, QTableWidgetItem(str(order.ticket)))
            self.trade_table.setItem(row, 2, QTableWidgetItem(order.open_time.strftime("%Y.%m.%d %H:%M")))
            self.trade_table.setItem(row, 3, QTableWidgetItem(order.order_type.value))
            self.trade_table.setItem(row, 4, QTableWidgetItem(f"{order.volume:.2f}"))
            self.trade_table.setItem(row, 5, QTableWidgetItem(f"{order.open_price:.5f}"))
            self.trade_table.setItem(row, 6, QTableWidgetItem(f"{order.sl:.5f}" if order.sl > 0 else "0.00000"))
            self.trade_table.setItem(row, 7, QTableWidgetItem(f"{order.tp:.5f}" if order.tp > 0 else "0.00000"))
            
            # Profit with color
            profit_item = QTableWidgetItem(f"{profit:.2f}")
            profit_item.setForeground(QColor("#4caf50") if profit >= 0 else QColor("#f44336"))
            profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.trade_table.setItem(row, 8, profit_item)
    
    def _update_history_table(self):
        """Update History (closed trades) table."""
        orders = self.broker.get_order_history()
        self.history_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders[-50:]):  # Show last 50
            profit = order.calculate_profit(order.close_price or order.open_price)
            
            self.history_table.setItem(row, 0, QTableWidgetItem(order.symbol))
            self.history_table.setItem(row, 1, QTableWidgetItem(str(order.ticket)))
            self.history_table.setItem(row, 2, QTableWidgetItem(order.open_time.strftime("%Y.%m.%d %H:%M")))
            self.history_table.setItem(row, 3, QTableWidgetItem(order.order_type.value))
            self.history_table.setItem(row, 4, QTableWidgetItem(f"{order.volume:.2f}"))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{order.open_price:.5f}"))
            self.history_table.setItem(row, 6, QTableWidgetItem(f"{order.sl:.5f}" if order.sl > 0 else "0.00000"))
            self.history_table.setItem(row, 7, QTableWidgetItem(f"{order.tp:.5f}" if order.tp > 0 else "0.00000"))
            self.history_table.setItem(row, 8, QTableWidgetItem(f"{order.close_price:.5f}" if order.close_price else ""))
            
            # Profit with color
            profit_item = QTableWidgetItem(f"{profit:.2f}")
            profit_item.setForeground(QColor("#4caf50") if profit >= 0 else QColor("#f44336"))
            profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.history_table.setItem(row, 9, profit_item)
    
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
        """Show new order dialog."""
        QMessageBox.information(self, "New Order", "New Order dialog - to be implemented")
    
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
