#!/usr/bin/env python3
"""
Play mode detection for TonieToolbox.

This module determines whether to use single file or playlist mode
for the --play command based on the input type and content.
"""

import os
from typing import Tuple
from pathlib import Path

from ...media.playlist.discovery import PlaylistFileDiscovery
from ...utils import get_logger

logger = get_logger(__name__)


class PlayModeDetector:
    """Detects whether to use single file or playlist mode for playback."""
    
    @staticmethod
    def determine_play_mode(input_path: str) -> Tuple[str, bool]:
        """
        Determine if input should use single file or playlist mode.
        
        Args:
            input_path: Input path from command line
            
        Returns:
            Tuple of (mode, needs_playlist_discovery)
            where mode is 'single' or 'playlist'
            and needs_playlist_discovery indicates if file discovery is needed
        """
        logger.debug(f"Determining play mode for: {input_path}")
        
        # Convert to string if it's a Path object
        input_str = str(input_path)
        
        # Handle direct TAF file
        if os.path.isfile(input_path) and input_str.lower().endswith('.taf'):
            logger.debug("Single TAF file detected")
            return 'single', False
        
        # Handle .lst playlist file
        if os.path.isfile(input_path) and input_str.lower().endswith('.lst'):
            logger.debug("Playlist file detected")
            return 'playlist', True
        
        # Handle directory
        if os.path.isdir(input_path):
            # Check if directory contains multiple TAF files
            taf_count = PlayModeDetector._count_taf_files_in_directory(input_path)
            if taf_count > 1:
                logger.debug(f"Directory with {taf_count} TAF files detected - using playlist mode")
                return 'playlist', True
            elif taf_count == 1:
                logger.debug("Directory with single TAF file detected - could use either mode")
                return 'single', True  # Let discovery find the single file
            else:
                logger.debug("Directory with no TAF files detected")
                return 'playlist', True  # Let discovery handle and potentially show error
        
        # Handle patterns (e.g., *.taf, /path/to/*.taf)
        if '*' in input_path or '?' in input_path:
            logger.debug("Pattern detected - using playlist mode")
            return 'playlist', True
        
        # Handle non-existent file/path
        if not os.path.exists(input_path):
            # Could be a pattern without wildcards
            logger.debug("Non-existent path - trying as pattern for playlist mode")
            return 'playlist', True
        
        # Default to single file mode
        logger.debug("Defaulting to single file mode")
        return 'single', False
    
    @staticmethod
    def _count_taf_files_in_directory(directory: str) -> int:
        """Count TAF files in a directory (non-recursive)."""
        try:
            taf_files = []
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path) and item.lower().endswith('.taf'):
                    taf_files.append(item_path)
            return len(taf_files)
        except Exception as e:
            logger.debug(f"Error counting TAF files in {directory}: {e}")
            return 0
    
    @staticmethod
    def get_single_file_from_input(input_path: str) -> str:
        """
        Get a single TAF file path from input, discovering if necessary.
        
        Args:
            input_path: Input path that should resolve to a single TAF file
            
        Returns:
            Path to the single TAF file
            
        Raises:
            ValueError: If no single TAF file can be determined
        """
        # Direct file
        if os.path.isfile(input_path) and input_path.lower().endswith('.taf'):
            return input_path
        
        # Directory with single TAF file
        if os.path.isdir(input_path):
            items = PlaylistFileDiscovery.discover_taf_files(input_path, recursive=False)
            if len(items) == 1:
                return str(items[0].file_path)
            elif len(items) == 0:
                raise ValueError(f"No TAF files found in directory: {input_path}")
            else:
                raise ValueError(f"Multiple TAF files found in directory: {input_path}. Use playlist mode.")
        
        # Try discovery for other cases
        items = PlaylistFileDiscovery.discover_taf_files(input_path, recursive=False)
        if len(items) == 1:
            return str(items[0].file_path)
        elif len(items) == 0:
            raise ValueError(f"No TAF files found for input: {input_path}")
        else:
            raise ValueError(f"Multiple TAF files found for input: {input_path}. Use playlist mode.")
    
    @staticmethod
    def should_use_recursive_discovery(input_path: str) -> bool:
        """
        Determine if recursive discovery should be used based on input characteristics.
        
        Currently returns False as recursive discovery will be added later.
        This is a placeholder for future functionality.
        """
        # For now, we don't use recursive discovery by default
        # This can be enhanced later when --recursive support is added to --play
        return False