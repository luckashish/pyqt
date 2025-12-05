"""
MT5-Style Trading Platform - Main Entry Point
A comprehensive trading platform built with PyQt5
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import pyqtSlot

# Import our modules
from utils.config_manager import config
from utils.logger import logger
from core.event_bus import event_bus
from brokers.factory import broker_factory
from brokers.registry import register_builtin_brokers

from data.models import Symbol, Order, OrderType
from ui.order_dialog import OrderDialog

# EA System
from core.ea_manager import ea_manager
from core.execution_service import execution_service
from core.position_tracker import position_tracker
from plugins.strategies.ma_crossover import create_ma_crossover_ea
from plugins.strategies.bullish_breakout import create_bullish_breakout_ea
from plugins.strategies.bearish_breakout import create_bearish_breakout_ea
from plugins.strategies.fixed_price_trigger import create_fixed_price_trigger_ea
from plugins.strategies.time_based_breakout import create_time_based_ea

# New Managers
from ui.main_window_ui import MainWindowUI
from core.chart_manager import ChartManager
from core.connection_manager import ConnectionManager
from core.plugin_manager import plugin_manager


class MainWindow(QMainWindow):
    """Main application window matching MT5 layout."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MT5 Trading Platform - Demo Account")
        self.setGeometry(100, 100, 1400, 900)
        
        # Load configuration FIRST
        try:
            config.load_config("config.yaml")
        except:
            logger.warning("Config file not found, using defaults")
        
        # Register brokers
        register_builtin_brokers()
        
        # Create broker instance (now config is loaded!)
        self.broker = broker_factory.create_broker()  # Uses config.yaml
        
        # Initialize Managers
        self.ui = MainWindowUI(self)
        self.chart_manager = ChartManager(self, self.broker)
        self.connection_manager = ConnectionManager(self, self.broker)
        
        # Initialize UI
        self.ui.init_ui(self.broker)
        
        # Initialize EA System
        self._init_ea_system()
        
        # Discover and Load Plugins
        plugin_manager.discover_plugins()
        self.ui.navigator.update_plugins(plugin_manager.get_all_plugins())
        
        # Create default charts
        self.chart_manager.create_default_charts()
        
        # Connect to broker
        self.connection_manager.connect_broker()
        
    # --- Delegate Methods for UI Signals ---
    
    def _fetch_chart_data(self, symbol_name, timeframe="M5"):
        self.chart_manager.fetch_chart_data(symbol_name, timeframe)
        
    def _change_timeframe(self, timeframe):
        self.chart_manager.change_timeframe(timeframe)
        
    def _on_tab_close(self, index):
        self.chart_manager.on_tab_close(index)
        
    def _on_symbol_added(self, symbol: str):
        """Handle new symbol added from Market Watch."""
        logger.info(f"Adding symbol: {symbol}")
        self.ui.status_bar.showMessage(f"Adding symbol: {symbol}...", 3000)
        self.broker.subscribe([symbol])

    def _on_clear_cache(self):
        """Handle clear cache action."""
        from utils.cache_manager import clear_cache
        
        reply = QMessageBox.question(
            self, 
            "Clear Cache", 
            "Are you sure you want to clear the application cache?\n"
            "This will delete temporary files and may require a restart.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                count = clear_cache(os.getcwd())
                QMessageBox.information(
                    self, 
                    "Cache Cleared", 
                    f"Successfully cleared {count} cache items.\n"
                    "Please restart the application for changes to take full effect."
                )
                logger.info(f"User cleared cache: {count} items deleted")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear cache: {str(e)}")
                logger.error(f"Failed to clear cache: {e}")

    def _toggle_paper_trading(self, checked):
        """Toggle paper trading mode."""
        execution_service.set_paper_trading(checked)
        status = "ENABLED" if checked else "DISABLED"
        self.ui.status_bar.showMessage(f"Paper Trading {status}", 3000)
        
        # Update button style
        if checked:
            self.ui.paper_trading_btn.setText("Paper Trading")
            self.ui.paper_trading_btn.setStyleSheet("QPushButton:checked { background-color: #4CAF50; color: white; }")
        else:
            self.ui.paper_trading_btn.setText("Real Trading")
            self.ui.paper_trading_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

    def _on_plugin_double_clicked(self, plugin_name, plugin_type):
        """Handle plugin activation from Navigator."""
        # This logic was in main.py, keeping it here or moving to a PluginManager?
        # It interacts with UI (applying indicators to charts).
        # ChartManager handles charts.
        
        logger.info(f"Plugin activated: {plugin_name} ({plugin_type})")
        
        try:
            if plugin_type == "Indicator":
                self._apply_indicator(plugin_name)
            elif plugin_type == "Script":
                self._run_script(plugin_name)
            elif plugin_type == "Strategy":
                if "MA Crossover" in plugin_name:
                    self._start_ma_crossover_ea()
                elif "Time Based" in plugin_name:
                    self._start_time_based_ea()
                else:
                    QMessageBox.information(self, "Strategy", f"Strategy '{plugin_name}' selected.")
        except Exception as e:
            logger.error(f"Error executing plugin {plugin_name}: {e}")
            QMessageBox.critical(self, "Plugin Error", f"Error executing plugin: {e}")

    def _apply_indicator(self, name):
        """Apply an indicator to the active chart."""
        from core.plugin_manager import plugin_manager
        from ui.indicator_dialog import IndicatorDialog
        from PyQt5.QtWidgets import QDialog
        
        # Get active chart via ChartManager
        chart_tabs = self.ui.chart_tabs
        current_index = chart_tabs.currentIndex()
        if current_index == -1:
            QMessageBox.warning(self, "No Chart", "Please open a chart first.")
            return
            
        symbol = chart_tabs.tabText(current_index)
        if symbol not in self.chart_manager.charts:
            return
            
        chart_widget = self.chart_manager.charts[symbol]
        
        # Get indicator
        indicator = plugin_manager.get_indicator(name)
        if not indicator:
            return
            
        # Get data
        data = chart_widget.get_data()
        if data is None or data.empty:
            QMessageBox.warning(self, "No Data", "Chart has no data to calculate indicator.")
            return
            
        # Configure Indicator
        dialog = IndicatorDialog(indicator, self)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get updated indicator
        indicator = dialog.get_parameters()
        
        # Calculate
        logger.info(f"Calculating {name} for {symbol}...")
        data = indicator.calculate(data)
        
        # Plot
        indicator.plot(chart_widget, data)
        logger.info(f"Applied {name} to {symbol}")

    def _run_script(self, name):
        """Run a script."""
        from core.plugin_manager import plugin_manager
        script = plugin_manager.get_script(name)
        if script:
            script.run(broker=self.broker, parent=self)

    # --- Event Handlers (Called by ConnectionManager/EventBus) ---

    @pyqtSlot(Symbol)
    def _on_tick_received(self, symbol: Symbol):
        """Handle tick update."""
        # Update Market Watch
        if self.ui.market_watch:
            self.ui.market_watch.update_tick(symbol)
        
        # Route to EA Manager
        ea_manager.on_tick(symbol)
        
        # Route to Position Tracker (Client-Side SL/TP)
        position_tracker.on_tick(symbol)
        
        # Update Charts
        self.chart_manager.update_tick(symbol)
    
    @pyqtSlot(object)
    def _on_alert_triggered(self, alert):
        """Handle alert being triggered."""
        logger.info(f"Alert triggered: {alert.symbol} {alert.condition} {alert.price}")
        
        message = f"{alert.symbol}\n{alert.condition.upper()} {alert.price:.2f}"
        
        if alert.notification_type in ["visual", "both"]:
            QMessageBox.information(self, "Price Alert Triggered!", message, QMessageBox.Ok)
        
        if alert.notification_type in ["audio", "both"]:
            # Audio logic...
            pass
        
        self.ui.status_bar.showMessage(f"Alert triggered: {alert.symbol} {alert.condition} {alert.price}", 10000)
    
    @pyqtSlot(Order)
    def _on_order_placed(self, order: Order):
        """Handle new order."""
        logger.info(f"Order placed: {order.ticket} | {order.symbol} | SL: {order.sl} | TP: {order.tp}")
        self.ui.terminal.update_trade_table()
        self.ui.status_bar.showMessage(f"Order {order.ticket} placed successfully", 3000)
    
    @pyqtSlot(Order)
    def _on_order_closed(self, order: Order):
        """Handle order closed."""
        logger.info(f"Order closed: {order.ticket}")
        
        # Log to Journal
        reason = order.comment if order.comment else "Manual"
        log_msg = f"Order Closed: {order.ticket} {order.symbol} P/L: {order.profit:.2f} ({reason})"
        self.ui.terminal.log_message(log_msg)
        
        self.ui.terminal.update_trade_table()

        self.ui.status_bar.showMessage(f"Order {order.ticket} closed", 3000)
    
    @pyqtSlot(dict)
    def _on_account_updated(self, account_info: dict):
        """Handle account info update."""
        self.ui.terminal.update_account_info(account_info)

    # --- Order Management ---

    def _place_market_order(self, symbol: str, order_type_str: str):
        """Place a market order."""
        from data.models import OrderType
        
        order_type = OrderType.BUY if order_type_str == "BUY" else OrderType.SELL
        volume = 0.1
        
        order = self.broker.place_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            comment="One-click trading"
        )
        
        if order:
            logger.info(f"Market order placed: {order.ticket}")
        else:
            logger.error("Failed to place order")
    
    def _show_new_order_dialog(self):
        """Show the new order dialog."""
        symbol = "NSE|26000" # Default
        price = 0.0
        
        # Try to get from active chart
        current_index = self.ui.chart_tabs.currentIndex()
        if current_index != -1:
            symbol = self.ui.chart_tabs.tabText(current_index)
        
        dialog = OrderDialog(symbol, price, self)
        dialog.order_placed.connect(self._place_order_from_dialog)
        dialog.exec_()
        
    def _place_order_from_dialog(self, order_data):
        """Handle order placement from dialog."""
        try:
            logger.info(f"Placing order: {order_data}")
            
            # Check for Paper Trading
            if execution_service.paper_trading:
                logger.info(f"[PAPER] Manual Order: {order_data}")
                self.ui.status_bar.showMessage(f"[PAPER] Order Placed: {order_data['symbol']} {order_data['side']}", 3000)
                return

            
            side = order_data['side']
            o_type = order_data['order_type']
            
            final_order_type = OrderType.BUY
            if side == "BUY":
                if o_type == "MARKET": final_order_type = OrderType.BUY
                elif o_type == "LIMIT": final_order_type = OrderType.BUY_LIMIT
                elif o_type in ["SL-L", "SL-M"]: final_order_type = OrderType.BUY_STOP
            else:
                if o_type == "MARKET": final_order_type = OrderType.SELL
                elif o_type == "LIMIT": final_order_type = OrderType.SELL_LIMIT
                elif o_type in ["SL-L", "SL-M"]: final_order_type = OrderType.SELL_STOP
            
            self.broker.place_order(
                symbol=order_data['symbol'],
                order_type=final_order_type,
                volume=order_data['quantity'],
                price=order_data['price'],
                trigger_price=order_data['trigger_price'],
                product_type=order_data['product_type']
            )
            
            self.ui.status_bar.showMessage(f"Order placed for {order_data['symbol']}", 5000)
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            QMessageBox.critical(self, "Order Error", f"Failed to place order: {str(e)}")

    # --- EA System ---

    def _init_ea_system(self):
        """Initialize Expert Advisor system."""
        logger.info("Initializing EA system...")
        
        try:
            execution_service.set_broker(self.broker)
            execution_service.set_paper_trading(True)
            
            try:
                ea_manager.signal_generated.disconnect(self._on_ea_signal)
            except TypeError:
                pass  # Not connected
            ea_manager.signal_generated.connect(self._on_ea_signal)
            
            ea_manager.ea_started.connect(lambda name: self.ui.status_bar.showMessage(f"EA Started: {name}", 3000))
            ea_manager.ea_stopped.connect(lambda name: self.ui.status_bar.showMessage(f"EA Stopped: {name}", 3000))
            ea_manager.ea_error.connect(self._on_ea_error)
            
            try: execution_service.order_placed.disconnect(self._on_order_placed)
            except TypeError: pass
            execution_service.order_placed.connect(self._on_order_placed)
            
            try: execution_service.order_rejected.disconnect(self._on_order_rejected)
            except TypeError: pass
            execution_service.order_rejected.connect(self._on_order_rejected)
            
            # Connect to Position Tracker (CRITICAL for SL/TP monitoring)
            try: execution_service.order_placed.disconnect(position_tracker.update_position)
            except TypeError: pass
            execution_service.order_placed.connect(position_tracker.update_position)
            
            try: execution_service.order_filled.disconnect(position_tracker.update_position)
            except TypeError: pass
            execution_service.order_filled.connect(position_tracker.update_position)
            
            # --- EA STATISTICS WIRING ---
            # Connect order updates to EA Manager for stats tracking
            try: execution_service.order_placed.disconnect(ea_manager.on_order_update)
            except TypeError: pass
            execution_service.order_placed.connect(ea_manager.on_order_update)
            
            try: execution_service.order_closed.disconnect(ea_manager.on_order_update)
            except TypeError: pass
            execution_service.order_closed.connect(ea_manager.on_order_update)
            
            try: event_bus.order_closed.disconnect(ea_manager.on_order_update)
            except TypeError: pass
            event_bus.order_closed.connect(ea_manager.on_order_update)
            # ----------------------------
            
            # --- CRITICAL WIRING ---
            # 1. Connect EA Signals to Execution Service (Auto-Trading)
            try: ea_manager.signal_generated.disconnect(execution_service.execute_signal)
            except TypeError: pass
            ea_manager.signal_generated.connect(execution_service.execute_signal)
            
            # 2. Connect Trailing Stop Updates to Execution Service
            # Note: Lambda functions are hard to disconnect by reference. 
            # We'll use a named method or just accept this one might duplicate if not careful.
            # Ideally, we should define a wrapper method.
            # For now, let's assume this one is less critical or fix it properly.
            
            # Better approach: Define a slot for trailing stop
            try: position_tracker.trailing_stop_updated.disconnect(self._on_trailing_stop_updated)
            except TypeError: pass
            position_tracker.trailing_stop_updated.connect(self._on_trailing_stop_updated)
            # -----------------------

            position_tracker.position_opened.connect(lambda p: logger.info(f"Position opened: {p.symbol}"))
            position_tracker.position_closed.connect(lambda p: logger.info(f"Position closed: {p.symbol} P/L: {p.profit:.2f}"))
            
            # Register EAs
            ma_ea = create_ma_crossover_ea("MCX|463007", "M1", 10, 20, "SMA", 1, 50, 100, True, 30)
            ea_manager.register_ea(ma_ea)
            
            breakout_ea = create_bullish_breakout_ea("MCX|463007", "M1", 5, 1, 0, True, 30)
            ea_manager.register_ea(breakout_ea)
            
            bearish_ea = create_bearish_breakout_ea("MCX|463007", "M1", 5, 1, 0, True, 30)
            ea_manager.register_ea(bearish_ea)
            
            trigger_ea = create_fixed_price_trigger_ea("MCX|463007", 440.0, 1, 10, 20)
            ea_manager.register_ea(trigger_ea)
            
            time_ea = create_time_based_ea("MCX|463007", "10:33 pm", True, 404.0, True, 400.0, 1, 10, 20)
            ea_manager.register_ea(time_ea)
            
            self.ui.ea_panel.refresh_table()
            logger.info("EA system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EA system: {e}")
            QMessageBox.warning(self, "EA System Error", f"Failed to initialize Expert Advisor system:\n{e}")

    def _start_ma_crossover_ea(self):
        self._start_ea("MA Crossover EA")
        
    def _start_bullish_breakout_ea(self):
        self._start_ea("Bullish Breakout EA")
        
    def _start_bearish_breakout_ea(self):
        self._start_ea("Bearish Breakout EA")
        
    def _start_fixed_price_trigger_ea(self):
        self._start_ea("Fixed Price Trigger EA")
        
    def _start_time_based_ea(self):
        self._start_ea("Time Based Breakout EA")
        
    def _start_ea(self, ea_name):
        """Generic helper to start an EA."""
        ea = ea_manager.get_ea(ea_name)
        if not ea:
            QMessageBox.warning(self, "EA Not Found", f"{ea_name} not registered.")
            return
        
        if ea.is_running:
            QMessageBox.information(self, "EA Running", f"{ea_name} is already running.")
            return
        
        success = ea_manager.start_ea(ea_name)
        if success:
            self.ui.ea_panel.refresh_table()
            QMessageBox.information(self, "EA Started", f"{ea_name} started successfully!")
        else:
            QMessageBox.critical(self, "EA Error", f"Failed to start {ea_name}.")

    def _on_ea_signal(self, signal):
        logger.info(f"EA Signal: {signal.ea_name} - {signal.signal_type} @ {signal.price}")
        
        # Log to Journal
        log_msg = f"[EA] {signal.ea_name}: {signal.signal_type} {signal.symbol} @ {signal.price}"
        if hasattr(signal, 'sl') and signal.sl: log_msg += f" SL={signal.sl}"
        if hasattr(signal, 'tp') and signal.tp: log_msg += f" TP={signal.tp}"
        self.ui.terminal.log_message(log_msg)
        
        self.ui.status_bar.showMessage(f"{signal.ea_name}: {signal.signal_type} {signal.symbol} @ {signal.price}", 5000)
        event_bus.ea_signal_generated.emit(signal)
    
    def _on_ea_error(self, ea_name: str, error_msg: str):
        logger.error(f"EA Error - {ea_name}: {error_msg}")
        self.ui.status_bar.showMessage(f"EA Error - {ea_name}: {error_msg}", 10000)
        self.ui.ea_panel.refresh_table()
    
    def _on_order_rejected(self, ea_name: str, reason: str):
        logger.warning(f"Order rejected from {ea_name}: {reason}")
        self.ui.status_bar.showMessage(f"Order rejected: {reason}", 5000)

    def _on_trailing_stop_updated(self, ticket: int, sl: float):
        """Handle trailing stop update."""
        execution_service.modify_position(ticket, sl=sl)

    def closeEvent(self, event):
        """Handle application close."""
        logger.info("Application closing...")
        ea_manager.stop_all()
        self.connection_manager.disconnect()
        event.accept()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("MT5 Trading Platform")
    window = MainWindow()
    window.show()
    logger.info("Application started")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
