#!/usr/bin/python3
"""
Header processing for TAF file analysis.
Handles Tonie header parsing and Opus metadata extraction.
"""
import hashlib
import struct
from typing import Dict, Tuple, Any
from ..utils import get_logger
from ..file.taf import tonie_header_pb2
from ..media.formats import OggPage

logger = get_logger(__name__)


# Import domain service for bitrate extraction
def extract_bitrate_from_encoder_options(encoder_options: str) -> int:
    """
    Extract bitrate from Opus encoder_options string.
    
    Delegates to domain service for pure business logic.
    
    Args:
        encoder_options (str): Encoder options string
        
    Returns:
        int: Detected bitrate in kbps, or None if not found
    """
    from ..media.services import BitrateExtractionService
    return BitrateExtractionService.extract_from_encoder_options(encoder_options)


def get_header_info(in_file) -> tuple:
    """
    Get header information from a Tonie file.
    
    Args:
        in_file: Input file handle
        
    Returns:
        tuple: Header size, Tonie header object, file size, audio size, SHA1 sum,
               Opus header found flag, Opus version, channel count, sample rate, bitstream serial number,
               Opus comments dictionary
               
    Raises:
        RuntimeError: If OGG pages cannot be found
    """
    logger.debug("Reading Tonie header information")
    
    # Read Tonie header
    tonie_header = tonie_header_pb2.TonieHeader()
    header_size = struct.unpack(">L", in_file.read(4))[0]
    logger.debug("Header size: %d bytes", header_size)
    
    tonie_header = tonie_header.FromString(in_file.read(header_size))
    logger.debug("Read Tonie header with %d chapter pages", len(tonie_header.chapterPages))
    
    # Calculate SHA1 hash of remaining data
    sha1sum = hashlib.sha1(in_file.read())
    logger.debug("Calculated SHA1: %s", sha1sum.hexdigest())
    
    # Calculate file and audio sizes
    file_size = in_file.tell()
    in_file.seek(4 + header_size)
    audio_size = file_size - in_file.tell()
    logger.debug("File size: %d bytes, Audio size: %d bytes", file_size, audio_size)
    
    # Find and parse first OGG page (Opus header)
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("First OGG page not found")
        raise RuntimeError("First ogg page not found")
        
    first_page = OggPage(in_file)
    logger.debug("Read first OGG page")
    
    # Parse Opus header
    unpacked = struct.unpack("<8sBBHLH", first_page.segments[0].data[0:18])
    opus_head_found = unpacked[0] == b"OpusHead"
    opus_version = unpacked[1]
    channel_count = unpacked[2]
    sample_rate = unpacked[4]
    bitstream_serial_no = first_page.serial_no
    
    logger.debug("Opus header found: %s, Version: %d, Channels: %d, Sample rate: %d Hz, Serial: %d", 
                opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no)
    
    # Find and parse second OGG page (Opus comments)
    opus_comments = {}
    found = OggPage.seek_to_page_header(in_file)
    if not found:
        logger.error("Second OGG page not found")
        raise RuntimeError("Second ogg page not found")
        
    second_page = OggPage(in_file)
    logger.debug("Read second OGG page")
    
    # Parse Opus comments
    opus_comments = _parse_opus_comments(second_page)
    
    return (
        header_size, tonie_header, file_size, audio_size, sha1sum,
        opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no,
        opus_comments
    )


