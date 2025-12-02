"""
EA Control Panel Widget.
Displays list of EAs with controls and status monitoring.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QGroupBox, QHeaderView, QMenu, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor

from core.ea_manager import ea_manager
from data.models import EAState
from ui.ea_config_dialog import EAConfigDialog
from utils.logger import logger


class EAControlPanel(QWidget):
    """
    Expert Advisor Control Panel.
    Displays registered EAs with start/stop controls and status monitoring.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel("Expert Advisors")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)
        
        # EA Table
        self.ea_table = QTableWidget()
        self.ea_table.setColumnCount(7)
        self.ea_table.setHorizontalHeaderLabels([
            "EA Name", "Status", "Symbol", "Open Pos", "Trades", "Profit", "Win Rate"
        ])
        
        # Configure table
        header = self.ea_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        
        self.ea_table.setColumnWidth(1, 80)
        self.ea_table.setColumnWidth(2, 100)
        self.ea_table.setColumnWidth(3, 70)
        self.ea_table.setColumnWidth(4, 60)
        self.ea_table.setColumnWidth(5, 80)
        self.ea_table.setColumnWidth(6, 70)
        
        self.ea_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.ea_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ea_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.ea_table)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.btn_start = QPushButton("Start")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_start.clicked.connect(self.start_selected_ea)
        
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_selected_ea)
        
        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        self.btn_pause.clicked.connect(self.pause_selected_ea)
        
        self.btn_config = QPushButton("Configure")
        self.btn_config.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_config.clicked.connect(self.configure_selected_ea)
        
        self.btn_stop_all = QPushButton("Stop All")
        self.btn_stop_all.setStyleSheet("background-color: #9E9E9E; color: white; font-weight: bold;")
        self.btn_stop_all.clicked.connect(self.stop_all_eas)
        
        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_stop)
        button_layout.addWidget(self.btn_config)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_stop_all)
        
        layout.addLayout(button_layout)
        
        # Statistics box
        stats_group = QGroupBox("Overall Statistics")
        stats_layout = QHBoxLayout(stats_group)
        
        self.lbl_running = QLabel("Running: 0")
        self.lbl_total_profit = QLabel("Total Profit: $0.00")
        self.lbl_total_trades = QLabel("Total Trades: 0")
        
        stats_layout.addWidget(self.lbl_running)
        stats_layout.addWidget(self.lbl_total_profit)
        stats_layout.addWidget(self.lbl_total_trades)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
    def connect_signals(self):
        """Connect to EA Manager signals."""
        ea_manager.ea_registered.connect(self.on_ea_registered)
        ea_manager.ea_unregistered.connect(self.on_ea_unregistered)
        ea_manager.ea_started.connect(self.refresh_table)
        ea_manager.ea_stopped.connect(self.refresh_table)
        ea_manager.ea_error.connect(self.on_ea_error)
        
    @pyqtSlot(str)
    def on_ea_registered(self, ea_name: str):
        """Handle EA registration."""
        logger.info(f"UI: EA registered - {ea_name}")
        self.refresh_table()
        
    @pyqtSlot(str)
    def on_ea_unregistered(self, ea_name: str):
        """Handle EA unregistration."""
        logger.info(f"UI: EA unregistered - {ea_name}")
        self.refresh_table()
        
    @pyqtSlot(str, str)
    def on_ea_error(self, ea_name: str, error: str):
        """Handle EA error."""
        logger.error(f"UI: EA error - {ea_name}: {error}")
        self.refresh_table()
        
    def refresh_table(self):
        """Refresh EA table with current states."""
        # Get all EA states
        states = ea_manager.get_all_states()
        
        # Update table
        self.ea_table.setRowCount(len(states))
        
        total_profit = 0.0
        total_trades = 0
        running_count = 0
        
        for row, (ea_name, state) in enumerate(states.items()):
            # EA Name
            name_item = QTableWidgetItem(ea_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.ea_table.setItem(row, 0, name_item)
            
            # Status
            status_item = QTableWidgetItem(state.status.upper())
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            
            # Color code status
            if state.status == "running":
                status_item.setForeground(QColor("#4CAF50"))
                running_count += 1
            elif state.status == "stopped":
                status_item.setForeground(QColor("#9E9E9E"))
            elif state.status == "paused":
                status_item.setForeground(QColor("#FF9800"))
            elif state.status == "error":
                status_item.setForeground(QColor("#f44336"))
                
            self.ea_table.setItem(row, 1, status_item)
            
            # Symbol
            symbol_item = QTableWidgetItem(state.symbol)
            symbol_item.setFlags(symbol_item.flags() & ~Qt.ItemIsEditable)
            self.ea_table.setItem(row, 2, symbol_item)
            
            # Open Positions
            pos_item = QTableWidgetItem(str(state.open_positions))
            pos_item.setFlags(pos_item.flags() & ~Qt.ItemIsEditable)
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.ea_table.setItem(row, 3, pos_item)
            
            # Total Trades
            trades_item = QTableWidgetItem(str(state.total_trades))
            trades_item.setFlags(trades_item.flags() & ~Qt.ItemIsEditable)
            trades_item.setTextAlignment(Qt.AlignCenter)
            self.ea_table.setItem(row, 4, trades_item)
            
            # Profit
            profit_item = QTableWidgetItem(f"${state.profit:.2f}")
            profit_item.setFlags(profit_item.flags() & ~Qt.ItemIsEditable)
            profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            if state.profit > 0:
                profit_item.setForeground(QColor("#4CAF50"))
            elif state.profit < 0:
                profit_item.setForeground(QColor("#f44336"))
                
            self.ea_table.setItem(row, 5, profit_item)
            
            # Win Rate
            wr_item = QTableWidgetItem(f"{state.win_rate:.1f}%")
            wr_item.setFlags(wr_item.flags() & ~Qt.ItemIsEditable)
            wr_item.setTextAlignment(Qt.AlignCenter)
            self.ea_table.setItem(row, 6, wr_item)
            
            # Accumulate stats
            total_profit += state.profit
            total_trades += state.total_trades
            
        # Update statistics
        self.lbl_running.setText(f"Running: {running_count}/{len(states)}")
        self.lbl_total_profit.setText(f"Total Profit: ${total_profit:.2f}")
        
        if total_profit > 0:
            self.lbl_total_profit.setStyleSheet("color: #4CAF50; font-weight: bold;")
        elif total_profit < 0:
            self.lbl_total_profit.setStyleSheet("color: #f44336; font-weight: bold;")
        else:
            self.lbl_total_profit.setStyleSheet("")
            
        self.lbl_total_trades.setText(f"Total Trades: {total_trades}")
        
    def get_selected_ea_name(self) -> str:
        """Get selected EA name."""
        selected_rows = self.ea_table.selectedItems()
        
        if not selected_rows:
            return None
            
        row = selected_rows[0].row()
        return self.ea_table.item(row, 0).text()
        
    def start_selected_ea(self):
        """Start selected EA."""
        ea_name = self.get_selected_ea_name()
        
        if ea_name:
            success = ea_manager.start_ea(ea_name)
            
            if success:
                logger.info(f"UI: Started EA - {ea_name}")
                self.refresh_table()  # Update UI
            else:
                logger.error(f"UI: Failed to start EA - {ea_name}")
                
    def stop_selected_ea(self):
        """Stop selected EA."""
        ea_name = self.get_selected_ea_name()
        
        if ea_name:
            success = ea_manager.stop_ea(ea_name)
            
            if success:
                logger.info(f"UI: Stopped EA - {ea_name}")
                self.refresh_table()  # Update UI
            else:
                logger.error(f"UI: Failed to stop EA - {ea_name}")
                
    def pause_selected_ea(self):
        """Pause selected EA."""
        ea_name = self.get_selected_ea_name()
        
        if ea_name:
            success = ea_manager.pause_ea(ea_name)
            
            if success:
                logger.info(f"UI: Paused EA - {ea_name}")
                self.refresh_table()  # Update UI
            else:
                logger.error(f"UI: Failed to pause EA - {ea_name}")
                
    def configure_selected_ea(self):
        """Open configuration dialog for selected EA."""
        ea_name = self.get_selected_ea_name()
        
        if not ea_name:
            return
        
        # Get EA instance
        ea = ea_manager.get_ea(ea_name)
        
        if not ea:
            QMessageBox.warning(self, "EA Not Found", f"EA '{ea_name}' not found.")
            return
        
        # Check if EA is running
        if ea.is_running:
            reply = QMessageBox.question(
                self,
                "EA Running",
                f"EA '{ea_name}' is currently running.\n\n"
                "Do you want to stop it before configuring?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                ea_manager.stop_ea(ea_name)
            else:
                QMessageBox.information(
                    self,
                    "Configuration",
                    "Please stop the EA before configuring."
                )
                return
        
        # Show dialog with EA object (not config)
        dialog = EAConfigDialog(ea, self)
        
        if dialog.exec_() == dialog.Accepted:
            # Config already updated inside dialog
            self.refresh_table()
            
            QMessageBox.information(
                self,
                "Configuration Updated",
                f"EA '{ea_name}' configuration updated successfully!\n\n"
                "Restart the EA for changes to take full effect."
            )
            
            logger.info(f"UI: Configured EA - {ea_name}")
            
    def stop_all_eas(self):
        """Stop all running EAs."""
        ea_manager.stop_all()
        logger.info("UI: Stopped all EAs")
        self.refresh_table()  # Update UI
        
    def show_context_menu(self, position):
        """Show context menu."""
        menu = QMenu(self)
        
        start_action = menu.addAction("Start")
        pause_action = menu.addAction("Pause")
        stop_action = menu.addAction("Stop")
        menu.addSeparator()
        config_action = menu.addAction("Configure")
        menu.addSeparator()
        remove_action = menu.addAction("Remove")
        
        action = menu.exec_(self.ea_table.viewport().mapToGlobal(position))
        
        ea_name = self.get_selected_ea_name()
        
        if not ea_name:
            return
            
        if action == start_action:
            self.start_selected_ea()
        elif action == pause_action:
            self.pause_selected_ea()
        elif action == stop_action:
            self.stop_selected_ea()
        elif action == config_action:
            self.configure_selected_ea()
        elif action == remove_action:
            ea_manager.unregister_ea(ea_name)
