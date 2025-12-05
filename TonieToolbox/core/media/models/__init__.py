#!/usr/bin/env python3
"""
Domain Models for Media Module.

Pure domain objects for audio processing, formats, and conversion
without external dependencies.
"""

from .audio import (
    AudioFormat,
    BitrateMode,
    AudioCodecParams,
    ConversionRequest,
    AudioMetadata,
    ConversionResult
)

__all__ = [
    'AudioFormat',
    'BitrateMode',
    'AudioCodecParams',
    'ConversionRequest',
    'AudioMetadata',
    'ConversionResult'
]