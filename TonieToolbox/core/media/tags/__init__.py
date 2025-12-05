#!/usr/bin/python3
"""
Media tags module for TonieToolbox.
Clean Architecture implementation with proper separation of concerns.

This module exposes the Clean Architecture components directly:
- Domain layer: Pure business logic and entities
- Infrastructure layer: External dependencies (mutagen, filesystem)  
- Application layer: Coordination and orchestration services
- Display utilities: Console output functionality

Usage:
    from TonieToolbox.core.media.tags.application import MediaTagService
    from TonieToolbox.core.media.tags.domain import MediaTag, MediaTagCollection
    from TonieToolbox.core.media.tags.infrastructure import MutagenTagReader
    
    # For configured service instance:
    service = get_media_tag_service()
    tags = service.get_file_tags(file_path)
"""

from .application import MediaTagService
from .domain import *
from .infrastructure import *
from .display import show_file_tags
from ...config.application_constants import TAG_MAPPINGS, TAG_VALUE_REPLACEMENTS, ARTWORK_NAMES, ARTWORK_EXTENSIONS
from ...utils import get_logger

# Factory function for creating configured service instances
def get_media_tag_service(logger=None) -> MediaTagService:
    """
    Factory function to create a properly configured MediaTagService instance.
    
    Args:
        logger: Optional logger instance. If None, creates a new one.
        
    Returns:
        Configured MediaTagService instance ready for use
        
    Example:
        service = get_media_tag_service()
        tags = service.get_file_tags("audio.mp3")
        artwork = service.extract_artwork("audio.mp3")
    """
    if logger is None:
        logger = get_logger(__name__)
        
    return MediaTagService(
        tag_mappings=TAG_MAPPINGS,
        value_replacements=TAG_VALUE_REPLACEMENTS,
        artwork_names=ARTWORK_NAMES,
        artwork_extensions=ARTWORK_EXTENSIONS,
        logger=logger
    )

__all__ = [
    # Factory function
    'get_media_tag_service',
    
    # Application layer
    'MediaTagService',
    
    # Domain layer exports (from domain/__init__.py)
    'MediaTag',
    'MediaTagCollection', 
    'ArtworkData',
    'TagNormalizationError',
    'ArtworkExtractionError',
    'TagReader',
    'ArtworkExtractor',
    'TagReaderFactory',
    'FileSystemService',
    'CoverImageFinder',
    'TagNormalizationService',
    'FilenameFormattingService',
    'AlbumAnalysisService',
    
    # Infrastructure layer exports (from infrastructure/__init__.py)
    'MutagenTagReader',
    'MutagenTagReaderFactory', 
    'MutagenArtworkExtractor',
    'StandardFileSystemService',
    'StandardCoverImageFinder',
    
    # Display utilities
    'show_file_tags'
]