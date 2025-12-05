#!/usr/bin/env python3
"""
Domain models for TAF file analysis.

These are pure domain objects that represent TAF analysis results without
any external dependencies like protobuf objects or infrastructure concerns.
Following Clean Architecture principles, these models contain only business logic.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass(frozen=True)
class ChapterInfo:
    """Pure domain model representing a chapter within a Tonie file."""
    id: int
    title: str
    seconds: float
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as MM:SS.ms"""
        minutes = int(self.seconds // 60)
        seconds = self.seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"


@dataclass(frozen=True)
class TonieHeaderInfo:
    """Pure domain model for Tonie header information."""
    timestamp: int
    data_length: int
    chapter_pages: List[int]
    chapters: List[ChapterInfo]
    
    @property
    def chapter_count(self) -> int:
        """Number of chapters in the Tonie."""
        return len(self.chapters)
    
    @property
    def formatted_date(self) -> str:
        """Format timestamp as human-readable date."""
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(self.timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, OSError):
            return f"Invalid timestamp: {self.timestamp}"


@dataclass(frozen=True)
class OpusInfo:
    """Pure domain model for Opus audio information."""
    head_found: bool
    version: Optional[int]
    channels: int
    sample_rate: int
    bitstream_serial: int
    comments: Dict[str, str]
    
    @property
    def is_stereo(self) -> bool:
        """Check if audio is stereo."""
        return self.channels == 2
    
    @property
    def is_mono(self) -> bool:
        """Check if audio is mono."""
        return self.channels == 1


@dataclass(frozen=True)
class AudioAnalysisInfo:
    """Pure domain model for audio analysis results."""
    page_count: int
    duration_seconds: float
    bitrate_kbps: Optional[int]
    accurate_bitrate: bool
    alignment_okay: bool
    page_size_okay: bool
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as HH:MM:SS.ms"""
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
        else:
            return f"{minutes:02d}:{seconds:06.3f}"


@dataclass(frozen=True)
class TafAnalysisResult:
    """
    Pure domain model representing comprehensive TAF file analysis results.
    
    This is the main domain object that encapsulates all TAF analysis information
    without any external dependencies or infrastructure concerns.
    """
    # File metadata
    file_path: Path
    file_name: str
    file_size: int
    audio_size: int
    valid: bool
    sha1_hash: Optional[str]
    
    # Structure information
    header_size: int
    tonie_header: TonieHeaderInfo
    opus_info: OpusInfo
    audio_analysis: AudioAnalysisInfo
    
    @property
    def file_size_formatted(self) -> str:
        """Format file size as human-readable string."""
        if self.file_size < 1024:
            return f"{self.file_size} bytes"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"
    
    @property
    def audio_size_formatted(self) -> str:
        """Format audio size as human-readable string."""
        if self.audio_size < 1024:
            return f"{self.audio_size} bytes"
        elif self.audio_size < 1024 * 1024:
            return f"{self.audio_size / 1024:.1f} KB"
        elif self.audio_size < 1024 * 1024 * 1024:
            return f"{self.audio_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.audio_size / (1024 * 1024 * 1024):.1f} GB"
    
    @property
    def has_chapters(self) -> bool:
        """Check if the TAF file contains chapter information."""
        return self.tonie_header.chapter_count > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Useful for JSON serialization, GUI components, or other consumers
        that need a serializable representation.
        """
        return {
            'file_path': str(self.file_path),
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_size_formatted': self.file_size_formatted,
            'audio_size': self.audio_size,
            'audio_size_formatted': self.audio_size_formatted,
            'valid': self.valid,
            'sha1_hash': self.sha1_hash,
            'header_size': self.header_size,
            'tonie_header': {
                'timestamp': self.tonie_header.timestamp,
                'formatted_date': self.tonie_header.formatted_date,
                'data_length': self.tonie_header.data_length,
                'chapter_count': self.tonie_header.chapter_count,
                'chapter_pages': self.tonie_header.chapter_pages,
                'chapters': [
                    {
                        'id': chapter.id,
                        'title': chapter.title,
                        'seconds': chapter.seconds,
                        'duration_formatted': chapter.duration_formatted
                    }
                    for chapter in self.tonie_header.chapters
                ]
            },
            'opus_info': {
                'head_found': self.opus_info.head_found,
                'version': self.opus_info.version,
                'channels': self.opus_info.channels,
                'is_stereo': self.opus_info.is_stereo,
                'is_mono': self.opus_info.is_mono,
                'sample_rate': self.opus_info.sample_rate,
                'bitstream_serial': self.opus_info.bitstream_serial,
                'comments': self.opus_info.comments
            },
            'audio_analysis': {
                'page_count': self.audio_analysis.page_count,
                'duration_seconds': self.audio_analysis.duration_seconds,
                'duration_formatted': self.audio_analysis.duration_formatted,
                'bitrate_kbps': self.audio_analysis.bitrate_kbps,
                'accurate_bitrate': self.audio_analysis.accurate_bitrate,
                'alignment_okay': self.audio_analysis.alignment_okay,
                'page_size_okay': self.audio_analysis.page_size_okay
            },
            'has_chapters': self.has_chapters
        }