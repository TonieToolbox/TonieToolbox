#!/usr/bin/env python3
"""
Internationalization (i18n) System for PyQt6 GUI.

This module provides comprehensive internationalization support for the TonieToolbox GUI.
Handles translation management, locale detection, language switching, and translation loading
for multiple languages. Provides the tr() function for string translation throughout the GUI
and supports dynamic language switching without application restart.
"""

from .manager import TranslationManager
from .utils import tr, get_translation_manager

__all__ = [
    'TranslationManager',
    'tr',
    'get_translation_manager'
]