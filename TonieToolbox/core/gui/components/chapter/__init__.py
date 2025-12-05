#!/usr/bin/env python3
"""
Chapter Management GUI Components.

This module provides GUI components for displaying and managing TAF file chapters.
Includes chapter list widgets showing chapter metadata, durations, and navigation controls.
Enables chapter-based playback control and visualization of multi-chapter TAF files.
"""

from .list_widget import ChapterWidget

__all__ = ['ChapterWidget']