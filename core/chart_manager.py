import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from utils.logger import logger
from utils.worker_threads import HistoricalDataWorker
from ui.charts.chart_widget import ChartWidget
from data.models import OrderType

class ChartManager:
    """
    Manages chart tabs, data fetching, and chart interactions.
    """
    def __init__(self, main_window, broker):
        self.main_window = main_window
        self.broker = broker
        self.charts = {}
        self.active_workers = []

    def create_default_charts(self):
        """Create default charts on startup."""
        for symbol in ["EURUSD.H1", "GBPUSD.H1", "USDJPY.H1", "USDCHF.H1", "SBIN-EQ"]:
            chart_widget = self._create_chart_widget(symbol)
            self.main_window.ui.chart_tabs.addTab(chart_widget, symbol)

    def _create_chart_widget(self, symbol_timeframe: str):
        """Create a single chart widget."""
        # Create chart widget
        symbol = symbol_timeframe.split('.')[0]
        chart = ChartWidget(symbol)
        
        # Store reference to update later
        self.charts[symbol] = chart
        
        # Connect alert signal
        chart.alert_triggered.connect(self.main_window._on_alert_triggered)
        
        # Add one-click trading panel overlay or side widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add chart
        layout.addWidget(chart)
        
        # Overlay trading panel (simplified as side widget for now)
        # In a real implementation, this might be an overlay
        # For now, we are not adding it to the layout to keep it clean, 
        # or we could add it if requested. The original code called _create_one_click_trading
        # but didn't add it to the layout in the final version shown in the file view?
        # Re-checking the file view...
        # Line 265: trading_panel = self._create_one_click_trading(symbol)
        # Line 270: return container
        # It seems it wasn't added to the layout in the original code either!
        # I will keep it consistent.
        
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
        buy_btn.clicked.connect(lambda: self.main_window._place_market_order(symbol, "BUY"))
        layout.addWidget(buy_btn)
        
        # Sell button with price
        sell_btn = QPushButton("SELL\n1.09565")
        sell_btn.setObjectName("sellButton")
        sell_btn.setMinimumHeight(50)
        sell_btn.clicked.connect(lambda: self.main_window._place_market_order(symbol, "SELL"))
        layout.addWidget(sell_btn)
        
        # Lot size selector
        lot_label = QLabel("Lot Size: 0.1")
        lot_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(lot_label)
        
        return panel

    def fetch_chart_data(self, symbol_name, timeframe="M5"):
        """
        Fetch chart data for a symbol.
        """
        try:
            logger.info(f"Opening chart for {symbol_name} ({timeframe})")
            
            # 1. Check if tab already exists
            tab_index = -1
            chart_tabs = self.main_window.ui.chart_tabs
            for i in range(chart_tabs.count()):
                if chart_tabs.tabText(i) == symbol_name:
                    tab_index = i
                    break
            
            # 2. Open or focus chart tab
            if tab_index != -1:
                # Tab exists, switch to it
                chart_tabs.setCurrentIndex(tab_index)
            else:
                # Tab does not exist, create it
                chart_container = self._create_chart_widget(f"{symbol_name}.{timeframe}")
                chart_tabs.addTab(chart_container, symbol_name)
                chart_tabs.setCurrentIndex(chart_tabs.count() - 1)
            
            # 3. Fetch data
            logger.info(f"Requesting chart data for {symbol_name} {timeframe}")
            
            # Example: Fetch last 7 days of data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
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
            if symbol_name in self.charts:
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
            logger.error(f"Error in fetch_chart_data: {e}", exc_info=True)
            self.main_window.ui.status_bar.showMessage(f"Error opening chart: {e}")

    def change_timeframe(self, timeframe: str):
        """
        Change timeframe for the currently active chart.
        """
        try:
            chart_tabs = self.main_window.ui.chart_tabs
            # Get current tab index
            current_index = chart_tabs.currentIndex()
            if current_index == -1:
                return
                
            # Get symbol from tab text
            symbol_name = chart_tabs.tabText(current_index)
            
            logger.info(f"Changing timeframe for {symbol_name} to {timeframe}")
            
            # Update chart widget timeframe
            if symbol_name in self.charts:
                chart_widget = self.charts[symbol_name]
                chart_widget.timeframe = timeframe
                
                # Refresh data
                self.fetch_chart_data(symbol_name, timeframe)
                
        except Exception as e:
            logger.error(f"Error changing timeframe: {e}")
            self.main_window.ui.status_bar.showMessage(f"Error changing timeframe: {e}")

    def on_tab_close(self, index):
        """Handle tab close request."""
        chart_tabs = self.main_window.ui.chart_tabs
        tab_text = chart_tabs.tabText(index)
        logger.info(f"Closing tab: {tab_text}")
        
        # Remove from charts dict
        if tab_text in self.charts:
            del self.charts[tab_text]
            
        chart_tabs.removeTab(index)

    def update_tick(self, symbol):
        """Update charts with new tick data."""
        # logger.info(f"ChartManager received tick for {symbol.name}: {symbol.last}")
        
        # Check if we have any charts for this symbol
        if symbol.name in self.charts:
            # logger.info(f"Updating chart for {symbol.name} with price {symbol.last}")
            self.charts[symbol.name].update_tick(symbol)
        else:
            # logger.debug(f"No chart found for {symbol.name}. Active charts: {list(self.charts.keys())}")
            pass
