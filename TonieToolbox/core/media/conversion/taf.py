#!/usr/bin/python3
"""
TAF (Tonie Audio Format) conversion functions.
"""
import os
import math
import tempfile
import subprocess
import struct
from ...utils import get_logger
from ...file.taf import tonie_header_pb2
from ..formats.ogg import OggPage
from .converter import convert_audio_with_ffmpeg

logger = get_logger(__name__)


# Use domain service for bitrate extraction 
def extract_bitrate_from_encoder_options(opus_comments: dict) -> int:
    """
    Extract bitrate from Opus encoder_options comment.
    
    Delegates to domain service for consistent business logic.
    
    Args:
        opus_comments: Dictionary of Opus comments
        
    Returns:
        Detected bitrate in kbps, or None if not found
    """
    from ..services import BitrateExtractionService
    
    if not opus_comments or "encoder_options" not in opus_comments:
        return None
    
    return BitrateExtractionService.extract_from_encoder_options(
        opus_comments["encoder_options"]
    )





def convert_taf_to_chapter_files(filename: str, output: str = None, 
                                format: str = "mp3", codec_options: dict = None,
                                ffmpeg_binary: str = None, auto_download: bool = False,
                                extra_ffmpeg_args: list = None) -> bool:
    """
    Convert TAF file chapters to separate audio files.
    
    Args:
        filename: Path to the TAF file
        output: Output directory (optional)
        format: Output audio format (mp3, wav, flac, ogg, etc.)
        codec_options: Dictionary of codec-specific options (e.g., {'bitrate': 128, 'sample_rate': 44100})
        ffmpeg_binary: Path to ffmpeg binary (optional)
        auto_download: Whether to auto-download dependencies
        extra_ffmpeg_args: Additional ffmpeg arguments as list (optional)
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        FileNotFoundError: If TAF file doesn't exist
        RuntimeError: If FFmpeg binary is not provided
        ValueError: If TAF file is corrupted or invalid format
        OSError: If output directory cannot be created
        PermissionError: If insufficient permissions to write output files
    """
    
    if not os.path.isfile(filename):
        logger.error("File not found: %s", filename)
        raise FileNotFoundError(f"File not found: {filename}")
    
    logger.info("Converting TAF file to individual %s tracks: %s", format, filename)
    
    # Setup default codec options
    if codec_options is None:
        codec_options = {}
    
    # FFmpeg binary should be provided by caller (dependencies manager)
    if ffmpeg_binary is None:
        logger.error("FFmpeg binary not provided. This function should be called with a resolved ffmpeg_binary path")
        raise RuntimeError("FFmpeg binary not provided. This function should be called with a resolved ffmpeg_binary path")
    
    try:
        from ...analysis.header import get_header_info
        with open(filename, "rb") as taf_file:
            # Get header info including Opus comments to detect source bitrate
            header_size, tonie_header, file_size, audio_size, sha1sum, \
            opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no, \
            opus_comments = get_header_info(taf_file)
            
            # Try to detect source bitrate from encoder options if not specified
            detected_bitrate = extract_bitrate_from_encoder_options(opus_comments)
            if detected_bitrate and 'bitrate' not in codec_options:
                codec_options['bitrate'] = detected_bitrate
                logger.info("Using detected source bitrate: %d kbps", detected_bitrate)
            
            # Reset file position to start of audio data
            taf_file.seek(4 + header_size)

            abs_path = os.path.abspath(filename)
            if output:
                if not os.path.exists(output):
                    logger.debug("Creating output directory: %s", output)
                    os.makedirs(output)
                path = output
            else:
                path = os.path.dirname(abs_path)
                
            logger.debug("Output path: %s", path)
            
            name = os.path.basename(abs_path)
            pos = name.rfind('.')
            if pos == -1:
                name = name + f".{format}"
            else:
                name = name[:pos] + f".{format}"
                
            filename_template = "{{:02d}}_{}".format(name)
            out_path = "{}{}".format(path, os.path.sep)
            logger.debug("Output filename template: %s", out_path + filename_template)

            # Read the first two OGG pages (Opus identification and comment headers)
            found = OggPage.seek_to_page_header(taf_file)
            if not found:
                logger.error("First OGG page not found")
                raise RuntimeError("First ogg page not found")
                
            first_page = OggPage(taf_file)
            logger.debug("Read first OGG page")

            found = OggPage.seek_to_page_header(taf_file)
            if not found:
                logger.error("Second OGG page not found")
                raise RuntimeError("Second ogg page not found")
                
            second_page = OggPage(taf_file)
            logger.debug("Read second OGG page")

            found = OggPage.seek_to_page_header(taf_file)
            page = OggPage(taf_file)
            logger.debug("Read third OGG page")

            pad_len = math.ceil(math.log(len(tonie_header.chapterPages) + 1, 10))
            format_string = "[{{:0{}d}}/{:0{}d}] {{}}".format(pad_len, len(tonie_header.chapterPages), pad_len)
            
            for i in range(0, len(tonie_header.chapterPages)):
                if (i + 1) < len(tonie_header.chapterPages):
                    end_page = tonie_header.chapterPages[i + 1]
                else:
                    end_page = 0
                    
                granule = 0
                output_filename = filename_template.format(i + 1)
                print(format_string.format(i + 1, output_filename))
                logger.info("Creating track %d: %s (end page: %d)", i + 1, out_path + output_filename, end_page)
                
                # Create temporary Opus data
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_opus:
                    # Write Opus header pages and audio data
                    first_page.write_page(temp_opus)
                    second_page.write_page(temp_opus)
                    page_count = 0
                    
                    while found and ((page.page_no < end_page) or (end_page == 0)):
                        page.correct_values(granule)
                        granule = page.granule_position
                        page.write_page(temp_opus)
                        page_count += 1
                        
                        found = OggPage.seek_to_page_header(taf_file)
                        if found:
                            page = OggPage(taf_file)
                    
                    logger.debug("Track %d: Collected %d pages, final granule position: %d", 
                                i + 1, page_count, granule)
                    
                    temp_opus.flush()
                    
                    # Convert using FFmpeg with flexible options
                    output_file_path = "{}{}".format(out_path, output_filename)
                    success = convert_audio_with_ffmpeg(
                        input_path=temp_opus.name,
                        output_path=output_file_path,
                        output_format=format,
                        codec_options=codec_options,
                        ffmpeg_binary=ffmpeg_binary,
                        extra_ffmpeg_args=extra_ffmpeg_args
                    )
                    
                    # Clean up temporary file
                    try:
                        os.unlink(temp_opus.name)
                    except:
                        pass
                    
                    if not success:
                        logger.error("Failed to convert track %d", i + 1)
                        return False
                    else:
                        logger.debug("Successfully converted track %d", i + 1)
            
            logger.info("Successfully converted TAF file to %d individual %s tracks", len(tonie_header.chapterPages), format)
            return True
            
    except Exception as e:
        logger.error("Error converting TAF file: %s", str(e))
        return False


