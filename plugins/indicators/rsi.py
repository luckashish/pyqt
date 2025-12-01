"""
RSI Indicator.
Calculates Relative Strength Index.
"""
import pandas as pd
from core.interfaces.plugin import Indicator
from PyQt5.QtGui import QColor
import pyqtgraph as pg
import numpy as np

class RSI(Indicator):
    """
    Relative Strength Index (RSI) Indicator.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "RSI"
        self.version = "1.0"
        self.author = "System"
        self.description = "Calculates Relative Strength Index."
        
        # Parameters
        self.period = 14
        self.color = "#00BCD4" # Cyan
        self.width = 2
        self.upper_level = 70
        self.lower_level = 30
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate RSI.
        """
        if data is None or data.empty:
            return data
            
        if 'close' not in data.columns:
            return data
            
        # Calculate RSI using pure pandas
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.rolling(window=self.period, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=1).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        col_name = f"RSI_{self.period}"
        
        data[col_name] = rsi
        self.output_column = col_name
        
        return data
        
    def plot(self, chart_widget, data: pd.DataFrame):
        """
        Plot RSI on a separate plot area (if supported) or main chart.
        For now, we'll assume ChartWidget supports adding a separate dock/plot.
        """
        if self.output_column not in data.columns:
            return
            
        # Note: RSI should be in a separate window/plot below the main price chart.
        # Since ChartWidget currently only has one plot item, we might need to extend it.
        # For this iteration, we will just log a warning if separate plot is not supported,
        # or try to add it to a new viewbox if ChartWidget allows.
        
        # Check if chart_widget has a method to add a new plot area
        if hasattr(chart_widget, 'add_indicator_plot'):
            plot_item = chart_widget.add_indicator_plot("RSI")
            
            # x = (data.index.astype('int64') / 10**9).values
            # Use integer index to match the main chart's coordinate system
            x = np.arange(len(data))
            y = data[self.output_column].values
            
            curve = pg.PlotCurveItem(
                x=x, 
                y=y, 
                pen=pg.mkPen(color=QColor(self.color), width=self.width),
                name=f"RSI ({self.period})"
            )
            plot_item.addItem(curve)
            
            # Add levels
            line_pen = pg.mkPen(color=QColor("#808080"), style=pg.QtCore.Qt.DashLine)
            plot_item.addLine(y=self.upper_level, pen=line_pen)
            plot_item.addLine(y=self.lower_level, pen=line_pen)
            
        else:
            # Fallback: Plot on main chart (not ideal for RSI but proves plugin works)
            # Or better: Don't plot and log
            print("ChartWidget does not support separate indicator plots yet.")
