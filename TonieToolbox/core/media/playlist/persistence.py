#!/usr/bin/env python3
"""
Playlist persistence for saving and loading playlist files.

Supports .lst file format - a simple text-based format with comments.
"""

from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .models import PlaylistItem, Playlist, RepeatMode
from ...utils import get_logger

logger = get_logger(__name__)


@dataclass
class PlaylistMetadata:
    """Metadata for a saved playlist."""
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None


class PlaylistPersistence:
    """
    Handle saving and loading playlist files in .lst format.
    
    Format is a simple text file with comments:
    - Lines starting with # are comments
    - # playlistname: <name> - Playlist name
    - # playlist: <name> - Alternative playlist name format
    - # playtime_track: <index> - Current track index (0-based)
    - # playtime_seek: <MM:SS> or <HH:MM:SS> - Current seek position
    - # filename: <name> - Output filename (for conversion)
    - # output: <name> - Alternative output filename format
    - # name: "<name>" - Alternative name format with quotes
    - Other lines are file paths (absolute or relative)
    
    Example .lst file:
        # My Playlist
        # playlistname: My Favorite Stories
        # playtime_track: 2
        # playtime_seek: 01:23
        /path/to/file1.taf
        /path/to/file2.taf
        ./relative/path/file3.taf
    
    Features:
        - Simple, human-readable format
        - Supports both absolute and relative paths
        - Playlist name stored in comments
        - Playback state (track and position) stored in comments
        - Compatible with TonieToolbox conversion workflow
    """
    
    COMMENT_PREFIX = "#"
    PLAYLIST_NAME_MARKERS = ["# playlistname:", "# playlist:"]
    PLAYTIME_TRACK_MARKER = "# playtime_track:"
    PLAYTIME_SEEK_MARKER = "# playtime_seek:"
    
    @staticmethod
    def save_playlist(playlist: Playlist, file_path: Path, 
                     playlist_name: Optional[str] = None,
                     current_track: Optional[int] = None,
                     seek_position: Optional[float] = None) -> bool:
        """
        Save playlist to .lst file.
        
        Args:
            playlist: Playlist object to save
            file_path: Path where playlist file will be saved
            playlist_name: Custom name for the playlist (optional)
            current_track: Current track index (0-based, optional)
            seek_position: Current seek position in seconds (optional)
            
        Returns:
            True if playlist was saved successfully, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write header comment
                f.write("# TonieToolbox Playlist\n")
                f.write("#\n")
                
                # Write playlist name if provided
                if playlist_name:
                    f.write(f"# playlistname: {playlist_name}\n")
                    f.write("#\n")
                
                # Write playback state if provided
                if current_track is not None and current_track >= 0:
                    f.write(f"# playtime_track: {current_track}\n")
                    if seek_position is not None and seek_position > 0:
                        # Format as MM:SS or HH:MM:SS
                        hours = int(seek_position // 3600)
                        minutes = int((seek_position % 3600) // 60)
                        seconds = int(seek_position % 60)
                        if hours > 0:
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            time_str = f"{minutes:02d}:{seconds:02d}"
                        f.write(f"# playtime_seek: {time_str}\n")
                    f.write("#\n")
                
                # Write file paths
                for item in playlist.items:
                    # Use absolute paths for reliability
                    f.write(f"{item.file_path.resolve()}\n")
            
            logger.info(f"Saved playlist to {file_path} ({len(playlist.items)} items)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save playlist to {file_path}: {e}")
            return False
    
    @staticmethod
    def load_playlist(file_path: Path) -> Tuple[List[PlaylistItem], Optional[str], Optional[int], Optional[float], dict]:
        """
        Load playlist from .lst file.
        
        Args:
            file_path: Path to the .lst file to load
            
        Returns:
            Tuple of (list of PlaylistItems, playlist_name, current_track, seek_position, stats)
            stats dict contains: total_files, skipped_non_taf, skipped_missing
            Returns ([], None, None, None, {}) if file cannot be loaded
        """
        items: List[PlaylistItem] = []
        playlist_name: Optional[str] = None
        current_track: Optional[int] = None
        seek_position: Optional[float] = None
        stats = {'total_files': 0, 'skipped_non_taf': 0, 'skipped_missing': 0}
        
        try:
            if not file_path.exists():
                logger.error(f"Playlist file not found: {file_path}")
                return ([], None, None, None, {})
            
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Parse playlist name from comments
                    if not playlist_name:
                        for marker in PlaylistPersistence.PLAYLIST_NAME_MARKERS:
                            if line.startswith(marker):
                                playlist_name = line[len(marker):].strip()
                                logger.debug(f"Loaded playlist name: {playlist_name}")
                                break
                    
                    # Parse playback state from comments
                    if line.startswith(PlaylistPersistence.PLAYTIME_TRACK_MARKER):
                        try:
                            track_str = line[len(PlaylistPersistence.PLAYTIME_TRACK_MARKER):].strip()
                            current_track = int(track_str)
                            logger.debug(f"Loaded playtime track: {current_track}")
                        except ValueError as e:
                            logger.warning(f"Invalid playtime_track value at line {line_num}: {e}")
                        continue
                    
                    if line.startswith(PlaylistPersistence.PLAYTIME_SEEK_MARKER):
                        try:
                            time_str = line[len(PlaylistPersistence.PLAYTIME_SEEK_MARKER):].strip()
                            # Parse HH:MM:SS or MM:SS format
                            parts = time_str.split(':')
                            if len(parts) == 3:  # HH:MM:SS
                                hours, minutes, seconds = map(int, parts)
                                seek_position = hours * 3600 + minutes * 60 + seconds
                            elif len(parts) == 2:  # MM:SS
                                minutes, seconds = map(int, parts)
                                seek_position = minutes * 60 + seconds
                            else:
                                raise ValueError(f"Invalid time format: {time_str}")
                            logger.debug(f"Loaded playtime seek: {seek_position}s ({time_str})")
                        except (ValueError, AttributeError) as e:
                            logger.warning(f"Invalid playtime_seek value at line {line_num}: {e}")
                        continue
                    
                    # Skip all comment lines
                    if line.startswith(PlaylistPersistence.COMMENT_PREFIX):
                        continue
                    
                    # Parse file path
                    try:
                        taf_path = Path(line)
                        stats['total_files'] += 1
                        
                        # Convert to absolute path if relative
                        if not taf_path.is_absolute():
                            # Try relative to playlist file location
                            taf_path = (file_path.parent / taf_path).resolve()
                        
                        # Filter: Only accept .taf files
                        if taf_path.suffix.lower() != '.taf':
                            stats['skipped_non_taf'] += 1
                            logger.warning(f"Skipping non-TAF file in playlist: {taf_path.name} (only .taf files are supported)")
                            continue
                        
                        # Verify file exists
                        if not taf_path.exists():
                            stats['skipped_missing'] += 1
                            logger.warning(f"TAF file not found: {taf_path}")
                            # Skip missing files instead of adding them
                            continue
                        
                        # Create playlist item
                        item = PlaylistItem(
                            file_path=taf_path,
                            title=None,  # Will be loaded from TAF file metadata
                            duration=0.0  # Will be loaded from TAF file analysis
                        )
                        items.append(item)
                        logger.debug(f"Loaded playlist item: {item.file_path.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to parse file path at line {line_num}: {line} - {e}")
                        continue
            
            logger.info(f"Loaded playlist from {file_path} ({len(items)} items, name: {playlist_name or 'unnamed'}, track: {current_track}, seek: {seek_position}, total: {stats['total_files']}, skipped: {stats['skipped_non_taf'] + stats['skipped_missing']})")
            return (items, playlist_name, current_track, seek_position, stats)
            
        except Exception as e:
            logger.error(f"Failed to load playlist from {file_path}: {e}")
            return ([], None, None, None, {})
    
    @staticmethod
    def is_valid_playlist_file(file_path: Path) -> bool:
        """
        Check if a file is a valid .lst playlist file.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file is a valid playlist file
        """
        if not file_path.exists() or not file_path.is_file():
            return False
        
        if file_path.suffix.lower() != '.lst':
            return False
        
        try:
            # Check if file contains at least one non-comment line
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith(PlaylistPersistence.COMMENT_PREFIX):
                        return True
            return False
        except Exception:
            return False
