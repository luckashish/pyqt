from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTabWidget, QWidget, QRadioButton, QButtonGroup,
    QFrame, QMessageBox, QComboBox, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

class OrderDialog(QDialog):
    """
    Advanced Order Dialog for placing Buy/Sell orders.
    Supports Market, Limit, SL-M, SL-L orders.
    """
    
    order_placed = pyqtSignal(dict)  # Signal emitted when order is placed
    
    def __init__(self, symbol, price=0.0, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.current_price = price
        self.setWindowTitle(f"Place Order - {symbol}")
        self.setFixedWidth(450)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QRadioButton { color: #e0e0e0; }
            QRadioButton:checked { color: #e0e0e0; }
            QLineEdit, QSpinBox, QDoubleSpinBox { 
                padding: 8px; 
                border: 1px solid #3d3d3d; 
                border-radius: 4px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QPushButton {
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                background-color: #3d3d3d;
                color: #e0e0e0;
                border: 1px solid #4d4d4d;
            }
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                background: #2d2d2d;
                color: #a0a0a0;
                padding: 8px 16px;
                margin-right: 4px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3d3d3d;
                color: #e0e0e0;
                font-weight: bold;
                border-bottom: 2px solid #0e639c;
            }
        """)
        
        self.is_buy = True
        self.order_type = "MARKET" # MARKET, LIMIT, SL-M, SL-L
        self.product_type = "C" # C (CNC/Delivery), M (MIS/Intraday)
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 1. Header (Symbol Info)
        header_layout = QHBoxLayout()
        
        sym_label = QLabel(self.symbol)
        sym_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_layout.addWidget(sym_label)
        
        header_layout.addStretch()
        
        self.price_label = QLabel(f"₹{self.current_price:.2f}")
        self.price_label.setFont(QFont("Arial", 14, QFont.Bold))
        # self.price_label.setStyleSheet("color: #d32f2f;") # Red for down, Green for up
        header_layout.addWidget(self.price_label)
        
        layout.addLayout(header_layout)
        
        # 2. Product Type Tabs (Intraday vs Delivery)
        self.product_tabs = QTabWidget()
        self.product_tabs.addTab(QWidget(), "Intraday (MIS)")
        self.product_tabs.addTab(QWidget(), "Longterm (CNC)")
        self.product_tabs.currentChanged.connect(self._on_product_changed)
        layout.addWidget(self.product_tabs)
        
        # 3. Order Type Tabs (Market, Limit, etc.)
        # We'll use a custom segment control style layout for this
        type_layout = QHBoxLayout()
        type_layout.setSpacing(0)
        
        self.btn_market = self._create_type_btn("Market", True)
        self.btn_limit = self._create_type_btn("Limit")
        self.btn_sl = self._create_type_btn("SL")
        self.btn_slm = self._create_type_btn("SL-M")
        
        type_layout.addWidget(self.btn_market)
        type_layout.addWidget(self.btn_limit)
        type_layout.addWidget(self.btn_sl)
        type_layout.addWidget(self.btn_slm)
        type_layout.addStretch()
        
        # Buy/Sell Toggle
        self.toggle_layout = QHBoxLayout()
        self.toggle_buy = QRadioButton("Buy")
        self.toggle_sell = QRadioButton("Sell")
        self.toggle_buy.setChecked(True)
        self.toggle_buy.toggled.connect(self._update_colors)
        
        self.toggle_layout.addWidget(QLabel("Side:"))
        self.toggle_layout.addWidget(self.toggle_buy)
        self.toggle_layout.addWidget(self.toggle_sell)
        
        type_layout.addLayout(self.toggle_layout)
        layout.addLayout(type_layout)
        
        # 4. Inputs (Qty, Price, Trigger)
        input_layout = QHBoxLayout()
        
        # Qty
        qty_layout = QVBoxLayout()
        qty_layout.addWidget(QLabel("Quantity"))
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 100000)
        self.qty_spin.setValue(1)
        qty_layout.addWidget(self.qty_spin)
        input_layout.addLayout(qty_layout)
        
        # Price
        price_layout = QVBoxLayout()
        price_layout.addWidget(QLabel("Price"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.05, 1000000.0)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(self.current_price)
        self.price_spin.setEnabled(False) # Disabled for Market
        price_layout.addWidget(self.price_spin)
        input_layout.addLayout(price_layout)
        
        # Trigger Price
        trig_layout = QVBoxLayout()
        trig_layout.addWidget(QLabel("Trigger Price"))
        self.trig_spin = QDoubleSpinBox()
        self.trig_spin.setRange(0.05, 1000000.0)
        self.trig_spin.setDecimals(2)
        self.trig_spin.setValue(0.0)
        self.trig_spin.setEnabled(False)
        trig_layout.addWidget(self.trig_spin)
        input_layout.addLayout(trig_layout)
        
        layout.addLayout(input_layout)
        
        # 5. Action Button
        self.action_btn = QPushButton("Instant Buy")
        self.action_btn.setFixedHeight(45)
        self.action_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.clicked.connect(self._on_place_order)
        layout.addWidget(self.action_btn)
        
        # 6. Footer (Margin)
        footer_layout = QHBoxLayout()
        self.margin_label = QLabel("Margin Required: ₹0.00")
        footer_layout.addWidget(self.margin_label)
        footer_layout.addStretch()
        layout.addLayout(footer_layout)
        
        self._update_colors()
        
    def _create_type_btn(self, text, checked=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.clicked.connect(lambda: self._on_type_changed(btn))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: none;
                padding: 5px 15px;
                color: #a0a0a0;
            }
            QPushButton:checked {
                background-color: #3d3d3d;
                color: #e0e0e0;
                border-bottom: 2px solid #2196f3;
            }
        """)
        return btn
        
    def _on_product_changed(self, index):
        if index == 0:
            self.product_type = "I" # MIS/Intraday
        else:
            self.product_type = "C" # CNC/Delivery
            
    def _on_type_changed(self, active_btn):
        # Uncheck others
        for btn in [self.btn_market, self.btn_limit, self.btn_sl, self.btn_slm]:
            if btn != active_btn:
                btn.setChecked(False)
        
        active_btn.setChecked(True)
        text = active_btn.text()
        
        if text == "Market":
            self.order_type = "MARKET"
            self.price_spin.setEnabled(False)
            self.trig_spin.setEnabled(False)
        elif text == "Limit":
            self.order_type = "LIMIT"
            self.price_spin.setEnabled(True)
            self.trig_spin.setEnabled(False)
        elif text == "SL":
            self.order_type = "SL-L"
            self.price_spin.setEnabled(True)
            self.trig_spin.setEnabled(True)
        elif text == "SL-M":
            self.order_type = "SL-M"
            self.price_spin.setEnabled(False)
            self.trig_spin.setEnabled(True)
            
    def _update_colors(self):
        self.is_buy = self.toggle_buy.isChecked()
        
        if self.is_buy:
            color = "#4caf50" # Green
            text = "Instant Buy"
        else:
            color = "#f44336" # Red
            text = "Instant Sell"
            
        self.action_btn.setText(text)
        self.action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {QColor(color).lighter(110).name()};
            }}
        """)
        
    def _on_place_order(self):
        # Gather data
        qty = self.qty_spin.value()
        price = self.price_spin.value()
        trigger = self.trig_spin.value()
        
        order_data = {
            "symbol": self.symbol,
            "side": "BUY" if self.is_buy else "SELL",
            "product_type": self.product_type,
            "order_type": self.order_type,
            "quantity": qty,
            "price": price if self.order_type != "MARKET" else 0,
            "trigger_price": trigger if "SL" in self.order_type else 0
        }
        
        self.order_placed.emit(order_data)
        self.accept()
