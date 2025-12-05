#!/usr/bin/python3
"""
Media Tags Domain Layer.

This module contains pure domain models and business logic for media tag processing.
Defines tag entities, normalization services, filename formatting, and album analysis.
All domain components are framework-independent and testable in isolation following
Clean Architecture principles.
"""
from .entities import MediaTag, MediaTagCollection, ArtworkData, TagNormalizationError, ArtworkExtractionError
from .interfaces import TagReader, ArtworkExtractor, TagReaderFactory, FileSystemService, CoverImageFinder
from .services import TagNormalizationService, FilenameFormattingService, AlbumAnalysisService

__all__ = [
    # Entities
    'MediaTag',
    'MediaTagCollection', 
    'ArtworkData',
    
    # Exceptions
    'TagNormalizationError',
    'ArtworkExtractionError',
    
    # Interfaces
    'TagReader',
    'ArtworkExtractor',
    'TagReaderFactory',
    'FileSystemService',
    'CoverImageFinder',
    
    # Services
    'TagNormalizationService',
    'FilenameFormattingService',
    'AlbumAnalysisService'
]