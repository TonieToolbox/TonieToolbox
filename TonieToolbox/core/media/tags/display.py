#!/usr/bin/python3
"""
Tag display functionality for console output.
"""
import os
from typing import List
from ...utils import get_logger
from ..conversion import get_input_files

logger = get_logger(__name__)


def show_file_tags(input_pattern: str) -> int:
    """
    Display tags for all files matching the input pattern.
    
    Args:
        input_pattern: File pattern to process
        
    Returns:
        Exit code: 0 for success, 1 for error
    """
    files = get_input_files(input_pattern)
    logger.debug("Found %d files to process", len(files))
    
    if len(files) == 0:
        logger.error("No files found for pattern %s", input_pattern)
        return 1
    
    for file_index, file_path in enumerate(files):
        # Use the media tag service to get detailed tags
        from . import get_media_tag_service
        service = get_media_tag_service()
        tags = service.get_all_file_tags(file_path)
        if tags:
            print(f"\nFile {file_index + 1}: {os.path.basename(file_path)}")
            print("-" * 40)
            for tag_name, tag_info in sorted(tags.items()):
                # Extract information from the tag structure
                if isinstance(tag_info, dict):
                    original = tag_info.get('original', tag_name)
                    readable = tag_info.get('readable')
                    value = tag_info.get('value', '')
                    
                    # Format: Original Tag: Human Readable Name: Value
                    if readable:
                        print(f"{original}: {readable.title()}: {value}")
                    else:
                        print(f"{original}: {value}")
        else:
            print(f"\nFile {file_index + 1}: {os.path.basename(file_path)} - No tags found")
    
    return 0