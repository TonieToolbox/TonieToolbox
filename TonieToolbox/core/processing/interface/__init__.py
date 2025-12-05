#!/usr/bin/env python3
"""
Processing interface package.

This module contains interface layer components that coordinate between
external interfaces (CLI, GUI) and application services following Clean Architecture principles.

Interface Layer Components:
- Adapters: Coordinate between external interfaces and application services
- CLI: Command-line interface implementations
- Mode Detection: Enhanced processing mode detection capabilities
"""

from .adapters import (
    BaseInterfaceAdapter,
    ProgressTrackingMixin,
    SingleFileProcessingAdapter,
    FileAnalysisAdapter,
    BatchFileProcessingAdapter,
    FilesToTafAdapter,
    RecursiveProcessingAdapter
)

from .cli import (
    CLIProcessingCoordinator,
    CLIArgumentValidator,
    create_cli_coordinator
)

from .mode_detector import EnhancedModeDetector

__all__ = [
    # Adapters
    'BaseInterfaceAdapter',
    'ProgressTrackingMixin',
    'SingleFileProcessingAdapter',
    'FileAnalysisAdapter', 
    'BatchFileProcessingAdapter',
    'FilesToTafAdapter',
    'RecursiveProcessingAdapter',
    
    # CLI
    'CLIProcessingCoordinator',
    'CLIArgumentValidator',
    'create_cli_coordinator',
    
    # Mode Detection
    'EnhancedModeDetector'
]