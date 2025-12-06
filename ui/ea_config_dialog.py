"""
EA Configuration Dialog.
Allows editing EA parameters, symbol, and risk settings.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
    QDoubleSpinBox, QCheckBox, QGroupBox, QMessageBox,
    QTimeEdit
)
from PyQt5.QtCore import Qt, QTime

from core.ea_base import ExpertAdvisor
from utils.logger import logger
from datetime import datetime, timedelta


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
        
        # Track processed parameters to avoid duplicates
        processed_params = set()
        
        if self.ea.config.parameters:
            # Convert to list to access by index if needed, though dict is ordered
            params = self.ea.config.parameters
            
            for param_name, param_value in params.items():
                if param_name in processed_params:
                    continue
                
                # Dynamic default for target_time
                if param_name == 'target_time':
                    # Set to system time + 1 minute
                    future_time = datetime.now() + timedelta(minutes=1)
                    
                    # Create QTimeEdit
                    widget = QTimeEdit()
                    widget.setDisplayFormat("HH:mm")
                    widget.setTime(QTime(future_time.hour, future_time.minute))
                    
                    self.param_widgets[param_name] = widget
                    
                    display_name = param_name.replace('_', ' ').title() + ":"
                    layout.addRow(display_name, widget)
                    processed_params.add(param_name)
                    continue
                
                # Check for "enable_" pattern
                if param_name.startswith("enable_") and isinstance(param_value, bool):
                    # Try to find corresponding parameter (e.g. enable_buy -> buy_level)
                    base_name = param_name.replace("enable_", "")
                    target_param = None
                    
                    # Look for likely matches
                    candidates = [f"{base_name}_level", f"{base_name}_price", base_name]
                    for candidate in candidates:
                        if candidate in params:
                            target_param = candidate
                            break
                    
                    if target_param:
                        # Found a pair! Create a group
                        sub_group = QGroupBox(f"{base_name.title()} Settings")
                        sub_layout = QFormLayout(sub_group)
                        
                        # Checkbox (Enable)
                        checkbox = self._create_param_widget(param_name, param_value)
                        self.param_widgets[param_name] = checkbox
                        sub_layout.addRow(f"Enable {base_name.title()}", checkbox)
                        
                        # Value Widget
                        target_value = params[target_param]
                        widget = self._create_param_widget(target_param, target_value)
                        self.param_widgets[target_param] = widget
                        
                        # Disable input if checkbox is unchecked
                        widget.setEnabled(param_value)
                        checkbox.toggled.connect(widget.setEnabled)
                        
                        # For level parameters, add "Get LTP" button
                        if target_param.endswith('_level') or target_param.endswith('_price'):
                            level_layout = QHBoxLayout()
                            level_layout.addWidget(widget)
                            
                            ltp_btn = QPushButton("Get LTP")
                            ltp_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 4px 8px;")
                            ltp_btn.setMaximumWidth(80)
                            ltp_btn.clicked.connect(lambda checked, w=widget: self._fetch_and_set_ltp(w))
                            level_layout.addWidget(ltp_btn)
                            
                            display_name = target_param.replace('_', ' ').title() + ":"
                            sub_layout.addRow(display_name, level_layout)
                        else:
                            display_name = target_param.replace('_', ' ').title() + ":"
                            sub_layout.addRow(display_name, widget)
                        
                        layout.addRow(sub_group)
                        
                        # Mark both as processed
                        processed_params.add(param_name)
                        processed_params.add(target_param)
                        continue

                # Default handling for non-grouped parameters
                widget = self._create_param_widget(param_name, param_value)
                self.param_widgets[param_name] = widget
                
                display_name = param_name.replace('_', ' ').title() + ":"
                layout.addRow(display_name, widget)
                processed_params.add(param_name)
                
        else:
            no_params_label = QLabel("This EA has no custom parameters")
            no_params_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addRow(no_params_label)
        
        return group
    
    def _create_param_widget(self, param_name: str, param_value):
        """Create appropriate widget for parameter based on its type."""
        # Boolean parameters (Must be checked before int because bool is subclass of int)
        if isinstance(param_value, bool):
            widget = QCheckBox()
            widget.setChecked(param_value)
            return widget
            
        # Integer parameters
        elif isinstance(param_value, int):
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
                elif isinstance(widget, QTimeEdit):
                    self.ea.config.parameters[param_name] = widget.time().toString("HH:mm")
            
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
    
    def _fetch_and_set_ltp(self, widget):
        """Fetch current LTP for the configured symbol and set it to the widget."""
        try:
            symbol_name = self.symbol_edit.text().strip()
            
            if not symbol_name:
                QMessageBox.warning(self, "No Symbol", "Please enter a symbol first.")
                return
            
            # Get broker from main window (traverse up the widget hierarchy)
            broker = None
            current_widget = self.parent()
            
            # Try to find the main window with broker attribute
            while current_widget is not None:
                if hasattr(current_widget, 'broker'):
                    broker = current_widget.broker
                    break
                current_widget = current_widget.parent()
            
            if broker is None:
                QMessageBox.warning(self, "No Broker", "Broker connection not available.")
                return
            
            # Try to get symbol info from broker
            symbol_info = broker.get_symbol_info(symbol_name)
            ltp = None
            
            if symbol_info:
                ltp = symbol_info.last
                logger.info(f"Got LTP from broker for {symbol_name}: {ltp}")
            
            # If no valid price from broker, try position tracker cache (always try if no price)
            if ltp is None or ltp == 0:
                from core.position_tracker import position_tracker
                cached_ltp = position_tracker.current_prices.get(symbol_name)
                if cached_ltp and cached_ltp > 0:
                    ltp = cached_ltp
                    logger.info(f"Got LTP from position tracker cache for {symbol_name}: {ltp}")
            
            # If still no price, show detailed error
            if ltp is None or ltp == 0:
                error_msg = f"No price data available for {symbol_name}.\n\n"
                
                if symbol_info is None:
                    error_msg += "Symbol not found in broker.\n\n"
                    error_msg += "Please check:\n"
                    error_msg += "1. Symbol format is correct (e.g., MCX|463007)\n"
                    error_msg += "2. Symbol is added to Market Watch\n"
                    error_msg += "3. Broker is connected\n\n"
                else:
                    error_msg += "Symbol found but no price data.\n\n"
                    error_msg += "This is likely because:\n"
                    error_msg += "• Market is closed (opens at 9:15 AM)\n"
                    error_msg += "• Pre-market data not available yet\n\n"
                
                error_msg += "You can enter the price manually for now."
                
                QMessageBox.warning(self, "No Price Data", error_msg)
                logger.warning(f"No LTP available for {symbol_name}. symbol_info={symbol_info}, ltp={ltp}")
                return
            
            # Set to widget
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(ltp)
            elif isinstance(widget, QLineEdit):
                widget.setText(str(ltp))
            
            logger.info(f"Set LTP for {symbol_name}: {ltp}")
            QMessageBox.information(
                self,
                "LTP Updated",
                f"Current price for {symbol_name}:\n{ltp:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error fetching LTP: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to fetch LTP:\n{str(e)}")
