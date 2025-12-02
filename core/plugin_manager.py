"""
Plugin Manager.
Handles discovery, loading, and lifecycle management of plugins.
"""
import os
import importlib.util
import inspect
from typing import Dict, List, Type
from core.interfaces.plugin import Plugin, Indicator, Strategy, Script
from utils.logger import logger
from core.event_bus import event_bus

class PluginManager:
    """
    Manages the lifecycle of plugins (Indicators, Strategies, Scripts).
    """
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.indicators: Dict[str, Indicator] = {}
        self.strategies: Dict[str, Strategy] = {}
        self.scripts: Dict[str, Script] = {}
        
        # Paths
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.plugin_dirs = {
            "indicators": os.path.join(self.base_path, "plugins", "indicators"),
            "strategies": os.path.join(self.base_path, "plugins", "strategies"),
            "scripts": os.path.join(self.base_path, "plugins", "scripts"),
        }
        
    def discover_plugins(self):
        """Scan plugin directories and load available plugins."""
        logger.info("Discovering plugins...")
        
        for category, path in self.plugin_dirs.items():
            if not os.path.exists(path):
                logger.warning(f"Plugin directory not found: {path}")
                continue
                
            for filename in os.listdir(path):
                if filename.endswith(".py") and not filename.startswith("__"):
                    self._load_plugin_from_file(os.path.join(path, filename), category)
                    
        logger.info(f"Loaded {len(self.plugins)} plugins.")

    def _load_plugin_from_file(self, filepath: str, category: str):
        """Load a plugin module from a file."""
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if not spec or not spec.loader:
                return
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                    # Avoid loading base classes if they are imported
                    if obj in [Indicator, Strategy, Script]:
                        continue
                    
                    # Skip ExpertAdvisor base class (it's abstract)
                    if obj.__name__ == 'ExpertAdvisor':
                        continue
                    
                    # Skip any abstract classes
                    if inspect.isabstract(obj):
                        continue
                        
                    # Instantiate and register
                    try:
                        plugin_instance = obj()
                        self.register_plugin(plugin_instance)
                        logger.info(f"Loaded plugin: {plugin_instance.name} ({category})")
                    except Exception as e:
                        logger.error(f"Failed to instantiate plugin {name}: {e}")
                        
        except Exception as e:
            logger.error(f"Error loading plugin from {filepath}: {e}")

    def register_plugin(self, plugin: Plugin):
        """Register a plugin instance."""
        self.plugins[plugin.name] = plugin
        
        if isinstance(plugin, Indicator):
            self.indicators[plugin.name] = plugin
        elif isinstance(plugin, Strategy):
            self.strategies[plugin.name] = plugin
            # Connect strategy to event bus
            event_bus.tick_received.connect(plugin.on_tick)
            event_bus.candle_updated.connect(plugin.on_bar)
        elif isinstance(plugin, Script):
            self.scripts[plugin.name] = plugin
            
        plugin.on_load()

    def get_indicator(self, name: str) -> Indicator:
        return self.indicators.get(name)

    def get_strategy(self, name: str) -> Strategy:
        return self.strategies.get(name)

    def get_script(self, name: str) -> Script:
        return self.scripts.get(name)
        
    def get_all_plugins(self) -> List[Plugin]:
        return list(self.plugins.values())

# Global instance
plugin_manager = PluginManager()
