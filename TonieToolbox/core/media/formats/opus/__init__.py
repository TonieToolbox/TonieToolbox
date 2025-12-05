"""
Opus Audio Format Handling Module.

This module provides comprehensive support for Opus audio codec operations.
It includes packet parsing, manipulation, and validation for Opus-encoded audio streams,
which are essential for TAF file processing in TonieToolbox.
"""

from .packet import OpusPacket

__all__ = ['OpusPacket']