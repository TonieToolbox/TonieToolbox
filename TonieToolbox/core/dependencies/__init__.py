#!/usr/bin/python3
"""
Dependency management package for TonieToolbox.

This package provides a modular architecture for managing external dependencies,
including FFmpeg and Python packages.
"""

# Import main classes for easy access
from .manager import (
    DependencyManager,
    get_dependency_manager,
    get_ffmpeg_binary,
    get_ffplay_binary, 
    ensure_dependency
)

from .base import DependencyInfo
from .manager import DEPENDENCIES

# GUI dependency management
from .gui import (
    GUIDependencyManager,
    get_gui_dependency_manager,
    check_pyqt6_available,
    get_pyqt6_modules,
    get_gui_mock_classes
)

__all__ = [
    'DependencyManager',
    'get_dependency_manager',
    'get_ffmpeg_binary',
    'get_ffplay_binary',
    'ensure_dependency',
    'DependencyInfo',
    'DEPENDENCIES',
    'GUIDependencyManager',
    'get_gui_dependency_manager',
    'check_pyqt6_available',
    'get_pyqt6_modules',
    'get_gui_mock_classes'
]