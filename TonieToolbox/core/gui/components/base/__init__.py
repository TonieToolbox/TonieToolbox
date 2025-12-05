#!/usr/bin/env python3
"""
Base GUI Components for PyQt6.

This module provides the foundational base component class (QtBaseComponent) that all other
GUI components inherit from. Implements common lifecycle methods, theme integration, event
handling patterns, and resource management for consistent component behavior across the application.
"""

from .component import QtBaseComponent

__all__ = ['QtBaseComponent']