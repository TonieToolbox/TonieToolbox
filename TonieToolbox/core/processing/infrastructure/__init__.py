#!/usr/bin/env python3
"""
Processing infrastructure package.

This module contains concrete implementations of application layer interfaces,
providing integration with external systems and services.

Infrastructure Layer Components:
- Repositories: Data access implementations
- Services: External service integrations
- Adapters: Protocol and format adapters
"""

from .repositories import FileSystemRepository, FileSystemIterator
from .services import (
    FFmpegConverter,
    TeddyCloudAdapter,
    TeddyCloudConnection,
    TeddyCloudConnectionManager,
    TafAnalysisService
)

__all__ = [
    # Repositories
    'FileSystemRepository',
    'FileSystemIterator',
    
    # Services
    'FFmpegConverter',
    'TeddyCloudAdapter',
    'TeddyCloudConnection',
    'TeddyCloudConnectionManager',
    'TafAnalysisService'
]