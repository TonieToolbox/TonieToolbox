#!/usr/bin/env python3
"""
Interface adapters package.

This module contains interface adapters that coordinate between external
interfaces (CLI, GUI) and application services.
"""

from .base_adapter import BaseInterfaceAdapter, ProgressTrackingMixin
from .single_file_adapter import SingleFileProcessingAdapter, FileAnalysisAdapter, BatchFileProcessingAdapter
from .files_to_taf_adapter import FilesToTafAdapter, RecursiveProcessingAdapter

__all__ = [
    'BaseInterfaceAdapter',
    'ProgressTrackingMixin',
    'SingleFileProcessingAdapter',
    'FileAnalysisAdapter',
    'BatchFileProcessingAdapter',
    'FilesToTafAdapter',
    'RecursiveProcessingAdapter'
]