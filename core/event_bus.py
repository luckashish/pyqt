"""Event Bus for inter-module communication using Qt signals/slots."""
from PyQt5.QtCore import QObject, pyqtSignal
from data.models import Symbol, Order, OHLCData
from typing import List


class EventBus(QObject):
    """Central event bus for application-wide communication."""
    
    # Price update signals
    tick_received = pyqtSignal(Symbol)  # New tick data
    candle_updated = pyqtSignal(str, OHLCData)  # symbol, candle data
    
    # Order signals
    order_placed = pyqtSignal(Order)
    order_modified = pyqtSignal(Order)
    order_closed = pyqtSignal(Order)
    
    # Account signals
    account_updated = pyqtSignal(dict)  # balance, equity, margin, etc.
    
    # Connection signals
    connected = pyqtSignal(str)  # broker name
    disconnected = pyqtSignal(str)  # reason
    
    # UI signals
    symbol_selected = pyqtSignal(str)  # symbol name
    timeframe_changed = pyqtSignal(str)  # timeframe
    
    # Alert signals
    alert_triggered = pyqtSignal(str, float)  # symbol, price
    
    # Plugin signals
    indicator_applied = pyqtSignal(str, str)  # indicator name, symbol
    
    # EA signals
    ea_started = pyqtSignal(str)  # EA name
    ea_stopped = pyqtSignal(str)  # EA name
    ea_paused = pyqtSignal(str)  # EA name
    ea_signal_generated = pyqtSignal(object)  # EASignal
    ea_order_request = pyqtSignal(object)  # Order request
    ea_error = pyqtSignal(str, str)  # EA name, error message
    ea_performance_update = pyqtSignal(str, dict)  # EA name, performance data
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance


# Global event bus instance
event_bus = EventBus()
