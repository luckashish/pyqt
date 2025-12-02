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

from core.ea_base import ExpertAdvisor
from utils.logger import logger


class EAConfigDialog(QDialog):
    """
    Dialog for configuring Expert Advisor parameters.
    Dynamically creates parameter fields based on EA's config.
    """
    
    def __init__(self, ea: ExpertAdvisor, parent=None):
        super().__init__(parent)
        
        self.ea = ea
        self.param_widgets = {}
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"Configure {self.ea.config.name}")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Basic Settings
        layout.addWidget(self._create_basic_settings())
        
        # Strategy Parameters (DYNAMIC)
        layout.addWidget(self._create_strategy_params())
        
        # Risk Management
        layout.addWidget(self._create_risk_management())
        
        # Trailing Stop
        layout.addWidget(self._create_trailing_stop())
        
        # Filters
        layout.addWidget(self._create_filters())
        
        # Buttons
        layout.addLayout(self._create_buttons())
        
    def _create_basic_settings(self):
        """Create basic settings section."""
        group = QGroupBox("Basic Settings")
        layout = QFormLayout(group)
        
        self.symbol_edit = QLineEdit()
        self.symbol_edit.setText(self.ea.config.symbol)
        self.symbol_edit.setPlaceholderText("e.g., NSE|26000, MCX|463007")
        layout.addRow("Symbol:", self.symbol_edit)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1", "TICK"])
        index = self.timeframe_combo.findText(self.ea.config.timeframe)
        if index >= 0:
            self.timeframe_combo.setCurrentIndex(index)
        layout.addRow("Timeframe:", self.timeframe_combo)
        
        return group
    
    def _create_strategy_params(self):
        """Create strategy parameters section (DYNAMIC)."""
        group = QGroupBox("Strategy Parameters")
        layout = QFormLayout(group)
        
        # Dynamically create parameter fields
        if self.ea.config.parameters:
            for param_name, param_value in self.ea.config.parameters.items():
                widget = self._create_param_widget(param_name, param_value)
                self.param_widgets[param_name] = widget
                
                # Format parameter name for display
                display_name = param_name.replace('_', ' ').title() + ":"
                layout.addRow(display_name, widget)
        else:
            no_params_label = QLabel("This EA has no custom parameters")
            no_params_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addRow(no_params_label)
        
        return group
    
    def _create_param_widget(self, param_name: str, param_value):
        """Create appropriate widget for parameter based on its type."""
        # Integer parameters
        if isinstance(param_value, int):
            widget = QSpinBox()
            widget.setRange(-10000, 10000)
            widget.setValue(param_value)
            return widget
        
        # Float parameters
        elif isinstance(param_value, float):
            widget = QDoubleSpinBox()
            widget.setRange(-10000.0, 10000.0)
            widget.setDecimals(2)
            widget.setValue(param_value)
            return widget
        
        # Boolean parameters
        elif isinstance(param_value, bool):
            widget = QCheckBox()
            widget.setChecked(param_value)
            return widget
        
        # String parameters  
        else:
            widget = QLineEdit()
            widget.setText(str(param_value))
            return widget
    
    def _create_risk_management(self):
        """Create risk management section."""
        group = QGroupBox("Risk Management")
        layout = QFormLayout(group)
        
        self.lot_size_spin = QDoubleSpinBox()
        self.lot_size_spin.setRange(0.01, 100)
        self.lot_size_spin.setSingleStep(0.1)
        self.lot_size_spin.setValue(self.ea.config.lot_size)
        layout.addRow("Lot Size:", self.lot_size_spin)
        
        self.risk_percent_spin = QDoubleSpinBox()
        self.risk_percent_spin.setRange(0.1, 10)
        self.risk_percent_spin.setSingleStep(0.1)
        self.risk_percent_spin.setValue(self.ea.config.risk_percent)
        self.risk_percent_spin.setSuffix(" %")
        layout.addRow("Risk per Trade:", self.risk_percent_spin)
        
        self.sl_pips_spin = QDoubleSpinBox()
        self.sl_pips_spin.setRange(1, 1000)
        self.sl_pips_spin.setValue(self.ea.config.stop_loss_pips)
        self.sl_pips_spin.setSuffix(" pips")
        layout.addRow("Stop Loss:", self.sl_pips_spin)
        
        self.tp_pips_spin = QDoubleSpinBox()
        self.tp_pips_spin.setRange(0, 1000)
        self.tp_pips_spin.setValue(self.ea.config.take_profit_pips)
        self.tp_pips_spin.setSuffix(" pips")
        layout.addRow("Take Profit:", self.tp_pips_spin)
        
        return group
    
    def _create_trailing_stop(self):
        """Create trailing stop section."""
        group = QGroupBox("Trailing Stop")
        layout = QFormLayout(group)
        
        self.use_trailing = QCheckBox("Enable Trailing Stop")
        self.use_trailing.setChecked(self.ea.config.use_trailing_stop)
        layout.addRow("", self.use_trailing)
        
        self.trailing_pips_spin = QDoubleSpinBox()
        self.trailing_pips_spin.setRange(1, 500)
        self.trailing_pips_spin.setValue(self.ea.config.trailing_stop_pips)
        self.trailing_pips_spin.setSuffix(" pips")
        layout.addRow("Trailing Distance:", self.trailing_pips_spin)
        
        return group
    
    def _create_filters(self):
        """Create filters section."""
        group = QGroupBox("Trade Filters")
        layout = QFormLayout(group)
        
        self.enable_time_filter = QCheckBox("Enable Time Filter")
        self.enable_time_filter.setChecked(self.ea.config.enable_time_filter)
        layout.addRow("", self.enable_time_filter)
        
        self.start_hour_spin = QSpinBox()
        self.start_hour_spin.setRange(0, 23)
        self.start_hour_spin.setValue(self.ea.config.trading_start_hour)
        layout.addRow("Trading Start Hour:", self.start_hour_spin)
        
        self.end_hour_spin = QSpinBox()
        self.end_hour_spin.setRange(0, 23)
        self.end_hour_spin.setValue(self.ea.config.trading_end_hour)
        layout.addRow("Trading End Hour:", self.end_hour_spin)
        
        self.max_spread_spin = QDoubleSpinBox()
        self.max_spread_spin.setRange(0.1, 20)
        self.max_spread_spin.setSingleStep(0.1)
        self.max_spread_spin.setValue(self.ea.config.max_spread_pips)
        self.max_spread_spin.setSuffix(" pips")
        layout.addRow("Max Spread:", self.max_spread_spin)
        
        self.max_positions_spin = QSpinBox()
        self.max_positions_spin.setRange(1, 10)
        self.max_positions_spin.setValue(self.ea.config.max_concurrent_positions)
        layout.addRow("Max Concurrent Positions:", self.max_positions_spin)
        
        return group
    
    def _create_buttons(self):
        """Create button layout."""
        layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_config)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        
        layout.addStretch()
        layout.addWidget(self.save_btn)
        layout.addWidget(self.cancel_btn)
        
        return layout
    
    def _save_config(self):
        """Save configuration and close dialog."""
        try:
            # Update basic settings
            self.ea.config.symbol = self.symbol_edit.text().strip()
            self.ea.config.timeframe = self.timeframe_combo.currentText()
            
            # Update strategy parameters dynamically
            for param_name, widget in self.param_widgets.items():
                if isinstance(widget, QSpinBox):
                    self.ea.config.parameters[param_name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    self.ea.config.parameters[param_name] = widget.value()
                elif isinstance(widget, QCheckBox):
                    self.ea.config.parameters[param_name] = widget.isChecked()
                elif isinstance(widget, QLineEdit):
                    # Try to convert to number if possible
                    text = widget.text()
                    try:
                        self.ea.config.parameters[param_name] = float(text)
                    except ValueError:
                        self.ea.config.parameters[param_name] = text
                elif isinstance(widget, QComboBox):
                    self.ea.config.parameters[param_name] = widget.currentText()
            
            # Update risk management
            self.ea.config.lot_size = self.lot_size_spin.value()
            self.ea.config.risk_percent = self.risk_percent_spin.value()
            self.ea.config.stop_loss_pips = self.sl_pips_spin.value()
            self.ea.config.take_profit_pips = self.tp_pips_spin.value()
            
            # Update trailing stop
            self.ea.config.use_trailing_stop = self.use_trailing.isChecked()
            self.ea.config.trailing_stop_pips = self.trailing_pips_spin.value()
            
            # Update filters
            self.ea.config.enable_time_filter = self.enable_time_filter.isChecked()
            self.ea.config.trading_start_hour = self.start_hour_spin.value()
            self.ea.config.trading_end_hour = self.end_hour_spin.value()
            self.ea.config.max_spread_pips = self.max_spread_spin.value()
            self.ea.config.max_concurrent_positions = self.max_positions_spin.value()
            
            # Reinitialize EA with new config
            self.ea.initialize(self.ea.config)
            
            logger.info(f"{self.ea.name}: Configuration updated")
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving EA config: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")
