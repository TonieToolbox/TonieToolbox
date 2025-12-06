#!/usr/bin/python3
"""
Dependency management commands for TonieToolbox.

This module handles external dependency setup and validation including
FFmpeg binary location, auto-download, and media tag dependencies.
"""

import sys
import logging
from typing import Dict

from ..dependencies import get_ffmpeg_binary, get_ffprobe_binary, ensure_dependency
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
        
        # Setup FFprobe (derive from FFmpeg path)
        ffprobe_binary = self._setup_ffprobe(ffmpeg_binary, args)
        
        # Handle media tags dependencies
        self._setup_media_tags(args)
        
        return {
            'ffmpeg': ffmpeg_binary,
            'ffprobe': ffprobe_binary
        }
    
    def _setup_ffmpeg(self, args) -> str:
        """Setup FFmpeg binary."""
        ffmpeg_binary = args.ffmpeg
        if ffmpeg_binary is None:
            force_creation = getattr(args, 'force_creation', False)
            logger.debug("No FFmpeg specified, attempting to locate binary "
                            "(auto_download=%s, force_creation=%s)", args.auto_download, force_creation)
            ffmpeg_binary = get_ffmpeg_binary(args.auto_download, force_creation)
            if ffmpeg_binary is None:
                logger.error("Could not find FFmpeg. Please install FFmpeg "
                                "or specify its location using --ffmpeg or use --auto-download")
                sys.exit(1)
            logger.debug("Using FFmpeg binary: %s", ffmpeg_binary)
        return ffmpeg_binary
    
    def _setup_ffprobe(self, ffmpeg_binary: str, args) -> str:
        """Setup FFprobe binary."""
        # FFprobe is typically bundled with FFmpeg, so we use the same auto_download flag
        force_creation = getattr(args, 'force_creation', False)
        logger.debug("Attempting to locate FFprobe binary "
                        "(auto_download=%s, force_creation=%s)", args.auto_download, force_creation)
        ffprobe_binary = get_ffprobe_binary(args.auto_download, force_creation)
        if ffprobe_binary is None:
            logger.error("Could not find FFprobe. Please install FFmpeg "
                            "(which includes FFprobe) or use --auto-download")
            sys.exit(1)
        logger.debug("Using FFprobe binary: %s", ffprobe_binary)
        return ffprobe_binary
    
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