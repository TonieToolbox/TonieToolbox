#!/usr/bin/env python3
"""
Infrastructure repositories package.

This module provides concrete implementations of data access patterns
for the processing domain.
"""

from .filesystem_repository import FileSystemRepository, FileSystemIterator

__all__ = [
    'FileSystemRepository',
    'FileSystemIterator'
]