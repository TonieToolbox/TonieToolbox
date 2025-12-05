#!/usr/bin/env python3
"""
Base theme class for PyQt6 GUI themes.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QPalette, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QApplication = object
    QObject = object
    pyqtSignal = lambda: None
    QPalette = object
    QColor = object

from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class BaseTheme(ABC):
    """
    Abstract base class for PyQt6 themes.
    Defines the interface for theme implementation.
    """
    
    def __init__(self, name: str, display_name: str):
        """
        Initialize the theme.
        
        Args:
            name: Internal theme name (used for identification)
            display_name: Human-readable theme name
        """
        self.name = name
        self.display_name = display_name
        self._style_sheet: Optional[str] = None
        self._palette: Optional[QPalette] = None
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Get theme description."""
        pass
    
    @property
    @abstractmethod
    def author(self) -> str:
        """Get theme author."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Get theme version."""
        pass
    
    @abstractmethod
    def get_style_sheet(self) -> str:
        """
        Get the Qt StyleSheet (QSS) for this theme.
        
        Returns:
            Complete QSS string for the theme
        """
        pass
    
    @abstractmethod
    def get_palette(self) -> Optional[QPalette]:
        """
        Get the QPalette for this theme.
        
        Returns:
            QPalette object or None if not used
        """
        pass
    
    @abstractmethod
    def get_colors(self) -> Dict[str, str]:
        """
        Get theme color definitions.
        
        Returns:
            Dictionary of color names to hex color codes
        """
        pass
    
    def apply(self, app: QApplication):
        """
        Apply this theme to the application.
        
        Args:
            app: QApplication instance to apply theme to
        """
        if not PYQT6_AVAILABLE:
            logger.warning("PyQt6 not available, cannot apply theme")
            return
        
        try:
            # Apply stylesheet
            style_sheet = self.get_style_sheet()
            if style_sheet:
                app.setStyleSheet(style_sheet)
                logger.debug(f"Applied stylesheet for theme: {self.name}")
            
            # Apply palette if provided
            palette = self.get_palette()
            if palette:
                app.setPalette(palette)
                logger.debug(f"Applied palette for theme: {self.name}")
            
            logger.info(f"Theme '{self.display_name}' applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply theme '{self.name}': {e}")
            raise
    
    def get_theme_info(self) -> Dict[str, Any]:
        """
        Get comprehensive theme information.
        
        Returns:
            Dictionary with theme metadata
        """
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'author': self.author,
            'version': self.version,
            'colors': self.get_colors()
        }
    
    def _load_qss_file(self, qss_path: Path) -> str:
        """
        Load a QSS file and return its contents.
        
        Args:
            qss_path: Path to the QSS file
            
        Returns:
            QSS file contents
        """
        try:
            if qss_path.exists():
                with open(qss_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                logger.warning(f"QSS file not found: {qss_path}")
                return ""
        except Exception as e:
            logger.error(f"Failed to load QSS file {qss_path}: {e}")
            return ""
    
    def _create_color_palette(self, colors: Dict[str, str]) -> QPalette:
        """
        Create a QPalette from color definitions.
        
        Args:
            colors: Dictionary of color role names to hex colors
            
        Returns:
            Configured QPalette
        """
        if not PYQT6_AVAILABLE:
            return None
        
        palette = QPalette()
        
        # Map common color names to QPalette roles
        color_role_map = {
            'window': QPalette.ColorRole.Window,
            'window_text': QPalette.ColorRole.WindowText,
            'base': QPalette.ColorRole.Base,
            'alternate_base': QPalette.ColorRole.AlternateBase,
            'tool_tip_base': QPalette.ColorRole.ToolTipBase,
            'tool_tip_text': QPalette.ColorRole.ToolTipText,
            'text': QPalette.ColorRole.Text,
            'button': QPalette.ColorRole.Button,
            'button_text': QPalette.ColorRole.ButtonText,
            'bright_text': QPalette.ColorRole.BrightText,
            'link': QPalette.ColorRole.Link,
            'highlight': QPalette.ColorRole.Highlight,
            'highlighted_text': QPalette.ColorRole.HighlightedText,
        }
        
        for color_name, hex_color in colors.items():
            if color_name in color_role_map:
                try:
                    color = QColor(hex_color)
                    palette.setColor(color_role_map[color_name], color)
                except Exception as e:
                    logger.warning(f"Invalid color '{hex_color}' for role '{color_name}': {e}")
        
        return palette