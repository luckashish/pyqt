from PyQt5.QtWidgets import (
    QDockWidget, QTabWidget, QTableWidget, QTableWidgetItem, 
    QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStatusBar,
    QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from utils.worker_threads import OrderBookWorker, PositionBookWorker
from datetime import datetime

class Terminal(QDockWidget):
    """Terminal dock widget."""
    
    def __init__(self, broker, parent=None):
        super().__init__("Terminal", parent)
        self.broker = broker
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI components."""
        # Create container widget
        terminal_widget = QWidget()
        terminal_layout = QVBoxLayout(terminal_widget)
        terminal_layout.setContentsMargins(0, 0, 0, 0)
        
        # Account info bar
        self.account_info_bar = self._create_account_info_bar()
        terminal_layout.addWidget(self.account_info_bar)
        
        # Create tab widget for terminal tabs
        self.terminal_tabs = QTabWidget()
        self.terminal_tabs.currentChanged.connect(self._on_tab_changed)
        
        # Trade tab
        self.trade_table = QTableWidget(0, 9)
        self.trade_table.setHorizontalHeaderLabels([
            "Symbol", "Ticket", "Time", "Type", "Volume", "Price", "S/L", "T/P", "Profit"
        ])
        self.trade_table.horizontalHeader().setStretchLastSection(True)
        self.trade_table.setAlternatingRowColors(True)
        self.terminal_tabs.addTab(self.trade_table, "Trade")
        
        # News tab
        news_widget = QLabel("Market News Feed\n\nFed Holds Interest Rates Steady - Reuters\nECB Signals Potential Rate Cut - Bloomberg\n...")
        news_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        news_widget.setWordWrap(True)
        self.terminal_tabs.addTab(news_widget, "News")
        
        # Calendar tab
        calendar_widget = QLabel("Economic Calendar\n\n2025-11-30 14:30 USD Non-Farm Payrolls (High Impact)\n...")
        calendar_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        calendar_widget.setWordWrap(True)
        self.terminal_tabs.addTab(calendar_widget, "Calendar")
        
        # Alerts tab
        alerts_widget = QLabel("Price Alerts\n\nNo active alerts")
        alerts_widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.terminal_tabs.addTab(alerts_widget, "Alerts")
        
        # Journal tab
        self.journal_widget = QTextEdit()
        self.journal_widget.setReadOnly(True)
        self.journal_widget.setStyleSheet("font-family: monospace; background-color: #1e1e1e; color: #d4d4d4;")
        self.journal_widget.append(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Application started")
        self.journal_widget.append(f"[{datetime.now().strftime('%H:%M:%S')}] [INFO] Connected to Demo Server")
        self.terminal_tabs.addTab(self.journal_widget, "Journal")
        
        # Order Book tab
        self.order_book_tab = self._create_order_book_tab()
        self.terminal_tabs.addTab(self.order_book_tab, "Order Book")
        
        # Position Book tab
        self.position_book_tab = self._create_position_book_tab()
        self.terminal_tabs.addTab(self.position_book_tab, "Position Book")
        
        terminal_layout.addWidget(self.terminal_tabs)
        self.setWidget(terminal_widget)
        
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
        
    def _create_order_book_tab(self):
        """Create Order Book tab widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.refresh_order_book)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Table
        self.order_book_table = QTableWidget(0, 11)
        self.order_book_table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Status", "Volume", "Price", 
            "Trigger", "Time", "Rejection Reason", "Comment", "Exchange ID"
        ])
        self.order_book_table.horizontalHeader().setStretchLastSection(True)
        self.order_book_table.setAlternatingRowColors(True)
        self.order_book_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.order_book_table)
        
        return widget
        
    def _on_tab_changed(self, index):
        """Handle terminal tab change."""
        tab_text = self.terminal_tabs.tabText(index)
        if tab_text == "Order Book":
            self.refresh_order_book()
        elif tab_text == "Position Book":
            self.refresh_position_book()
            
    def refresh_order_book(self):
        """Refresh order book data."""
        if not hasattr(self, 'order_book_worker'):
            self.order_book_worker = OrderBookWorker(self.broker)
            self.order_book_worker.data_received.connect(self._update_order_book_table)
            # Note: Error handling via status bar needs parent access or signal
            # For now, we'll just print to console/log
        
        if not self.order_book_worker.isRunning():
            self.order_book_worker.start()
            
    def _update_order_book_table(self, orders):
        """Update Order Book table with data."""
        self.order_book_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            # Ticket
            self.order_book_table.setItem(row, 0, QTableWidgetItem(str(order.ticket)))
            
            # Symbol
            self.order_book_table.setItem(row, 1, QTableWidgetItem(order.symbol))
            
            # Type
            type_item = QTableWidgetItem(order.order_type.value)
            if "buy" in order.order_type.value.lower():
                type_item.setForeground(QColor("#4caf50"))
            else:
                type_item.setForeground(QColor("#f44336"))
            self.order_book_table.setItem(row, 2, type_item)
            
            # Status
            status_item = QTableWidgetItem(order.status.value.upper())
            if order.status.value == "active":
                status_item.setForeground(QColor("#2196f3"))
            elif order.status.value == "filled":
                status_item.setForeground(QColor("#4caf50"))
            elif order.status.value == "rejected":
                status_item.setForeground(QColor("#f44336"))
            self.order_book_table.setItem(row, 3, status_item)
            
            # Volume
            self.order_book_table.setItem(row, 4, QTableWidgetItem(str(order.volume)))
            
            # Price
            self.order_book_table.setItem(row, 5, QTableWidgetItem(f"{order.open_price:.2f}"))
            
            # Trigger Price (placeholder)
            self.order_book_table.setItem(row, 6, QTableWidgetItem(""))
            
            # Time
            time_str = order.open_time.strftime("%H:%M:%S") if order.open_time else ""
            self.order_book_table.setItem(row, 7, QTableWidgetItem(time_str))
            
            # Rejection Reason
            self.order_book_table.setItem(row, 8, QTableWidgetItem(order.rejection_reason))
            
            # Comment
            self.order_book_table.setItem(row, 9, QTableWidgetItem(order.comment))
            
            # Exchange ID (placeholder)
            self.order_book_table.setItem(row, 10, QTableWidgetItem(""))
            
    def update_trade_table(self):
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
            

    def update_account_info(self, account_info: dict):
        """Update account info bar."""
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

    def log_message(self, message: str):
        """Log a message to the Journal tab."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.journal_widget.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        cursor = self.journal_widget.textCursor()
        cursor.movePosition(cursor.End)
        self.journal_widget.setTextCursor(cursor)

    def _create_position_book_tab(self):
        """Create Position Book tab widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_btn.clicked.connect(self.refresh_position_book)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Table
        self.position_book_table = QTableWidget(0, 12)
        self.position_book_table.setHorizontalHeaderLabels([
            "Symbol", "Net Qty", "Avg Price", "LTP", "P&L", "M2M", 
            "Day Buy Qty", "Day Sell Qty", "Product", "CF Sell Qty", "Day Buy Amt", "Day Sell Amt"
        ])
        self.position_book_table.horizontalHeader().setStretchLastSection(True)
        self.position_book_table.setAlternatingRowColors(True)
        self.position_book_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.position_book_table)
        
        return widget

    def refresh_position_book(self):
        """Refresh position book data."""
        if not hasattr(self, 'position_book_worker'):
            self.position_book_worker = PositionBookWorker(self.broker)
            self.position_book_worker.data_received.connect(self._update_position_book_table)
        
        if not self.position_book_worker.isRunning():
            self.position_book_worker.start()

    def _update_position_book_table(self, positions):
        """Update Position Book table with data."""
        self.position_book_table.setRowCount(len(positions))
        
        for row, pos in enumerate(positions):
            # Symbol
            self.position_book_table.setItem(row, 0, QTableWidgetItem(pos.get('tsym', '')))
            
            # Net Qty
            net_qty = pos.get('netqty', '0')
            qty_item = QTableWidgetItem(net_qty)
            if int(net_qty) > 0:
                qty_item.setForeground(QColor("#4caf50"))
            elif int(net_qty) < 0:
                qty_item.setForeground(QColor("#f44336"))
            self.position_book_table.setItem(row, 1, qty_item)
            
            # Avg Price
            self.position_book_table.setItem(row, 2, QTableWidgetItem(pos.get('netavgprc', '0.00')))
            
            # LTP
            self.position_book_table.setItem(row, 3, QTableWidgetItem(pos.get('lp', '0.00')))
            
            # P&L (Realized)
            rpnl = float(pos.get('rpnl', '0.00'))
            pnl_item = QTableWidgetItem(f"{rpnl:.2f}")
            pnl_item.setForeground(QColor("#4caf50") if rpnl >= 0 else QColor("#f44336"))
            self.position_book_table.setItem(row, 4, pnl_item)
            
            # M2M (Unrealized)
            urmtom = float(pos.get('urmtom', '0.00'))
            m2m_item = QTableWidgetItem(f"{urmtom:.2f}")
            m2m_item.setForeground(QColor("#4caf50") if urmtom >= 0 else QColor("#f44336"))
            self.position_book_table.setItem(row, 5, m2m_item)
            
            # Day Stats
            self.position_book_table.setItem(row, 6, QTableWidgetItem(pos.get('daybuyqty', '0')))
            self.position_book_table.setItem(row, 7, QTableWidgetItem(pos.get('daysellqty', '0')))
            
            # Product Name
            self.position_book_table.setItem(row, 8, QTableWidgetItem(pos.get('prd', '0')))
            self.position_book_table.setItem(row, 9, QTableWidgetItem(pos.get('cfsellqty', '0')))

            #Day Amt
            self.position_book_table.setItem(row, 10, QTableWidgetItem(pos.get('daybuyamt', '0.00')))
            self.position_book_table.setItem(row, 11, QTableWidgetItem(pos.get('daysellamt', '0.00')))