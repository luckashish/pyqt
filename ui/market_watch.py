from PyQt5.QtWidgets import (
    QDockWidget, QTabWidget, QTableWidget, QTableWidgetItem, 
    QLabel, QWidget, QVBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor

class MarketWatch(QDockWidget):
    """Market Watch dock widget."""
    
    # Signals
    symbol_double_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__("Market Watch", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI components."""
        # Create tab widget for Market Watch tabs
        self.tabs = QTabWidget()
        
        # Symbols tab
        self.symbols_table = QTableWidget(0, 3)
        self.symbols_table.setHorizontalHeaderLabels(["Symbol", "Bid", "Ask"])
        self.symbols_table.horizontalHeader().setStretchLastSection(True)
        self.symbols_table.setAlternatingRowColors(True)
        self.symbols_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.symbols_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.symbols_table.doubleClicked.connect(self._on_table_double_click)
        
        self.tabs.addTab(self.symbols_table, "Symbols")
        self.tabs.addTab(QLabel("Details view"), "Details")
        self.tabs.addTab(QLabel("Trading view"), "Trading")
        self.tabs.addTab(QLabel("Ticks view"), "Ticks")
        
        self.setWidget(self.tabs)
        
    def _on_table_double_click(self, index):
        """Handle double click on symbol table."""
        row = index.row()
        symbol_item = self.symbols_table.item(row, 0)
        if symbol_item:
            # Extract symbol name (remove the "● " prefix)
            symbol_text = symbol_item.text()
            symbol_name = symbol_text.replace("● ", "")
            self.symbol_double_clicked.emit(symbol_name)
            
    def update_quotes(self, quotes: list):
        """Update quotes in the table."""
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
