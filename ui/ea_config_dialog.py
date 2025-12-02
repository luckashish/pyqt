"""
EA Configuration Dialog.
Allows editing EA parameters, symbol, and risk settings.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QGroupBox, QMessageBox
)
from PyQt5.QtCore import Qt

from data.models import EAConfig
from utils.logger import logger


class EAConfigDialog(QDialog):
    """
    Dialog for configuring Expert Advisor parameters.
    """
    
    def __init__(self, ea_config: EAConfig, parent=None):
        super().__init__(parent)
        
        self.config = ea_config
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"Configure {self.config.name}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Basic Settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout(basic_group)
        
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("e.g., NSE|26000, NSE|22")
        basic_layout.addRow("Symbol:", self.symbol_edit)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        basic_layout.addRow("Timeframe:", self.timeframe_combo)
        
        layout.addWidget(basic_group)
        
        # Strategy Parameters
        strategy_group = QGroupBox("Strategy Parameters")
        strategy_layout = QFormLayout(strategy_group)
        
        self.fast_period_spin = QSpinBox()
        self.fast_period_spin.setRange(1, 200)
        self.fast_period_spin.setValue(10)
        strategy_layout.addRow("Fast MA Period:", self.fast_period_spin)
        
        self.slow_period_spin = QSpinBox()
        self.slow_period_spin.setRange(1, 200)
        self.slow_period_spin.setValue(20)
        strategy_layout.addRow("Slow MA Period:", self.slow_period_spin)
        
        self.ma_type_combo = QComboBox()
        self.ma_type_combo.addItems(["SMA", "EMA"])
        strategy_layout.addRow("MA Type:", self.ma_type_combo)
        
        layout.addWidget(strategy_group)
        
        # Risk Management
        risk_group = QGroupBox("Risk Management")
        risk_layout = QFormLayout(risk_group)
        
        self.lot_size_spin = QDoubleSpinBox()
        self.lot_size_spin.setRange(0.01, 100)
        self.lot_size_spin.setSingleStep(0.1)
        self.lot_size_spin.setValue(0.1)
        risk_layout.addRow("Lot Size:", self.lot_size_spin)
        
        self.risk_percent_spin = QDoubleSpinBox()
        self.risk_percent_spin.setRange(0.1, 10)
        self.risk_percent_spin.setSingleStep(0.1)
        self.risk_percent_spin.setValue(2.0)
        self.risk_percent_spin.setSuffix(" %")
        risk_layout.addRow("Risk per Trade:", self.risk_percent_spin)
        
        self.use_dynamic_sizing = QCheckBox("Use Dynamic Position Sizing")
        risk_layout.addRow("", self.use_dynamic_sizing)
        
        self.sl_pips_spin = QDoubleSpinBox()
        self.sl_pips_spin.setRange(1, 1000)
        self.sl_pips_spin.setValue(50)
        self.sl_pips_spin.setSuffix(" pips")
        risk_layout.addRow("Stop Loss:", self.sl_pips_spin)
        
        self.tp_pips_spin = QDoubleSpinBox()
        self.tp_pips_spin.setRange(1, 1000)
        self.tp_pips_spin.setValue(100)
        self.tp_pips_spin.setSuffix(" pips")
        risk_layout.addRow("Take Profit:", self.tp_pips_spin)
        
        layout.addWidget(risk_group)
        
        # Trailing Stop
        trailing_group = QGroupBox("Trailing Stop")
        trailing_layout = QFormLayout(trailing_group)
        
        self.use_trailing = QCheckBox("Enable Trailing Stop")
        trailing_layout.addRow("", self.use_trailing)
        
        self.trailing_pips_spin = QDoubleSpinBox()
        self.trailing_pips_spin.setRange(1, 500)
        self.trailing_pips_spin.setValue(30)
        self.trailing_pips_spin.setSuffix(" pips")
        trailing_layout.addRow("Trailing Distance:", self.trailing_pips_spin)
        
        layout.addWidget(trailing_group)
        
        # Filters
        filters_group = QGroupBox("Trade Filters")
        filters_layout = QFormLayout(filters_group)
        
        self.enable_time_filter = QCheckBox("Enable Time Filter")
        filters_layout.addRow("", self.enable_time_filter)
        
        self.start_hour_spin = QSpinBox()
        self.start_hour_spin.setRange(0, 23)
        self.start_hour_spin.setValue(9)
        filters_layout.addRow("Trading Start Hour:", self.start_hour_spin)
        
        self.end_hour_spin = QSpinBox()
        self.end_hour_spin.setRange(0, 23)
        self.end_hour_spin.setValue(15)
        filters_layout.addRow("Trading End Hour:", self.end_hour_spin)
        
        self.max_spread_spin = QDoubleSpinBox()
        self.max_spread_spin.setRange(0.1, 20)
        self.max_spread_spin.setSingleStep(0.1)
        self.max_spread_spin.setValue(3.0)
        self.max_spread_spin.setSuffix(" pips")
        filters_layout.addRow("Max Spread:", self.max_spread_spin)
        
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 10)
        self.max_positions_spin.setValue(1)
        filters_layout.addRow("Max Concurrent Positions:", self.max_positions_spin)
        
        layout.addWidget(filters_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def load_config(self):
        """Load current configuration into fields."""
        # Basic
        self.symbol_edit.setText(self.config.symbol)
        index = self.timeframe_combo.findText(self.config.timeframe)
        if index >= 0:
            self.timeframe_combo.setCurrentIndex(index)
        
        # Strategy
        params = self.config.parameters
        self.fast_period_spin.setValue(params.get('fast_period', 10))
        self.slow_period_spin.setValue(params.get('slow_period', 20))
        ma_type_index = self.ma_type_combo.findText(params.get('ma_type', 'SMA'))
        if ma_type_index >= 0:
            self.ma_type_combo.setCurrentIndex(ma_type_index)
        
        # Risk
        self.lot_size_spin.setValue(self.config.lot_size)
        self.risk_percent_spin.setValue(self.config.risk_percent)
        self.use_dynamic_sizing.setChecked(self.config.use_dynamic_sizing)
        self.sl_pips_spin.setValue(self.config.stop_loss_pips)
        self.tp_pips_spin.setValue(self.config.take_profit_pips)
        
        # Trailing
        self.use_trailing.setChecked(self.config.use_trailing_stop)
        self.trailing_pips_spin.setValue(self.config.trailing_stop_pips)
        
        # Filters
        self.enable_time_filter.setChecked(self.config.enable_time_filter)
        self.start_hour_spin.setValue(self.config.trading_start_hour)
        self.end_hour_spin.setValue(self.config.trading_end_hour)
        self.max_spread_spin.setValue(self.config.max_spread_pips)
        self.max_positions_spin.setValue(self.config.max_concurrent_positions)
        
    def get_config(self) -> EAConfig:
        """Get updated configuration."""
        # Update config with new values
        self.config.symbol = self.symbol_edit.text().strip()
        self.config.timeframe = self.timeframe_combo.currentText()
        
        # Strategy parameters
        self.config.parameters = {
            'fast_period': self.fast_period_spin.value(),
            'slow_period': self.slow_period_spin.value(),
            'ma_type': self.ma_type_combo.currentText()
        }
        
        # Risk
        self.config.lot_size = self.lot_size_spin.value()
        self.config.risk_percent = self.risk_percent_spin.value()
        self.config.use_dynamic_sizing = self.use_dynamic_sizing.isChecked()
        self.config.stop_loss_pips = self.sl_pips_spin.value()
        self.config.take_profit_pips = self.tp_pips_spin.value()
        
        # Trailing
        self.config.use_trailing_stop = self.use_trailing.isChecked()
        self.config.trailing_stop_pips = self.trailing_pips_spin.value()
        
        # Filters
        self.config.enable_time_filter = self.enable_time_filter.isChecked()
        self.config.trading_start_hour = self.start_hour_spin.value()
        self.config.trading_end_hour = self.end_hour_spin.value()
        self.config.max_spread_pips = self.max_spread_spin.value()
        self.config.max_concurrent_positions = self.max_positions_spin.value()
        
        return self.config
        
    def accept(self):
        """Validate and accept."""
        # Validate symbol
        symbol = self.symbol_edit.text().strip()
        if not symbol:
            QMessageBox.warning(self, "Validation Error", "Please enter a symbol.")
            return
        
        # Validate MA periods
        if self.fast_period_spin.value() >= self.slow_period_spin.value():
            QMessageBox.warning(
                self,
                "Validation Error",
                "Fast MA period must be less than Slow MA period."
            )
            return
        
        # Validate time filter
        if self.enable_time_filter.isChecked():
            if self.start_hour_spin.value() >= self.end_hour_spin.value():
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    "Start hour must be before end hour."
                )
                return
        
        super().accept()
