#!/usr/bin/python3
"""
Media command processor for TonieToolbox.

This module handles media-related operations including tag display,
media file analysis, and other media-specific commands.
"""

import logging
from ..utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)


class MediaCommandProcessor:
    """Handles all media-related command operations."""
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize media command processor (logger parameter kept for compatibility)."""
        pass
    
    def should_handle_media_commands(self, args) -> bool:
        """Check if any media-related commands should be handled."""
        return getattr(args, 'show_media_tags', False)
    
    def process_media_commands(self, args) -> int:
        """Process media commands that should exit immediately."""
        if getattr(args, 'show_media_tags', False):
            return self.handle_show_tags(args.input_filename)
        
        return 0
    
    def handle_show_tags(self, input_filename: str) -> int:
        """
        Handle the show-tags command by displaying media tags for files.
        
        Args:
            input_filename: Input file or pattern to show tags for
            
        Returns:
            Exit code: 0 for success, 1 for error
        """
        # Import only when needed to avoid tight coupling
        from ..media.tags import show_file_tags
        return show_file_tags(input_filename)