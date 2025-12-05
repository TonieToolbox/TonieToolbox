#!/usr/bin/python3
"""
TeddyCloud Infrastructure Layer.

This module contains concrete implementations of domain interfaces for TeddyCloud integration.
Includes HTTP repositories for API communication, file system caching, metadata extraction,
and template processing. All infrastructure components implement domain-defined interfaces
to ensure proper dependency inversion and testability.
"""

# Repositories
from .http_repository import HttpTeddyCloudRepository

# Adapters
from .adapters import (
    StandardFileSystemService, StandardTemplateProcessor,
    MediaTagMetadataExtractor, SimpleMetadataExtractor
)

# Factory
from .factory import (
    create_teddycloud_service, create_teddycloud_connection_from_args,
    get_teddycloud_service
)

__all__ = [
    # Repositories
    'HttpTeddyCloudRepository',
    
    # Adapters
    'StandardFileSystemService',
    'StandardTemplateProcessor', 
    'MediaTagMetadataExtractor',
    'SimpleMetadataExtractor',
    
    # Factory
    'create_teddycloud_service',
    'create_teddycloud_connection_from_args',
    'get_teddycloud_service'
]