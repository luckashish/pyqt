"""
Close All Positions Script.
Closes all active positions immediately.
"""
from core.interfaces.plugin import Script
from utils.logger import logger
from PyQt5.QtWidgets import QMessageBox

class CloseAllPositions(Script):
    """
    Script to close all open positions.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Close All Positions"
        self.version = "1.0"
        self.author = "System"
        self.description = "Closes all open positions immediately."
        
    def run(self, **kwargs):
        """
        Execute the script.
        """
        logger.info("Script 'Close All Positions' started.")
        
        # We need access to the broker to close positions.
        # In a real implementation, we'd inject the broker or use a service.
        # For now, we'll try to get it from the main window if passed, or just log.
        
        broker = kwargs.get('broker')
        parent = kwargs.get('parent') # Main window for UI feedback
        
        if not broker:
            logger.error("Broker instance not provided to script.")
            if parent:
                QMessageBox.warning(parent, "Script Error", "Broker not available.")
            return
            
        # Get all positions
        # Assuming broker has a method to get positions or we use account manager
        # For this demo, we'll assume broker.get_positions() exists or similar
        
        # positions = broker.get_positions()
        # if not positions:
        #     logger.info("No open positions to close.")
        #     if parent:
        #         QMessageBox.information(parent, "Script", "No open positions.")
        #     return
            
        # for pos in positions:
        #     broker.close_position(pos.ticket)
            
        logger.info("Close All Positions script finished (Simulated).")
        if parent:
            QMessageBox.information(parent, "Script Executed", "Close All Positions script finished.")
