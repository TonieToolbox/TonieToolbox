#!/usr/bin/python3
"""
TeddyCloud Domain Layer.

This module contains pure domain models, entities, and business logic for TeddyCloud integration.
Defines connection models, tag entities, upload results, authentication types, and domain exceptions.
All domain objects are independent of external frameworks and infrastructure concerns following
Clean Architecture principles.
"""

# Entities
from .entities import (
    TeddyCloudConnection, TeddyCloudTag, TeddyCloudFile,
    UploadResult, DirectoryCreationResult, TagRetrievalResult,
    TagSourceAssignment, UnassignedTag, TagAssignmentSummary,
    AuthenticationType, SpecialFolder, TagValidationStatus,
    TeddyCloudError, TeddyCloudConnectionError, TeddyCloudAuthenticationError,
    TeddyCloudUploadError, TeddyCloudValidationError
)

# Interfaces
from .interfaces import (
    TeddyCloudRepository, FileSystemService,
    TemplateProcessor, MetadataExtractor
)

# Services
from .services import (
    ConnectionValidationService, UploadPathResolutionService,
    DirectoryManagementService, TagDisplayService, UploadValidationService
)

__all__ = [
    # Entities
    'TeddyCloudConnection',
    'TeddyCloudTag',
    'TeddyCloudFile',
    'UploadResult',
    'DirectoryCreationResult',
    'TagRetrievalResult',
    'TagSourceAssignment',
    'UnassignedTag',
    'TagAssignmentSummary',
    
    # Enums
    'AuthenticationType',
    'SpecialFolder', 
    'TagValidationStatus',
    
    # Exceptions
    'TeddyCloudError',
    'TeddyCloudConnectionError',
    'TeddyCloudAuthenticationError',
    'TeddyCloudUploadError',
    'TeddyCloudValidationError',
    
    # Interfaces
    'TeddyCloudRepository',
    'FileSystemService',
    'TemplateProcessor',
    'MetadataExtractor',
    
    # Services
    'ConnectionValidationService',
    'UploadPathResolutionService',
    'DirectoryManagementService',
    'TagDisplayService',
    'UploadValidationService'
]