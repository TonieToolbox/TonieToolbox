#!/usr/bin/env python3
"""
Main application class for TonieToolbox PyQt6 GUI.
Coordinates the entire Qt application architecture.
"""
import sys
import signal
from typing import Optional, Callable
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication, QMessageBox
    from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject, QCoreApplication
    from PyQt6.QtGui import QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QApplication = object
    QMessageBox = object
    QTimer = object
    QThread = object
    pyqtSignal = lambda: None
    QObject = object
    QCoreApplication = object
    QIcon = object

from .main_window import MainWindow
from ..themes.manager import ThemeManager
from TonieToolbox.core.gui.i18n.manager import TranslationManager
from ..utils.threading import QtThreadManager
from TonieToolbox.core.utils import get_logger
from .... import __version__

logger = get_logger(__name__)


class TonieToolboxQtApplication:
    """
    Main PyQt6 application coordinator.
    Manages application lifecycle, window management, and component coordination.
    """
    
    def __init__(self, plugin_manager=None):
        """Initialize the Qt application.
        
        Args:
            plugin_manager: Optional PluginManager instance for plugin support
        """
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 is not available")
        
        # Create QApplication instance
        self.qt_app = QApplication.instance()
        if self.qt_app is None:
            self.qt_app = QApplication(sys.argv)
        
        # Set application properties
        self.qt_app.setApplicationName("TonieToolbox")
        self.qt_app.setApplicationVersion(__version__)
        self.qt_app.setOrganizationName("Quentendo64")
        self.qt_app.setOrganizationDomain("github.com/TonieToolbox")
        
        # Core components
        self.main_window: Optional[MainWindow] = None
        self.theme_manager: Optional[ThemeManager] = None
        self.translation_manager: Optional[TranslationManager] = None
        self.thread_manager: Optional[QtThreadManager] = None
        self.plugin_manager = plugin_manager
        
        # State
        self._ready_callbacks = []
        self._initialized = False
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("TonieToolbox Qt Application initialized")
    
    def _setup_signal_handlers(self):
        """Setup system signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.quit()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _determine_initial_language(self) -> str:
        """Determine the initial language to use."""
        try:
            from TonieToolbox.core.config import get_config_manager
            import locale
            
            config_manager = get_config_manager()
            # Use configured language if auto-detection is disabled
            auto_detect = config_manager.get_setting('gui.auto_detect_language')
            configured_lang = config_manager.get_setting('gui.language')
            logger.debug(f"Auto-detect: {auto_detect}, Configured language: {configured_lang}")
            
            if not auto_detect:
                logger.debug(f"Auto-detect disabled, using configured language: {configured_lang}")
                return configured_lang
            
            # Try to detect system language if auto-detection is enabled
            try:
                system_locale = locale.getlocale()[0]
                logger.debug(f"System locale detected: {system_locale}")
                if system_locale:
                    if system_locale.startswith('de') or system_locale.startswith('German'):
                        logger.debug("System locale is German, using de_DE")
                        return 'de_DE'
                    elif system_locale.startswith('en') or system_locale.startswith('English'):
                        logger.debug("System locale is English, using en_US")
                        return 'en_US'
                logger.debug(f"System locale '{system_locale}' not recognized, falling back to configured language")
            except Exception as e:
                logger.debug(f"Failed to detect system locale: {e}")
            
            # Fall back to configured language or default
            fallback_lang = configured_lang or config_manager.get_setting('gui.fallback_language')
            logger.debug(f"Final fallback language: {fallback_lang}")
            return fallback_lang
            
        except Exception as e:
            logger.error(f"Error determining initial language: {e}")
            return "en_US"  # Ultimate fallback
    
    def _initialize_components(self):
        """Initialize all application components."""
        if self._initialized:
            return
        
        try:
            # Initialize managers in correct order
            logger.debug("Initializing theme manager...")
            self.theme_manager = ThemeManager()
            
            logger.debug("Initializing translation manager...")
            from TonieToolbox.core.gui.i18n.manager import get_translation_manager
            self.translation_manager = get_translation_manager()
            
            logger.debug("Initializing thread manager...")
            self.thread_manager = QtThreadManager()
            
            logger.debug("Creating main window...")
            self.main_window = MainWindow(
                theme_manager=self.theme_manager,
                translation_manager=self.translation_manager,
                thread_manager=self.thread_manager,
                plugin_manager=self.plugin_manager
            )
            
            # Apply initial theme
            if self.theme_manager:
                self.theme_manager.apply_theme("default")
            
            # Set initial language from configuration
            if self.translation_manager:
                initial_language = self._determine_initial_language()
                logger.info(f"Setting initial language to: {initial_language}")
                self.translation_manager.set_language(initial_language)
            
            # Initialize and enable GUI plugins
            if self.plugin_manager:
                self._initialize_plugins()
            
            self._initialized = True
            logger.info("All components initialized successfully")
            
            # Call ready callbacks
            for callback in self._ready_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in ready callback: {e}")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            self._show_error("Initialization Error", 
                           f"Failed to initialize application components:\n{e}")
            raise
    
    def _initialize_plugins(self):
        """Initialize and enable GUI plugins in dependency-resolved order."""
        try:
            from ...plugins.base import PluginType, PluginContext
            
            # Get GUI component registry from main window
            if not self.main_window:
                logger.warning("Cannot initialize plugins - main window not available")
                return
            
            gui_registry = self.main_window.get_gui_registry()
            if not gui_registry:
                logger.warning("Cannot initialize plugins - GUI registry not available")
                return
            
            # Register core services for plugin access
            player_controller = self.get_player_controller()
            if player_controller:
                PluginContext._shared_services['player_controller'] = player_controller
                logger.debug("Registered player controller as shared service for plugins")
            
            # Register main window
            if self.main_window:
                PluginContext._shared_services['main_window'] = self.main_window
                logger.debug("Registered main window as shared service for plugins")
            
            # Register application instance
            PluginContext._shared_services['application'] = self
            logger.debug("Registered application as shared service for plugins")
            
            # Get all loaded plugins and resolve initialization order based on dependencies
            loaded_plugins = self.plugin_manager.get_loaded_plugins()
            logger.debug(f"Resolving initialization order for {len(loaded_plugins)} plugins...")
            
            # Use dependency-aware ordering
            ordered_plugins = self.plugin_manager._resolve_initialization_order(loaded_plugins)
            logger.info(f"Plugin initialization order (dependency-resolved): {ordered_plugins}")
            
            for plugin_id in ordered_plugins:
                try:
                    # Initialize plugin
                    if self.plugin_manager.initialize_plugin(plugin_id):
                        plugin = self.plugin_manager.get_plugin(plugin_id)
                        
                        # Register GUI components if it's a GUI plugin
                        if plugin and hasattr(plugin, 'register_components'):
                            plugin.register_components(gui_registry)
                            logger.debug(f"Registered components for plugin: {plugin_id}")
                        
                        # Enable all loaded plugins (disabled ones were already filtered out during load)
                        self.plugin_manager.enable_plugin(plugin_id)
                        logger.info(f"Plugin enabled: {plugin_id}")
                    else:
                        logger.warning(f"Failed to initialize plugin: {plugin_id}")
                        
                except Exception as e:
                    logger.error(f"Error initializing plugin {plugin_id}: {e}")
            
            # Update menus and tabs with registered plugin components
            if self.main_window:
                self.main_window.update_plugin_menus()
                self.main_window.update_plugin_tabs()
                self.main_window.update_title_bar_actions()
                
        except Exception as e:
            logger.error(f"Failed to initialize plugins: {e}")
    
    def _show_error(self, title: str, message: str):
        """Show an error dialog."""
        if PYQT6_AVAILABLE:
            msg_box = QMessageBox()
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.exec()
    
    def on_ready(self, callback: Callable):
        """Register a callback to be called when the application is ready."""
        self._ready_callbacks.append(callback)
    
    def get_player_controller(self):
        """Get the player controller instance."""
        if self.main_window:
            return self.main_window.get_player_controller()
        return None
    
    def get_main_window(self) -> Optional[MainWindow]:
        """Get the main window instance."""
        return self.main_window
    
    def show(self):
        """Show the main window."""
        if not self._initialized:
            self._initialize_components()
        
        if self.main_window:
            self.main_window.show()
            logger.info("Main window shown")
    
    def run(self) -> int:
        """Run the Qt application event loop."""
        try:
            # Initialize components and show window
            self.show()
            
            # Start the Qt event loop
            logger.info("Starting Qt application event loop")
            return self.qt_app.exec()
            
        except Exception as e:
            logger.error(f"Application run failed: {e}")
            self._show_error("Application Error", f"Application failed to run:\n{e}")
            return 1
        finally:
            self.cleanup()
    
    def quit(self):
        """Quit the application gracefully."""
        logger.info("Quitting application...")
        
        if self.main_window:
            self.main_window.close()
        
        if self.qt_app:
            self.qt_app.quit()
    
    def cleanup(self):
        """Cleanup resources before exit."""
        logger.debug("Cleaning up application resources...")
        
        try:
            if self.thread_manager:
                self.thread_manager.shutdown()
            
            # Event bridge cleanup no longer needed
            
            if self.main_window:
                self.main_window.cleanup()
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("Application cleanup completed")