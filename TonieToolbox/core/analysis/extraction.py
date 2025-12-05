#!/usr/bin/python3
"""
Audio extraction and conversion functions for TAF files.
"""
import os
import subprocess
import tempfile


def _get_audio_info_with_ffprobe(audio_data_start: int, audio_size: int, in_file, ffmpeg_binary: str = None) -> tuple:
    """
    Get accurate duration and bitrate by extracting audio data and using ffprobe.
    
    Args:
        audio_data_start: Position in file where audio data starts
        audio_size: Size of audio data in bytes
        in_file: File handle positioned at start of file
        ffmpeg_binary: Path to ffmpeg binary (used to locate ffprobe)
        
    Returns:
        Tuple of (duration in seconds, bitrate in kbps), or (0, 0) if ffprobe fails
        
    Raises:
        OSError: If temporary file creation fails
        subprocess.TimeoutExpired: If ffprobe execution times out
        PermissionError: If insufficient permissions to create temp file
    """
    from ..utils import get_logger
    
    logger = get_logger(__name__)
    
    # Find ffprobe binary
    ffprobe_path = None
    if ffmpeg_binary:
        ffmpeg_dir, _ = os.path.split(ffmpeg_binary)
        ffprobe_candidates = [
            os.path.join(ffmpeg_dir, 'ffprobe'),
            os.path.join(ffmpeg_dir, 'ffprobe.exe'),
        ]
    else:
        ffprobe_candidates = []
    
    ffprobe_candidates.extend(['ffprobe', 'ffprobe.exe'])
    
    for candidate in ffprobe_candidates:
        try:
            result = subprocess.run([candidate, '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if result.returncode == 0:
                ffprobe_path = candidate
                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    if not ffprobe_path:
        logger.debug("ffprobe not found, cannot get accurate audio info")
        return 0, 0
    
    # Extract audio data to temporary file
    try:
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            in_file.seek(audio_data_start)
            temp_file.write(in_file.read(audio_size))
            temp_file.flush()
            
            # Use ffprobe to get duration and bitrate
            probe_cmd = [
                ffprobe_path, '-v', 'error', '-show_entries', 'format=duration,bit_rate', 
                '-of', 'csv=p=0', temp_file.name
            ]
            
            result = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            
            if result.returncode == 0:
                output_parts = result.stdout.strip().split(',')
                try:
                    duration = float(output_parts[0]) if output_parts[0] else 0
                    bitrate_bps = int(output_parts[1]) if len(output_parts) > 1 and output_parts[1] else 0
                    bitrate_kbps = round(bitrate_bps / 1000) if bitrate_bps > 0 else 0
                    
                    logger.debug(f"ffprobe detected - duration: {duration:.2f} seconds, bitrate: {bitrate_kbps} kbps")
                    return duration, bitrate_kbps
                except (ValueError, IndexError) as e:
                    logger.debug(f"Could not parse ffprobe output: {result.stdout.strip()}, error: {e}")
            else:
                logger.debug(f"ffprobe failed: {result.stderr}")
                
    except Exception as e:
        logger.debug(f"Error using ffprobe for audio info: {e}")
    finally:
        # Clean up temporary file
        try:
            if 'temp_file' in locals():
                os.unlink(temp_file.name)
        except:
            pass
    
    return 0, 0


def split_to_opus_files(filename: str, output: str = None) -> None:
    """
    Split TAF file into separate Opus files for each chapter.
    
    Args:
        filename: Path to the TAF file
        output: Output directory (optional)
    """
    import os
    import math
    from .header import get_header_info
    from ..media.formats.ogg import OggPage
    from ..utils import get_logger
    from ..file.taf import tonie_header_pb2
    import struct
    
    logger = get_logger(__name__)
    
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"File not found: {filename}")
    
    logger.info("Splitting TAF file into individual Opus tracks: %s", filename)
    
    with open(filename, "rb") as taf_file:
        tonie_header = tonie_header_pb2.TonieHeader()
        header_size = struct.unpack(">L", taf_file.read(4))[0]
        logger.debug("Header size: %d bytes", header_size)
        
        tonie_header = tonie_header.FromString(taf_file.read(header_size))
        logger.debug("Read Tonie header with %d chapter pages", len(tonie_header.chapterPages))

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
            name = name + ".opus"
        else:
            name = name[:pos] + ".opus"
            
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
            
            with open("{}{}".format(out_path, output_filename), "wb") as out_file:
                # Write the Opus header pages for each track
                first_page.write_page(out_file)
                second_page.write_page(out_file)
                page_count = 0
                
                # Write audio data pages with proper granule correction
                while found and ((page.page_no < end_page) or (end_page == 0)):
                    page.correct_values(granule)
                    granule = page.granule_position
                    page.write_page(out_file)
                    page_count += 1
                    
                    found = OggPage.seek_to_page_header(taf_file)
                    if found:
                        page = OggPage(taf_file)
                
                logger.debug("Track %d: Wrote %d pages, final granule position: %d", 
                            i + 1, page_count, granule)
        
        logger.info("Successfully split Tonie file into %d individual tracks", len(tonie_header.chapterPages))








def get_audio_info(in_file, sample_rate: int, tonie_header, header_size: int, ffmpeg_binary: str = None) -> tuple:
    """
    Get audio information from TAF file.
    
    Args:
        in_file: File handle
        sample_rate: Sample rate in kHz
        tonie_header: Parsed Tonie header
        header_size: Size of header in bytes
        ffmpeg_binary: Path to ffmpeg binary (optional)
        
    Returns:
        Tuple of (page_count, alignment_okay, page_size_okay, duration_str, chapter_durations, bitrate_kbps)
    """
    from ..utils import get_logger
    from ..media.formats import OggPage
    
    logger = get_logger(__name__)
    
    # Calculate page count and get accurate duration from granule positions
    in_file.seek(4 + header_size)  # Skip header
    page_count = 0
    alignment_okay = True
    page_size_okay = True
    last_granule_position = 0
    ffprobe_bitrate = 0  # Initialize bitrate
    
    try:
        while OggPage.seek_to_page_header(in_file):
            page = OggPage(in_file)
            page_count += 1
            # Store the last granule position which represents total samples
            if page.granule_position > 0:
                last_granule_position = page.granule_position
            if page_count > 50000:  # Safety limit
                break
    except Exception as e:
        logger.debug(f"Error reading pages: {e}")
    
    # Try to get accurate duration using ffprobe first
    audio_data_start = 4 + header_size  # Position where audio data starts
    if hasattr(tonie_header, 'dataLength'):
        audio_size = tonie_header.dataLength
    else:
        # Calculate audio size by reading to end
        current_pos = in_file.tell()
        in_file.seek(0, 2)  # Seek to end
        file_end = in_file.tell()
        audio_size = file_end - audio_data_start
        in_file.seek(current_pos)  # Restore position
    
    ffprobe_duration, ffprobe_bitrate = _get_audio_info_with_ffprobe(audio_data_start, audio_size, in_file, ffmpeg_binary)
    
    if ffprobe_duration > 0:
        # Use accurate ffprobe duration
        total_duration_seconds = ffprobe_duration
        total_minutes = int(total_duration_seconds // 60)
        remaining_seconds = total_duration_seconds % 60
        seconds = int(remaining_seconds)
        centiseconds = int((remaining_seconds - seconds) * 100)
        total_time = f"{total_minutes:02d}:{seconds:02d}.{centiseconds:02d}"
        logger.debug(f"Using ffprobe duration: {total_time}")
    elif last_granule_position > 0:
        # Fallback to granule position calculation
        total_duration_seconds = last_granule_position / (sample_rate * 1000)
        total_minutes = int(total_duration_seconds // 60)
        remaining_seconds = total_duration_seconds % 60
        seconds = int(remaining_seconds)
        centiseconds = int((remaining_seconds - seconds) * 100)
        total_time = f"{total_minutes:02d}:{seconds:02d}.{centiseconds:02d}"
        logger.debug(f"Using granule-based duration: {total_time}")
    else:
        # Final fallback to page-based estimation
        total_duration_ms = page_count * 50
        total_minutes = total_duration_ms // 60000
        total_seconds = (total_duration_ms % 60000) // 1000
        total_centiseconds = (total_duration_ms % 1000) // 10
        total_time = f"{total_minutes:02d}:{total_seconds:02d}.{total_centiseconds:02d}"
        logger.debug(f"Using page-based duration estimate: {total_time}")
    
    # Calculate chapter durations using accurate granule-based method
    chapter_durations = []
    if hasattr(tonie_header, 'chapterPages') and len(tonie_header.chapterPages) > 1:
        # We need to re-read pages to get granule positions for chapter boundaries
        in_file.seek(4 + header_size)  # Reset to start of audio data
        pages_granules = []
        
        try:
            while OggPage.seek_to_page_header(in_file):
                page = OggPage(in_file)
                pages_granules.append(page.granule_position)
                if len(pages_granules) >= page_count:
                    break
        except Exception as e:
            logger.debug(f"Error reading pages for chapter calculation: {e}")
        
        for i, chapter_start_page in enumerate(tonie_header.chapterPages):
            # Determine end page for this chapter
            if i + 1 < len(tonie_header.chapterPages):
                chapter_end_page = tonie_header.chapterPages[i + 1]
            else:
                chapter_end_page = page_count
            
            # Get granule positions for chapter boundaries
            start_granule = pages_granules[chapter_start_page] if chapter_start_page < len(pages_granules) else 0
            end_granule = pages_granules[min(chapter_end_page - 1, len(pages_granules) - 1)] if chapter_end_page <= len(pages_granules) else last_granule_position
            
            # Calculate accurate chapter duration
            if end_granule > start_granule and sample_rate > 0:
                chapter_samples = end_granule - start_granule
                chapter_duration_seconds = chapter_samples / (sample_rate * 1000)
                ch_minutes = int(chapter_duration_seconds // 60)
                remaining_seconds = chapter_duration_seconds % 60
                ch_seconds = int(remaining_seconds)
                ch_centiseconds = int((remaining_seconds - ch_seconds) * 100)
                chapter_duration_str = f"{ch_minutes:02d}:{ch_seconds:02d}.{ch_centiseconds:02d}"
            else:
                # Fallback to page-based estimation
                pages_in_chapter = chapter_end_page - chapter_start_page
                chapter_duration_ms = pages_in_chapter * 50
                ch_minutes = chapter_duration_ms // 60000
                ch_seconds = (chapter_duration_ms % 60000) // 1000
                ch_centiseconds = (chapter_duration_ms % 1000) // 10
                chapter_duration_str = f"{ch_minutes:02d}:{ch_seconds:02d}.{ch_centiseconds:02d}"
            
            chapter_durations.append(chapter_duration_str)
    else:
        # Single chapter spanning entire file
        chapter_durations = [total_time]
    
    logger.debug(f"Calculated audio info: {page_count} pages, {total_time} duration, {ffprobe_bitrate if ffprobe_bitrate > 0 else 'unknown'} kbps bitrate")
    
    return (page_count, alignment_okay, page_size_okay, total_time, chapter_durations, ffprobe_bitrate)