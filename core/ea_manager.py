"""
Expert Advisor Manager.
Manages multiple EAs, handles their lifecycle, and coordinates execution.
"""
from typing import Dict, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal

from core.ea_base import ExpertAdvisor
from data.models import Symbol, OHLCData, Order, EASignal, EAState
from utils.logger import logger
from utils.symbol_normalizer import symbol_normalizer


class EAManager(QObject):
    """
    Manages all Expert Advisors in the system.
    Singleton pattern for centralized EA management.
    """
    
    # Signals
    ea_registered = pyqtSignal(str)  # EA name
    ea_unregistered = pyqtSignal(str)  # EA name
    ea_started = pyqtSignal(str)  # EA name
    ea_stopped = pyqtSignal(str)  # EA name
    ea_error = pyqtSignal(str, str)  # EA name, error message
    ea_updated = pyqtSignal(str)  # EA name (for stats update)
    signal_generated = pyqtSignal(object)  # EASignal
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance
        
    def __init__(self):
        """Initialize EA Manager."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        
        # Storage
        self.eas: Dict[str, ExpertAdvisor] = {}  # name -> EA instance
        self.running_eas: List[str] = []  # List of running EA names
        
        # Limits
        self.max_concurrent_eas = 5
        
        logger.info("EA Manager initialized")
        
    def register_ea(self, ea: ExpertAdvisor) -> bool:
        """
        Register an EA with the manager.
        
        Args:
            ea: Expert Advisor instance
            
        Returns:
            True if registered successfully
        """
        if ea.name in self.eas:
            logger.warning(f"EA '{ea.name}' already registered")
            return False
            
        # Connect EA signals
        ea.signal_generated.connect(self._on_ea_signal)
        ea.state_changed.connect(self._on_ea_state_changed)
        ea.error_occurred.connect(lambda msg: self._on_ea_error(ea.name, msg))
        
        self.eas[ea.name] = ea
        self.ea_registered.emit(ea.name)
        
        logger.info(f"Registered EA: {ea.name}")
        return True
        
    def unregister_ea(self, ea_name: str) -> bool:
        """
        Unregister an EA.
        
        Args:
            ea_name: EA name
            
        Returns:
            True if unregistered successfully
        """
        if ea_name not in self.eas:
            logger.warning(f"EA '{ea_name}' not found")
            return False
            
        # Stop if running
        if ea_name in self.running_eas:
            self.stop_ea(ea_name)
            
        # Remove EA
        ea = self.eas.pop(ea_name)
        
        # Disconnect signals
        try:
            ea.signal_generated.disconnect(self._on_ea_signal)
            ea.state_changed.disconnect(self._on_ea_state_changed)
        except:
            pass
            
        self.ea_unregistered.emit(ea_name)
        logger.info(f"Unregistered EA: {ea_name}")
        return True
        
    def start_ea(self, ea_name: str) -> bool:
        """
        Start an EA.
        
        Args:
            ea_name: EA name
            
        Returns:
            True if started successfully
        """
        if ea_name not in self.eas:
            logger.error(f"EA '{ea_name}' not found")
            return False
            
        if ea_name in self.running_eas:
            logger.warning(f"EA '{ea_name}' already running")
            return False
            
        # Check concurrent EA limit
        if len(self.running_eas) >= self.max_concurrent_eas:
            logger.error(f"Maximum concurrent EAs ({self.max_concurrent_eas}) reached")
            return False
            
        ea = self.eas[ea_name]
        
        try:
            ea.start()
            self.running_eas.append(ea_name)
            self.ea_started.emit(ea_name)
            return True
        except Exception as e:
            logger.error(f"Failed to start EA '{ea_name}': {e}")
            return False
            
    def stop_ea(self, ea_name: str) -> bool:
        """
        Stop an EA.
        
        Args:
            ea_name: EA name
            
        Returns:
            True if stopped successfully
        """
        if ea_name not in self.eas:
            logger.error(f"EA '{ea_name}' not found")
            return False
            
        if ea_name not in self.running_eas:
            logger.warning(f"EA '{ea_name}' not running")
            return False
            
        ea = self.eas[ea_name]
        
        try:
            ea.stop()
            self.running_eas.remove(ea_name)
            self.ea_stopped.emit(ea_name)
            return True
        except Exception as e:
            logger.error(f"Failed to stop EA '{ea_name}': {e}")
            return False
            
    def pause_ea(self, ea_name: str) -> bool:
        """Pause an EA."""
        if ea_name not in self.eas:
            return False
            
        ea = self.eas[ea_name]
        ea.pause()
        return True
        
    def resume_ea(self, ea_name: str) -> bool:
        """Resume an EA."""
        if ea_name not in self.eas:
            return False
            
        ea = self.eas[ea_name]
        ea.resume()
        return True
        
    def stop_all(self):
        """Stop all running EAs."""
        for ea_name in list(self.running_eas):
            self.stop_ea(ea_name)
            
        logger.info("All EAs stopped")
        
    def on_tick(self, symbol: Symbol):
        """
        Route tick to relevant EAs.
        
        Args:
            symbol: Tick data
        """
        for ea_name in self.running_eas:
            ea = self.eas[ea_name]
            
            # Only send tick if EA is monitoring this symbol (with format matching)
            if ea.config:
                if symbol_normalizer.match(ea.config.symbol, symbol.name):
                    try:
                        ea.on_tick(symbol)
                    except Exception as e:
                        logger.error(f"Error in EA '{ea_name}' on_tick: {e}")
                        self._on_ea_error(ea_name, str(e))
                    
    def on_bar(self, symbol: str, bar: OHLCData):
        """
        Route bar to relevant EAs.
        
        Args:
            symbol: Symbol name
            bar: Closed bar data
        """
        logger.info(f"EA Manager: Received bar for {symbol}, routing to {len(self.running_eas)} running EAs")
        
        for ea_name in self.running_eas:
            ea = self.eas[ea_name]
            
            # Only send bar if EA is monitoring this symbol (with format matching)
            if ea.config:
                match_result = symbol_normalizer.match(ea.config.symbol, symbol)
                
                # Log matching attempts at INFO level for debugging
                if match_result:
                    logger.info(f"[OK] Routing bar to '{ea_name}': {symbol}")
                
                if match_result:
                    try:
                        ea.on_bar(bar)
                    except Exception as e:
                        logger.error(f"Error in EA '{ea_name}' on_bar: {e}")
                        self._on_ea_error(ea_name, str(e))
                    
    def on_order_update(self, order: Order):
        """
        Route order update to relevant EAs.
        
        Args:
            order: Updated order
        """
        for ea_name in self.running_eas:
            ea = self.eas[ea_name]
            
            # Only send update if order is from this EA or symbol matches
            if order.comment.startswith(ea.name) or (ea.config and ea.config.symbol == order.symbol):
                logger.info(f"EAManager: Routing order {order.ticket} ({order.status.value}) to {ea_name}")
                try:
                    ea.on_order_update(order)
                except Exception as e:
                    logger.error(f"Error in EA '{ea_name}' on_order_update: {e}")
                    
    def get_ea(self, ea_name: str) -> Optional[ExpertAdvisor]:
        """Get EA instance by name."""
        return self.eas.get(ea_name)
        
    def get_all_eas(self) -> List[str]:
        """Get list of all registered EA names."""
        return list(self.eas.keys())
        
    def get_running_eas(self) -> List[str]:
        """Get list of running EA names."""
        return list(self.running_eas)
        
    def get_ea_state(self, ea_name: str) -> Optional[EAState]:
        """Get EA state."""
        ea = self.get_ea(ea_name)
        return ea.get_state() if ea else None
        
    def get_all_states(self) -> Dict[str, EAState]:
        """Get states of all EAs."""
        return {name: ea.get_state() for name, ea in self.eas.items()}
        
    def _on_ea_signal(self, signal: EASignal):
        """Handle signal from EA."""
        logger.info(f"Signal from {signal.ea_name}: {signal.signal_type} {signal.symbol} @ {signal.price}")
        self.signal_generated.emit(signal)
        
    def _on_ea_state_changed(self, state: EAState):
        """Handle EA state change."""
        # Re-emit as generic update for UI
        self.ea_updated.emit(state.name)
        
    def _on_ea_error(self, ea_name: str, error_msg: str):
        """Handle EA error."""
        logger.error(f"EA '{ea_name}' error: {error_msg}")
        self.ea_error.emit(ea_name, error_msg)
        
        # Auto-pause EA on error
        ea = self.eas.get(ea_name)
        if ea and ea.is_running and not ea.is_paused:
            ea.pause()
            
    def set_max_concurrent_eas(self, limit: int):
        """Set maximum concurrent EAs."""
        self.max_concurrent_eas = max(1, limit)
        logger.info(f"Max concurrent EAs set to {self.max_concurrent_eas}")


# Global EA Manager instance
ea_manager = EAManager()
