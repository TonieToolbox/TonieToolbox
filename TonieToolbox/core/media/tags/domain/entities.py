#!/usr/bin/python3
"""
Domain entities and value objects for media tags.
Pure business logic with no external dependencies.
"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MediaTag:
    """
    Domain entity representing a single metadata tag.
    Contains business rules for tag validation and normalization.
    """
    key: str
    value: str
    original_key: Optional[str] = None
    format_type: Optional[str] = None
    
    def __post_init__(self):
        """Validate tag data according to business rules."""
        if not self.key:
            raise ValueError("Tag key cannot be empty")
        if self.value is None:
            self.value = ""
        
    def is_empty(self) -> bool:
        """Check if tag has meaningful content."""
        return not self.value or self.value.strip() == ""
    
    def normalize(self, replacements: Dict[str, str]) -> 'MediaTag':
        """Apply business rules for tag value normalization."""
        normalized_value = self.value
        
        # Apply direct replacements
        if normalized_value in replacements:
            normalized_value = replacements[normalized_value]
        
        # Apply partial replacements
        for pattern, replacement in replacements.items():
            if pattern in normalized_value:
                normalized_value = normalized_value.replace(pattern, replacement)
        
        return MediaTag(
            key=self.key,
            value=normalized_value,
            original_key=self.original_key,
            format_type=self.format_type
        )


@dataclass 
class MediaTagCollection:
    """
    Domain entity representing a collection of tags from a media file.
    Encapsulates business logic for tag operations.
    """
    tags: Dict[str, MediaTag]
    source_file: Optional[str] = None
    
    def get_tag(self, key: str) -> Optional[MediaTag]:
        """Get a tag by key."""
        return self.tags.get(key)
    
    def get_value(self, key: str, default: str = "") -> str:
        """Get tag value with fallback."""
        tag = self.get_tag(key)
        return tag.value if tag and not tag.is_empty() else default
    
    def has_tag(self, key: str) -> bool:
        """Check if collection contains a non-empty tag."""
        tag = self.get_tag(key)
        return tag is not None and not tag.is_empty()
    
    def get_standardized_tags(self) -> Dict[str, str]:
        """Get tags as simple key-value dictionary."""
        return {key: tag.value for key, tag in self.tags.items() if not tag.is_empty()}
    
    def merge_with(self, other: 'MediaTagCollection') -> 'MediaTagCollection':
        """Merge with another tag collection, preferring non-empty values."""
        merged_tags = self.tags.copy()
        
        for key, other_tag in other.tags.items():
            if key not in merged_tags or merged_tags[key].is_empty():
                merged_tags[key] = other_tag
        
        return MediaTagCollection(tags=merged_tags)


@dataclass
class ArtworkData:
    """Domain entity for artwork/cover art data."""
    data: bytes
    mime_type: str
    format_extension: str
    
    def __post_init__(self):
        """Validate artwork data."""
        if not self.data:
            raise ValueError("Artwork data cannot be empty")
        if not self.mime_type:
            raise ValueError("MIME type is required")
        
    @property
    def size(self) -> int:
        """Get artwork data size in bytes."""
        return len(self.data)
    
    def is_jpeg(self) -> bool:
        """Check if artwork is JPEG format."""
        return self.mime_type == 'image/jpeg'
    
    def is_png(self) -> bool:
        """Check if artwork is PNG format.""" 
        return self.mime_type == 'image/png'


class TagNormalizationError(Exception):
    """Domain exception for tag normalization failures.
    
    Raised when tag names cannot be normalized from various input formats
    (ID3, Vorbis, APE) to the standard internal representation.
    
    Example:
        Unknown tag format::
        
            if tag_name not in KNOWN_TAG_FORMATS:
                raise TagNormalizationError(
                    f"Cannot normalize unknown tag format: {tag_name}"
                )
        
        Handling normalization errors::
        
            try:
                normalized = normalize_tag_name('UNKNOWN_TAG')
            except TagNormalizationError as e:
                logger.warning(f"Tag normalization failed: {e}")
                # Use original tag name as fallback
                normalized = 'UNKNOWN_TAG'
    """
    pass


class ArtworkExtractionError(Exception):
    """Domain exception for artwork extraction failures.
    
    Raised when embedded artwork cannot be extracted from audio files
    due to missing data, corrupted images, or unsupported formats.
    
    Example:
        No artwork found::
        
            if not audio_file.tags or 'APIC:' not in audio_file.tags:
                raise ArtworkExtractionError(
                    f"No artwork found in {file_path}"
                )
        
        Corrupted artwork data::
        
            try:
                Image.open(BytesIO(artwork_data))
            except Exception:
                raise ArtworkExtractionError(
                    "Artwork data is corrupted or in unsupported format"
                )
        
        Handling extraction errors::
        
            try:
                artwork = extract_artwork_from_file(file_path)
            except ArtworkExtractionError as e:
                logger.info(f"No artwork available: {e}")
                artwork = None  # Use default artwork
    """
    pass