#!/usr/bin/env python3
"""
Domain services for media processing.

Pure domain services that handle business logic for audio processing
without external dependencies.
"""

import re
from typing import Optional, Dict, Any
from pathlib import Path

from ..models import AudioFormat, AudioCodecParams, BitrateMode, AudioMetadata
from ...utils import get_logger

logger = get_logger(__name__)


class BitrateExtractionService:
    """
    Pure domain service for extracting bitrate information from metadata.
    
    Analyzes encoder options, audio comments, and tags to detect bitrate settings
    from various audio formats. Handles multiple encoding patterns and metadata
    field variations for robust bitrate detection.
    
    Example:
        >>> # Extract bitrate from Opus encoder options
        >>> encoder_opts = "--bitrate=96 --vbr --comp 10"
        >>> bitrate = BitrateExtractionService.extract_from_encoder_options(encoder_opts)
        >>> print(f"Detected bitrate: {bitrate} kbps")
        Detected bitrate: 96 kbps
        >>> 
        >>> # Extract from audio comments dictionary
        >>> comments = {
        ...     'encoder_options': '--bitrate 128',
        ...     'encoder': 'Lavf58.29.100',
        ...     'title': 'Chapter 1'
        ... }
        >>> bitrate = BitrateExtractionService.extract_from_comments(comments)
        >>> print(f"Bitrate from comments: {bitrate} kbps")
        Bitrate from comments: 128 kbps
        >>> 
        >>> # Handle alternative comment formats
        >>> alt_comments = {'BITRATE': '192', 'format': 'mp3'}
        >>> bitrate = BitrateExtractionService.extract_from_comments(alt_comments)
        >>> print(f"Alternative format bitrate: {bitrate} kbps")
        Alternative format bitrate: 192 kbps
    """
    
    @staticmethod
    def extract_from_encoder_options(encoder_options: str) -> Optional[int]:
        """
        Extract bitrate from Opus encoder_options string.
        
        This is pure business logic without external dependencies.
        
        Args:
            encoder_options: Encoder options string
            
        Returns:
            Detected bitrate in kbps, or None if not found
        """
        if not encoder_options:
            return None
        
        logger.debug("Extracting bitrate from encoder options: %s", encoder_options)
        
        # Match --bitrate followed by = or space and then digits
        bitrate_match = re.search(r'--bitrate[=\s]+(\d+)', encoder_options)
        if bitrate_match:
            bitrate = int(bitrate_match.group(1))
            logger.debug("Detected bitrate: %d kbps", bitrate)
            return bitrate
        
        logger.debug("No bitrate found in encoder_options")
        return None
    
    @staticmethod
    def extract_from_comments(comments: Dict[str, str]) -> Optional[int]:
        """
        Extract bitrate from audio comments/tags.
        
        Args:
            comments: Dictionary of audio comments/tags
            
        Returns:
            Detected bitrate in kbps, or None if not found
        """
        if not comments:
            return None
        
        # Try encoder_options first
        if 'encoder_options' in comments:
            return BitrateExtractionService.extract_from_encoder_options(
                comments['encoder_options']
            )
        
        # Try other comment fields
        for key in ['bitrate', 'BITRATE', 'Bitrate']:
            if key in comments:
                try:
                    # Extract numeric value
                    value = comments[key]
                    if isinstance(value, str):
                        numeric_match = re.search(r'(\d+)', value)
                        if numeric_match:
                            return int(numeric_match.group(1))
                    elif isinstance(value, (int, float)):
                        return int(value)
                except (ValueError, AttributeError):
                    continue
        
        return None


