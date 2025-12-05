#!/usr/bin/env python3
"""
Audio Player GUI Components.

This module provides GUI components for TAF audio playback including playback controls,
progress indicators, and information panels. Components handle user interactions for
play/pause, seeking, volume control, and display playback state, chapter information,
and file metadata.
"""

from .controls import PlayerControls
from .progress import PlayerProgress
from .info_panel import PlayerInfoPanel

__all__ = [
    'PlayerControls',
    'PlayerProgress',
    'PlayerInfoPanel'
]