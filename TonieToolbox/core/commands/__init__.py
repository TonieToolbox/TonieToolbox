#!/usr/bin/python3
"""
Commands package for TonieToolbox.

This package provides focused command processors for different operational concerns:
- Version management (updates, cache)
- Dependency setup (FFmpeg, external tools)
- Integration management (system integration)
"""

from .version_processor import VersionCommandProcessor
from .dependency_processor import DependencyCommandProcessor
from .integration_processor import IntegrationCommandProcessor
from .media_processor import MediaCommandProcessor

__all__ = [
    'VersionCommandProcessor',
    'DependencyCommandProcessor', 
    'IntegrationCommandProcessor',
    'MediaCommandProcessor'
]