#!/usr/bin/env python3
"""
Playlist file discovery for TonieToolbox.

This module provides functionality for discovering TAF files and building playlists
from directories, file patterns, and manual file selection.
"""

import os
import glob
from typing import List
from pathlib import Path

from .models import PlaylistItem
from ...utils import get_logger, natural_sort

logger = get_logger(__name__)


class PlaylistFileDiscovery:
    """Handles discovery and loading of TAF files for playlists."""
    
    @staticmethod
    def discover_taf_files(input_path, recursive: bool = False) -> List[PlaylistItem]:
        """
        Discover TAF files from various input types.
        
        Args:
            input_path: Path to file, directory, or pattern (str or Path)
            recursive: Whether to search recursively in directories
            
        Returns:
            List of PlaylistItem objects for discovered TAF files
        """
        logger.debug(f"Discovering TAF files from: {input_path} (recursive: {recursive})")
        
        # Convert Path objects to strings for compatibility
        if isinstance(input_path, Path):
            input_path_str = str(input_path)
        else:
            input_path_str = input_path
        
        # Handle .lst files (playlist files)
        if input_path_str.endswith('.lst'):
            return PlaylistFileDiscovery._discover_from_lst_file(input_path_str)
        
        # Handle single TAF file
        if os.path.isfile(input_path_str) and input_path_str.lower().endswith('.taf'):
            return [PlaylistFileDiscovery._create_playlist_item(Path(input_path_str))]
        
        # Handle directory
        if os.path.isdir(input_path_str):
            return PlaylistFileDiscovery._discover_from_directory(input_path_str, recursive)
        
        # Handle glob patterns
        return PlaylistFileDiscovery._discover_from_pattern(input_path_str)
    
    @staticmethod
    def discover_taf_files_from_multiple_inputs(input_paths: List[str]) -> List[PlaylistItem]:
        """
        Discover TAF files from multiple input paths.
        
        Args:
            input_paths: List of paths to files, directories, or patterns
            
        Returns:
            List of PlaylistItem objects for all discovered TAF files
        """
        all_items = []
        
        for input_path in input_paths:
            items = PlaylistFileDiscovery.discover_taf_files(input_path)
            all_items.extend(items)
            logger.debug(f"Found {len(items)} TAF files from: {input_path}")
        
        # Remove duplicates while preserving order
        seen_paths = set()
        unique_items = []
        for item in all_items:
            path_str = str(item.file_path)
            if path_str not in seen_paths:
                seen_paths.add(path_str)
                unique_items.append(item)
        
        logger.info(f"Discovered {len(unique_items)} unique TAF files from {len(input_paths)} inputs")
        return unique_items
    
    @staticmethod
    def _discover_from_lst_file(lst_path: str) -> List[PlaylistItem]:
        """Discover TAF files from a .lst playlist file."""
        logger.debug(f"Loading TAF files from playlist: {lst_path}")
        
        if not os.path.exists(lst_path):
            logger.warning(f"Playlist file not found: {lst_path}")
            return []
        
        try:
            # Use PlaylistPersistence to load the playlist
            from .persistence import PlaylistPersistence
            items, playlist_name = PlaylistPersistence.load_playlist(Path(lst_path))
            
            if playlist_name:
                logger.debug(f"Loaded playlist '{playlist_name}' with {len(items)} items")
            
            return items
            
        except Exception as e:
            logger.error(f"Error reading playlist file {lst_path}: {e}")
            return []
    
    @staticmethod
    def _discover_from_directory(dir_path: str, recursive: bool = False) -> List[PlaylistItem]:
        """Discover TAF files from a directory."""
        logger.debug(f"Discovering TAF files from directory: {dir_path} (recursive: {recursive})")
        
        if not os.path.isdir(dir_path):
            logger.warning(f"Directory not found: {dir_path}")
            return []
        
        taf_files = []
        
        if recursive:
            # Use recursive glob to find all TAF files
            pattern = os.path.join(dir_path, "**", "*.taf")
            taf_files = glob.glob(pattern, recursive=True)
        else:
            # Find TAF files in immediate directory only
            pattern = os.path.join(dir_path, "*.taf")
            taf_files = glob.glob(pattern)
        
        # Sort files naturally (handles numbers correctly)
        taf_files = natural_sort(taf_files)
        
        items = []
        for taf_file in taf_files:
            if os.path.isfile(taf_file):
                items.append(PlaylistFileDiscovery._create_playlist_item(Path(taf_file)))
        
        logger.info(f"Found {len(items)} TAF files in directory: {dir_path}")
        return items
    
    @staticmethod
    def _discover_from_pattern(pattern: str) -> List[PlaylistItem]:
        """Discover TAF files from a glob pattern."""
        logger.debug(f"Discovering TAF files from pattern: {pattern}")
        
        # First try the pattern as-is
        matching_files = glob.glob(pattern)
        
        # If no matches and no extension, try adding .taf
        if not matching_files and not os.path.splitext(pattern)[1]:
            taf_pattern = pattern + "*.taf"
            logger.debug(f"No matches for pattern, trying TAF pattern: {taf_pattern}")
            matching_files = glob.glob(taf_pattern)
        
        # Filter to only TAF files and sort
        taf_files = [f for f in matching_files 
                    if os.path.isfile(f) and f.lower().endswith('.taf')]
        taf_files = natural_sort(taf_files)
        
        items = []
        for taf_file in taf_files:
            items.append(PlaylistFileDiscovery._create_playlist_item(Path(taf_file)))
        
        logger.info(f"Found {len(items)} TAF files matching pattern: {pattern}")
        return items
    
    @staticmethod
    def _create_playlist_item(file_path: Path) -> PlaylistItem:
        """Create a PlaylistItem from a TAF file path."""
        item = PlaylistItem(file_path=file_path)
        
        # Try to extract basic metadata without full TAF parsing
        try:
            item.file_size = file_path.stat().st_size
        except Exception as e:
            logger.debug(f"Could not get file size for {file_path}: {e}")
        
        return item
    
    @staticmethod
    def validate_taf_file(file_path: Path) -> bool:
        """
        Quick validation that a file appears to be a TAF file.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if file appears to be a valid TAF file
        """
        if not file_path.exists() or not file_path.is_file():
            return False
        
        if file_path.suffix.lower() != '.taf':
            return False
        
        # Quick size check - TAF files should be reasonably sized
        try:
            size = file_path.stat().st_size
            if size < 1024:  # Too small to be a real TAF file
                return False
        except Exception:
            return False
        
        # Could add header validation here if needed
        return True