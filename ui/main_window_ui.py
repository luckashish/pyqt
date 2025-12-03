import os
from PyQt5.QtWidgets import (
    QDockWidget, QTabWidget, QWidget, QVBoxLayout, QLabel, 
    QPushButton, QAction, QToolBar, QStatusBar, QMessageBox, QMenu
)
from PyQt5.QtCore import Qt
from utils.logger import logger
from ui.market_watch import MarketWatch
from ui.navigator import Navigator
from ui.terminal import Terminal
from ui.ea_control_panel import EAControlPanel
from core.ea_manager import ea_manager

class MainWindowUI:
    """
    Handles the initialization and setup of the Main Window UI components.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.market_watch = None
        self.navigator = None
        self.terminal = None
        self.ea_panel = None
        self.chart_tabs = None
        self.status_bar = None
        self.connection_label = None
        self.time_label = None

    def init_ui(self, broker):
        """Initialize the user interface."""
        # Create menu bar
        self._create_menu_bar()
        
        # Create toolbar
        self._create_toolbar()
        
        # Create central widget (chart area)
        self._create_chart_area()
        
        # Create Market Watch dock (left)
        self.market_watch = MarketWatch(self.main_window)
        self.market_watch.symbol_double_clicked.connect(self.main_window._fetch_chart_data)
        self.market_watch.symbol_added.connect(self.main_window._on_symbol_added)
        self.main_window.addDockWidget(Qt.LeftDockWidgetArea, self.market_watch)
        
        # Create Navigator dock (left, below market watch)
        self._create_navigator()
        
        # Create Terminal dock (bottom)
        self.terminal = Terminal(broker, self.main_window)
        self.main_window.addDockWidget(Qt.BottomDockWidgetArea, self.terminal)
        
        # Create EA Control Panel dock (right)
        self.ea_panel = EAControlPanel(self.main_window)
        ea_dock = QDockWidget("Expert Advisors", self.main_window)
        ea_dock.setWidget(self.ea_panel)
        self.main_window.addDockWidget(Qt.RightDockWidgetArea, ea_dock)
        
        # Create status bar
        self._create_status_bar()
        
        # Apply stylesheet
        self._apply_stylesheet()
        
        logger.info("UI initialized successfully")

    def _create_menu_bar(self):
        """Create menu bar."""
        menubar = self.main_window.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        new_chart_action = QAction("New Chart", self.main_window)
        file_menu.addAction(new_chart_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self.main_window)
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Market Watch")
        view_menu.addAction("Navigator")
        view_menu.addAction("Terminal")
        
        # Insert menu
        insert_menu = menubar.addMenu("Insert")
        insert_menu.addAction("Indicators")
        insert_menu.addAction("Objects")
        
        # Charts menu
        charts_menu = menubar.addMenu("Charts")
        charts_menu.addAction("Templates")
        charts_menu.addAction("Refresh")
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction("Options")
        tools_menu.addAction("MetaQuotes Language Editor")
        tools_menu.addSeparator()
        
        # EA sub-menu
        ea_submenu = tools_menu.addMenu("Expert Advisors")
        start_ma_ea_action = QAction("Start MA Crossover EA", self.main_window)
        start_ma_ea_action.triggered.connect(self.main_window._start_ma_crossover_ea)
        ea_submenu.addAction(start_ma_ea_action)
        
        start_breakout_ea_action = QAction("Start Bullish Breakout EA", self.main_window)
        start_breakout_ea_action.triggered.connect(self.main_window._start_bullish_breakout_ea)
        ea_submenu.addAction(start_breakout_ea_action)
        
        start_bearish_ea_action = QAction("Start Bearish Breakout EA", self.main_window)
        start_bearish_ea_action.triggered.connect(self.main_window._start_bearish_breakout_ea)
        ea_submenu.addAction(start_bearish_ea_action)
        
        start_trigger_ea_action = QAction("Start Fixed Price Trigger EA", self.main_window)
        start_trigger_ea_action.triggered.connect(self.main_window._start_fixed_price_trigger_ea)
        ea_submenu.addAction(start_trigger_ea_action)
        
        ea_submenu.addAction("Stop All EAs").triggered.connect(lambda: ea_manager.stop_all())
        
        tools_menu.addSeparator()
        
        clear_cache_action = QAction("Clear Cache", self.main_window)
        clear_cache_action.setStatusTip("Clear application cache and temporary files")
        clear_cache_action.triggered.connect(self.main_window._on_clear_cache)
        tools_menu.addAction(clear_cache_action)
        
        # Window menu
        window_menu = menubar.addMenu("Window")
        window_menu.addAction("Tile Windows")
        window_menu.addAction("Cascade Windows")
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("Help Topics")
        help_menu.addAction("About")

    def _create_toolbar(self):
        """Create main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.main_window.addToolBar(toolbar)
        
        # Add toolbar buttons (using text since we don't have icons)
        new_order_btn = QPushButton("New Order")
        new_order_btn.setToolTip("Open new order dialog")
        new_order_btn.clicked.connect(self.main_window._show_new_order_dialog)
        toolbar.addWidget(new_order_btn)
        
        toolbar.addSeparator()
        
        # Timeframe buttons
        for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN"]:
            btn = QPushButton(tf)
            btn.setFixedWidth(55)
            btn.setToolTip(f"Switch to {tf} timeframe")
            btn.clicked.connect(lambda checked, t=tf: self.main_window._change_timeframe(t))
            toolbar.addWidget(btn)
        
        toolbar.addSeparator()
        
        # Chart type buttons
        toolbar.addWidget(QPushButton("Candlestick"))
        toolbar.addWidget(QPushButton("Bar"))
        toolbar.addWidget(QPushButton("Line"))

    def _create_chart_area(self):
        """Create central chart area with tabs."""
        # Create tab widget for multiple charts
        self.chart_tabs = QTabWidget()
        self.chart_tabs.setTabsClosable(True)
        self.chart_tabs.setMovable(True)
        self.chart_tabs.tabCloseRequested.connect(self.main_window._on_tab_close)
        
        self.main_window.setCentralWidget(self.chart_tabs)

    def _create_navigator(self):
        """Create Navigator dock."""
        self.navigator = Navigator(self.main_window)
        self.navigator.plugin_double_clicked.connect(self.main_window._on_plugin_double_clicked)
        self.main_window.addDockWidget(Qt.LeftDockWidgetArea, self.navigator)

    def _create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.main_window.setStatusBar(self.status_bar)
        
        self.connection_label = QLabel("Not Connected")
        self.connection_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.connection_label)
        
        self.time_label = QLabel("00:00:00")
        self.status_bar.addPermanentWidget(self.time_label)
        
        self.status_bar.showMessage("Ready", 3000)

    def _apply_stylesheet(self):
        """Apply dark theme stylesheet."""
        if os.path.exists("resources/styles.qss"):
            with open("resources/styles.qss", "r") as f:
                self.main_window.setStyleSheet(f.read())
            logger.info("Stylesheet applied")
        else:
            logger.warning("Stylesheet file not found")
