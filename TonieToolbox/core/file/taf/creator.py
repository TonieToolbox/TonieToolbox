#!/usr/bin/python3
"""
TAF file creator - main functionality for creating Tonie files.
"""
import hashlib
import math
import os
import time
from typing import List
from ...utils import get_logger
from ...config.application_constants import TIMESTAMP_DEDUCT
from ...config import get_config_manager
from ....core.media.formats.ogg import OggPage
from .processor import copy_first_and_second_page, skip_first_two_pages, read_all_remaining_pages, resize_pages, fix_tonie_header

logger = get_logger(__name__)


def create_tonie_file(
    output_file: str,
    input_files: List[str],
    no_tonie_header: bool = False,
    user_timestamp: int = None,
    bitrate: int = None,
    vbr: bool = True,
    ffmpeg_binary: str = None,
    keep_temp: bool = False,
    auto_download: bool = False,
    use_custom_tags: bool = True,
    no_mono_conversion: bool = False
) -> None:
    """
    Create a TAF file from audio input files.

    Args:
        output_file (str): Path where the TAF file will be saved
        input_files (List[str]): List of audio files to include in the TAF file
        no_tonie_header (bool): If True, skip adding Tonie header (creates raw OGG)
        user_timestamp (int | None): Custom timestamp for the file. If None, uses current time
        bitrate (int): Target bitrate in kbps for the Opus encoding
        vbr (bool): Enable variable bitrate encoding
        ffmpeg_binary (str | None): Path to FFmpeg binary
        keep_temp (bool): Keep temporary files for debugging
        auto_download (bool): Allow automatic downloading of missing dependencies
        use_custom_tags (bool): Use custom tags in the Opus comments
        no_mono_conversion (bool): Skip automatic mono conversion
        
    Raises:
        FileNotFoundError: If any input audio file doesn't exist
        ValueError: If input_files list is empty or output_file is invalid
        RuntimeError: If FFmpeg is not available and auto_download is False
        OSError: If output directory cannot be created or written to
        PermissionError: If insufficient permissions to write output file
    """
    # Get default bitrate from config if not provided
    if bitrate is None:
        config_manager = get_config_manager()
        bitrate = config_manager.processing.audio.default_bitrate
    
    logger.trace("Entering create_tonie_file(output_file=%s, input_files=%s, no_tonie_header=%s, user_timestamp=%s, "
                "bitrate=%d, vbr=%s, ffmpeg_binary=%s, keep_temp=%s, auto_download=%s, use_custom_tags=%s, no_mono_conversion=%s)",
                output_file, input_files, no_tonie_header, user_timestamp, bitrate, vbr, ffmpeg_binary, 
                keep_temp, auto_download, use_custom_tags, no_mono_conversion)
    from ....core.media.conversion import convert_audio_with_ffmpeg
    
    logger.trace("Entering create_tonie_file(output_file=%s, input_files=%s, no_tonie_header=%s, user_timestamp=%s, "
                "bitrate=%d, vbr=%s, ffmpeg_binary=%s, keep_temp=%s, auto_download=%s, use_custom_tags=%s, no_mono_conversion=%s)",
                output_file, input_files, no_tonie_header, user_timestamp, bitrate, vbr, ffmpeg_binary, 
                keep_temp, auto_download, use_custom_tags, no_mono_conversion)
    
    logger.info("Creating Tonie file from %d input files", len(input_files))
    logger.debug("Output file: %s, Bitrate: %d kbps, VBR: %s, No header: %s", 
                output_file, bitrate, vbr, no_tonie_header)
    
    temp_files = []
    
    with open(output_file, "wb") as out_file:
        if not no_tonie_header:
            logger.debug("Reserving space for Tonie header (0x1000 bytes)")
            out_file.write(bytearray(0x1000))
        
        if user_timestamp is not None:
            if os.path.isfile(user_timestamp) and user_timestamp.lower().endswith('.taf'):
                logger.debug("Extracting timestamp from Tonie file: %s", user_timestamp)
                from ....core.analysis.header import get_header_info
                try:
                    with open(user_timestamp, "rb") as taf_file:
                        _, tonie_header, _, _, _, _, _, _, _, bitstream_serial_no = get_header_info(taf_file)
                        timestamp = bitstream_serial_no
                        logger.debug("Extracted timestamp from Tonie file: %d", timestamp)
                except Exception as e:
                    logger.error("Failed to extract timestamp from Tonie file: %s", str(e))
                    timestamp = int(time.time())
                    logger.debug("Falling back to current timestamp: %d", timestamp)
            elif user_timestamp.startswith("0x"):
                timestamp = int(user_timestamp, 16)
                logger.debug("Using user-provided hexadecimal timestamp: %d", timestamp)
            else:
                try:
                    timestamp = int(user_timestamp)
                    logger.debug("Using user-provided decimal timestamp: %d", timestamp)
                except ValueError:
                    logger.error("Invalid timestamp format: %s", user_timestamp)
                    timestamp = int(time.time())
                    logger.debug("Falling back to current timestamp: %d", timestamp)
        else:
            timestamp = int(time.time()-TIMESTAMP_DEDUCT)
            logger.debug("Using current timestamp - 0x50000000: %d", timestamp)
        
        sha1 = hashlib.sha1()
        template_page = None
        chapters = []
        total_granule = 0
        next_page_no = 2
        max_size = 0x1000
        other_size = 0xE00
        last_track = False
        
        pad_len = math.ceil(math.log(len(input_files) + 1, 10))
        format_string = "[{{:0{}d}}/{:0{}d}] {{}}".format(pad_len, len(input_files), pad_len)
        
        for index in range(len(input_files)):
            fname = input_files[index]
            logger.info(format_string.format(index + 1, fname))
            
            if index == len(input_files) - 1:
                last_track = True
                logger.debug("Processing last track")
            
            if fname.lower().endswith(".opus"):
                logger.debug("Input is already in Opus format")
                handle = open(fname, "rb")
                temp_file_path = None
            else:
                logger.debug("Converting %s to Opus format (bitrate: %d kbps, VBR: %s, no_mono_conversion: %s)", 
                            fname, bitrate, vbr, no_mono_conversion)
                
                # Use the new unified conversion system
                import tempfile
                import os
                
                # FFmpeg binary should be provided by caller (dependencies manager)
                if ffmpeg_binary is None:
                    raise RuntimeError("FFmpeg binary not provided. This function should be called with a resolved ffmpeg_binary path")
                
                # Setup codec options
                codec_options = {
                    'bitrate': bitrate,
                    'sample_rate': 48000
                }
                
                # Handle mono to stereo conversion if needed
                if not no_mono_conversion:
                    try:
                        # Use ffprobe to detect channels
                        ffmpeg_dir = os.path.dirname(ffmpeg_binary)
                        ffprobe_candidates = [
                            os.path.join(ffmpeg_dir, 'ffprobe'),
                            os.path.join(ffmpeg_dir, 'ffprobe.exe'),
                            'ffprobe', 'ffprobe.exe'
                        ]
                        
                        ffprobe_path = None
                        for candidate in ffprobe_candidates:
                            try:
                                import subprocess
                                result = subprocess.run([candidate, '-version'], capture_output=True, timeout=5)
                                if result.returncode == 0:
                                    ffprobe_path = candidate
                                    break
                            except:
                                continue
                        
                        if ffprobe_path:
                            probe_cmd = [ffprobe_path, '-v', 'error', '-select_streams', 'a:0', 
                                       '-show_entries', 'stream=channels', '-of', 'default=noprint_wrappers=1:nokey=1', fname]
                            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                            if result.returncode == 0 and result.stdout.strip() == '1':
                                logger.info("Mono input detected, converting to stereo")
                                codec_options['channels'] = 2
                    except Exception as e:
                        logger.warning("Could not detect channel count: %s", e)
                
                if keep_temp:
                    # Create persistent temporary file
                    temp_dir = os.path.join(tempfile.gettempdir(), "tonie_toolbox_temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    base_filename = os.path.basename(fname)
                    temp_file_path = os.path.join(temp_dir, f"{os.path.splitext(base_filename)[0]}_{bitrate}kbps.opus")
                    
                    success = convert_audio_with_ffmpeg(
                        input_path=fname,
                        output_path=temp_file_path,
                        output_format="opus",
                        codec_options=codec_options,
                        ffmpeg_binary=ffmpeg_binary,
                        auto_download=auto_download
                    )
                    
                    if success:
                        logger.debug("Opus file created: %s", temp_file_path)
                        handle = open(temp_file_path, "rb")
                        temp_files.append(temp_file_path)
                        logger.debug("Temporary opus file saved to: %s", temp_file_path)
                    else:
                        raise RuntimeError("Failed to convert audio to Opus format")
                else:
                    # Create temporary file for conversion
                    with tempfile.NamedTemporaryFile(suffix='.opus', delete=False) as temp_output:
                        temp_file_path = temp_output.name
                    
                    try:
                        success = convert_audio_with_ffmpeg(
                            input_path=fname,
                            output_path=temp_file_path,
                            output_format="opus", 
                            codec_options=codec_options,
                            ffmpeg_binary=ffmpeg_binary,
                            auto_download=auto_download
                        )
                        
                        if success:
                            handle = open(temp_file_path, 'rb')
                            # Store temp file for cleanup (will be deleted later)
                            temp_files.append(temp_file_path)
                        else:
                            raise RuntimeError("Failed to convert audio to Opus format")
                    except Exception as e:
                        # Clean up on error
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        raise
            
            try:
                if next_page_no == 2:
                    logger.debug("Processing first file: copying first and second page")
                    copy_first_and_second_page(handle, out_file, timestamp, sha1, use_custom_tags, bitrate, vbr)
                else:
                    logger.debug("Processing subsequent file: skipping first and second page")
                    other_size = max_size
                    skip_first_two_pages(handle)
                
                logger.debug("Reading remaining pages from file")
                pages = read_all_remaining_pages(handle)
                logger.debug("Read %d pages from file", len(pages))
                
                if template_page is None:
                    template_page = OggPage.from_page(pages[0])
                    template_page.serial_no = timestamp
                    logger.debug("Created template page with serial no %d", timestamp)
                
                if next_page_no == 2:
                    chapters.append(0)
                    logger.debug("Added first chapter at page 0")
                else:
                    chapters.append(next_page_no)
                    logger.debug("Added chapter at page %d", next_page_no)
                
                logger.debug("Resizing pages for track %d", index + 1)
                new_pages = resize_pages(pages, max_size, other_size, template_page,
                                        total_granule, next_page_no, last_track)
                logger.debug("Resized to %d pages for track %d", len(new_pages), index + 1)
                
                for i, new_page in enumerate(new_pages):
                    logger.trace("Writing page %d/%d (page number: %d)", i+1, len(new_pages), new_page.page_no)
                    new_page.write_page(out_file, sha1)
                
                last_page = new_pages[len(new_pages) - 1]
                total_granule = last_page.granule_position
                next_page_no = last_page.page_no + 1
                logger.debug("Track %d processed, next page no: %d, total granule: %d", 
                            index + 1, next_page_no, total_granule)
                            
            except Exception as e:
                logger.error("Error processing file %s: %s", fname, str(e))
                raise
            finally:
                handle.close()
        
        if not no_tonie_header:
            logger.debug("Writing Tonie header")
            fix_tonie_header(out_file, chapters, timestamp, sha1)
    
    # Handle temporary file cleanup
    if keep_temp and temp_files:
        logger.info("Kept %d temporary opus files in %s", len(temp_files), os.path.dirname(temp_files[0]))
    elif temp_files and not keep_temp:
        # Clean up temporary files
        cleaned_count = 0
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    cleaned_count += 1
            except Exception as e:
                logger.warning("Could not delete temporary file %s: %s", temp_file, e)
        if cleaned_count > 0:
            logger.debug("Cleaned up %d temporary opus files", cleaned_count)
    
    logger.trace("Exiting create_tonie_file() successfully")
    logger.info("Successfully created Tonie file: %s", output_file)