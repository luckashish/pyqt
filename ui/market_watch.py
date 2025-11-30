from PyQt5.QtWidgets import (
    QDockWidget, QTabWidget, QTableWidget, QTableWidgetItem, 
    QLabel, QWidget, QVBoxLayout, QCompleter, QStyledItemDelegate, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QStringListModel
from PyQt5.QtGui import QColor

class SymbolDelegate(QStyledItemDelegate):
    """Delegate to handle autocomplete in the table."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None

    def setCompleter(self, completer):
        self.completer = completer

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if self.completer:
            editor.setCompleter(self.completer)
        return editor

class MarketWatch(QDockWidget):
    """Market Watch dock widget."""
    
    # Signals
    symbol_double_clicked = pyqtSignal(str)
    symbol_added = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__("Market Watch", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.row_map = {} # Symbol name -> Row index
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
        
        # Allow editing for the "add" row
        self.symbols_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed | QTableWidget.AnyKeyPressed)
        
        self.symbols_table.doubleClicked.connect(self._on_table_double_click)
        self.symbols_table.cellChanged.connect(self._on_cell_changed)
        
        # Set custom delegate for the first column (Symbol)
        self.symbol_delegate = SymbolDelegate(self.symbols_table)
        self.symbols_table.setItemDelegateForColumn(0, self.symbol_delegate)
        
        self.tabs.addTab(self.symbols_table, "Symbols")
        self.tabs.addTab(QLabel("Details view"), "Details")
        self.tabs.addTab(QLabel("Trading view"), "Trading")
        self.tabs.addTab(QLabel("Ticks view"), "Ticks")
        
        self.setWidget(self.tabs)
        
        # Initialize with just the "add" row
        self._ensure_add_row()
        
    def set_search_completer(self, symbols: list):
        """Set the list of symbols for autocomplete."""
        completer = QCompleter(symbols, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.symbol_delegate.setCompleter(completer)
        
    def _ensure_add_row(self):
        """Ensure the 'click to add' row exists at the bottom."""
        row_count = self.symbols_table.rowCount()
        
        # Check if last row is already the add row
        if row_count > 0:
            item = self.symbols_table.item(row_count - 1, 0)
            if item and item.text() == "+ Click to add...":
                return

        # Add new row
        self.symbols_table.insertRow(row_count)
        last_row = row_count
        
        add_item = QTableWidgetItem("+ Click to add...")
        add_item.setForeground(QColor("#808080"))
        add_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
        self.symbols_table.setItem(last_row, 0, add_item)
        
        # Empty items for other columns
        self.symbols_table.setItem(last_row, 1, QTableWidgetItem(""))
        self.symbols_table.setItem(last_row, 2, QTableWidgetItem(""))
        
        # Make other columns read-only
        self.symbols_table.item(last_row, 1).setFlags(Qt.NoItemFlags)
        self.symbols_table.item(last_row, 2).setFlags(Qt.NoItemFlags)

    def _on_table_double_click(self, index):
        """Handle double click on symbol table."""
        row = index.row()
        # Ignore double click on the "add" row (last row)
        if row == self.symbols_table.rowCount() - 1:
            return
            
        symbol_item = self.symbols_table.item(row, 0)
        if symbol_item:
            # Extract symbol name (remove the "● " prefix)
            symbol_text = symbol_item.text()
            symbol_name = symbol_text.replace("● ", "")
            self.symbol_double_clicked.emit(symbol_name)
            
    def _on_cell_changed(self, row, column):
        """Handle cell changes (for adding new symbols)."""
        # Check if it's the last row and first column
        if row == self.symbols_table.rowCount() - 1 and column == 0:
            item = self.symbols_table.item(row, column)
            if item and item.text().strip() and item.text() != "+ Click to add...":
                symbol = item.text().strip()
                
                # Emit signal
                self.symbol_added.emit(symbol)
                
                # Reset the item to placeholder
                self.symbols_table.blockSignals(True)
                item.setText("+ Click to add...")
                item.setForeground(QColor("#808080"))
                self.symbols_table.blockSignals(False)
                self.symbols_table.clearSelection()

    def update_tick(self, symbol):
        """Update a single symbol tick."""
        name = symbol.name
        
        # Find row
        if name in self.row_map:
            row = self.row_map[name]
        else:
            # Add new row before the "add" row
            row = self.symbols_table.rowCount() - 1
            self.symbols_table.insertRow(row)
            self.row_map[name] = row
            
            # Initialize items
            self.symbols_table.setItem(row, 0, QTableWidgetItem())
            self.symbols_table.setItem(row, 1, QTableWidgetItem())
            self.symbols_table.setItem(row, 2, QTableWidgetItem())
            
        # Update items
        # Symbol name with color indicator
        symbol_item = self.symbols_table.item(row, 0)
        symbol_item.setText(f"● {name}")
        symbol_item.setForeground(QColor("#4caf50") if symbol.trend == "up" else QColor("#f44336"))
        symbol_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        
        # Bid price
        bid_item = self.symbols_table.item(row, 1)
        bid_item.setText(f"{symbol.bid:.2f}")
        bid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bid_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        
        # Ask price
        ask_item = self.symbols_table.item(row, 2)
        ask_item.setText(f"{symbol.ask:.2f}")
        ask_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ask_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    def update_quotes(self, quotes: list):
        """Batch update quotes (legacy support)."""
        for symbol in quotes:
            self.update_tick(symbol)
