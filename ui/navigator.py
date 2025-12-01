"""
Navigator Widget.
Displays accounts, indicators, strategies, and scripts in a tree view.
"""
from PyQt5.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List
from core.interfaces.plugin import Plugin, Indicator, Strategy, Script

class Navigator(QDockWidget):
    """Navigator dock widget."""
    
    plugin_double_clicked = pyqtSignal(str, str) # plugin_name, plugin_type
    
    def __init__(self, parent=None):
        super().__init__("Navigator", parent)
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self._init_ui()
        
    def _init_ui(self):
        """Initialize UI components."""
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Create root items
        self.accounts_root = QTreeWidgetItem(self.tree, ["Accounts"])
        self.indicators_root = QTreeWidgetItem(self.tree, ["Indicators"])
        self.strategies_root = QTreeWidgetItem(self.tree, ["Expert Advisors"])
        self.scripts_root = QTreeWidgetItem(self.tree, ["Scripts"])
        
        # Add dummy account
        demo_acc = QTreeWidgetItem(self.accounts_root, ["Demo Account (10000 USD)"])
        demo_acc.setIcon(0, self.style().standardIcon(self.style().SP_ComputerIcon))
        
        self.tree.expandAll()
        self.setWidget(self.tree)
        
    def update_plugins(self, plugins: List[Plugin]):
        """Update the tree with available plugins."""
        # Clear existing plugin items
        self.indicators_root.takeChildren()
        self.strategies_root.takeChildren()
        self.scripts_root.takeChildren()
        
        for plugin in plugins:
            if isinstance(plugin, Indicator):
                item = QTreeWidgetItem(self.indicators_root, [plugin.name])
                item.setToolTip(0, plugin.description)
                item.setData(0, Qt.UserRole, "Indicator")
            elif isinstance(plugin, Strategy):
                item = QTreeWidgetItem(self.strategies_root, [plugin.name])
                item.setToolTip(0, plugin.description)
                item.setData(0, Qt.UserRole, "Strategy")
            elif isinstance(plugin, Script):
                item = QTreeWidgetItem(self.scripts_root, [plugin.name])
                item.setToolTip(0, plugin.description)
                item.setData(0, Qt.UserRole, "Script")
                
        self.tree.expandAll()

    def _on_item_double_clicked(self, item, column):
        """Handle double click on tree item."""
        plugin_type = item.data(0, Qt.UserRole)
        if plugin_type:
            plugin_name = item.text(0)
            self.plugin_double_clicked.emit(plugin_name, plugin_type)
