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


class ChartWidget(QWidget):
    """Main chart widget."""
    
    def __init__(self, symbol=""):
        super().__init__()
        self.symbol = symbol
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PyQtGraph look
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#dcdcdc')
        
        # Create PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Price')
        self.plot_widget.setLabel('bottom', 'Time')
        
        # Enable crosshair
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
        # Mouse movement for crosshair
        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved, rateLimit=60, slot=self.mouse_moved)
        
        self.layout.addWidget(self.plot_widget)
        
        # Placeholder for data
        self.candle_item = None
        
    def update_chart(self, ohlc_data):
        """
        Update chart with new OHLC data.
        ohlc_data: List of OHLCData objects
        """
        if not ohlc_data:
            return
            
        self.plot_widget.clear()
        
        # Re-add crosshairs
        self.plot_widget.addItem(self.v_line, ignoreBounds=True)
        self.plot_widget.addItem(self.h_line, ignoreBounds=True)
        
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
            timestamps.append(candle.timestamp.strftime("%H:%M"))
            
        # Create and add item
        self.candle_item = CandlestickItem(chart_data)
        self.plot_widget.addItem(self.candle_item)
        
        # Set X-axis labels (custom tick strings)
        axis = self.plot_widget.getAxis('bottom')
        # Show a label every N ticks to avoid crowding
        n = max(1, len(timestamps) // 10)
        ticks = [(i, t) for i, t in enumerate(timestamps) if i % n == 0]
        axis.setTicks([ticks])
        
        # Auto range
        self.plot_widget.enableAutoRange()
        
        # Set title
        self.plot_widget.setTitle(f"{self.symbol}")

    def mouse_moved(self, evt):
        """Update crosshair position."""
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            self.v_line.setPos(mouse_point.x())
            self.h_line.setPos(mouse_point.y())
