#!/usr/bin/python3
"""
Opus header handling for TAF files.
"""
import struct
from ...utils import get_logger
from ...config.application_constants import OPUS_TAGS, SAMPLE_RATE_KHZ
from ...config import get_config_manager
from ...media.formats.opus import OpusPacket
from ...media.formats.ogg import OggPage
from .comments import toniefile_comment_add

logger = get_logger(__name__)


def check_identification_header(page) -> None:
    """
    Check if a page contains a valid Opus identification header.
    
    Args:
        page: OggPage to check
        
    Raises:
        RuntimeError: If the header is invalid or unsupported
    """
    segment = page.segments[0]
    unpacked = struct.unpack("<8sBBHLH", segment.data[0:18])
    logger.debug("Checking Opus identification header")
    
    if unpacked[0] != b"OpusHead":
        logger.error("Invalid opus file: OpusHead signature not found")
        raise RuntimeError("Invalid opus file: OpusHead signature not found")
    
    if unpacked[1] != 1:
        logger.error("Invalid opus file: Version mismatch")
        raise RuntimeError("Invalid opus file: Opus version mismatch")
    
    if unpacked[2] != 2:
        logger.error("Only stereo tracks are supported, found channel count: %d", unpacked[2])
        raise RuntimeError(f"Only stereo tracks (2 channels) are supported. Found {unpacked[2]} channel(s). Please convert your audio to stereo format.")
    
    if unpacked[4] != SAMPLE_RATE_KHZ * 1000:
        logger.error("Sample rate needs to be 48 kHz, found: %d Hz", unpacked[4])
        raise RuntimeError(f"Sample rate needs to be 48 kHz. Found {unpacked[4]} Hz.")
    
    logger.debug("Opus identification header is valid")


def prepare_opus_tags(page, custom_tags: bool = False, bitrate: int = None, vbr: bool = True) -> OggPage:
    """
    Prepare standard Opus tags for a Tonie file.
    
    Args:
        page: OggPage to modify
        custom_tags (bool): Whether to use custom TonieToolbox tags instead of default ones
        bitrate (int): Actual bitrate used for encoding
        vbr (bool): Whether variable bitrate was used
        
    Returns:
        OggPage: Modified page with Tonie-compatible Opus tags
    """
    # Get default bitrate from config if not provided
    if bitrate is None:
        config_manager = get_config_manager()
        bitrate = config_manager.processing.audio.default_bitrate
    
    logger.debug("Preparing Opus tags for Tonie compatibility")
    page.segments.clear()
    
    if not custom_tags:
        segment = OpusPacket(None)
        segment.size = len(OPUS_TAGS[0])
        segment.data = bytearray(OPUS_TAGS[0])
        segment.spanning_packet = True
        segment.first_packet = True
        page.segments.append(segment)
        
        segment = OpusPacket(None)
        segment.size = len(OPUS_TAGS[1])
        segment.data = bytearray(OPUS_TAGS[1])
        segment.spanning_packet = False
        segment.first_packet = False
        page.segments.append(segment)
    else:
        logger.debug("Creating custom Opus tags")
        comment_data = bytearray(0x1B4)
        comment_data_pos = 0
        
        comment_data[comment_data_pos:comment_data_pos+8] = b"OpusTags"
        comment_data_pos += 8        
        comment_data_pos = toniefile_comment_add(comment_data, comment_data_pos, "TonieToolbox")        
        
        comments_count = 3
        comment_data[comment_data_pos:comment_data_pos+4] = struct.pack("<I", comments_count)
        comment_data_pos += 4        
        
        from .... import __version__
        version_str = f"version={__version__}"
        comment_data_pos = toniefile_comment_add(comment_data, comment_data_pos, version_str)        
        
        encoder_info = "libopus (via FFmpeg)"
        comment_data_pos = toniefile_comment_add(comment_data, comment_data_pos, f"encoder={encoder_info}")        
        
        vbr_opt = "--vbr" if vbr else "--cbr"
        encoder_options = f"encoder_options=--bitrate {bitrate} {vbr_opt}"
        comment_data_pos = toniefile_comment_add(comment_data, comment_data_pos, encoder_options)        
        
        remain = len(comment_data) - comment_data_pos - 4
        comment_data[comment_data_pos:comment_data_pos+4] = struct.pack("<I", remain)
        comment_data_pos += 4
        comment_data[comment_data_pos:comment_data_pos+4] = b"pad="        
        comment_data = comment_data[:comment_data_pos + remain]
        
        remaining_data = comment_data
        first_segment = True        
        while remaining_data:
            chunk_size = min(255, len(remaining_data))
            segment = OpusPacket(None)
            segment.size = chunk_size
            segment.data = remaining_data[:chunk_size]
            segment.spanning_packet = len(remaining_data) > chunk_size
            segment.first_packet = first_segment
            page.segments.append(segment)
            remaining_data = remaining_data[chunk_size:]
            first_segment = False
    
    page.correct_values(0)
    logger.trace("Opus tags prepared with %d segments", len(page.segments))
    return page