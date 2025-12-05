#!/usr/bin/env python3
"""
Default theme for TonieToolbox PyQt6 GUI.
"""
from typing import Dict, Optional
from pathlib import Path

try:
    from PyQt6.QtGui import QPalette
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QPalette = object

from ..base import BaseTheme


class DefaultTheme(BaseTheme):
    """
    Default theme for TonieToolbox.
    Provides a clean, modern dark theme with blue accents.
    """
    
    def __init__(self):
        """Initialize the default theme."""
        super().__init__(
            name="default",
            display_name="Default Dark"
        )
    
    @property
    def description(self) -> str:
        """Get theme description."""
        return "Clean dark theme with blue accents and modern styling"
    
    @property
    def author(self) -> str:
        """Get theme author."""
        return "TonieToolbox"
    
    @property
    def version(self) -> str:
        """Get theme version."""
        return "1.0.0"
    
    def get_colors(self) -> Dict[str, str]:
        """Get theme color definitions."""
        return {
            # Background colors
            'window': '#2b2b2b',
            'window_text': '#ffffff',
            'base': '#353535',
            'alternate_base': '#404040',
            
            # Text colors
            'text': '#ffffff',
            'disabled_text': '#808080',
            'bright_text': '#ffffff',
            
            # Button colors
            'button': '#404040',
            'button_text': '#ffffff',
            'button_hover': '#4a4a4a',
            'button_pressed': '#2a2a2a',
            
            # Accent colors
            'highlight': '#3daee9',
            'highlighted_text': '#ffffff',
            'link': '#3daee9',
            'link_visited': '#2980b9',
            
            # Status colors
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#e74c3c',
            'info': '#3498db',
            
            # Tool tip colors
            'tool_tip_base': '#404040',
            'tool_tip_text': '#ffffff',
            
            # Border colors
            'border': '#555555',
            'border_light': '#666666',
            'border_dark': '#333333',
        }
    
    def get_style_sheet(self) -> str:
        """Get the Qt StyleSheet for this theme."""
        colors = self.get_colors()
        
        return f"""
        /* Global Application Style */
        QApplication {{
            background-color: {colors['window']};
            color: {colors['text']};
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 9pt;
        }}
        
        /* Main Window */
        QMainWindow {{
            background-color: {colors['window']};
            color: {colors['text']};
        }}
        
        /* Frames and Containers */
        QFrame {{
            background-color: {colors['base']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
        }}
        
        QFrame[frameShape="0"] {{
            border: none;
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {colors['button']};
            color: {colors['button_text']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 12px;
            min-height: 20px;
            font-weight: 500;
        }}
        
        QPushButton:hover {{
            background-color: {colors['button_hover']};
            border-color: {colors['border_light']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['button_pressed']};
            border-color: {colors['border_dark']};
        }}
        
        QPushButton:disabled {{
            background-color: {colors['base']};
            color: {colors['disabled_text']};
            border-color: {colors['border_dark']};
        }}
        
        /* Primary Button */
        QPushButton[primary="true"] {{
            background-color: {colors['highlight']};
            color: {colors['highlighted_text']};
            border-color: {colors['highlight']};
        }}
        
        QPushButton[primary="true"]:hover {{
            background-color: #4cbff0;
        }}
        
        QPushButton[primary="true"]:pressed {{
            background-color: #2a9fd6;
        }}
        
        /* Labels */
        QLabel {{
            color: {colors['text']};
            background-color: transparent;
        }}
        
        QLabel[class="title"] {{
            font-size: 14pt;
            font-weight: bold;
            color: {colors['text']};
        }}
        
        QLabel[class="subtitle"] {{
            font-size: 10pt;
            color: {colors['disabled_text']};
        }}
        
        QLabel[class="info"] {{
            color: {colors['info']};
        }}
        
        QLabel[class="success"] {{
            color: {colors['success']};
        }}
        
        QLabel[class="warning"] {{
            color: {colors['warning']};
        }}
        
        QLabel[class="error"] {{
            color: {colors['error']};
        }}
        
        /* Progress Bar */
        QProgressBar {{
            background-color: {colors['base']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            text-align: center;
            color: {colors['text']};
            height: 20px;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['highlight']};
            border-radius: 3px;
        }}
        
        /* Sliders */
        QSlider::groove:horizontal {{
            background-color: {colors['base']};
            height: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {colors['highlight']};
            width: 14px;
            height: 14px;
            border-radius: 7px;
            margin: -4px 0;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: #4cbff0;
        }}
        
        QSlider::sub-page:horizontal {{
            background-color: {colors['highlight']};
            border-radius: 3px;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {colors['window']};
            color: {colors['text']};
            border-bottom: 1px solid {colors['border']};
        }}
        
        QMenuBar::item {{
            padding: 4px 8px;
            background-color: transparent;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['highlight']};
        }}
        
        /* Menus */
        QMenu {{
            background-color: {colors['base']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 4px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['highlight']};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {colors['border']};
            margin: 4px;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {colors['window']};
            color: {colors['text']};
            border-top: 1px solid {colors['border']};
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {colors['border']};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {colors['base']};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['button']};
            min-height: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['button_hover']};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors['base']};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors['button']};
            min-width: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['button_hover']};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* Text Edit and Plain Text Edit */
        QTextEdit, QPlainTextEdit {{
            background-color: {colors['base']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px;
            selection-background-color: {colors['highlight']};
        }}
        
        /* Line Edit */
        QLineEdit {{
            background-color: {colors['base']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px;
            selection-background-color: {colors['highlight']};
        }}
        
        QLineEdit:focus {{
            border-color: {colors['highlight']};
        }}
        
        /* Tool Tips */
        QToolTip {{
            background-color: {colors['tool_tip_base']};
            color: {colors['tool_tip_text']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px;
        }}
        """
    
    def get_palette(self) -> Optional['QPalette']:
        """Get the QPalette for this theme."""
        if not PYQT6_AVAILABLE:
            return None
        
        colors = self.get_colors()
        return self._create_color_palette(colors)