class AudioFormatService:
    """
    Pure domain service for audio format operations.
    
    Provides format detection, codec parameter creation, and conversion necessity
    determination. Supports multiple audio formats including MP3, OPUS, OGG, WAV,
    FLAC, AAC, and TAF with intelligent default parameter selection.
    
    Example:
        >>> from pathlib import Path
        >>> from TonieToolbox.core.media.domain import AudioFormat, AudioCodecParams
        >>> 
        >>> # Detect audio format from file extension
        >>> audio_file = Path('audiobook.mp3')
        >>> detected_format = AudioFormatService.detect_format_from_path(audio_file)
        >>> print(f"Detected format: {detected_format.name}")
        Detected format: MP3
        >>> 
        >>> # Create default codec parameters for TAF
        >>> taf_params = AudioFormatService.create_default_codec_params(
        ...     audio_format=AudioFormat.TAF,
        ...     bitrate_kbps=96
        ... )
        >>> print(f"TAF params: {taf_params.sample_rate_hz}Hz, {taf_params.channels}ch")
        TAF params: 48000Hz, 2ch
        >>> 
        >>> # Check if conversion is needed
        >>> current_params = AudioCodecParams(bitrate_kbps=128, sample_rate_hz=44100, channels=2)
        >>> target_params = AudioCodecParams(bitrate_kbps=96, sample_rate_hz=48000, channels=1)
        >>> needs_conversion = AudioFormatService.is_conversion_needed(
        ...     AudioFormat.MP3, AudioFormat.TAF, current_params, target_params
        ... )
        >>> print(f"Conversion needed: {needs_conversion}")
        Conversion needed: True
    """
    
    @staticmethod
    def detect_format_from_path(file_path: Path) -> Optional[AudioFormat]:
        """
        Detect audio format from file path.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Detected AudioFormat or None
        """
        return AudioFormat.from_extension(file_path.suffix)
    
    @staticmethod
    def create_default_codec_params(
        audio_format: AudioFormat,
        bitrate_kbps: Optional[int] = None
    ) -> AudioCodecParams:
        """
        Create default codec parameters for an audio format.
        
        Args:
            audio_format: Target audio format
            bitrate_kbps: Optional target bitrate
            
        Returns:
            Default AudioCodecParams for the format
        """
        # Default parameters per format
        defaults = {
            AudioFormat.MP3: {
                'bitrate_kbps': bitrate_kbps or 128,
                'sample_rate_hz': 44100,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            },
            AudioFormat.OPUS: {
                'bitrate_kbps': bitrate_kbps or 96,
                'sample_rate_hz': 48000,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            },
            AudioFormat.OGG: {
                'bitrate_kbps': bitrate_kbps or 128,
                'sample_rate_hz': 44100,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            },
            AudioFormat.WAV: {
                'bitrate_kbps': None,  # Uncompressed
                'sample_rate_hz': 44100,
                'channels': 2,
                'bitrate_mode': BitrateMode.CBR
            },
            AudioFormat.FLAC: {
                'bitrate_kbps': None,  # Lossless
                'sample_rate_hz': 44100,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            },
            AudioFormat.AAC: {
                'bitrate_kbps': bitrate_kbps or 128,
                'sample_rate_hz': 44100,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            },
            AudioFormat.TAF: {
                'bitrate_kbps': bitrate_kbps or 96,
                'sample_rate_hz': 48000,
                'channels': 2,
                'bitrate_mode': BitrateMode.VBR
            }
        }
        
        params = defaults.get(audio_format, defaults[AudioFormat.MP3])
        return AudioCodecParams(**params)
    
    @staticmethod
    def is_conversion_needed(
        input_format: AudioFormat,
        output_format: AudioFormat,
        current_params: AudioCodecParams,
        target_params: AudioCodecParams
    ) -> bool:
        """
        Determine if conversion is needed based on format and parameters.
        
        Args:
            input_format: Current audio format
            output_format: Target audio format
            current_params: Current codec parameters
            target_params: Target codec parameters
            
        Returns:
            True if conversion is needed
        """
        # Format change always requires conversion
        if input_format != output_format:
            return True
        
        # Same format, check if parameters differ significantly
        if current_params.sample_rate_hz != target_params.sample_rate_hz:
            return True
        
        if current_params.channels != target_params.channels:
            return True
        
        # For compressed formats, check bitrate
        if not output_format.is_lossless:
            if (current_params.bitrate_kbps and target_params.bitrate_kbps and
                abs(current_params.bitrate_kbps - target_params.bitrate_kbps) > 10):
                return True
        
        return False


class MetadataService:
    """Pure domain service for audio metadata operations."""
    
    @staticmethod
    def create_metadata_from_dict(data: Dict[str, Any]) -> AudioMetadata:
        """
        Create AudioMetadata from dictionary.
        
        Args:
            data: Dictionary with metadata fields
            
        Returns:
            AudioMetadata object
        """
        return AudioMetadata(
            title=data.get('title'),
            artist=data.get('artist'),
            album=data.get('album'),
            album_artist=data.get('album_artist') or data.get('albumartist'),
            track_number=data.get('track_number') or data.get('track'),
            year=data.get('year') or data.get('date'),
            genre=data.get('genre'),
            duration_seconds=data.get('duration_seconds') or data.get('duration')
        )
    
    @staticmethod
    def merge_metadata(primary: AudioMetadata, secondary: AudioMetadata) -> AudioMetadata:
        """
        Merge two AudioMetadata objects, preferring non-None values from primary.
        
        Args:
            primary: Primary metadata (takes precedence)
            secondary: Secondary metadata (fallback)
            
        Returns:
            Merged AudioMetadata
        """
        return AudioMetadata(
            title=primary.title or secondary.title,
            artist=primary.artist or secondary.artist,
            album=primary.album or secondary.album,
            album_artist=primary.album_artist or secondary.album_artist,
            track_number=primary.track_number or secondary.track_number,
            year=primary.year or secondary.year,
            genre=primary.genre or secondary.genre,
            duration_seconds=primary.duration_seconds or secondary.duration_seconds
        )