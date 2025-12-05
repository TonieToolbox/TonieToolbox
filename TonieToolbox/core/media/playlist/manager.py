#!/usr/bin/env python3
"""
Playlist manager for TonieToolbox media player.

This module provides high-level playlist management functionality,
coordinating between playlist models and file discovery.
"""

from typing import List, Optional, Callable, Any, Tuple
from pathlib import Path

from .models import Playlist, PlaylistItem, RepeatMode
from .discovery import PlaylistFileDiscovery
from .cache import PlaylistFileCache
from .persistence import PlaylistPersistence
from ...utils import get_logger

logger = get_logger(__name__)


class PlaylistManager:
    """
    High-level playlist management for TonieToolbox media player.
    
    Handles playlist operations and coordinates between playlist models
    and the underlying media player. Includes file caching and persistence.
    """
    
    def __init__(self, enable_cache: bool = True, cache_size: int = 100):
        """
        Initialize playlist manager.
        
        Args:
            enable_cache: Enable file info caching (default: True)
            cache_size: Maximum cache size (default: 100)
        """
        self.playlist = Playlist()
        self._playlist_changed_callbacks: List[Callable] = []
        self._current_item_changed_callbacks: List[Callable] = []
        self._playlist_name: Optional[str] = None
        self._playlist_file_path: Optional[Path] = None
        self._source_path: Optional[Path] = None  # Track where playlist was loaded from
        self._saved_seek_position: Optional[float] = None  # Seek position loaded from playlist file
        
        # File info cache
        self.file_cache: Optional[PlaylistFileCache] = None
        if enable_cache:
            self.file_cache = PlaylistFileCache(max_size=cache_size)
            logger.debug("File caching enabled")
    
    def add_playlist_changed_callback(self, callback: Callable) -> None:
        """Add a callback to be called when playlist changes."""
        self._playlist_changed_callbacks.append(callback)
    
    def add_current_item_changed_callback(self, callback: Callable) -> None:
        """Add a callback to be called when current item changes."""
        self._current_item_changed_callbacks.append(callback)
    
    def load_from_path(self, input_path: str, recursive: bool = False) -> bool:
        """
        Load playlist from a file, directory, or pattern.
        
        Args:
            input_path: Path to load from
            recursive: Whether to search recursively in directories
            
        Returns:
            True if any files were loaded successfully
        """
        logger.info(f"Loading playlist from: {input_path}")
        
        try:
            items = PlaylistFileDiscovery.discover_taf_files(input_path, recursive)
            self._source_path = Path(input_path)  # Track source for display
            if self._source_path.is_dir():
                self._playlist_name = self._source_path.name
            return self._load_items(items)
        except Exception as e:
            logger.error(f"Failed to load playlist from {input_path}: {e}")
            return False
    
    def load_from_multiple_paths(self, input_paths: List[str]) -> bool:
        """
        Load playlist from multiple paths.
        
        Args:
            input_paths: List of paths to load from
            
        Returns:
            True if any files were loaded successfully
        """
        logger.info(f"Loading playlist from {len(input_paths)} paths")
        
        try:
            items = PlaylistFileDiscovery.discover_taf_files_from_multiple_inputs(input_paths)
            return self._load_items(items)
        except Exception as e:
            logger.error(f"Failed to load playlist from multiple paths: {e}")
            return False
    
    def add_file(self, file_path: Path) -> bool:
        """
        Add a single TAF file to the playlist.
        
        Args:
            file_path: Path to TAF file to add
            
        Returns:
            True if file was added successfully
        """
        try:
            if PlaylistFileDiscovery.validate_taf_file(file_path):
                # Get cached analysis if available
                analysis_result = None
                if self.file_cache:
                    analysis_result = self.file_cache.get(file_path)
                
                # Analyze file if not cached
                if not analysis_result:
                    from ...analysis import analyze_taf_file
                    analysis_result = analyze_taf_file(file_path)
                    if self.file_cache and analysis_result:
                        self.file_cache.put(file_path, analysis_result)
                
                # Create playlist item with metadata from analysis
                title = None
                duration = 0.0
                if analysis_result:
                    if hasattr(analysis_result, 'tonie_header') and analysis_result.tonie_header:
                        title = getattr(analysis_result.tonie_header, 'name', None)
                    if hasattr(analysis_result, 'audio_analysis') and analysis_result.audio_analysis:
                        duration = getattr(analysis_result.audio_analysis, 'duration_seconds', 0.0)
                
                item = PlaylistItem(
                    file_path=file_path,
                    title=title,
                    duration=duration,
                    metadata={'analysis': analysis_result} if analysis_result else {}
                )
                self.playlist.add_item(item)
                self._notify_playlist_changed()
                logger.info(f"Added file to playlist: {file_path.name}")
                return True
            else:
                logger.warning(f"Invalid TAF file: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to add file to playlist: {e}")
            return False
    
    def remove_item(self, index: int) -> bool:
        """
        Remove an item from the playlist.
        
        Args:
            index: Index of item to remove
            
        Returns:
            True if item was removed successfully
        """
        if self.playlist.remove_item(index):
            self._notify_playlist_changed()
            return True
        return False
    
    def move_item(self, from_index: int, to_index: int) -> bool:
        """
        Move an item from one position to another.
        
        Args:
            from_index: Current index of item to move
            to_index: Target index to move item to
            
        Returns:
            True if item was moved successfully
        """
        if self.playlist.move_item(from_index, to_index):
            self._notify_playlist_changed()
            logger.debug(f"Moved playlist item from {from_index} to {to_index}")
            return True
        return False
    
    def clear_playlist(self) -> None:
        """Clear all items from the playlist."""
        self.playlist.clear()
        self._notify_playlist_changed()
        logger.info("Playlist cleared")
    
    def get_current_item(self) -> Optional[PlaylistItem]:
        """Get the currently selected playlist item."""
        return self.playlist.get_current_item()
    
    def next_item(self) -> Optional[PlaylistItem]:
        """Move to and return the next item in the playlist."""
        item = self.playlist.get_next_item()
        if item:
            self._notify_current_item_changed()
            logger.debug(f"Advanced to next item: {item.title}")
        return item
    
    def previous_item(self) -> Optional[PlaylistItem]:
        """Move to and return the previous item in the playlist."""
        item = self.playlist.get_previous_item()
        if item:
            self._notify_current_item_changed()
            logger.debug(f"Moved to previous item: {item.title}")
        return item
    
    def jump_to_item(self, index: int) -> Optional[PlaylistItem]:
        """Jump to a specific item in the playlist."""
        item = self.playlist.jump_to_item(index)
        if item:
            self._notify_current_item_changed()
            logger.debug(f"Jumped to item {index}: {item.title}")
        return item
    
    def has_next(self) -> bool:
        """Check if there's a next item available."""
        return self.playlist.has_next()
    
    def has_previous(self) -> bool:
        """Check if there's a previous item available."""
        return self.playlist.has_previous()
    
    def set_shuffle_mode(self, enabled: bool) -> None:
        """Enable or disable shuffle mode."""
        self.playlist.set_shuffle_mode(enabled)
        self._notify_playlist_changed()
    
    def is_shuffle_enabled(self) -> bool:
        """Check if shuffle mode is enabled."""
        return self.playlist.shuffle_mode
    
    def set_repeat_mode(self, mode: RepeatMode) -> None:
        """Set the repeat mode."""
        self.playlist.set_repeat_mode(mode)
        logger.info(f"Repeat mode set to: {mode.value}")
    
    def get_repeat_mode(self) -> RepeatMode:
        """Get the current repeat mode."""
        return self.playlist.repeat_mode
    
    def cycle_repeat_mode(self) -> RepeatMode:
        """Cycle through repeat modes: OFF -> ALL -> ONE -> OFF."""
        modes = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        current_index = modes.index(self.playlist.repeat_mode)
        next_index = (current_index + 1) % len(modes)
        new_mode = modes[next_index]
        self.set_repeat_mode(new_mode)
        return new_mode
    
    def get_playlist_info(self) -> dict:
        """Get information about the current playlist."""
        return {
            'total_items': self.playlist.size(),
            'current_index': self.playlist.current_index,
            'current_item': self.get_current_item(),
            'is_empty': self.playlist.is_empty(),
            'shuffle_mode': self.playlist.shuffle_mode,
            'repeat_mode': self.playlist.repeat_mode.value,
            'total_duration': self.playlist.get_total_duration(),
            'has_next': self.has_next(),
            'has_previous': self.has_previous(),
            'source_path': str(self._source_path) if self._source_path else None,
            'playlist_name': self._playlist_name
        }
    
    def get_all_items(self) -> List[PlaylistItem]:
        """Get all items in the playlist."""
        return list(self.playlist.items)
    
    def is_empty(self) -> bool:
        """Check if playlist is empty."""
        return self.playlist.is_empty()
    
    def save_to_file(self, file_path: Path, playlist_name: Optional[str] = None,
                     current_track: Optional[int] = None,
                     seek_position: Optional[float] = None) -> bool:
        """
        Save current playlist to a .lst file.
        
        Args:
            file_path: Path where playlist file will be saved
            playlist_name: Custom name for the playlist (uses current name if None)
            current_track: Current track index (uses current index if None)
            seek_position: Current seek position in seconds (optional)
            
        Returns:
            True if playlist was saved successfully
        """
        name = playlist_name or self._playlist_name or file_path.stem
        
        # Use provided track index or current playlist index
        track = current_track if current_track is not None else self.playlist.current_index
        
        success = PlaylistPersistence.save_playlist(
            self.playlist, file_path, name, track, seek_position
        )
        if success:
            self._playlist_file_path = file_path
            self._playlist_name = name
            logger.info(f"Saved playlist '{name}' to {file_path}")
        return success
    
    def load_from_file(self, file_path: Path) -> bool:
        """
        Load playlist from a .lst file.
        
        Args:
            file_path: Path to the .lst file to load
            
        Returns:
            True if playlist was loaded successfully
        """
        items, playlist_name, current_track, seek_position, stats = PlaylistPersistence.load_playlist(file_path)
        
        if not items:
            # Store error key and parameters for translation in UI layer
            if stats.get('skipped_non_taf', 0) > 0:
                error_msg = f"No valid TAF files found in playlist. {stats['skipped_non_taf']} non-TAF file(s) were skipped. Only .taf files are supported."
                logger.error(error_msg)
                # Return translation key with parameter
                self._last_error = ('playlist_no_taf_files', {'count': stats['skipped_non_taf']})
            elif stats.get('skipped_missing', 0) > 0:
                error_msg = f"No accessible files in playlist. {stats['skipped_missing']} file(s) not found."
                logger.error(error_msg)
                self._last_error = ('playlist_no_accessible_files', {'count': stats['skipped_missing']})
            elif stats.get('total_files', 0) == 0:
                error_msg = "Playlist file is empty or contains only comments"
                logger.error(error_msg)
                self._last_error = ('playlist_empty', {})
            else:
                error_msg = f"No items loaded from {file_path}"
                logger.warning(error_msg)
                self._last_error = ('playlist_no_items', {})
            return False
        
        # Clear existing playlist
        self.playlist.clear()
        
        # Add all items
        for item in items:
            self.playlist.add_item(item)
            
            # Cache analysis result if available in metadata
            if self.file_cache and item.metadata and 'analysis' in item.metadata:
                self.file_cache.put(item.file_path, item.metadata['analysis'])
        
        # Set current track index from saved state or default to first item
        if current_track is not None and 0 <= current_track < len(items):
            self.playlist.current_index = current_track
            logger.debug(f"Restored playlist position: track {current_track}")
        elif items:
            self.playlist.current_index = 0
        
        # Store seek position for retrieval after loading
        self._saved_seek_position = seek_position
        if seek_position is not None:
            logger.debug(f"Restored seek position: {seek_position}s")
        
        # Store playlist metadata
        self._playlist_file_path = file_path
        self._playlist_name = playlist_name or file_path.stem
        
        self._notify_playlist_changed()
        self._notify_current_item_changed()
        
        logger.info(f"Loaded playlist '{self._playlist_name}' from {file_path} ({len(items)} items)")
        return True
    
    def get_playlist_name(self) -> Optional[str]:
        """Get the current playlist name."""
        return self._playlist_name
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error message from playlist operations."""
        return getattr(self, '_last_error', None)
    
    def set_playlist_name(self, name: str) -> None:
        """Set the playlist name."""
        self._playlist_name = name
        logger.debug(f"Playlist name set to: {name}")
    
    def get_playlist_file_path(self) -> Optional[Path]:
        """Get the file path of the loaded/saved playlist."""
        return self._playlist_file_path
    
    def update_item_title(self, index: int, new_title: str) -> bool:
        """
        Update the title of a playlist item.
        
        Args:
            index: Index of the item to update
            new_title: New title for the item
            
        Returns:
            True if title was updated successfully
        """
        if 0 <= index < len(self.playlist.items):
            self.playlist.items[index].title = new_title
            self._notify_playlist_changed()
            logger.debug(f"Updated item {index} title to: {new_title}")
            return True
        return False
    
    def clear_cache(self) -> None:
        """Clear the file info cache."""
        if self.file_cache:
            self.file_cache.clear()
            logger.debug("File cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if self.file_cache:
            return self.file_cache.get_stats()
        return {'enabled': False}
    
    def get_saved_seek_position(self) -> Optional[float]:
        """
        Get the seek position that was loaded from the playlist file.
        
        Returns:
            Seek position in seconds, or None if not available
        """
        return self._saved_seek_position
    
    def clear_saved_seek_position(self) -> None:
        """Clear the saved seek position after it has been used."""
        self._saved_seek_position = None
    
    def _load_items(self, items: List[PlaylistItem]) -> bool:
        """Load a list of playlist items."""
        if not items:
            logger.warning("No TAF files found to load")
            return False
        
        # Clear existing playlist
        self.playlist.clear()
        
        # Add all items
        for item in items:
            self.playlist.add_item(item)
        
        # Set first item as current
        if items:
            self.playlist.current_index = 0
        
        self._notify_playlist_changed()
        self._notify_current_item_changed()
        
        logger.info(f"Loaded {len(items)} items into playlist")
        return True
    
    def _notify_playlist_changed(self) -> None:
        """Notify all registered callbacks that the playlist has changed."""
        for callback in self._playlist_changed_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in playlist changed callback: {e}")
    
    def _notify_current_item_changed(self) -> None:
        """Notify all registered callbacks that the current item has changed."""
        for callback in self._current_item_changed_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in current item changed callback: {e}")
    
    def __len__(self) -> int:
        """Get the number of items in the playlist."""
        return len(self.playlist)
    
    def __bool__(self) -> bool:
        """Check if playlist has items."""
        return bool(self.playlist)