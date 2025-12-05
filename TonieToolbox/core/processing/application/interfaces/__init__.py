#!/usr/bin/env python3
"""
Interfaces module for processing application.

This module exports all interfaces used in the processing application layer.
"""

from .file_repository import FileRepository, FileWatcher, FileIterator
from .media_converter import MediaConverter, ConversionProgress
from .upload_service import (
    UploadService, 
    UploadQueue, 
    UploadProgress, 
    UploadResult
)

__all__ = [
    # File repository interfaces
    'FileRepository',
    'FileWatcher', 
    'FileIterator',
    
    # Media converter interfaces
    'MediaConverter',
    'ConversionProgress',
    
    # Upload service interfaces
    'UploadService',
    'UploadQueue',
    'UploadProgress',
    'UploadResult'
]