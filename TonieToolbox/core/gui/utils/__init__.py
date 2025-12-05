#!/usr/bin/env python3
"""
Utilities for PyQt6 GUI integration.
"""

from .threading import QtThreadManager
from .imports import import_pyqt6_modules, get_pyqt6_component_base
from .formatting import format_chapter_info

__all__ = [
    'QtThreadManager',
    'import_pyqt6_modules',
    'get_pyqt6_component_base',
    'format_chapter_info'
]