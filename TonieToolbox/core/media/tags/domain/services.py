#!/usr/bin/python3
"""
Domain services for media tag processing business logic.
Pure business logic with no infrastructure dependencies.
"""
from typing import Dict, List, Optional
import logging

from .entities import MediaTagCollection, MediaTag
from .interfaces import TagReader, FileSystemService


class TagNormalizationService:
    """
    Domain service for normalizing tag values according to business rules.
    """
    
    def __init__(self, replacement_mappings: Dict[str, str], logger: logging.Logger):
        """
        Initialize with replacement rules.
        
        Args:
            replacement_mappings: Dictionary of value replacements
            logger: Logger instance
        """
        self.replacement_mappings = replacement_mappings
        self.logger = logger
    
    def normalize_tag(self, tag: MediaTag) -> MediaTag:
        """
        Normalize a single tag according to business rules.
        
        Args:
            tag: Tag to normalize
            
        Returns:
            Normalized tag
        """
        if not tag or tag.is_empty():
            return tag
            
        normalized = tag.normalize(self.replacement_mappings)
        
        if normalized.value != tag.value:
            self.logger.debug("Normalized tag '%s': '%s' -> '%s'", 
                            tag.key, tag.value, normalized.value)
        
        return normalized
    
    def normalize_collection(self, collection: MediaTagCollection) -> MediaTagCollection:
        """
        Normalize all tags in a collection.
        
        Args:
            collection: Tag collection to normalize
            
        Returns:
            Collection with normalized tags
        """
        normalized_tags = {}
        
        for key, tag in collection.tags.items():
            normalized_tags[key] = self.normalize_tag(tag)
        
        return MediaTagCollection(
            tags=normalized_tags,
            source_file=collection.source_file
        )


class FilenameFormattingService:
    """
    Domain service for generating filenames from tag data.
    """
    
    def __init__(self, logger: logging.Logger):
        """Initialize filename formatter."""
        self.logger = logger
    
    def format_filename(self, tags: MediaTagCollection, template: str = "{tracknumber} - {title}") -> str:
        """
        Format filename using tag data and template.
        
        Args:
            tags: Tag collection
            template: Format template with {key} placeholders
            
        Returns:
            Formatted filename
        """
        if not tags.tags:
            return "unknown"
        
        # Prepare format dictionary with defaults
        format_dict = self._prepare_format_dictionary(tags)
        
        try:
            # Format using template
            formatted = template.format(**format_dict)
            
            # Apply filename sanitization rules
            sanitized = self._sanitize_filename(formatted)
            
            self.logger.debug("Formatted filename: '%s'", sanitized)
            return sanitized
            
        except KeyError as e:
            self.logger.warning("Template contains unknown field: %s", e)
            return f"{format_dict.get('tracknumber', '00')} - {format_dict.get('title', 'unknown')}"
    
    def _prepare_format_dictionary(self, tags: MediaTagCollection) -> Dict[str, str]:
        """Prepare dictionary for string formatting with proper defaults."""
        format_dict = {}
        
        # Get all tag values
        for key, tag in tags.tags.items():
            format_dict[key] = tag.value if not tag.is_empty() else "unknown"
        
        # Ensure required fields exist
        if 'tracknumber' not in format_dict:
            format_dict['tracknumber'] = "00"
        if 'title' not in format_dict:
            format_dict['title'] = "unknown"
        
        return format_dict
    
    def _sanitize_filename(self, filename: str) -> str:
        """Apply filename sanitization rules."""
        # Characters that are problematic in filenames
        replacements = {
            '/': '-',
            '\\': '-', 
            ':': '-',
            '*': '',
            '?': '',
            '"': '',
            '<': '',
            '>': '',
            '|': ''
        }
        
        sanitized = filename
        for char, replacement in replacements.items():
            sanitized = sanitized.replace(char, replacement)
        
        return sanitized


class AlbumAnalysisService:
    """
    Domain service for analyzing album metadata from multiple files.
    """
    
    def __init__(self, tag_reader: TagReader, fs_service: FileSystemService, logger: logging.Logger):
        """
        Initialize album analysis service.
        
        Args:
            tag_reader: Tag reader implementation
            fs_service: File system service
            logger: Logger instance
        """
        self.tag_reader = tag_reader
        self.fs_service = fs_service
        self.logger = logger
    
    def extract_album_info(self, directory: str, audio_files: List[str]) -> MediaTagCollection:
        """
        Extract common album information from multiple audio files.
        
        Args:
            directory: Directory containing files
            audio_files: List of audio file paths
            
        Returns:
            MediaTagCollection with most common tag values
        """
        if not audio_files:
            self.logger.debug("No audio files provided for album analysis")
            return MediaTagCollection(tags={})
        
        # Read tags from all files
        all_tag_collections = []
        for file_path in audio_files:
            try:
                tags = self.tag_reader.read_tags(file_path)
                if tags.tags:
                    all_tag_collections.append(tags)
            except Exception as e:
                self.logger.warning("Could not read tags from %s: %s", file_path, e)
        
        if not all_tag_collections:
            self.logger.debug("No tags found in any files")
            return MediaTagCollection(tags={})
        
        # Find most common values for each tag
        album_tags = self._find_most_common_tags(all_tag_collections)
        
        self.logger.debug("Extracted album info with %d tags", len(album_tags))
        return MediaTagCollection(tags=album_tags, source_file=directory)
    
    def _find_most_common_tags(self, tag_collections: List[MediaTagCollection]) -> Dict[str, MediaTag]:
        """Find most common tag values across all collections."""
        # Get all unique tag keys
        all_tag_keys = set()
        for collection in tag_collections:
            all_tag_keys.update(collection.tags.keys())
        
        result_tags = {}
        
        for key in all_tag_keys:
            # Count occurrences of each value for this key
            value_counts = {}
            
            for collection in tag_collections:
                if key in collection.tags and not collection.tags[key].is_empty():
                    value = collection.tags[key].value
                    value_counts[value] = value_counts.get(value, 0) + 1
            
            if value_counts:
                # Use the most common value
                most_common_value = max(value_counts, key=value_counts.get)
                # Use the tag structure from the first occurrence
                for collection in tag_collections:
                    if key in collection.tags and collection.tags[key].value == most_common_value:
                        result_tags[key] = collection.tags[key]
                        break
        
        return result_tags