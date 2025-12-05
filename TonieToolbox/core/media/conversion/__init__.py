#!/usr/bin/python3
"""
Audio conversion utilities.
"""
import os
from ...config.application_constants import SUPPORTED_EXTENSIONS
from ...utils import get_logger
from .converter import convert_audio_with_ffmpeg
from .utils import get_input_files, append_to_filename
from .taf import convert_taf_to_chapter_files, convert_taf_to_single_file

logger = get_logger(__name__)


def convert_opus_to_mp3(opus_data: bytes, output_path: str, ffmpeg_binary: str = None,
                       bitrate: int = 128, auto_download: bool = False) -> bool:
    """
    Convert Opus audio data to MP3 format using FFmpeg.
    
    This function is now a wrapper around the universal conversion function.
    
    Args:
        opus_data: Raw Opus audio data (OGG container with Opus codec)
        output_path: Path where to save the MP3 file
        ffmpeg_binary: Path to the ffmpeg binary
        bitrate: Bitrate for the MP3 encoding in kbps
        auto_download: Whether to automatically download dependencies if not found
        
    Returns:
        True if conversion was successful, False otherwise
        
    Example:
        >>> # Convert Opus audio bytes to MP3 file
        >>> with open('audio.opus', 'rb') as f:
        ...     opus_data = f.read()
        >>> 
        >>> success = convert_opus_to_mp3(
        ...     opus_data=opus_data,
        ...     output_path='audio.mp3',
        ...     ffmpeg_binary='/usr/bin/ffmpeg',
        ...     bitrate=192
        ... )
        >>> print(f"Conversion {'succeeded' if success else 'failed'}")
        Conversion succeeded
    """
    logger.debug("Converting Opus data to MP3 format (bitrate: %d kbps)", bitrate)
    
    return convert_audio_with_ffmpeg(
        input_data=opus_data,
        output_path=output_path,
        output_format="mp3",
        codec_options={'bitrate': bitrate},
        ffmpeg_binary=ffmpeg_binary,
        auto_download=auto_download
    )



def filter_directories(glob_list: list[str]) -> list[str]:
    """
    Filter a list of glob results to include only audio files that can be handled by ffmpeg.
    
    Args:
        glob_list: List of path names from glob.glob()
        
    Returns:
        Filtered list containing only supported audio files
    """
    logger.debug("Filtering %d glob results for supported audio files", len(glob_list))
    supported_extensions = SUPPORTED_EXTENSIONS
    logger.debug("Supported audio file extensions: %s", supported_extensions)
    
    filtered = []
    for name in glob_list:
        if os.path.isfile(name):
            ext = os.path.splitext(name)[1].lower()
            if ext in supported_extensions:
                filtered.append(name)
                logger.debug("Added supported file: %s", name)
            else:
                logger.debug("Skipped unsupported file: %s (ext: %s)", name, ext)
        else:
            logger.debug("Skipped non-file: %s", name)
    
    logger.debug("Filtered to %d supported audio files", len(filtered))
    return filtered


__all__ = [
    'filter_directories',
    'convert_opus_to_mp3',
    'convert_audio_with_ffmpeg', 
    'get_input_files',
    'append_to_filename',
    'convert_taf_to_chapter_files',
    'convert_taf_to_single_file'
]