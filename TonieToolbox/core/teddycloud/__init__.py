#!/usr/bin/python3
"""
TeddyCloud module following Clean Architecture principles.
Provides TeddyCloud integration for uploading files and managing tags.
"""

#!/usr/bin/python3
"""
TeddyCloud module following Clean Architecture principles.
Provides TeddyCloud integration for uploading files and managing tags.
"""

# Clean Architecture Exports
from .domain import *
from .application import *
from .infrastructure import *
from .processors import *

# Service Provider
from .service_provider import TeddyCloudServiceProvider, get_teddycloud_provider

# Events
from .events import (
    TeddyCloudUploadStartedEvent, TeddyCloudUploadCompletedEvent, TeddyCloudUploadFailedEvent,
    TeddyCloudTagsRetrievedEvent, TeddyCloudConnectionEstablishedEvent, TeddyCloudConnectionFailedEvent,
    TeddyCloudBatchUploadStartedEvent, TeddyCloudBatchUploadCompletedEvent,
    TeddyCloudTagAssignmentStartedEvent, TeddyCloudTagAssignmentCompletedEvent, TeddyCloudTagAssignmentFailedEvent
)


__all__ = [
    # Domain Layer
    'TeddyCloudConnection', 'TeddyCloudTag', 'TeddyCloudFile',
    'UploadResult', 'DirectoryCreationResult', 'TagRetrievalResult',
    'AuthenticationType', 'SpecialFolder', 'TagValidationStatus',
    'TeddyCloudError', 'TeddyCloudConnectionError', 'TeddyCloudAuthenticationError',
    'TeddyCloudUploadError', 'TeddyCloudValidationError',
    'TeddyCloudRepository', 'FileSystemService',
    'TemplateProcessor', 'MetadataExtractor',
    'ConnectionValidationService', 'UploadPathResolutionService',
    'DirectoryManagementService', 'TagDisplayService', 'UploadValidationService',
    
    # Application Layer
    'TeddyCloudService', 'TeddyCloudUploadCoordinator', 'TeddyCloudTagCoordinator',
    'TeddyCloudConfigurationCoordinator',
    
    # Infrastructure Layer
    'HttpTeddyCloudRepository',
    'StandardFileSystemService', 'StandardTemplateProcessor',
    'MediaTagMetadataExtractor', 'SimpleMetadataExtractor',
    'create_teddycloud_service', 'create_teddycloud_connection_from_args', 'get_teddycloud_service',
    
    # Processors
    'TeddyCloudUploadProcessor', 'TeddyCloudTagProcessor', 'TeddyCloudDirectUploadProcessor',
    
    # Service Provider
    'TeddyCloudServiceProvider', 'get_teddycloud_provider',
    
    # Events
    'TeddyCloudUploadStartedEvent', 'TeddyCloudUploadCompletedEvent', 'TeddyCloudUploadFailedEvent',
    'TeddyCloudTagsRetrievedEvent', 'TeddyCloudConnectionEstablishedEvent', 'TeddyCloudConnectionFailedEvent',
    'TeddyCloudBatchUploadStartedEvent', 'TeddyCloudBatchUploadCompletedEvent',
    'TeddyCloudTagAssignmentStartedEvent', 'TeddyCloudTagAssignmentCompletedEvent', 'TeddyCloudTagAssignmentFailedEvent'
]
