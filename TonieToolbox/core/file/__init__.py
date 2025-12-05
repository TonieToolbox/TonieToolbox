"""
File Operations Infrastructure Module.

Provides low-level TAF and Opus file manipulation primitives within
the Clean Architecture framework. These are infrastructure-level operations
used by higher layers for file creation and processing.

Architecture Position:
- Layer: Infrastructure (file I/O primitives)
- Dependencies: media formats, protobuf
- Used by: processing/ infrastructure layer, media conversion

Provides:
- TAF file creation (create_tonie_file)
- Opus header and comment handling
- Low-level file page manipulation
"""

from .taf.creator import create_tonie_file
from .taf.processor import copy_first_and_second_page, skip_first_two_pages, read_all_remaining_pages, resize_pages, fix_tonie_header
from .opus.comments import toniefile_comment_add
from .opus.headers import check_identification_header, prepare_opus_tags

__all__ = [
    'create_tonie_file',
    'copy_first_and_second_page',
    'skip_first_two_pages', 
    'read_all_remaining_pages',
    'resize_pages',
    'fix_tonie_header',
    'toniefile_comment_add',
    'check_identification_header',
    'prepare_opus_tags'
]