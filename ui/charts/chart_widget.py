"""
Chart Widget using PyQtGraph
Renders interactive candlestick charts with zooming and panning.
"""
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPicture
import numpy as np
from datetime import datetime, timedelta

class CandlestickItem(pg.GraphicsObject):
    """Custom GraphicsObject for drawing candlesticks."""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # list of (time, open, close, min, max)
        self.generatePicture()

    def update_last_candle(self, index, open, close, low, high):
        """Update the last candle data and repaint."""
        if index < 0 or index >= len(self.data):
            return
            
        self.prepareGeometryChange()
        self.data[index] = (index, open, close, low, high)
        self.generatePicture()
        self.update()

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
    
    # Signals
    alert_triggered = pyqtSignal(object)  # Emits Alert object when triggered
    
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
        
        # Store alerts
        self.alerts = []  # List of Alert objects
        self.alert_lines = []  # List of (Alert, InfiniteLine, TextItem) tuples
        
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

    def update_tick(self, tick_data):
        """
        Update chart with new tick data.
        tick_data: Symbol object or dict with 'last_price', 'timestamp'
        """
        price = tick_data.last
        # print(f"Chart update_tick: {price}")
        
        if price <= 0:
            return

        if not self.data:
            # Initialize with first candle if no data exists
            from data.models import OHLCData
            current_time = datetime.now()
            
            # Create first candle
            new_candle = OHLCData(
                timestamp=current_time,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0
            )
            self.data = [new_candle]
            
            # Initialize plot
            self.update_chart(self.data)
            return
        
        last_candle = self.data[-1]
        
        # Check if we need a new candle
        # Simple time check based on timeframe
        current_time = datetime.now() # Or use tick timestamp if available
        
        # Determine timeframe delta
        delta = None
        if self.timeframe == "M1":
            delta = timedelta(minutes=1)
        elif self.timeframe == "M5":
            delta = timedelta(minutes=5)
        elif self.timeframe == "M15":
            delta = timedelta(minutes=15)
        elif self.timeframe == "M30":
            delta = timedelta(minutes=30)
        elif self.timeframe == "H1":
            delta = timedelta(hours=1)
        elif self.timeframe == "D1":
            delta = timedelta(days=1)
            
        if delta:
            # Check if last candle time + delta <= current time
            # Note: This is a simplification. Ideally we align to grid (e.g. 10:00, 10:05)
            # But for now, let's just check if we crossed the boundary
            
            # Align current time to timeframe start
            # e.g. 10:03:45 M5 -> 10:00:00
            # If last candle is 10:00:00, and now is 10:05:01, we need new candle
            
            # Helper to floor time
            def floor_time(dt, delta):
                seconds = int((dt - dt.min).total_seconds())
                step = int(delta.total_seconds())
                floored_seconds = (seconds // step) * step
                return dt.min + timedelta(seconds=floored_seconds)

            current_candle_time = floor_time(current_time, delta)
            
            if current_candle_time > last_candle.timestamp:
                # Create new candle
                from data.models import OHLCData
                new_candle = OHLCData(
                    timestamp=current_candle_time,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=0
                )
                self.data.append(new_candle)
                last_candle = new_candle
                
                # Instead of full update_chart, just append to existing data
                # Get the new candle index
                new_idx = len(self.data) - 1
                
                # Append to candle_item data
                new_candle_data = (new_idx, price, price, price, price)
                self.candle_item.data.append(new_candle_data)
                
                # Update timestamps
                self.date_axis.timestamps.append(current_candle_time)
                
                # Regenerate picture
                self.candle_item.prepareGeometryChange()
                self.candle_item.generatePicture()
                self.candle_item.update()
                
                return

        # Update last candle
        last_candle.close = price
        last_candle.high = max(last_candle.high, price)
        last_candle.low = min(last_candle.low, price)
        
        # Trigger repaint
        # Ideally we should optimize this to not redraw everything
        # But for M5/H1, full redraw on tick is okay-ish for now
        # self.update_chart(self.data)
        
        # Optimization: Update the specific candle item
        if self.candle_item:
            # Update the last data point in the candle item
            # self.candle_item.data is list of (t, open, close, min, max)
            # We need to update the last tuple
            
            # Get last index from existing data
            last_idx = len(self.candle_item.data) - 1
            if last_idx >= 0:
                self.candle_item.update_last_candle(
                    last_idx,
                    last_candle.open,
                    last_candle.close,
                    last_candle.low,
                    last_candle.high
                )
        
        # Check if any alerts should trigger
        self.check_alerts(price)

    def contextMenuEvent(self, event):
        """Show context menu."""
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self)
        
        # Create Alert
        create_alert_action = QAction("Create Alert...", self)
        create_alert_action.triggered.connect(self._show_create_alert_dialog)
        menu.addAction(create_alert_action)
        
        # Manage Alerts (if any exist)
        if self.alerts:
            manage_menu = menu.addMenu("Manage Alerts")
            for alert in self.alerts:
                alert_text = f"{alert.condition.upper()} {alert.price:.2f}"
                if alert.triggered:
                    alert_text += " (TRIGGERED)"
                action = QAction(alert_text, self)
                action.triggered.connect(lambda checked, a=alert: self.remove_alert(a))
                manage_menu.addAction(action)
        
        menu.addSeparator()
        
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

    def add_alert(self, alert):
        """Add a price alert to the chart."""
        from data.models import Alert
        
        self.alerts.append(alert)
        
        # Create visual line
        line = pg.InfiniteLine(
            pos=alert.price,
            angle=0,
            pen=pg.mkPen(color='#ff9800', width=2, style=Qt.DashLine),
            movable=False
        )
        
        # Add label
        label_text = f"{alert.condition.upper()} {alert.price:.2f}"
        label = pg.TextItem(label_text, color='#ff9800', anchor=(0, 1))
        label.setPos(0, alert.price)
        
        self.plot_item.addItem(line)
        self.plot_item.addItem(label)
        
        self.alert_lines.append((alert, line, label))
        
    def remove_alert(self, alert):
        """Remove an alert from the chart."""
        if alert in self.alerts:
            self.alerts.remove(alert)
            
        # Find and remove from alert_lines
        for i, (a, line, label) in enumerate(self.alert_lines):
            if a == alert:
                self.plot_item.removeItem(line)
                self.plot_item.removeItem(label)
                self.alert_lines.pop(i)
                break
            
    def check_alerts(self, current_price):
        """Check if any alerts should be triggered."""
        for alert in self.alerts[:]:
            if not alert.enabled or alert.triggered:
                continue
                
            # Check crossover
            crossed = False
            if alert.condition == "above" and alert.last_price < alert.price <= current_price:
                crossed = True
            elif alert.condition == "below" and alert.last_price > alert.price >= current_price:
                crossed = True
                
            if crossed:
                from datetime import datetime
                alert.triggered = True
                alert.triggered_time = datetime.now()
                self.alert_triggered.emit(alert)
                
                # Change line color to indicate triggered
                for a, line, label in self.alert_lines:
                    if a == alert:
                        line.setPen(pg.mkPen(color='#4caf50', width=2, style=Qt.DashLine))
                        label.setColor('#4caf50')
                        break
                    
            # Update last price for next check
            alert.last_price = current_price

    def _show_create_alert_dialog(self):
        """Show dialog to create a new alert."""
        from ui.alert_dialog import AlertDialog
        from data.models import Alert
        
        # Get current price from last candle
        current_price = self.data[-1].close if self.data else 0.0
        
        dialog = AlertDialog(self.symbol, current_price, self)
        if dialog.exec_() == AlertDialog.Accepted:
            alert_data = dialog.get_alert_data()
            
            # Create Alert object
            alert = Alert(
                symbol=self.symbol,
                price=alert_data['price'],
                condition=alert_data['condition'],
                notification_type=alert_data['notification_type'],
                last_price=current_price
            )
            
            self.add_alert(alert)
