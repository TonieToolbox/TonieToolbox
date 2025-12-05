"""
Processing Workflow Orchestration Module.

This module provides the unified workflow orchestration layer following Clean Architecture.
It coordinates between specialized domain modules (analysis/, media/, file/) and external
interfaces (CLI, GUI, TeddyCloud) to execute file processing operations.

Architecture Position:
- Layer: Application (workflow orchestration)
- Dependencies: Injects specialized domain services (analysis.TafAnalysisService, media.*, file.*)
- Used by: CLI (TonieToolboxApp), GUI (MainWindow), command processors

Layer Structure:
- domain/ - Processing workflow domain models (ProcessingOperation, ProcessingResult)
- application/ - Use cases and workflow coordinators
- infrastructure/ - External service adapters (FFmpeg, TeddyCloud, file system)
- interface/ - CLI and GUI adapters

Relationship to Other Modules:
- Uses analysis/ for TAF domain logic
- Uses file/ for low-level file operations  
- Uses media/ for media domain services
- Orchestrates these into complete workflows
"""

from .main_service import MainProcessingService

# Domain layer exports
from .domain import (
    ProcessingOperation, ProcessingResult, ProcessingMode,
    InputSpecification, OutputSpecification, ProcessingOptions
)

# Application layer exports  
from .application.services.processing_application_service import ProcessingApplicationService
from .application.use_cases import (
    ConvertToTafUseCase, FilesToTafUseCase, FileAnalysisUseCase
)

# Infrastructure layer exports
from .infrastructure import (
    FileSystemRepository, FFmpegConverter, TafAnalysisService
)

# Interface layer exports
from .interface import (
    CLIProcessingCoordinator, EnhancedModeDetector,
    SingleFileProcessingAdapter, FilesToTafAdapter,
    RecursiveProcessingAdapter, FileAnalysisAdapter
)

__all__ = [
    # Main service
    'MainProcessingService',
    
    # Domain layer
    'ProcessingOperation', 'ProcessingResult', 'ProcessingMode',
    'InputSpecification', 'OutputSpecification', 'ProcessingOptions',
    
    # Application layer
    'ProcessingApplicationService',
    'ConvertToTafUseCase', 'FilesToTafUseCase', 'FileAnalysisUseCase',
    
    # Infrastructure layer
    'FileSystemRepository', 'FFmpegConverter', 'TafAnalysisService',
    
    # Interface layer
    'CLIProcessingCoordinator', 'EnhancedModeDetector',
    'SingleFileProcessingAdapter', 'FilesToTafAdapter',
    'RecursiveProcessingAdapter', 'FileAnalysisAdapter'
]