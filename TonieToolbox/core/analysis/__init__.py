#!/usr/bin/python3
"""
TAF Analysis Domain Module.

This module provides TAF file analysis domain services and models within
the Clean Architecture framework. It serves as the domain layer for TAF-specific
business logic and is used by the processing/ workflow orchestration layer.

Architecture Position:
- Layer: Domain (TAF-specific)
- Dependencies: Only media formats and utils (no external dependencies)
- Used by: processing/ application layer, GUI controllers

Provides:
- Pure domain models (TafAnalysisResult, ChapterInfo, etc.)
- Domain services (TafAnalysisService)
- TAF validation and extraction logic
"""
from .header import get_header_info, get_header_info_cli
from .validation import check_tonie_file, check_tonie_file_cli, compare_taf_files
from .extraction import split_to_opus_files, get_audio_info
from .taf_analyzer import analyze_taf_file

# Domain models
from .models import (
    ChapterInfo,
    TonieHeaderInfo,
    OpusInfo,
    AudioAnalysisInfo,
    TafAnalysisResult
)

# Domain services
from .services import TafAnalysisService

__all__ = [
    # Core analysis functions
    'get_header_info',
    'get_header_info_cli',
    'check_tonie_file',
    'check_tonie_file_cli',
    'compare_taf_files',
    'split_to_opus_files',
    'get_audio_info',
    
    # Domain-based analysis
    'analyze_taf_file',
    
    # Domain models
    'ChapterInfo',
    'TonieHeaderInfo',
    'OpusInfo',
    'AudioAnalysisInfo', 
    'TafAnalysisResult',
    
    # Domain services
    'TafAnalysisService'
]