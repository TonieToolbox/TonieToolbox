#!/usr/bin/python3
"""
TeddyCloud Application Layer.

This module contains application services and coordinators that orchestrate TeddyCloud operations.
Provides high-level workflows for file uploads, tag management, and configuration operations.
Services coordinate between domain logic and infrastructure implementations while maintaining
separation of concerns through dependency injection.
"""

# Services
from .service import TeddyCloudService

# Coordinators
from .coordinators import (
    TeddyCloudUploadCoordinator,
    TeddyCloudTagCoordinator,
    TeddyCloudConfigurationCoordinator
)

__all__ = [
    # Services
    'TeddyCloudService',
    
    # Coordinators
    'TeddyCloudUploadCoordinator',
    'TeddyCloudTagCoordinator', 
    'TeddyCloudConfigurationCoordinator'
]