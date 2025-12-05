#!/usr/bin/env python3
"""
Theme manager for PyQt6 GUI.
Centralized theme management and application.
"""
from typing import Dict, Optional, List, Callable
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QObject, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    
    class MockSignal:
        def emit(self, *args, **kwargs):
            pass
        def connect(self, *args, **kwargs):
            pass
    
    def pyqtSignal(*args, **kwargs):
        return MockSignal()
    
    class QObject:
        def __init__(self):
            pass

from .base import BaseTheme
from .default.theme import DefaultTheme
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class ThemeManager(QObject):
    """
    Centralized theme management for the PyQt6 application.
    Handles theme registration, switching, and application with dynamic loading.
    """
    
    # Signals
    theme_changed = pyqtSignal(str)  # theme_name
    theme_registered = pyqtSignal(str)  # theme_name
    
    def __init__(self):
        """Initialize the theme manager."""
        super().__init__()
        
        self._themes: Dict[str, BaseTheme] = {}
        self._current_theme: Optional[BaseTheme] = None
        self._app: Optional[QApplication] = None
        self._theme_change_callbacks: List[Callable[[str], None]] = []
        
        # Register built-in themes
        self._register_builtin_themes()
        
        logger.info("Theme manager initialized")
    
    def _register_builtin_themes(self):
        """Register built-in themes."""
        try:
            # Register default theme
            default_theme = DefaultTheme()
            self.register_theme(default_theme)
            
            logger.debug("Built-in themes registered")
        except Exception as e:
            logger.error(f"Failed to register built-in themes: {e}")
    
    def register_theme(self, theme: BaseTheme):
        """
        Register a theme.
        
        Args:
            theme: Theme instance to register
        """
        try:
            self._themes[theme.name] = theme
            self.theme_registered.emit(theme.name)
            logger.info(f"Theme registered: {theme.display_name} ({theme.name})")
        except Exception as e:
            logger.error(f"Failed to register theme {theme.name}: {e}")
            raise
    
    def unregister_theme(self, theme_name: str):
        """
        Unregister a theme.
        
        Args:
            theme_name: Name of theme to unregister
        """
        if theme_name in self._themes:
            del self._themes[theme_name]
            logger.info(f"Theme unregistered: {theme_name}")
        else:
            logger.warning(f"Attempted to unregister unknown theme: {theme_name}")
    
    def get_available_themes(self) -> Dict[str, str]:
        """
        Get list of available themes.
        
        Returns:
            Dictionary mapping theme names to display names
        """
        return {name: theme.display_name for name, theme in self._themes.items()}
    
    def get_theme_info(self, theme_name: str) -> Optional[Dict]:
        """
        Get detailed information about a theme.
        
        Args:
            theme_name: Name of theme to get info for
            
        Returns:
            Theme information dictionary or None if not found
        """
        theme = self._themes.get(theme_name)
        return theme.get_theme_info() if theme else None
    
    def set_application(self, app: QApplication):
        """
        Set the QApplication instance for theme application.
        
        Args:
            app: QApplication instance
        """
        self._app = app
        logger.debug("QApplication set for theme manager")
    
    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply a theme to the application.
        
        Args:
            theme_name: Name of theme to apply
            
        Returns:
            True if theme was applied successfully
        """
        if not PYQT6_AVAILABLE:
            logger.error("PyQt6 not available, cannot apply theme")
            return False
        
        if theme_name not in self._themes:
            logger.error(f"Theme not found: {theme_name}")
            return False
        
        if not self._app:
            # Try to get current QApplication instance
            self._app = QApplication.instance()
            if not self._app:
                logger.error("No QApplication instance available")
                return False
        
        try:
            theme = self._themes[theme_name]
            theme.apply(self._app)
            
            old_theme_name = self._current_theme.name if self._current_theme else None
            self._current_theme = theme
            
            # Emit signal
            self.theme_changed.emit(theme_name)
            
            # Call callbacks
            for callback in self._theme_change_callbacks:
                try:
                    callback(theme_name)
                except Exception as e:
                    logger.error(f"Error in theme change callback: {e}")
            
            logger.info(f"Theme applied: {theme.display_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply theme {theme_name}: {e}")
            return False
    
    def get_current_theme(self) -> Optional[BaseTheme]:
        """
        Get the currently active theme.
        
        Returns:
            Current theme instance or None
        """
        return self._current_theme
    
    def get_current_theme_name(self) -> Optional[str]:
        """
        Get the name of the currently active theme.
        
        Returns:
            Current theme name or None
        """
        return self._current_theme.name if self._current_theme else None
    
    def add_theme_change_callback(self, callback: Callable[[str], None]):
        """
        Add a callback to be called when theme changes.
        
        Args:
            callback: Function to call with theme name
        """
        self._theme_change_callbacks.append(callback)
    
    def remove_theme_change_callback(self, callback: Callable[[str], None]):
        """
        Remove a theme change callback.
        
        Args:
            callback: Callback function to remove
        """
        if callback in self._theme_change_callbacks:
            self._theme_change_callbacks.remove(callback)
    
    def load_theme_from_directory(self, theme_dir: Path) -> bool:
        """
        Dynamically load a theme from a directory.
        
        Args:
            theme_dir: Directory containing theme files
            
        Returns:
            True if theme was loaded successfully
        """
        try:
            # Look for theme.py file
            theme_file = theme_dir / "theme.py"
            if not theme_file.exists():
                logger.error(f"No theme.py file found in {theme_dir}")
                return False
            
            # Dynamic import of theme module
            import importlib.util
            spec = importlib.util.spec_from_file_location("custom_theme", theme_file)
            if not spec or not spec.loader:
                logger.error(f"Failed to create module spec for {theme_file}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for theme class (should inherit from BaseTheme)
            theme_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseTheme) and 
                    attr != BaseTheme):
                    theme_class = attr
                    break
            
            if not theme_class:
                logger.error(f"No BaseTheme subclass found in {theme_file}")
                return False
            
            # Instantiate and register theme
            theme_instance = theme_class()
            self.register_theme(theme_instance)
            
            logger.info(f"Dynamic theme loaded: {theme_instance.display_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load theme from {theme_dir}: {e}")
            return False
    
    def scan_for_themes(self, themes_directory: Path):
        """
        Scan a directory for theme subdirectories and load them.
        
        Args:
            themes_directory: Directory to scan for themes
        """
        if not themes_directory.exists():
            logger.warning(f"Themes directory does not exist: {themes_directory}")
            return
        
        logger.info(f"Scanning for themes in: {themes_directory}")
        
        for item in themes_directory.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                try:
                    self.load_theme_from_directory(item)
                except Exception as e:
                    logger.error(f"Error loading theme from {item}: {e}")


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """
    Get the global theme manager instance.
    
    Returns:
        ThemeManager singleton instance
    """
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager