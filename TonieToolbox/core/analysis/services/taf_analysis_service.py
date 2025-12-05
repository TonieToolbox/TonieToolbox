#!/usr/bin/env python3
"""
Domain services for TAF analysis.

These services convert between external representations (like protobuf objects)
and pure domain models, maintaining Clean Architecture boundaries.
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import hashlib

from ..models import (
    ChapterInfo,
    TonieHeaderInfo,
    OpusInfo,
    AudioAnalysisInfo,
    TafAnalysisResult
)
from ...utils import get_logger

logger = get_logger(__name__)


class TafAnalysisService:
    """
    Domain service for TAF file analysis.
    
    Converts between infrastructure layer results (protobuf, raw data)
    and pure domain models following Clean Architecture principles.
    """
    
    @staticmethod
    def create_chapter_info(chapter_id: int, title: str, seconds: float) -> ChapterInfo:
        """Create a ChapterInfo domain object."""
        return ChapterInfo(
            id=chapter_id,
            title=title or f"Chapter {chapter_id}",
            seconds=max(0.0, seconds)
        )
    
    @staticmethod
    def create_tonie_header_info(
        timestamp: int,
        data_length: int,
        chapter_pages: List[int],
        chapters: List[ChapterInfo]
    ) -> TonieHeaderInfo:
        """Create a TonieHeaderInfo domain object."""
        return TonieHeaderInfo(
            timestamp=timestamp,
            data_length=data_length,
            chapter_pages=list(chapter_pages),  # Make defensive copy
            chapters=list(chapters)  # Make defensive copy
        )
    
    @staticmethod
    def create_opus_info(
        head_found: bool,
        version: Optional[int],
        channels: int,
        sample_rate: int,
        bitstream_serial: int,
        comments: Dict[str, str]
    ) -> OpusInfo:
        """Create an OpusInfo domain object."""
        return OpusInfo(
            head_found=head_found,
            version=version,
            channels=max(1, channels),  # Ensure at least 1 channel
            sample_rate=max(1, sample_rate),  # Ensure positive sample rate
            bitstream_serial=bitstream_serial,
            comments=dict(comments)  # Make defensive copy
        )
    
    @staticmethod
    def create_audio_analysis_info(
        page_count: int,
        duration_seconds: float,
        bitrate_kbps: Optional[int],
        accurate_bitrate: bool,
        alignment_okay: bool,
        page_size_okay: bool
    ) -> AudioAnalysisInfo:
        """Create an AudioAnalysisInfo domain object."""
        return AudioAnalysisInfo(
            page_count=max(0, page_count),
            duration_seconds=max(0.0, duration_seconds),
            bitrate_kbps=bitrate_kbps if bitrate_kbps and bitrate_kbps > 0 else None,
            accurate_bitrate=accurate_bitrate,
            alignment_okay=alignment_okay,
            page_size_okay=page_size_okay
        )
    
    @staticmethod
    def create_taf_analysis_result(
        file_path: Path,
        file_size: int,
        audio_size: int,
        valid: bool,
        sha1_hash: Optional[str],
        header_size: int,
        tonie_header: TonieHeaderInfo,
        opus_info: OpusInfo,
        audio_analysis: AudioAnalysisInfo
    ) -> TafAnalysisResult:
        """Create a complete TafAnalysisResult domain object."""
        return TafAnalysisResult(
            file_path=file_path,
            file_name=file_path.name,
            file_size=max(0, file_size),
            audio_size=max(0, audio_size),
            valid=valid,
            sha1_hash=sha1_hash,
            header_size=max(0, header_size),
            tonie_header=tonie_header,
            opus_info=opus_info,
            audio_analysis=audio_analysis
        )
    
    @staticmethod
    def convert_protobuf_tonie_header(
        protobuf_header,
        chapters_data: Optional[List[Tuple[int, str, float]]] = None
    ) -> TonieHeaderInfo:
        """
        Convert a protobuf TonieHeader to domain model.
        
        Args:
            protobuf_header: The protobuf TonieHeader object
            chapters_data: Optional list of (id, title, seconds) tuples
        
        Returns:
            Pure domain TonieHeaderInfo object
        """
        # Extract basic header information
        timestamp = getattr(protobuf_header, 'timestamp', 0)
        data_length = getattr(protobuf_header, 'dataLength', 0)
        
        # Extract chapter pages
        chapter_pages = []
        if hasattr(protobuf_header, 'chapterPages'):
            chapter_pages = list(protobuf_header.chapterPages)
        
        # Create chapter info objects
        chapters = []
        if chapters_data:
            for chapter_id, title, seconds in chapters_data:
                chapter = TafAnalysisService.create_chapter_info(chapter_id, title, seconds)
                chapters.append(chapter)
        elif chapter_pages:
            # If we have chapter pages but no explicit chapter data, create default chapters
            for i, page in enumerate(chapter_pages):
                chapter = TafAnalysisService.create_chapter_info(
                    chapter_id=i + 1,
                    title=f"Chapter {i + 1}",
                    seconds=0.0  # Duration will be filled in later during audio analysis
                )
                chapters.append(chapter)

        return TafAnalysisService.create_tonie_header_info(
            timestamp=timestamp,
            data_length=data_length,
            chapter_pages=chapter_pages,
            chapters=chapters
        )
    
    @staticmethod
    def convert_raw_header_tuple_to_domain(
        header_tuple: Tuple
    ) -> Tuple[TonieHeaderInfo, OpusInfo, AudioAnalysisInfo, bool, int, int, Optional[str]]:
        """
        Convert raw header analysis tuple to domain objects.
        
        This method handles the conversion from the existing header analysis
        function results to pure domain objects.
        
        Args:
            header_tuple: Tuple from get_header_info_cli function
        
        Returns:
            Tuple of domain objects and remaining values
        """
        (header_size, protobuf_header, file_size, audio_size, sha1sum,
         opus_head_found, opus_version, channel_count, sample_rate, bitstream_serial_no,
         opus_comments, valid) = header_tuple
        
        # Convert protobuf header to domain object
        tonie_header = TafAnalysisService.convert_protobuf_tonie_header(protobuf_header)
        
        # Create Opus info domain object
        opus_info = TafAnalysisService.create_opus_info(
            head_found=opus_head_found,
            version=opus_version if opus_head_found else None,
            channels=channel_count,
            sample_rate=sample_rate,
            bitstream_serial=bitstream_serial_no,
            comments=opus_comments or {}
        )
        
        # Create placeholder audio analysis (will be filled later)
        audio_analysis = TafAnalysisService.create_audio_analysis_info(
            page_count=0,
            duration_seconds=0.0,
            bitrate_kbps=None,
            accurate_bitrate=False,
            alignment_okay=True,
            page_size_okay=True
        )
        
        sha1_hash = sha1sum.hexdigest() if sha1sum else None
        
        return tonie_header, opus_info, audio_analysis, valid, file_size, audio_size, sha1_hash