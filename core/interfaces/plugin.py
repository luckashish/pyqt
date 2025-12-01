"""
Plugin Interface Definitions.
Defines the base classes for all plugins in the system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class Plugin(ABC):
    """Base class for all plugins."""
    
    def __init__(self):
        self.name: str = "Unknown Plugin"
        self.version: str = "1.0"
        self.author: str = "Unknown"
        self.description: str = ""
        self.enabled: bool = True
        
    def on_load(self):
        """Called when the plugin is loaded."""
        pass
        
    def on_unload(self):
        """Called when the plugin is unloaded."""
        pass

class Indicator(Plugin):
    """
    Base class for Technical Indicators.
    """
    
    def __init__(self):
        super().__init__()
        self.type = "Indicator"
        
    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values based on OHLC data.
        
        Args:
            data: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns.
            
        Returns:
            DataFrame with original data plus new indicator columns.
        """
        pass
        
    def plot(self, chart_widget, data: pd.DataFrame):
        """
        Define how to plot the indicator on the chart.
        
        Args:
            chart_widget: The ChartWidget instance.
            data: DataFrame containing indicator values.
        """
        pass

class Strategy(Plugin):
    """
    Base class for Expert Advisors (Strategies).
    """
    
    def __init__(self):
        super().__init__()
        self.type = "Strategy"
        
    @abstractmethod
    def on_tick(self, tick: Any):
        """
        Called on every price tick.
        
        Args:
            tick: The tick data (Symbol object).
        """
        pass
        
    def on_bar(self, bar: Any):
        """
        Called when a new candle/bar is closed.
        
        Args:
            bar: The candle data (OHLCData object).
        """
        pass

class Script(Plugin):
    """
    Base class for one-time execution scripts.
    """
    
    def __init__(self):
        super().__init__()
        self.type = "Script"
        
    @abstractmethod
    def run(self, **kwargs):
        """
        Execute the script logic.
        """
        pass
