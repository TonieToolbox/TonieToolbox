#!/usr/bin/env python3
"""
FFmpeg media converter implementation.

This module provides concrete implementation of MediaConverter interface
using FFmpeg for audio processing operations.
"""

import subprocess
import json
import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
import logging
import threading
import time

from ...application.interfaces.media_converter import MediaConverter, ConversionProgress
from ...domain import ProcessingOptions


class FFmpegConverter(MediaConverter):
    """
    Concrete implementation of MediaConverter using FFmpeg.
    
    This converter handles all audio conversion operations using FFmpeg as the underlying
    processing engine. Supports conversion to/from TAF format, file combining, and format
    conversions with progress tracking and advanced audio processing options.
    
    Example:
        >>> from pathlib import Path
        >>> from TonieToolbox.core.processing.domain import ProcessingOptions
        >>> from TonieToolbox.core.utils import get_logger
        >>> 
        >>> # Initialize converter with FFmpeg paths
        >>> logger = get_logger(__name__)
        >>> converter = FFmpegConverter(
        ...     ffmpeg_path='/usr/bin/ffmpeg',
        ...     ffprobe_path='/usr/bin/ffprobe',
        ...     logger=logger
        ... )
        >>> 
        >>> # Convert single audio file to TAF
        >>> options = ProcessingOptions(bitrate=96, normalize_audio=True)
        >>> success = converter.convert_to_taf(
        ...     input_path=Path('audiobook.mp3'),
        ...     output_path=Path('audiobook.taf'),
        ...     options=options
        ... )
        >>> print(f"Conversion successful: {success}")
        Conversion successful: True
        >>> 
        >>> # Combine multiple files into one TAF
        >>> input_files = [Path('chapter1.mp3'), Path('chapter2.mp3'), Path('chapter3.mp3')]
        >>> success = converter.combine_files_to_taf(
        ...     input_paths=input_files,
        ...     output_path=Path('complete_audiobook.taf'),
        ...     options=options
        ... )
        >>> print(f"Combined {len(input_files)} files")
        Combined 3 files
        >>> 
        >>> # Convert TAF back to MP3 with progress tracking
        >>> def on_progress(progress):
        ...     print(f"Progress: {progress.percentage:.1f}%")
        >>> 
        >>> success = converter.convert_from_taf(
        ...     input_path=Path('audiobook.taf'),
        ...     output_path=Path('audiobook_export.mp3'),
        ...     output_format='mp3',
        ...     options=options,
        ...     progress_callback=on_progress
        ... )
        Progress: 25.0%
        Progress: 50.0%
        Progress: 75.0%
        Progress: 100.0%
    """
    
    def __init__(self, ffmpeg_path: str = 'ffmpeg', ffprobe_path: str = 'ffprobe',
                 logger: Optional[logging.Logger] = None):
        """
        Initialize FFmpeg converter.
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
            ffprobe_path: Path to FFprobe executable
            logger: Optional logger instance
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        
        # Verify FFmpeg availability
        self._verify_ffmpeg_availability()
    
    def _verify_ffmpeg_availability(self):
        """Verify that FFmpeg and FFprobe are available."""
        try:
            subprocess.run([self.ffmpeg_path, '-version'], 
                          capture_output=True, check=True, timeout=10)
            subprocess.run([self.ffprobe_path, '-version'], 
                          capture_output=True, check=True, timeout=10)
            self.logger.info("FFmpeg tools verified successfully")
        except Exception as e:
            error_msg = f"FFmpeg tools not available: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def convert_to_taf(self, input_path: Path, output_path: Path,
                      options: ProcessingOptions,
                      progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Convert audio file to TAF format."""
        try:
            self.logger.info(f"Converting {input_path} to TAF format: {output_path}")
            
            # Import the TAF creation function
            from ....file.taf.creator import create_tonie_file
            
            # Extract options for TAF creation
            bitrate = options.bitrate if hasattr(options, 'bitrate') else 128
            no_mono_conversion = options.no_mono_conversion if hasattr(options, 'no_mono_conversion') else False
            no_tonie_header = options.no_tonie_header if hasattr(options, 'no_tonie_header') else False
            user_timestamp = options.user_timestamp if hasattr(options, 'user_timestamp') else None
            keep_temp = options.keep_temp if hasattr(options, 'keep_temp') else False
            
            # Use the proper TAF creation function for single file
            create_tonie_file(
                output_file=str(output_path),
                input_files=[str(input_path)],  # Single file as list
                no_tonie_header=no_tonie_header,
                user_timestamp=user_timestamp,
                bitrate=bitrate,
                vbr=True,  # Default to VBR
                ffmpeg_binary=self.ffmpeg_path,
                keep_temp=keep_temp,
                auto_download=False,  # Dependencies should already be resolved
                use_custom_tags=True,  # Default to custom tags
                no_mono_conversion=no_mono_conversion
            )
            
            # Check if the file was created successfully
            if output_path.exists() and output_path.stat().st_size > 0:
                self.logger.info(f"Successfully created TAF file: {output_path}")
                return True
            else:
                self.logger.error(f"TAF file creation failed or resulted in empty file")
                return False
            
        except Exception as e:
            self.logger.error(f"TAF conversion failed for {input_path}: {str(e)}")
            return False
    
    def convert_from_taf(self, input_path: Path, output_path: Path,
                        output_format: str,
                        options: ProcessingOptions,
                        progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Convert TAF file to other audio format."""
        try:
            self.logger.info(f"Converting {input_path} from TAF to {output_format}: {output_path}")
            
            # Build FFmpeg command for format conversion
            cmd = self._build_format_conversion_command(
                input_path, output_path, output_format, options
            )
            
            # Execute conversion with progress monitoring
            return self._execute_conversion_with_progress(
                cmd, input_path, output_path, options, progress_callback
            )
            
        except Exception as e:
            self.logger.error(f"Format conversion failed for {input_path}: {str(e)}")
            return False
    
    def combine_files_to_taf(self, input_paths: List[Path], output_path: Path,
                           options: ProcessingOptions,
                           progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Combine multiple audio files into single TAF file."""
        try:
            self.logger.info(f"Combining {len(input_paths)} files to TAF: {output_path}")
            
            # Import the TAF creation function
            from ....file.taf.creator import create_tonie_file
            
            # Convert paths to strings for the TAF creator
            input_files = [str(path) for path in input_paths]
            
            # Extract options for TAF creation
            bitrate = options.bitrate if hasattr(options, 'bitrate') else 128
            no_mono_conversion = options.no_mono_conversion if hasattr(options, 'no_mono_conversion') else False
            no_tonie_header = options.no_tonie_header if hasattr(options, 'no_tonie_header') else False
            user_timestamp = options.user_timestamp if hasattr(options, 'user_timestamp') else None
            keep_temp = options.keep_temp if hasattr(options, 'keep_temp') else False
            
            # Use the proper TAF creation function
            create_tonie_file(
                output_file=str(output_path),
                input_files=input_files,
                no_tonie_header=no_tonie_header,
                user_timestamp=user_timestamp,
                bitrate=bitrate,
                vbr=True,  # Default to VBR
                ffmpeg_binary=self.ffmpeg_path,
                keep_temp=keep_temp,
                auto_download=False,  # Dependencies should already be resolved
                use_custom_tags=True,  # Default to custom tags
                no_mono_conversion=no_mono_conversion
            )
            
            # Check if the file was created successfully
            if output_path.exists() and output_path.stat().st_size > 0:
                self.logger.info(f"Successfully created TAF file: {output_path}")
                return True
            else:
                self.logger.error(f"TAF file creation failed or resulted in empty file")
                return False
            
        except Exception as e:
            self.logger.error(f"TAF file creation failed: {str(e)}")
            return False
    
    def split_taf_file(self, input_path: Path, output_directory: Path,
                      split_points: List[float],
                      options: ProcessingOptions,
                      progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> List[Path]:
        """Split TAF file at specified time points."""
        try:
            self.logger.info(f"Splitting {input_path} at {len(split_points)} points")
            
            output_files = []
            prev_time = 0.0
            
            for i, split_time in enumerate(split_points + [None]):  # Add None to process final segment
                # Determine segment output path
                segment_path = output_directory / f"{input_path.stem}_part_{i+1:03d}.taf"
                
                # Build command for this segment
                if split_time is not None:
                    duration = split_time - prev_time
                    cmd = self._build_split_command(input_path, segment_path, prev_time, duration, options)
                else:
                    # Final segment - no duration limit
                    cmd = self._build_split_command(input_path, segment_path, prev_time, None, options)
                
                # Execute segment extraction
                if self._execute_conversion_with_progress(
                    cmd, input_path, segment_path, options, progress_callback
                ):
                    output_files.append(segment_path)
                    self.logger.debug(f"Created segment: {segment_path}")
                else:
                    self.logger.warning(f"Failed to create segment: {segment_path}")
                
                if split_time is not None:
                    prev_time = split_time
                else:
                    break  # Final segment processed
            
            self.logger.info(f"Split operation complete: created {len(output_files)} segments")
            return output_files
            
        except Exception as e:
            self.logger.error(f"File splitting failed for {input_path}: {str(e)}")
            return []
    
    def normalize_audio(self, input_path: Path, output_path: Path,
                       options: ProcessingOptions,
                       target_level: float = -23.0,
                       progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """Normalize audio levels in file."""
        try:
            self.logger.info(f"Normalizing {input_path} to {target_level} LUFS: {output_path}")
            
            # Build FFmpeg command for normalization
            cmd = self._build_normalize_command(input_path, output_path, target_level, options)
            
            # Execute normalization with progress monitoring
            return self._execute_conversion_with_progress(
                cmd, input_path, output_path, options, progress_callback
            )
            
        except Exception as e:
            self.logger.error(f"Audio normalization failed for {input_path}: {str(e)}")
            return False
    
    def get_audio_info(self, file_path: Path) -> Dict[str, Any]:
        """Get audio file information."""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {'error': f"FFprobe failed: {result.stderr}"}
            
            probe_data = json.loads(result.stdout)
            
            # Extract relevant information
            info = {
                'format': probe_data.get('format', {}).get('format_name', 'unknown'),
                'duration': float(probe_data.get('format', {}).get('duration', 0)),
                'size': int(probe_data.get('format', {}).get('size', 0)),
                'bitrate': int(probe_data.get('format', {}).get('bit_rate', 0)) // 1000,  # Convert to kbps
            }
            
            # Get stream information
            streams = probe_data.get('streams', [])
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            
            if audio_stream:
                info.update({
                    'codec': audio_stream.get('codec_name', 'unknown'),
                    'channels': audio_stream.get('channels', 0),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channel_layout': audio_stream.get('channel_layout', 'unknown')
                })
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get audio info for {file_path}: {str(e)}")
            return {'error': str(e)}
    
    def validate_audio_file(self, file_path: Path) -> bool:
        """Validate audio file integrity."""
        try:
            # Use FFprobe to validate file
            cmd = [
                self.ffprobe_path,
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'csv=p=0',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return result.returncode == 0 and result.stdout.strip() != ''
            
        except Exception as e:
            self.logger.error(f"Audio validation failed for {file_path}: {str(e)}")
            return False
    
    def get_supported_input_formats(self) -> List[str]:
        """Get list of supported input audio formats."""
        return ['.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus', '.wma']
    
    def get_supported_output_formats(self) -> List[str]:
        """Get list of supported output audio formats."""
        return ['.mp3', '.ogg', '.wav', '.flac', '.taf']
    
    def estimate_conversion_time(self, file_path: Path, 
                               target_format: str,
                               options: ProcessingOptions) -> Optional[float]:
        """Estimate conversion time for file."""
        try:
            # Get file info for estimation
            info = self.get_audio_info(file_path)
            
            if 'error' in info:
                return None
            
            duration = info.get('duration', 0)
            if duration <= 0:
                return None
            
            # Rough estimation based on quality settings and format
            base_ratio = 0.1  # Base conversion ratio (10% of duration)
            
            # Adjust for quality
            quality_multipliers = {
                'LOW': 0.5,
                'MEDIUM': 1.0,
                'HIGH': 2.0,
                'LOSSLESS': 3.0
            }
            quality_mult = quality_multipliers.get(options.quality_level.name, 1.0)
            
            # Adjust for target format
            format_multipliers = {
                'mp3': 1.0,
                'taf': 1.2,  # TAF might be slightly slower
                'flac': 2.0,
                'wav': 0.8
            }
            format_mult = format_multipliers.get(target_format.lower(), 1.0)
            
            estimated_time = duration * base_ratio * quality_mult * format_mult
            
            return max(estimated_time, 1.0)  # Minimum 1 second
            
        except Exception as e:
            self.logger.error(f"Failed to estimate conversion time for {file_path}: {str(e)}")
            return None
    
    def _build_taf_conversion_command(self, input_path: Path, output_path: Path,
                                    options: ProcessingOptions) -> List[str]:
        """Build FFmpeg command for TAF conversion."""
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite output
            '-i', str(input_path)
        ]
        
        # Add quality settings
        cmd.extend(options.get_ffmpeg_quality_args())
        
        # Add compression settings
        cmd.extend(options.get_compression_args())
        
        # Add normalization if enabled
        if options.should_normalize_audio():
            cmd.extend(['-filter:a', 'loudnorm'])
        
        # Add fade effects if configured
        filters = []
        if options.fade_in_duration > 0:
            filters.append(f'afade=t=in:d={options.fade_in_duration}')
        if options.fade_out_duration > 0:
            filters.append(f'afade=t=out:d={options.fade_out_duration}')
        
        if filters:
            cmd.extend(['-af', ','.join(filters)])
        
        # Output format (TAF is typically OGG Vorbis)
        cmd.extend(['-c:a', 'libvorbis', str(output_path)])
        
        return cmd
    
    def _build_format_conversion_command(self, input_path: Path, output_path: Path,
                                       output_format: str, options: ProcessingOptions) -> List[str]:
        """Build FFmpeg command for format conversion."""
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite output
            '-i', str(input_path)
        ]
        
        # Add format-specific codec settings
        format_codecs = {
            'mp3': ['-c:a', 'libmp3lame'],
            'wav': ['-c:a', 'pcm_s16le'],
            'flac': ['-c:a', 'flac'],
            'ogg': ['-c:a', 'libvorbis']
        }
        
        codec_args = format_codecs.get(output_format.lower(), ['-c:a', 'copy'])
        cmd.extend(codec_args)
        
        # Add quality settings if not copying
        if codec_args != ['-c:a', 'copy']:
            cmd.extend(options.get_ffmpeg_quality_args())
        
        cmd.append(str(output_path))
        
        return cmd
    
    def _build_combine_command(self, file_list_path: str, output_path: Path,
                             options: ProcessingOptions) -> List[str]:
        """Build FFmpeg command for combining files."""
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite output
            '-f', 'concat',
            '-safe', '0',
            '-i', file_list_path
        ]
        
        # Add quality settings
        cmd.extend(options.get_ffmpeg_quality_args())
        
        # Output format
        cmd.extend(['-c:a', 'libvorbis', str(output_path)])
        
        return cmd
    
    def _build_split_command(self, input_path: Path, output_path: Path,
                           start_time: float, duration: Optional[float],
                           options: ProcessingOptions) -> List[str]:
        """Build FFmpeg command for splitting file."""
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite output
            '-ss', str(start_time),
            '-i', str(input_path)
        ]
        
        # Add duration if specified
        if duration is not None:
            cmd.extend(['-t', str(duration)])
        
        # Copy codec to avoid re-encoding
        cmd.extend(['-c', 'copy', str(output_path)])
        
        return cmd
    
    def _build_normalize_command(self, input_path: Path, output_path: Path,
                               target_level: float, options: ProcessingOptions) -> List[str]:
        """Build FFmpeg command for audio normalization."""
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite output
            '-i', str(input_path),
            '-filter:a', f'loudnorm=I={target_level}',
            '-c:a', 'libvorbis',
            str(output_path)
        ]
        
        return cmd
    
    def _execute_conversion_with_progress(self, cmd: List[str], input_path: Path,
                                        output_path: Path, options: ProcessingOptions,
                                        progress_callback: Optional[Callable[[ConversionProgress], None]]) -> bool:
        """Execute FFmpeg conversion with progress monitoring."""
        try:
            # Get input duration for progress calculation
            duration = 0.0
            try:
                info = self.get_audio_info(input_path)
                duration = info.get('duration', 0.0)
            except Exception:
                pass
            
            # Start FFmpeg process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Monitor progress in separate thread if callback provided
            if progress_callback and duration > 0:
                progress_thread = threading.Thread(
                    target=self._monitor_ffmpeg_progress,
                    args=(process, duration, input_path, progress_callback)
                )
                progress_thread.daemon = True
                progress_thread.start()
            
            # Wait for completion
            stdout, stderr = process.communicate(timeout=options.timeout_seconds)
            
            if process.returncode == 0:
                # Final progress update
                if progress_callback:
                    progress_callback(ConversionProgress(
                        current_file=str(input_path),
                        files_completed=1,
                        total_files=1,
                        current_file_progress=1.0,
                        overall_progress=1.0
                    ))
                
                self.logger.debug(f"Conversion successful: {input_path} -> {output_path}")
                return True
            else:
                self.logger.error(f"FFmpeg conversion failed: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Conversion timeout for {input_path}")
            process.kill()
            return False
        except Exception as e:
            self.logger.error(f"Conversion error for {input_path}: {str(e)}")
            return False
    
    def _monitor_ffmpeg_progress(self, process: subprocess.Popen, duration: float,
                               input_path: Path, progress_callback: Callable[[ConversionProgress], None]):
        """Monitor FFmpeg progress and call callback."""
        try:
            while process.poll() is None:
                # This is a simplified progress monitoring
                # Real implementation would parse FFmpeg stderr output
                # for progress information
                time.sleep(0.5)
                
                # For now, just provide periodic updates
                progress = ConversionProgress(
                    current_file=str(input_path),
                    files_completed=0,
                    total_files=1,
                    current_file_progress=0.5,  # Approximate mid-point
                    overall_progress=0.5
                )
                progress_callback(progress)
                
        except Exception as e:
            self.logger.debug(f"Progress monitoring error: {str(e)}")