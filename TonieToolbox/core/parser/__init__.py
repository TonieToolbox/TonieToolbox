#!/usr/bin/python3
"""
Parser Module for TonieToolbox.

This module provides all parsing functionality including command-line argument 
parsing and potentially other parsers in the future (config parsers, format parsers, etc.).

Following Clean Architecture principles, this module serves as part of the Interface Layer,
handling the parsing and validation of external inputs.
"""

from .argument_parser import TonieToolboxArgumentParser
from .factory import ArgumentParserFactory

__all__ = [
    # Main argument parser class
    'TonieToolboxArgumentParser',
    
    # Factory for creating parsers with dependency injection
    'ArgumentParserFactory',
]