"""
Indicator Configuration Dialog.
Allows users to modify indicator parameters before adding them to the chart.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QSpinBox, QDoubleSpinBox, 
    QComboBox, QPushButton, QFormLayout, QColorDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

class IndicatorDialog(QDialog):
    """Dialog to configure indicator parameters."""
    
    def __init__(self, indicator, parent=None):
        super().__init__(parent)
        self.indicator = indicator
        self.setWindowTitle(f"Configure {indicator.name}")
        self.setMinimumWidth(300)
        
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.layout.addLayout(self.form_layout)
        
        self.inputs = {}
        self._create_inputs()
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        self.layout.addLayout(button_layout)
        
    def _create_inputs(self):
        """Introspect indicator attributes and create inputs."""
        # Common attributes to ignore
        ignored = ['name', 'version', 'author', 'description', 'enabled', 'type', 'output_column']
        
        for attr, value in self.indicator.__dict__.items():
            if attr.startswith('_') or attr in ignored:
                continue
                
            label = attr.replace('_', ' ').title()
            
            if isinstance(value, int):
                inp = QSpinBox()
                inp.setRange(1, 1000)
                inp.setValue(value)
                self.inputs[attr] = inp
                self.form_layout.addRow(label, inp)
                
            elif isinstance(value, float):
                inp = QDoubleSpinBox()
                inp.setRange(0.0, 1000.0)
                inp.setDecimals(2)
                inp.setValue(value)
                self.inputs[attr] = inp
                self.form_layout.addRow(label, inp)
                
            elif isinstance(value, str):
                if value.startswith('#'): # Color
                    btn = QPushButton()
                    btn.setStyleSheet(f"background-color: {value}")
                    btn.clicked.connect(lambda checked, b=btn, a=attr: self._pick_color(b, a))
                    self.inputs[attr] = {'value': value, 'btn': btn}
                    self.form_layout.addRow(label, btn)
                else:
                    inp = QLineEdit(value)
                    self.inputs[attr] = inp
                    self.form_layout.addRow(label, inp)
                    
    def _pick_color(self, btn, attr):
        """Open color picker."""
        current_color = QColor(self.inputs[attr]['value'])
        color = QColorDialog.getColor(current_color, self, "Select Color")
        
        if color.isValid():
            hex_color = color.name()
            self.inputs[attr]['value'] = hex_color
            btn.setStyleSheet(f"background-color: {hex_color}")
            
    def get_parameters(self):
        """Update indicator with new values."""
        for attr, inp in self.inputs.items():
            if isinstance(inp, (QSpinBox, QDoubleSpinBox)):
                setattr(self.indicator, attr, inp.value())
            elif isinstance(inp, QLineEdit):
                setattr(self.indicator, attr, inp.text())
            elif isinstance(inp, dict): # Color
                setattr(self.indicator, attr, inp['value'])
                
        return self.indicator
