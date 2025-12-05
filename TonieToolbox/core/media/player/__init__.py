#!/usr/bin/python3
"""
Audio Player Module for TAF Files.

This module provides core audio playback functionality for Toniebox Audio Format (TAF) files.
The TAFPlayer engine handles chapter-based playback, seeking, volume control, and state management.
Player interfaces and UI components are located in the GUI module to maintain separation of concerns.
"""
from .engine import TAFPlayer, TAFPlayerError

__all__ = ['TAFPlayer', 'TAFPlayerError']