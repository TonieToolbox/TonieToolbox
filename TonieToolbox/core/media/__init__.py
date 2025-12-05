#!/usr/bin/python3
"""
Media Domain Module.

Provides media processing domain services and models within the Clean Architecture
framework. This module serves as the domain layer for media-specific business logic.

Architecture Position:
- Layer: Domain (media-specific) + Infrastructure (player, formats)
- Dependencies: FFmpeg (through conversion), PyQt6 (through player)
- Used by: processing/ application layer, GUI, TeddyCloud

Submodules:
- tags/ - Media tag extraction (Clean Architecture: domain/application/infrastructure)
- player/ - TAF audio player engine (infrastructure + domain)
- formats/ - Audio format handlers (Ogg, Opus) (infrastructure primitives)
- conversion/ - Media conversion utilities (infrastructure)
- playlist/ - Playlist discovery and management (domain)

Note: The tags/ module follows full Clean Architecture with domain/application/infrastructure layers.
"""
from .player import *
from .formats import *
from .conversion import *

# Import specific tags components (explicit imports for Clean Architecture clarity)
from .tags import get_media_tag_service, show_file_tags

__all__ = [
    # From player module
    'TAFPlayer',
    
    # From tags module (Clean Architecture only)
    'get_media_tag_service',
    'show_file_tags',
    
    # From formats module
    'OggPage',
    'create_crc_table',
    'crc32',
    
    # From conversion module
    'filter_directories'
]