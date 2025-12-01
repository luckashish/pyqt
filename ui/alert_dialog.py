"""
Alert Dialog for creating price alerts
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QDoubleSpinBox, QComboBox, QPushButton, QCheckBox
)
from PyQt5.QtCore import Qt


class AlertDialog(QDialog):
    """Dialog for creating price alerts."""
    
    def __init__(self, symbol: str, current_price: float, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.current_price = current_price
        self.setWindowTitle(f"Create Alert - {symbol}")
        self.setMinimumWidth(400)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Symbol and current price info
        info_label = QLabel(f"Symbol: {self.symbol}  |  Current Price: {self.current_price:.2f}")
        info_label.setStyleSheet("font-weight: bold; padding: 10px; background: #2d2d2d;")
        layout.addWidget(info_label)
        
        # Price input
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Alert Price:"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 999999.99)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(self.current_price)
        self.price_spin.setMinimumWidth(150)
        price_layout.addWidget(self.price_spin)
        price_layout.addStretch()
        layout.addLayout(price_layout)
        
        # Condition
        condition_layout = QHBoxLayout()
        condition_layout.addWidget(QLabel("Condition:"))
        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["Above", "Below"])
        self.condition_combo.setMinimumWidth(150)
        # Auto-select based on current price
        if self.current_price > 0:
            self.condition_combo.setCurrentText("Above")
        condition_layout.addWidget(self.condition_combo)
        condition_layout.addStretch()
        layout.addLayout(condition_layout)
        
        # Notification type
        notif_layout = QHBoxLayout()
        notif_layout.addWidget(QLabel("Notification:"))
        self.notif_combo = QComboBox()
        self.notif_combo.addItems(["Both", "Visual Only", "Audio Only"])
        self.notif_combo.setMinimumWidth(150)
        notif_layout.addWidget(self.notif_combo)
        notif_layout.addStretch()
        layout.addLayout(notif_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        create_btn = QPushButton("Create Alert")
        create_btn.setDefault(True)
        create_btn.clicked.connect(self.accept)
        create_btn.setStyleSheet("background-color: #4caf50; font-weight: bold;")
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
    def get_alert_data(self):
        """Return alert configuration as dict."""
        notif_map = {
            "Both": "both",
            "Visual Only": "visual",
            "Audio Only": "audio"
        }
        
        return {
            "price": self.price_spin.value(),
            "condition": self.condition_combo.currentText().lower(),
            "notification_type": notif_map[self.notif_combo.currentText()]
        }
