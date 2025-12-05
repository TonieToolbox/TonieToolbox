#!/usr/bin/env python3
"""
PyQt6 GUI Components for TonieToolbox.

This module provides reusable Qt-based UI components following a modular design pattern.
Components include player controls, progress indicators, information panels, dialogs, and more.
All components inherit from QtBaseComponent for consistent lifecycle management and theming support.
"""

# Base components
from .base.component import QtBaseComponent

# Player components  
from .player.controls import PlayerControls
from .player.progress import PlayerProgress
from .player.info_panel import PlayerInfoPanel

# About components
from .about.dialog import AboutDialog

__all__ = [
    'QtBaseComponent',
    'PlayerControls',
    'PlayerProgress', 
    'PlayerInfoPanel',
    'AboutDialog'
]