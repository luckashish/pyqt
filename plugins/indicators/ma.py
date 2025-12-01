"""
Moving Average Indicator.
Calculates Simple Moving Average (SMA) or Exponential Moving Average (EMA).
"""
import pandas as pd
from core.interfaces.plugin import Indicator
from PyQt5.QtGui import QColor
import pyqtgraph as pg
import numpy as np

class MovingAverage(Indicator):
    """
    Moving Average Indicator.
    Supports SMA and EMA.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Moving Average"
        self.version = "1.0"
        self.author = "System"
        self.description = "Calculates Simple or Exponential Moving Average."
        
        # Parameters
        self.period = 14
        self.ma_type = "SMA" # SMA or EMA
        self.color = "#FFEB3B" # Yellow
        self.width = 2
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MA.
        """
        if data is None or data.empty:
            return data
            
        # Ensure we have 'close' column
        if 'close' not in data.columns:
            return data
            
        # Calculate MA using pure pandas
        if self.ma_type == "SMA":
            ma = data['close'].rolling(window=self.period).mean()
            col_name = f"SMA_{self.period}"
        else:
            ma = data['close'].ewm(span=self.period, adjust=False).mean()
            col_name = f"EMA_{self.period}"
            
        # Add to dataframe
        data[col_name] = ma
        
        # Store column name for plotting
        self.output_column = col_name
        
        return data
        
    def plot(self, chart_widget, data: pd.DataFrame):
        """
        Plot MA on the chart.
        """
        if self.output_column not in data.columns:
            return
            
        # Get timestamps and values
        # Assuming data index is datetime or we have a 'time' column
        # ChartWidget expects x-axis as timestamps
        
        # x = (data.index.astype('int64') / 10**9).values # Convert to seconds if index is datetime
        # Use integer index to match the main chart's coordinate system
        x = np.arange(len(data))
        y = data[self.output_column].values
        
        # Create curve
        curve = pg.PlotCurveItem(
            x=x, 
            y=y, 
            pen=pg.mkPen(color=QColor(self.color), width=self.width),
            name=f"{self.ma_type} ({self.period})"
        )
        
        # Add to chart
        chart_widget.plot_item.addItem(curve)
        
        # Register for removal
        if hasattr(chart_widget, 'indicator_curves'):
            chart_widget.indicator_curves.append((f"{self.ma_type} ({self.period})", curve))
