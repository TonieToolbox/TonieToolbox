#!/usr/bin/python3
"""
Mutagen-based implementation of tag reading interfaces.
"""
import os
from typing import Dict, Optional, List

import mutagen
from mutagen.id3 import ID3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from ..domain import TagReader, MediaTagCollection, MediaTag
from ....config.application_constants import TAG_MAPPINGS


class MutagenTagReader(TagReader):
    """
    Concrete implementation of TagReader using the mutagen library.
    """
    
    def __init__(self, logger):
        """Initialize with logger."""
        self.logger = logger
    
    def read_tags(self, file_path: str) -> MediaTagCollection:
        """
        Read tags from media file using mutagen.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            MediaTagCollection with extracted tags
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.logger.debug("Reading tags from file: %s", file_path)
        
        try:
            audio = mutagen.File(file_path)
            if audio is None:
                self.logger.warning("Could not identify file format: %s", file_path)
                return MediaTagCollection(tags={}, source_file=file_path)
            
            # Determine format and extract tags
            tags = self._extract_tags_by_format(audio, file_path)
            
            self.logger.debug("Successfully read %d tags from file", len(tags))
            return MediaTagCollection(tags=tags, source_file=file_path)
            
        except Exception as e:
            self.logger.error("Error reading tags from file %s: %s", file_path, str(e))
            return MediaTagCollection(tags={}, source_file=file_path)
    
    def supports_format(self, file_path: str) -> bool:
        """Check if mutagen can handle this file format."""
        try:
            audio = mutagen.File(file_path)
            return audio is not None
        except Exception:
            return False
    
    def _extract_tags_by_format(self, audio, file_path: str) -> Dict[str, MediaTag]:
        """Extract tags based on detected audio format."""
        tags = {}
        
        # Handle ID3 tags (MP3)
        if isinstance(audio, ID3) or hasattr(audio, 'ID3'):
            tags = self._extract_id3_tags(audio)
        
        # Handle FLAC, Ogg Opus, Ogg Vorbis 
        elif isinstance(audio, (FLAC, OggOpus, OggVorbis)):
            tags = self._extract_vorbis_tags(audio)
        
        # Handle MP4/AAC
        elif isinstance(audio, MP4):
            tags = self._extract_mp4_tags(audio)
        
        # Handle other formats with generic approach
        else:
            tags = self._extract_generic_tags(audio)
        
        return tags
    
    def _extract_id3_tags(self, audio) -> Dict[str, MediaTag]:
        """Extract tags from ID3 format."""
        tags = {}
        
        try:
            id3 = audio if isinstance(audio, ID3) else audio.ID3
            for tag_key, tag_value in id3.items():
                tag_name = tag_key.split(':')[0]
                # Use mapping if available, otherwise use original tag name (lowercased for consistency)
                standardized_key = TAG_MAPPINGS.get(tag_name, tag_name.lower())
                tags[standardized_key] = MediaTag(
                    key=standardized_key,
                    value=str(tag_value),
                    original_key=tag_key,
                    format_type='id3'
                )
        except (AttributeError, TypeError) as e:
            self.logger.debug("Error accessing ID3 tags: %s", e)
            # Fallback to alternative access method
            try:
                if hasattr(audio, 'tags') and audio.tags:
                    for tag_key in audio.tags.keys():
                        tag_value = audio.tags[tag_key]
                        if hasattr(tag_value, 'text'):
                            value_str = str(tag_value.text[0]) if tag_value.text else ''
                        else:
                            value_str = str(tag_value)
                        
                        # Use mapping if available, otherwise use original key (lowercased for consistency)
                        standardized_key = TAG_MAPPINGS.get(tag_key, tag_key.lower())
                        tags[standardized_key] = MediaTag(
                            key=standardized_key,
                            value=value_str,
                            original_key=tag_key,
                            format_type='id3'
                        )
            except Exception as e:
                self.logger.debug("Alternative ID3 tag reading failed: %s", e)
        
        return tags
    
    def _extract_vorbis_tags(self, audio) -> Dict[str, MediaTag]:
        """Extract tags from Vorbis comment format (FLAC, OGG)."""
        tags = {}
        
        for tag_key, tag_values in audio.items():
            tag_key_lower = tag_key.lower()
            # Use mapping if available, otherwise use original key (lowercased for consistency)
            standardized_key = TAG_MAPPINGS.get(tag_key_lower, tag_key_lower)
            value = tag_values[0] if tag_values else ''
            tags[standardized_key] = MediaTag(
                key=standardized_key,
                value=value,
                original_key=tag_key,
                format_type='vorbis'
            )
        
        return tags
    
    def _extract_mp4_tags(self, audio) -> Dict[str, MediaTag]:
        """Extract tags from MP4 format.""" 
        tags = {}
        
        for tag_key, tag_value in audio.items():
            # Use mapping if available, otherwise use original key (lowercased for consistency)
            standardized_key = TAG_MAPPINGS.get(tag_key, tag_key.lower())
            
            if isinstance(tag_value, list):
                if tag_key in ('trkn', 'disk'):
                    if tag_value and isinstance(tag_value[0], tuple) and len(tag_value[0]) >= 1:
                        value_str = str(tag_value[0][0])
                    else:
                        value_str = ''
                else:
                    value_str = str(tag_value[0]) if tag_value else ''
            else:
                value_str = str(tag_value)
            
            tags[standardized_key] = MediaTag(
                key=standardized_key,
                value=value_str,
                original_key=tag_key,
                format_type='mp4'
            )
        
        return tags
    
    def _extract_generic_tags(self, audio) -> Dict[str, MediaTag]:
        """Extract tags using generic approach for other formats."""
        tags = {}
        
        for tag_key, tag_value in audio.items():
            tag_key_lower = tag_key.lower()
            # Use mapping if available, otherwise use original key (lowercased for consistency)
            standardized_key = TAG_MAPPINGS.get(tag_key_lower, tag_key_lower)
            
            if isinstance(tag_value, list):
                value_str = str(tag_value[0]) if tag_value else ''
            else:
                value_str = str(tag_value)
            
            tags[standardized_key] = MediaTag(
                key=standardized_key,
                value=value_str,
                original_key=tag_key,
                format_type='generic'
            )
        
        return tags


class MutagenTagReaderFactory:
    """
    Factory for creating mutagen-based tag readers.
    """
    
    def __init__(self, logger):
        """Initialize factory with logger."""
        self.logger = logger
        self._supported_formats = ['.mp3', '.flac', '.ogg', '.m4a', '.mp4', '.aac']
    
    def create_reader(self, file_path: str) -> Optional[MutagenTagReader]:
        """
        Create appropriate tag reader for file.
        
        Args:
            file_path: Path to media file
            
        Returns:
            MutagenTagReader instance if format is supported, None otherwise
        """
        file_ext = os.path.splitext(file_path.lower())[1]
        
        if file_ext in self._supported_formats:
            return MutagenTagReader(self.logger)
        
        return None
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        return self._supported_formats.copy()