def get_header_info_cli(in_file) -> tuple:
    """
    Get header information from a Tonie file (CLI version).
    
    Args:
        in_file: Input file handle
        
    Returns:
        tuple: Header size, Tonie header object, file size, audio size, SHA1 sum,
               Opus header found flag, Opus version, channel count, sample rate, bitstream serial number,
               Opus comments dictionary, valid flag
               
    Note:
        Instead of raising exceptions, this function returns default values and a valid flag
    """
    logger.debug("Reading Tonie header information")
    
    try:
        # Read Tonie header
        tonie_header = tonie_header_pb2.TonieHeader()
        header_size = struct.unpack(">L", in_file.read(4))[0]
        logger.debug("Header size: %d bytes", header_size)
        
        tonie_header = tonie_header.FromString(in_file.read(header_size))
        logger.debug("Read Tonie header with %d chapter pages", len(tonie_header.chapterPages))
        
        # Calculate SHA1 hash of remaining data
        sha1sum = hashlib.sha1(in_file.read())
        logger.debug("Calculated SHA1: %s", sha1sum.hexdigest())
        
        # Calculate file and audio sizes
        file_size = in_file.tell()
        in_file.seek(4 + header_size)
        audio_size = file_size - in_file.tell()
        logger.debug("File size: %d bytes, Audio size: %d bytes", file_size, audio_size)
        
        # Find and parse first OGG page (Opus header)
        found = OggPage.seek_to_page_header(in_file)
        if not found:
            logger.error("First OGG page not found")
            return (header_size, tonie_header, file_size, audio_size, sha1sum,
                    False, 0, 0, 0, 0, {}, False)
                    
        first_page = OggPage(in_file)
        logger.debug("Read first OGG page")
        
        # Parse Opus header
        unpacked = struct.unpack("<8sBBHLH", first_page.segments[0].data[0:18])
        opus_head_found = unpacked[0] == b"OpusHead"
        opus_version = unpacked[1]
        channel_count = unpacked[2]
        sample_rate = unpacked[4]
        bitstream_serial_no = first_page.serial_no
        
        logger.debug("Opus header found: %s, Version: %d, Channels: %d, Sample rate: %d Hz, Serial: %d", 
                    opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no)
        
        # Find and parse second OGG page (Opus comments)
        opus_comments = {}
        found = OggPage.seek_to_page_header(in_file)
        if not found:
            logger.error("Second OGG page not found")
            return (header_size, tonie_header, file_size, audio_size, sha1sum,
                   opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no, {}, False)
                   
        second_page = OggPage(in_file)
        logger.debug("Read second OGG page")
        
        # Parse Opus comments
        opus_comments = _parse_opus_comments(second_page)
        
        return (
            header_size, tonie_header, file_size, audio_size, sha1sum,
            opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no,
            opus_comments, True
        )
        
    except Exception as e:
        logger.error("Error processing Tonie file: %s", str(e))
        return (0, tonie_header_pb2.TonieHeader(), 0, 0, None, False, 0, 0, 0, 0, {}, False)


def _parse_opus_comments(page: OggPage) -> Dict[str, Any]:
    """
    Parse Opus comments from an OGG page.
    
    Args:
        page: OGG page containing Opus comments
        
    Returns:
        Dict[str, Any]: Dictionary of parsed comments
    """
    opus_comments = {}
    
    try:
        comment_data = bytearray()
        for segment in page.segments:
            comment_data.extend(segment.data)
            
        if comment_data.startswith(b"OpusTags"):
            pos = 8
            
            # Read vendor string
            if pos + 4 <= len(comment_data):
                vendor_length = struct.unpack("<I", comment_data[pos:pos+4])[0]
                pos += 4
                
                if pos + vendor_length <= len(comment_data):
                    vendor = comment_data[pos:pos+vendor_length].decode('utf-8', errors='replace')
                    opus_comments["vendor"] = vendor
                    pos += vendor_length
                    
                    # Read comments
                    if pos + 4 <= len(comment_data):
                        comments_count = struct.unpack("<I", comment_data[pos:pos+4])[0]
                        pos += 4
                        
                        for i in range(comments_count):
                            if pos + 4 <= len(comment_data):
                                comment_length = struct.unpack("<I", comment_data[pos:pos+4])[0]
                                pos += 4
                                
                                if pos + comment_length <= len(comment_data):
                                    comment = comment_data[pos:pos+comment_length].decode('utf-8', errors='replace')
                                    pos += comment_length
                                    
                                    if "=" in comment:
                                        key, value = comment.split("=", 1)
                                        opus_comments[key] = value
                                    else:
                                        opus_comments[f"comment_{i}"] = comment
                                else:
                                    break
                            else:
                                break
                                
    except Exception as e:
        logger.error("Failed to parse Opus comments: %s", str(e))
        
    return opus_comments