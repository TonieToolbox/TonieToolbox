#!/usr/bin/python3
"""
Dependency management commands for TonieToolbox.

This module handles external dependency setup and validation including
FFmpeg binary location, auto-download, and media tag dependencies.
"""

import sys
import logging
from typing import Dict

from ..dependencies import get_ffmpeg_binary, ensure_dependency
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DependencyCommandProcessor:
    """Handles all dependency setup and validation operations."""
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize dependency command processor (logger parameter kept for compatibility)."""
        pass
    
    def setup_dependencies(self, args) -> Dict[str, str]:
        """Setup and validate all external dependencies."""
        logger.debug("Checking for external dependencies")
        
        # Setup FFmpeg
        ffmpeg_binary = self._setup_ffmpeg(args)
        
        # Handle media tags dependencies
        self._setup_media_tags(args)
        
        return {
            'ffmpeg': ffmpeg_binary
        }
    
    def _setup_ffmpeg(self, args) -> str:
        """Setup FFmpeg binary."""
        ffmpeg_binary = args.ffmpeg
        if ffmpeg_binary is None:
            logger.debug("No FFmpeg specified, attempting to locate binary "
                            "(auto_download=%s)", args.auto_download)
            ffmpeg_binary = get_ffmpeg_binary(args.auto_download)
            if ffmpeg_binary is None:
                logger.error("Could not find FFmpeg. Please install FFmpeg "
                                "or specify its location using --ffmpeg or use --auto-download")
                sys.exit(1)
            logger.debug("Using FFmpeg binary: %s", ffmpeg_binary)
        return ffmpeg_binary
    
    def _setup_media_tags(self, args) -> None:
        """Setup media tags dependencies if needed."""
        # Mutagen is now a required dependency - no need for availability checks
        logger.debug("Media tags functionality enabled with mutagen library")
    
    def validate_integration_dependencies(self, args) -> bool:
        """Validate dependencies required for system integration."""
        if not ensure_dependency('ffmpeg'):
            logger.error("FFmpeg is required for context menu integration")
            return False
        return True