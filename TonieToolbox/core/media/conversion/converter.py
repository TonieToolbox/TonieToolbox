#!/usr/bin/python3
"""
Core audio conversion utilities using FFmpeg.
"""
import os
import subprocess
import tempfile
from ...utils import get_logger
from ...dependencies import get_ffmpeg_binary

logger = get_logger(__name__)


def convert_audio_with_ffmpeg(input_path: str = None, input_data: bytes = None, 
                             output_path: str = None, output_format: str = "mp3", 
                             codec_options: dict = None, ffmpeg_binary: str = None, 
                             auto_download: bool = False, extra_ffmpeg_args: list = None) -> bool:
    """
    Universal audio conversion using FFmpeg with flexible input/output options.
    
    Args:
        input_path (str | None): Path to input audio file
        input_data (bytes | None): Input audio data as bytes
        output_path (str | None): Path for output file (if None, returns converted data)
        output_format (str): Target format (mp3, wav, flac, ogg, opus, aac, etc.)
        codec_options (dict | None): Format-specific codec options
        ffmpeg_binary (str | None): Path to ffmpeg binary
        auto_download (bool): Whether to auto-download ffmpeg if not found
        extra_ffmpeg_args (list | None): Additional FFmpeg arguments
    
    Returns:
        bool: True if conversion successful, False otherwise
        
    Raises:
        ValueError: If neither input_path nor input_data is provided
        FileNotFoundError: If input_path is specified but file doesn't exist
        subprocess.SubprocessError: If FFmpeg execution fails
        OSError: If temporary file creation or output writing fails
        PermissionError: If insufficient permissions to write output file
        
    Examples:
        # File to file conversion
        convert_audio_with_ffmpeg("input.wav", output_path="output.mp3")
        
        # Memory to file with custom options
        convert_audio_with_ffmpeg(input_data=opus_data, output_path="result.mp3", 
                                 codec_options={"bitrate": 192})
        
        # Different format conversions
        convert_audio_with_ffmpeg("audio.mp3", "output.flac", "flac", 
                                 {"compression_level": 6})
    """
    # Validate inputs
    if not input_path and not input_data:
        logger.error("Either input_path or input_data must be provided")
        return False
    
    if not output_path:
        logger.error("output_path must be provided")
        return False
        
    # Get FFmpeg binary - prefer caller-provided path over dependency resolution
    if ffmpeg_binary is None:
        logger.warning("FFmpeg binary not provided by caller. Falling back to dependency resolution. " +
                      "Consider resolving dependencies at application level for better performance.")
        ffmpeg_binary = get_ffmpeg_binary(auto_download)
        if not ffmpeg_binary:
            logger.error("FFmpeg not found. Please install FFmpeg or use --auto-download")
            return False
    
    # Setup codec options
    codec_opts = codec_options or {}
    
    # Build FFmpeg command
    cmd = [ffmpeg_binary, "-y"]  # -y to overwrite output files
    
    # Input handling
    temp_input_file = None
    try:
        if input_data:
            # Create temporary input file from data
            temp_input_file = tempfile.NamedTemporaryFile(delete=False, suffix=".tmp")
            temp_input_file.write(input_data)
            temp_input_file.close()
            cmd.extend(["-i", temp_input_file.name])
        else:
            cmd.extend(["-i", input_path])
        
        # Add codec and format-specific options
        cmd.extend(_get_codec_args(output_format, codec_opts))
        
        # Add extra arguments if provided
        if extra_ffmpeg_args:
            cmd.extend(extra_ffmpeg_args)
        
        # Output file
        cmd.append(output_path)
        
        logger.debug("Running FFmpeg command: %s", " ".join(cmd))
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            logger.error("FFmpeg conversion failed: %s", result.stderr)
            return False
        
        # Verify output file was created
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            logger.error("Output file not created or is empty: %s", output_path)
            return False
        
        logger.debug("Conversion successful: %s", output_path)
        return True
        
    except Exception as e:
        logger.error("Audio conversion failed: %s", e)
        return False
        
    finally:
        # Clean up temporary input file
        if temp_input_file and os.path.exists(temp_input_file.name):
            try:
                os.unlink(temp_input_file.name)
            except OSError:
                pass


def _get_codec_args(output_format: str, codec_options: dict) -> list:
    """Get FFmpeg codec arguments for specific format."""
    args = []
    format_lower = output_format.lower()
    
    if format_lower == "mp3":
        args.extend(["-codec:a", "libmp3lame"])
        if "bitrate" in codec_options:
            args.extend(["-b:a", f"{codec_options['bitrate']}k"])
        if "quality" in codec_options:
            args.extend(["-q:a", str(codec_options["quality"])])
            
    elif format_lower == "wav":
        args.extend(["-codec:a", "pcm_s16le"])
        if "sample_rate" in codec_options:
            args.extend(["-ar", str(codec_options["sample_rate"])])
        if "channels" in codec_options:
            args.extend(["-ac", str(codec_options["channels"])])
            
    elif format_lower == "flac":
        args.extend(["-codec:a", "flac"])
        if "compression_level" in codec_options:
            args.extend(["-compression_level", str(codec_options["compression_level"])])
        if "sample_rate" in codec_options:
            args.extend(["-ar", str(codec_options["sample_rate"])])
            
    elif format_lower == "ogg":
        args.extend(["-codec:a", "libvorbis"])
        if "bitrate" in codec_options:
            args.extend(["-b:a", f"{codec_options['bitrate']}k"])
        if "quality" in codec_options:
            args.extend(["-q:a", str(codec_options["quality"])])
        if "channels" in codec_options:
            args.extend(["-ac", str(codec_options["channels"])])
            
    elif format_lower == "opus":
        args.extend(["-codec:a", "libopus"])
        if "bitrate" in codec_options:
            args.extend(["-b:a", f"{codec_options['bitrate']}k"])
        if "sample_rate" in codec_options:
            args.extend(["-ar", str(codec_options["sample_rate"])])
        if "channels" in codec_options:
            args.extend(["-ac", str(codec_options["channels"])])
            
    elif format_lower == "aac":
        args.extend(["-codec:a", "aac"])
        if "bitrate" in codec_options:
            args.extend(["-b:a", f"{codec_options['bitrate']}k"])
        if "sample_rate" in codec_options:
            args.extend(["-ar", str(codec_options["sample_rate"])])
    
    return args