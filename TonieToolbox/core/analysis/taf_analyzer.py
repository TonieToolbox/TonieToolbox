#!/usr/bin/env python3
"""
TAF file analyzer using pure domain models.

This analyzer returns domain objects that represent TAF analysis results
without any external dependencies, following Clean Architecture principles.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import os

from .header import get_header_info_cli
from .extraction import get_audio_info
from .models import TafAnalysisResult
from .services import TafAnalysisService
from ..utils import get_logger

logger = get_logger(__name__)


def analyze_taf_file(file_path: Path) -> Optional[TafAnalysisResult]:
    """
    Analyze a TAF file and return comprehensive information as domain model.
    
    This function provides detailed TAF analysis using pure domain objects
    that follow Clean Architecture principles without external dependencies.
    
    Args:
        file_path: Path to TAF file to analyze
        
    Returns:
        TafAnalysisResult domain object, or None if analysis fails
    """
    try:
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"TAF file not found: {file_path}")
            return None
            
        if file_path.suffix.lower() != '.taf':
            logger.error(f"File is not a TAF file: {file_path}")
            return None

        with open(file_path, 'rb') as taf_file:
            # Get header information using CLI analyzer
            header_tuple = get_header_info_cli(taf_file)
            
            # Convert raw tuple to domain objects
            (tonie_header_info, opus_info, audio_analysis_partial, valid, 
             file_size, audio_size, sha1_hash) = TafAnalysisService.convert_raw_header_tuple_to_domain(header_tuple)
            
            if not valid:
                logger.error(f"Invalid TAF file: {file_path}")
                return None
            
            # Get detailed audio analysis
            page_count, alignment_okay, page_size_okay, duration_str, chapter_durations, accurate_bitrate = get_audio_info(
                taf_file, opus_info.sample_rate // 1000, header_tuple[1], header_tuple[0], None
            )
            
            # Parse duration to seconds
            duration_seconds = 0.0
            try:
                if duration_str and ':' in duration_str:
                    parts = duration_str.split(':')
                    if len(parts) == 2:  # MM:SS.ms
                        minutes = int(parts[0])
                        seconds = float(parts[1])
                        duration_seconds = minutes * 60 + seconds
                    elif len(parts) == 3:  # HH:MM:SS.ms
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds = float(parts[2])
                        duration_seconds = hours * 3600 + minutes * 60 + seconds
            except (ValueError, IndexError):
                logger.warning(f"Could not parse duration: {duration_str}")
            
            # Create complete audio analysis with actual data
            audio_analysis = TafAnalysisService.create_audio_analysis_info(
                page_count=page_count,
                duration_seconds=duration_seconds,
                bitrate_kbps=accurate_bitrate if isinstance(accurate_bitrate, int) else None,
                accurate_bitrate=isinstance(accurate_bitrate, int),
                alignment_okay=alignment_okay,
                page_size_okay=page_size_okay
            )
            
            # Extract bitrate from encoder options if not detected
            if not audio_analysis.bitrate_kbps and opus_info.comments and 'encoder_options' in opus_info.comments:
                from .header import extract_bitrate_from_encoder_options
                bitrate_from_comments = extract_bitrate_from_encoder_options(opus_info.comments['encoder_options'])
                if bitrate_from_comments:
                    # Create updated audio analysis with detected bitrate
                    audio_analysis = TafAnalysisService.create_audio_analysis_info(
                        page_count=audio_analysis.page_count,
                        duration_seconds=audio_analysis.duration_seconds,
                        bitrate_kbps=bitrate_from_comments,
                        accurate_bitrate=True,
                        alignment_okay=audio_analysis.alignment_okay,
                        page_size_okay=audio_analysis.page_size_okay
                    )
            
            # Update chapter durations if we have them
            if chapter_durations and tonie_header_info.chapters:
                updated_chapters = []
                for i, chapter in enumerate(tonie_header_info.chapters):
                    if i < len(chapter_durations):
                        # Parse duration string to seconds
                        duration_seconds = 0.0
                        try:
                            if chapter_durations[i] and ':' in chapter_durations[i]:
                                parts = chapter_durations[i].split(':')
                                if len(parts) == 2:  # MM:SS.ms
                                    minutes = int(parts[0])
                                    seconds = float(parts[1])
                                    duration_seconds = minutes * 60 + seconds
                                elif len(parts) == 3:  # HH:MM:SS.ms
                                    hours = int(parts[0])
                                    minutes = int(parts[1])
                                    seconds = float(parts[2])
                                    duration_seconds = hours * 3600 + minutes * 60 + seconds
                        except (ValueError, IndexError):
                            logger.warning(f"Could not parse chapter duration: {chapter_durations[i]}")
                        
                        # Create updated chapter with actual duration
                        updated_chapter = TafAnalysisService.create_chapter_info(
                            chapter_id=chapter.id,
                            title=chapter.title,
                            seconds=duration_seconds
                        )
                        updated_chapters.append(updated_chapter)
                    else:
                        updated_chapters.append(chapter)
                
                # Create updated tonie header with corrected chapter durations
                updated_tonie_header = TafAnalysisService.create_tonie_header_info(
                    timestamp=tonie_header_info.timestamp,
                    data_length=tonie_header_info.data_length,
                    chapter_pages=tonie_header_info.chapter_pages,
                    chapters=updated_chapters
                )
                # Use the updated header
                tonie_header_info = updated_tonie_header
            
            # Create the complete domain result
            analysis_result = TafAnalysisService.create_taf_analysis_result(
                file_path=file_path,
                file_size=file_size,
                audio_size=audio_size,
                valid=valid,
                sha1_hash=sha1_hash,
                header_size=header_tuple[0],
                tonie_header=tonie_header_info,
                opus_info=opus_info,
                audio_analysis=audio_analysis
            )
            
            logger.debug(f"Successfully analyzed TAF file: {file_path.name}")
            return analysis_result
            
    except Exception as e:
        logger.error(f"Error analyzing TAF file {file_path}: {e}")
        return None





