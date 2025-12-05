#!/usr/bin/python3
"""
Media Tags Application Layer.

This module contains application services that orchestrate media tag operations.
MediaTagService provides high-level workflows for reading, normalizing, and processing
audio file metadata across different formats. Coordinates between domain services and
infrastructure implementations.
"""
from .service import MediaTagService

__all__ = [
    'MediaTagService'
]