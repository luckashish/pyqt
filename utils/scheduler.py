"""Task scheduler for periodic operations."""
from PyQt5.QtCore import QTimer, QObject


class Scheduler(QObject):
    """Schedule and manage periodic tasks."""
    
    def __init__(self):
        super().__init__()
        self._timers = {}
    
    def schedule(self, name: str, interval_ms: int, callback):
        """Schedule a recurring task."""
        if name in self._timers:
            self._timers[name].stop()
        
        timer = QTimer(self)
        timer.timeout.connect(callback)
        timer.start(interval_ms)
        self._timers[name] = timer
    
    def cancel(self, name: str):
        """Cancel a scheduled task."""
        if name in self._timers:
            self._timers[name].stop()
            del self._timers[name]
    
    def cancel_all(self):
        """Cancel all scheduled tasks."""
        for timer in self._timers.values():
            timer.stop()
        self._timers.clear()


# Global scheduler instance
scheduler = Scheduler()
