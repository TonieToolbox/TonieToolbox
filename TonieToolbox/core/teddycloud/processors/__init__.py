#!/usr/bin/python3
"""
TeddyCloud File Processors.

This module provides high-level processors for TeddyCloud integration workflows.
Processors handle file uploads, tag creation/updates, and direct upload scenarios.
They coordinate with application services and emit events for progress tracking and
UI updates during TeddyCloud operations.
"""

from .upload_processor import (
    TeddyCloudUploadProcessor,
    TeddyCloudTagProcessor,
    TeddyCloudDirectUploadProcessor
)

__all__ = [
    'TeddyCloudUploadProcessor',
    'TeddyCloudTagProcessor',
    'TeddyCloudDirectUploadProcessor'
]