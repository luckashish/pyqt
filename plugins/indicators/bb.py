"""
Bollinger Bands Indicator.
Calculates Bollinger Bands (Upper, Middle, Lower).
"""
import pandas as pd
from core.interfaces.plugin import Indicator
from PyQt5.QtGui import QColor
import pyqtgraph as pg
import numpy as np

class BollingerBands(Indicator):
    """
    Bollinger Bands Indicator.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Bollinger Bands"
        self.version = "1.0"
        self.author = "System"
        self.description = "Calculates Bollinger Bands."
        
        # Parameters
        self.period = 20
        self.std_dev = 2.0
        self.color = "#E91E63" # Pink
        self.width = 1
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate BB.
        """
        if data is None or data.empty:
            return data
            
        if 'close' not in data.columns:
            return data
            
        # Calculate BB using pure pandas
        sma = data['close'].rolling(window=self.period).mean()
        std = data['close'].rolling(window=self.period).std()
        
        upper = sma + (std * self.std_dev)
        lower = sma - (std * self.std_dev)
        
        # Add to dataframe
        data[f"BBL_{self.period}_{self.std_dev}"] = lower
        data[f"BBM_{self.period}_{self.std_dev}"] = sma
        data[f"BBU_{self.period}_{self.std_dev}"] = upper
        
        # Store column names
        self.lower_col = f"BBL_{self.period}_{self.std_dev}"
        self.mid_col = f"BBM_{self.period}_{self.std_dev}"
        self.upper_col = f"BBU_{self.period}_{self.std_dev}"
            
        return data
        
    def plot(self, chart_widget, data: pd.DataFrame):
        """
        Plot BB on the chart.
        """
        if self.upper_col not in data.columns:
            return
            
        # x = (data.index.astype('int64') / 10**9).values
        # Use integer index to match the main chart's coordinate system
        x = np.arange(len(data))
        
        # Upper Band
        upper = data[self.upper_col].values
        curve_upper = pg.PlotCurveItem(
            x=x, y=upper, 
            pen=pg.mkPen(color=QColor(self.color), width=self.width)
        )
        
        # Lower Band
        lower = data[self.lower_col].values
        curve_lower = pg.PlotCurveItem(
            x=x, y=lower, 
            pen=pg.mkPen(color=QColor(self.color), width=self.width)
        )
        
        # Middle Band
        mid = data[self.mid_col].values
        curve_mid = pg.PlotCurveItem(
            x=x, y=mid, 
            pen=pg.mkPen(color=QColor(self.color), width=self.width, style=pg.QtCore.Qt.DashLine)
        )
        
        chart_widget.plot_item.addItem(curve_upper)
        chart_widget.plot_item.addItem(curve_lower)
        chart_widget.plot_item.addItem(curve_mid)
        
        # Fill between bands (optional, requires FillBetweenItem)
        fill = pg.FillBetweenItem(curve_upper, curve_lower, brush=pg.mkBrush(QColor(self.color).red(), QColor(self.color).green(), QColor(self.color).blue(), 30))
        chart_widget.plot_item.addItem(fill)
        
        # Register for removal
        if hasattr(chart_widget, 'indicator_curves'):
            name = f"BB ({self.period}, {self.std_dev})"
            chart_widget.indicator_curves.append((f"{name} Upper", curve_upper))
            chart_widget.indicator_curves.append((f"{name} Lower", curve_lower))
            chart_widget.indicator_curves.append((f"{name} Mid", curve_mid))
            chart_widget.indicator_curves.append((f"{name} Fill", fill))
