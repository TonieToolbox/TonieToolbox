#!/usr/bin/env python3
"""
Domain Models for Analysis Module.

This package contains pure domain objects that represent analysis results
without any external dependencies or infrastructure concerns.
"""

from .taf_analysis import (
    ChapterInfo,
    TonieHeaderInfo, 
    OpusInfo,
    AudioAnalysisInfo,
    TafAnalysisResult
)

__all__ = [
    'ChapterInfo',
    'TonieHeaderInfo',
    'OpusInfo', 
    'AudioAnalysisInfo',
    'TafAnalysisResult'
]