def convert_taf_to_single_file(filename: str, output_path: str = None, 
                              format: str = "mp3", codec_options: dict = None,
                              ffmpeg_binary: str = None, auto_download: bool = False,
                              extra_ffmpeg_args: list = None) -> bool:
    """
    Convert full TAF audio to a single audio file.
    
    Args:
        filename: Path to the TAF file
        output_path: Output file path (optional)
        format: Output audio format (mp3, wav, flac, ogg, etc.)
        codec_options: Dictionary of codec-specific options (e.g., {'bitrate': 128, 'sample_rate': 44100})
        ffmpeg_binary: Path to ffmpeg binary (optional)
        auto_download: Whether to auto-download dependencies
        extra_ffmpeg_args: Additional ffmpeg arguments as list (optional)
        
    Returns:
        True if successful, False otherwise
    """
    
    if not os.path.isfile(filename):
        logger.error("File not found: %s", filename)
        return False
    
    logger.info("Converting full TAF audio to single %s file: %s", format, filename)
    
    # Generate output path if not provided
    if output_path is None:
        abs_path = os.path.abspath(filename)
        name = os.path.basename(abs_path)
        pos = name.rfind('.')
        if pos == -1:
            output_path = name + f".{format}"
        else:
            output_path = name[:pos] + f".{format}"
        output_path = os.path.join(os.path.dirname(abs_path), output_path)
    
    logger.debug("Output file: %s", output_path)
    
    # Setup default codec options
    if codec_options is None:
        codec_options = {}
    
    # FFmpeg binary should be provided by caller (dependencies manager)
    if ffmpeg_binary is None:
        logger.error("FFmpeg binary not provided. This function should be called with a resolved ffmpeg_binary path")
        return False
    
    try:
        from ...analysis.header import get_header_info
        with open(filename, "rb") as taf_file:
            # Get header info including Opus comments to detect source bitrate
            header_size, tonie_header, file_size, audio_size, sha1sum, \
            opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no, \
            opus_comments = get_header_info(taf_file)
            
            # Try to detect source bitrate from encoder options if not specified
            detected_bitrate = extract_bitrate_from_encoder_options(opus_comments)
            if detected_bitrate and 'bitrate' not in codec_options:
                codec_options['bitrate'] = detected_bitrate
                logger.info("Using detected source bitrate: %d kbps", detected_bitrate)
            
            # Reset file position to start of audio data and read all remaining Opus data
            taf_file.seek(4 + header_size)
            opus_data = taf_file.read()
            logger.debug("Read %d bytes of Opus audio data", len(opus_data))
            
            # Create temporary Opus file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_opus:
                temp_opus.write(opus_data)
                temp_opus.flush()
                
                # Convert using FFmpeg
                success = convert_audio_with_ffmpeg(
                    input_path=temp_opus.name,
                    output_path=output_path,
                    output_format=format,
                    codec_options=codec_options,
                    ffmpeg_binary=ffmpeg_binary,
                    extra_ffmpeg_args=extra_ffmpeg_args
                )
                
                # Clean up temporary file
                try:
                    os.unlink(temp_opus.name)
                except:
                    pass
                
                if success:
                    logger.info("Successfully converted full audio to %s: %s", format, output_path)
                    return True
                else:
                    logger.error("Failed to convert audio")
                    return False
                    
    except Exception as e:
        logger.error("Error converting TAF file: %s", str(e))
        return False