#!/usr/bin/env python3
"""
Processing application module.

This module contains the application layer for processing operations.
All use cases, application services, and interfaces are defined here.

The application layer orchestrates domain objects and coordinates
workflows while remaining independent of infrastructure details.
"""

# Import interfaces
from .interfaces import (
    FileRepository,
    FileWatcher,
    FileIterator,
    MediaConverter,
    ConversionProgress,
    UploadService,
    UploadQueue,
    UploadProgress,
    UploadResult
)

# Import use cases
from .use_cases import (
    BaseUseCase,
    ConvertToTafUseCase,
    FilesToTafUseCase,
    FileAnalysisUseCase
)

# Import services
from .services import (
    ProcessingApplicationService,
    WorkflowCoordinator
)

__all__ = [
    # Interfaces
    'FileRepository',
    'FileWatcher',
    'FileIterator',
    'MediaConverter',
    'ConversionProgress',
    'UploadService',
    'UploadQueue',
    'UploadProgress',
    'UploadResult',
    
    # Use cases
    'BaseUseCase',
    'ConvertToTafUseCase',
    'FilesToTafUseCase',
    'FileAnalysisUseCase',
    
    # Services
    'ProcessingApplicationService',
    'WorkflowCoordinator',
    
    # Processors
    'CustomJsonProcessor'
]

# Import processors after defining __all__
from .custom_json_processor import CustomJsonProcessor
