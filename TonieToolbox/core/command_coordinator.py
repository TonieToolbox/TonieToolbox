#!/usr/bin/python3
"""
Command coordination for TonieToolbox.

This module provides a coordinator that orchestrates different command processors
with clear separation of concerns while maintaining a unified interface.
"""

import logging
from typing import Dict

from .commands import VersionCommandProcessor, DependencyCommandProcessor, IntegrationCommandProcessor, MediaCommandProcessor
from .utils.logging import get_logger

logger = get_logger(__name__)


class CommandCoordinator:
    """
    Coordinates different command processors with clear separation of concerns.
    
    This coordinator orchestrates version checking, dependency management, integration setup,
    and media operations through specialized processor components. It handles early-exit commands
    that don't require full file processing initialization.
    
    Example:
        >>> from TonieToolbox.core.utils import get_logger
        >>> import argparse
        >>> 
        >>> # Initialize coordinator
        >>> logger = get_logger(__name__)
        >>> coordinator = CommandCoordinator(logger)
        >>> 
        >>> # Check if command requires early exit
        >>> args = argparse.Namespace(check_for_updates=True, install_integration=False)
        >>> if coordinator.should_handle_early_exit_commands(args):
        ...     exit_code = coordinator.process_early_exit_commands(args)
        ...     print(f"Early exit with code: {exit_code}")
        Early exit with code: 0
        >>> 
        >>> # Setup dependencies for file processing
        >>> args = argparse.Namespace(auto_download=True, dependency_path=None)
        >>> dependencies = coordinator.setup_dependencies(args)
        >>> print(f"FFmpeg available: {'ffmpeg' in dependencies}")
        FFmpeg available: True
    """
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize command coordinator with focused processors (logger parameter kept for compatibility)."""
        self.version_processor = VersionCommandProcessor()
        self.dependency_processor = DependencyCommandProcessor()
        self.integration_processor = IntegrationCommandProcessor()
        self.media_processor = MediaCommandProcessor()
    
    def should_handle_early_exit_commands(self, args) -> bool:
        """Check if any command should exit early (before file processing)."""
        return (self.version_processor.should_handle_version_commands(args) or
                self.integration_processor.should_handle_integration_commands(args) or
                self.media_processor.should_handle_media_commands(args))
    
    def process_early_exit_commands(self, args) -> int:
        """Process commands that should exit immediately."""
        # Handle version commands first (highest priority for early exit)
        if self.version_processor.should_handle_version_commands(args):
            return self.version_processor.process_version_commands(args)
        
        # Handle media commands 
        if self.media_processor.should_handle_media_commands(args):
            return self.media_processor.process_media_commands(args)
        
        # Handle integration commands
        if self.integration_processor.should_handle_integration_commands(args):
            return self.integration_processor.process_integration_commands(args, self.dependency_processor)
        
        return 0
    
    def process_version_check(self, args) -> None:
        """Handle version checking if not skipped."""
        self.version_processor.process_version_check(args)
    
    def setup_dependencies(self, args) -> Dict[str, str]:
        """Setup and validate external dependencies."""
        return self.dependency_processor.setup_dependencies(args)