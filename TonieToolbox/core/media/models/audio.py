#!/usr/bin/env python3
"""
Domain models for media processing.

Pure domain objects representing audio formats, conversion parameters,
and processing results without external dependencies.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from enum import Enum
from pathlib import Path


class AudioFormat(Enum):
    """Enumeration of supported audio formats."""
    MP3 = "mp3"
    OPUS = "opus"
    OGG = "ogg"
    WAV = "wav"
    FLAC = "flac"
    AAC = "aac"
    TAF = "taf"
    
    @classmethod
    def from_extension(cls, extension: str) -> Optional['AudioFormat']:
        """Create AudioFormat from file extension."""
        ext = extension.lower().lstrip('.')
        for fmt in cls:
            if fmt.value == ext:
                return fmt
        return None
    
    @property
    def is_lossless(self) -> bool:
        """Check if format is lossless."""
        return self in (AudioFormat.WAV, AudioFormat.FLAC)
    
    @property
    def is_compressed(self) -> bool:
        """Check if format uses compression."""
        return not self.is_lossless


class BitrateMode(Enum):
    """Bitrate encoding modes."""
    VBR = "vbr"  # Variable Bitrate
    CBR = "cbr"  # Constant Bitrate
    ABR = "abr"  # Average Bitrate


@dataclass(frozen=True)
class AudioCodecParams:
    """Pure domain model for audio codec parameters."""
    bitrate_kbps: Optional[int]
    sample_rate_hz: int
    channels: int
    bitrate_mode: BitrateMode
    quality: Optional[float] = None  # 0.0 to 1.0 for quality-based encoding
    
    def __post_init__(self):
        if self.channels < 1:
            raise ValueError("Channels must be at least 1")
        if self.sample_rate_hz < 1:
            raise ValueError("Sample rate must be positive")
        if self.bitrate_kbps is not None and self.bitrate_kbps < 1:
            raise ValueError("Bitrate must be positive")
        if self.quality is not None and not (0.0 <= self.quality <= 1.0):
            raise ValueError("Quality must be between 0.0 and 1.0")
    
    @property
    def is_stereo(self) -> bool:
        return self.channels == 2
    
    @property
    def is_mono(self) -> bool:
        return self.channels == 1


@dataclass(frozen=True)
class ConversionRequest:
    """Pure domain model for audio conversion requests."""
    input_format: AudioFormat
    output_format: AudioFormat
    codec_params: AudioCodecParams
    preserve_metadata: bool = True
    
    @property
    def is_format_change(self) -> bool:
        """Check if conversion changes audio format."""
        return self.input_format != self.output_format


@dataclass(frozen=True)
class AudioMetadata:
    """Pure domain model for audio metadata."""
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for external interfaces."""
        return {
            'title': self.title,
            'artist': self.artist,
            'album': self.album,
            'album_artist': self.album_artist,
            'track_number': self.track_number,
            'year': self.year,
            'genre': self.genre,
            'duration_seconds': self.duration_seconds
        }


@dataclass(frozen=True)
class ConversionResult:
    """Pure domain model for conversion results."""
    success: bool
    input_size_bytes: int
    output_size_bytes: int
    processing_time_seconds: float
    error_message: Optional[str] = None
    
    @property
    def compression_ratio(self) -> Optional[float]:
        """Calculate compression ratio."""
        if self.input_size_bytes > 0 and self.output_size_bytes > 0:
            return self.output_size_bytes / self.input_size_bytes
        return None
    
    @property
    def size_reduction_percentage(self) -> Optional[float]:
        """Calculate size reduction percentage."""
        ratio = self.compression_ratio
        if ratio is not None:
            return (1 - ratio) * 100
        return None