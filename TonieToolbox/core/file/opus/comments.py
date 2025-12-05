#!/usr/bin/python3
"""
Opus comment handling for TAF files.
"""
import struct
from ...utils import get_logger

logger = get_logger(__name__)


def toniefile_comment_add(buffer: bytearray, length: int, comment_str: str) -> int:
    """
    Add a comment string to an Opus comment packet buffer.
    
    Args:
        buffer (bytearray): Bytearray buffer to add comment to
        length (int): Current position in the buffer
        comment_str (str): Comment string to add
        
    Returns:
        int: New position in the buffer after adding comment
    """
    logger.debug("Adding comment: %s", comment_str)
    str_length = len(comment_str)
    buffer[length:length+4] = struct.pack("<I", str_length)
    length += 4
    buffer[length:length+str_length] = comment_str.encode('utf-8')
    length += str_length
    logger.trace("Added comment of length %d, new buffer position: %d", str_length, length)
    return length