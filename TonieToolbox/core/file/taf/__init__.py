"""
TAF (Toniebox Audio Format) File Operations Module.

This module provides comprehensive functionality for creating and manipulating TAF files.
Includes TAF file creation, OGG page processing, header management, and protobuf-based
metadata handling. TAF is the proprietary audio format used by Toniebox devices.
"""
from .creator import create_tonie_file
from .processor import (
    copy_first_and_second_page,
    skip_first_two_pages, 
    read_all_remaining_pages,
    resize_pages,
    fix_tonie_header
)
from . import tonie_header_pb2

__all__ = [
    'create_tonie_file',
    'copy_first_and_second_page',
    'skip_first_two_pages',
    'read_all_remaining_pages', 
    'resize_pages',
    'fix_tonie_header',
    'tonie_header_pb2'
]