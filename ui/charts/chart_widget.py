"""
Chart Widget using PyQtGraph
Renders interactive candlestick charts with zooming and panning.
"""
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPicture
import numpy as np
from datetime import datetime

class CandlestickItem(pg.GraphicsObject):
    """Custom GraphicsObject for drawing candlesticks."""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # list of (time, open, close, min, max)
        self.generatePicture()

    def generatePicture(self):
        """Pre-draw the picture for performance."""
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        # Colors
        w = 0.4  # width of candle body
        up_color = QColor("#4caf50")   # Green
        down_color = QColor("#f44336") # Red
        
        p.setPen(pg.mkPen('w'))  # White pen for wicks (or use body color)
        
        for (t, open, close, min, max) in self.data:
            if close >= open:
                p.setPen(pg.mkPen(up_color))
                p.setBrush(pg.mkBrush(up_color))
            else:
                p.setPen(pg.mkPen(down_color))
                p.setBrush(pg.mkBrush(down_color))
            
            # Draw wick (high to low)
            p.drawLine(pg.QtCore.QLineF(t, min, t, max)) # Center line
            
            # Draw body (open to close)
            p.drawRect(pg.QtCore.QRectF(t - w, open, w * 2, close - open))
            
        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class DateAxis(pg.AxisItem):
    """Axis that displays dates from a list of timestamps."""
    
    def __init__(self, orientation='bottom', *args, **kwargs):
        super().__init__(orientation, *args, **kwargs)
        self.timestamps = []
        self.setHeight(30)  # Increase height for 2-line labels
        self.setLabel("Time")
        
    def set_timestamps(self, timestamps):
        self.timestamps = timestamps
        
    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            # v is an index
            idx = int(v)
            if 0 <= idx < len(self.timestamps):
                dt = self.timestamps[idx]
                # Check if this tick is the start of a new day relative to the previous tick?
                # Hard to do stateless. 
                # Let's just show Date + Time.
                # Use newline to save horizontal space
                strings.append(dt.strftime("%H:%M\n%d/%m"))
            else:
                strings.append("")
        return strings


class ChartWidget(QWidget):
    """Main chart widget."""
    
    def __init__(self, symbol="", timeframe="M5"):
        super().__init__()
        self.symbol = symbol
        self.timeframe = timeframe
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PyQtGraph look
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#dcdcdc')
        
        # Create GraphicsLayoutWidget
        self.layout_widget = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.layout_widget)
        
        # Create custom DateAxis
        self.date_axis = DateAxis(orientation='bottom')
        
        # Add main plot area
        self.plot_item = self.layout_widget.addPlot(row=0, col=0, axisItems={'bottom': self.date_axis})
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.setLabel('left', 'Price')
        self.plot_item.addLegend()
        
        # Enable crosshair
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.plot_item.addItem(self.v_line, ignoreBounds=True)
        self.plot_item.addItem(self.h_line, ignoreBounds=True)
        
        # Mouse movement for crosshair
        self.proxy = pg.SignalProxy(self.plot_item.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)
        
        # Store indicator plots
        self.indicator_plots = {}
        self.indicator_curves = [] # List of (name, curve_item)
        
        # Placeholder for data
        self.candle_item = None
        self.data = [] # List of OHLCData
        
    def get_data(self):
        """
        Get current chart data as DataFrame.
        Returns: pd.DataFrame or None
        """
        if not self.data:
            return None
            
        import pandas as pd
        
        # Convert OHLCData objects to dicts
        data_list = [c.__dict__ for c in self.data]
        df = pd.DataFrame(data_list)
        
        # Ensure timestamp is datetime and set as index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
        return df
        
    def update_chart(self, ohlc_data):
        """
        Update chart with new OHLC data.
        ohlc_data: List of OHLCData objects
        """
        self.data = ohlc_data
        
        if not ohlc_data:
            return
            
        self.plot_item.clear()
        
        # Re-add crosshairs
        self.plot_item.addItem(self.v_line, ignoreBounds=True)
        self.plot_item.addItem(self.h_line, ignoreBounds=True)
        
        # Prepare data for CandlestickItem
        # Format: (time_index, open, close, low, high)
        # We use index for X-axis to avoid gaps for weekends/holidays
        chart_data = []
        timestamps = []
        
        for i, candle in enumerate(ohlc_data):
            chart_data.append((
                i, 
                candle.open, 
                candle.close, 
                candle.low, 
                candle.high
            ))
            timestamps.append(candle.timestamp)
            
        # Update axis timestamps
        self.date_axis.set_timestamps(timestamps)
            
        # Create and add item
        self.candle_item = CandlestickItem(chart_data)
        self.plot_item.addItem(self.candle_item)
        
        # Auto range
        self.plot_item.enableAutoRange()
        
        # Set title
        self.plot_item.setTitle(f"{self.symbol} ({self.timeframe})")

    def contextMenuEvent(self, event):
        """Show context menu."""
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self)
        
        # Remove Indicators
        if self.indicator_curves or self.indicator_plots:
            remove_menu = menu.addMenu("Remove Indicator")
            
            # Main chart indicators
            for name, curve in self.indicator_curves:
                action = QAction(name, self)
                action.triggered.connect(lambda checked, n=name: self.remove_indicator(n))
                remove_menu.addAction(action)
                
            # Separate plot indicators
            for name in self.indicator_plots:
                action = QAction(name, self)
                action.triggered.connect(lambda checked, n=name: self.remove_indicator(n))
                remove_menu.addAction(action)
                
            menu.addSeparator()
            clear_action = QAction("Clear All Indicators", self)
            clear_action.triggered.connect(self.clear_indicators)
            menu.addAction(clear_action)
            
        menu.exec_(event.globalPos())
        
    def remove_indicator(self, name):
        """Remove an indicator by name."""
        # Check main plot curves
        for i, (n, curve) in enumerate(self.indicator_curves):
            if n == name:
                self.plot_item.removeItem(curve)
                self.indicator_curves.pop(i)
                # Also remove from legend? PyQtGraph legend removal is tricky, 
                # usually clearing and re-adding is easier or just hiding.
                # For now, we just remove the item.
                return
                
        # Check separate plots
        if name in self.indicator_plots:
            plot_item = self.indicator_plots[name]
            self.layout_widget.removeItem(plot_item)
            del self.indicator_plots[name]
            return
            
    def clear_indicators(self):
        """Remove all indicators."""
        # Clear main chart curves
        for name, curve in self.indicator_curves:
            self.plot_item.removeItem(curve)
        self.indicator_curves.clear()
        
        # Clear separate plots
        for name, plot_item in self.indicator_plots.items():
            self.layout_widget.removeItem(plot_item)
        self.indicator_plots.clear()

    def mouse_moved(self, evt):
        """Update crosshair position."""
        pos = evt[0]
        if self.plot_item.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_item.vb.mapSceneToView(pos)
            self.v_line.setPos(mouse_point.x())
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())

    def add_indicator_plot(self, name: str, height_ratio: float = 0.25):
        """
        Add a separate plot area for an indicator.
        """
        if name in self.indicator_plots:
            return self.indicator_plots[name]
            
        # Add new row
        self.layout_widget.nextRow()
        
        # Create plot item
        # Link X-axis to main plot for synchronized zooming
        plot_item = self.layout_widget.addPlot(axisItems={'bottom': DateAxis(orientation='bottom')})
        plot_item.setXLink(self.plot_item)
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        plot_item.setLabel('left', name)
        plot_item.setMaximumHeight(200) # Limit height
        
        # Store
        self.indicator_plots[name] = plot_item
        
        return plot_item
