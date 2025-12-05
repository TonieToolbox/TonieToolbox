#!/usr/bin/env python3
"""
File analysis use case.

This use case handles analysis operations on TAF files including info display,
file splitting, format conversion, and playback.
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import time

from ...domain import ProcessingOperation, ProcessingResult, ProcessingModeType
from ...domain.models.processing_result import ProcessedFile, ProcessingStatus
from ..interfaces.media_converter import ConversionProgress
from .base_use_case import BaseUseCase


class FileAnalysisUseCase(BaseUseCase):
    """
    Use case for analyzing TAF files and performing analysis operations.
    
    Supports info display, file splitting, format conversion, and playback.
    """
    
    def __init__(self, file_repo, media_converter, analysis_service, logger=None):
        """
        Initialize file analysis use case.
        
        Args:
            file_repo: File repository for file operations
            media_converter: Media converter for audio operations
            analysis_service: TAF analysis service
            logger: Optional logger instance
        """
        # Initialize base use case
        super().__init__(
            file_repo=file_repo,
            media_converter=media_converter,
            logger=logger
        )
        self.analysis_service = analysis_service
    
    def execute(self, operation: ProcessingOperation,
               progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute file analysis operation.
        
        Args:
            operation: Processing operation to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with analysis results
        """
        # Validate operation
        if not self.validate_operation(operation):
            result = self._create_result(operation)
            result.mark_failed(ValueError("Operation validation failed"))
            return result
        
        # Start processing
        result = self._create_result(operation)
        result.mark_started()
        operation.mark_started()
        
        analysis_type = operation.options.get_custom_option('analysis_type', 'info')
        
        self.logger.info(f"Starting file analysis ({analysis_type}): {operation.operation_id}")
        self._publish_started_event(operation)
        
        try:
            # Resolve input files
            input_files = operation.input_spec.resolve_files()
            
            # For compare operation, check if second file is in custom options
            compare_file = operation.options.get_custom_option('compare_file')
            if compare_file and analysis_type == 'compare':
                # Add the compare file to input_files if not already there
                compare_path = Path(compare_file)
                if compare_path not in input_files:
                    input_files.append(compare_path)
            
            if not input_files:
                raise ValueError("No input files found")
            
            self.logger.info(f"Analyzing {len(input_files)} files with operation: {analysis_type}")
            
            # Execute appropriate analysis operation
            if analysis_type == 'info':
                self._execute_info_analysis(operation, input_files, result, progress_callback)
            elif analysis_type == 'split':
                self._execute_split_analysis(operation, input_files, result, progress_callback)
            elif analysis_type == 'extract':
                self._execute_extract_analysis(operation, input_files, result, progress_callback)
            elif analysis_type == 'compare':
                self._execute_compare_analysis(operation, input_files, result, progress_callback)
            elif analysis_type == 'convert_to_separate_mp3':
                self._execute_convert_to_mp3(operation, input_files, result, progress_callback, separate=True)
            elif analysis_type == 'convert_to_single_mp3':
                self._execute_convert_to_mp3(operation, input_files, result, progress_callback, separate=False)
            elif analysis_type == 'play':
                self._execute_play_analysis(operation, input_files, result, progress_callback)
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
            
            operation.mark_completed()
            self._publish_completed_event(operation, result)
            
        except Exception as e:
            self.logger.error(f"File analysis failed: {str(e)}")
            result.mark_failed(e)
            operation.mark_completed()
            self._publish_failed_event(operation, e)
        
        return self._finalize_result(operation, result)
    
    def _execute_info_analysis(self, operation: ProcessingOperation,
                             input_files: List[Path], result: ProcessingResult,
                             progress_callback: Optional[Callable] = None) -> None:
        """Execute info analysis operation."""
        self.logger.info("Displaying file information")
        
        for i, input_file in enumerate(input_files):
            if progress_callback:
                progress_callback({
                    'operation': f'Analyzing {input_file.name}',
                    'progress': i / len(input_files),
                    'files_completed': i,
                    'total_files': len(input_files)
                })
            
            try:
                # Check if this is a TAF file and use appropriate analyzer
                if input_file.suffix.lower() == '.taf':
                    # Use TAF analyzer for TAF files
                    from ....analysis.taf_analyzer import analyze_taf_file
                    taf_analysis = analyze_taf_file(input_file)
                    
                    if taf_analysis:
                        info_text = self._format_taf_info(input_file, taf_analysis)
                        metadata = {'taf_analysis': taf_analysis, 'info_text': info_text}
                    else:
                        info_text = f"File: {input_file.name}\nPath: {input_file}\nError: Failed to analyze TAF file"
                        metadata = {'info_text': info_text}
                else:
                    # Use FFmpeg analyzer for regular audio files
                    audio_info = self.media_converter.get_audio_info(input_file)
                    info_text = self._format_audio_info(input_file, audio_info)
                    metadata = {'audio_info': audio_info, 'info_text': info_text}
                
                # Display information (this would typically go to console/UI)
                self.logger.info(f"File info for {input_file}:\n{info_text}")
                
                # Create processed file entry (no output file for info)
                processed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.COMPLETED,
                    file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                    metadata=metadata
                )
                result.add_processed_file(processed_file)
                
            except Exception as e:
                self.logger.error(f"Failed to get info for {input_file}: {str(e)}")
                
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
        
        if progress_callback:
            progress_callback({
                'operation': 'Info analysis complete',
                'progress': 1.0,
                'files_completed': len(input_files),
                'total_files': len(input_files)
            })
    
    def _execute_split_analysis(self, operation: ProcessingOperation,
                              input_files: List[Path], result: ProcessingResult,
                              progress_callback: Optional[Callable] = None) -> None:
        """Execute split analysis operation."""
        # Get split configuration from operation options
        split_points = operation.options.get_custom_option('split_points', [])
        if not split_points:
            raise ValueError("Split operation requires split_points in options")
        
        self.logger.info(f"Splitting files at points: {split_points}")
        
        for i, input_file in enumerate(input_files):
            if progress_callback:
                progress_callback({
                    'operation': f'Splitting {input_file.name}',
                    'progress': i / len(input_files),
                    'files_completed': i,
                    'total_files': len(input_files)
                })
            
            try:
                # Determine output directory
                output_dir = operation.output_spec.resolve_output_path(input_file.stem).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                start_time = time.time()
                
                # Perform split
                output_files = self.media_converter.split_taf_file(
                    input_file,
                    output_dir,
                    split_points,
                    operation.options
                )
                
                processing_time = time.time() - start_time
                
                # Calculate output size
                total_output_size = sum(f.stat().st_size for f in output_files if f.exists())
                
                processed_file = ProcessedFile(
                    input_path=input_file,
                    output_path=output_dir,  # Directory containing split files
                    status=ProcessingStatus.COMPLETED,
                    processing_time=processing_time,
                    file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                    file_size_output=total_output_size,
                    metadata={'split_files': [str(f) for f in output_files]}
                )
                result.add_processed_file(processed_file)
                
                self.logger.info(f"Split {input_file} into {len(output_files)} files")
                
            except Exception as e:
                self.logger.error(f"Failed to split {input_file}: {str(e)}")
                
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
    
    def _execute_extract_analysis(self, operation: ProcessingOperation,
                                  input_files: List[Path], result: ProcessingResult,
                                  progress_callback: Optional[Callable] = None) -> None:
        """
        Execute OGG extraction from TAF files.
        
        Extracts the entire OGG/Opus stream from TAF file to a .ogg file.
        """
        self.logger.info(f"Extracting OGG streams from {len(input_files)} file(s)")
        
        for i, input_file in enumerate(input_files):
            if progress_callback:
                progress_callback({
                    'operation': f'Extracting {input_file.name}',
                    'progress': i / len(input_files),
                    'files_completed': i,
                    'total_files': len(input_files)
                })
            
            try:
                # Determine output file path
                # For SINGLE_FILE mode, output_spec already has the full path with .ogg extension
                output_path = operation.output_spec.output_path
                if output_path:
                    output_path = Path(output_path)
                else:
                    # Fallback if no output path specified
                    output_path = Path(input_file.parent / (input_file.stem + '.ogg'))
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                start_time = time.time()
                
                # Extract OGG stream from TAF file
                with open(input_file, 'rb') as taf_file:
                    # Skip Tonie header (first 4096 bytes typically)
                    header_size = 4096
                    taf_file.seek(header_size)
                    ogg_data = taf_file.read()
                
                # Write OGG data to output file
                with open(output_path, 'wb') as ogg_file:
                    ogg_file.write(ogg_data)
                
                processing_time = time.time() - start_time
                
                processed_file = ProcessedFile(
                    input_path=input_file,
                    output_path=output_path,
                    status=ProcessingStatus.COMPLETED,
                    processing_time=processing_time,
                    file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                    file_size_output=output_path.stat().st_size if output_path.exists() else 0,
                )
                result.add_processed_file(processed_file)
                
                self.logger.info(f"Extracted OGG stream from {input_file} to {output_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to extract OGG from {input_file}: {str(e)}")
                
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
    
    def _execute_compare_analysis(self, operation: ProcessingOperation,
                                input_files: List[Path], result: ProcessingResult,
                                progress_callback: Optional[Callable] = None) -> None:
        """
        Execute compare analysis operation.
        
        Handles:
        - TAF vs TAF: Compares TAF headers + optional OGG content (detailed mode)
        - Media vs Media: Compares using FFprobe
        - Mixed: Basic file metadata comparison
        """
        if len(input_files) < 2:
            raise ValueError("Compare operation requires at least 2 files")
        
        self.logger.info(f"Comparing {len(input_files)} files")
        
        # Determine file types
        file_types = [self._detect_file_type(f) for f in input_files]
        detailed = operation.options.get_custom_option('detailed', False)
        
        # Track temporary directories for cleanup
        temp_dirs = []
        
        try:
            # Analyze files based on type
            file_infos = {}
            for i, input_file in enumerate(input_files):
                if progress_callback:
                    progress_callback({
                        'operation': f'Analyzing {input_file.name}',
                        'progress': i / len(input_files),
                        'files_completed': i,
                        'total_files': len(input_files)
                    })
                
                try:
                    if file_types[i] == 'taf':
                        info = self._analyze_taf_for_comparison(input_file, detailed)
                        # Store temp_dir for cleanup
                        if detailed and 'detailed_ogg_analysis' in info:
                            temp_dir = info['detailed_ogg_analysis'].get('temp_dir')
                            if temp_dir:
                                temp_dirs.append(temp_dir)
                        file_infos[input_file] = info
                    else:
                        file_infos[input_file] = self._analyze_media_for_comparison(input_file)
                except Exception as e:
                    self.logger.error(f"Failed to analyze {input_file}: {str(e)}")
                    file_infos[input_file] = {'error': str(e), 'type': file_types[i]}
            
            # In detailed mode for TAF vs TAF, compare OGG content
            ogg_comparison = None
            if detailed and all(ft == 'taf' for ft in file_types) and len(file_infos) == 2:
                file_list = list(file_infos.items())
                ogg1_info = file_list[0][1].get('detailed_ogg_analysis', {})
                ogg2_info = file_list[1][1].get('detailed_ogg_analysis', {})
                
                ogg1_path = ogg1_info.get('ogg_file_path')
                ogg2_path = ogg2_info.get('ogg_file_path')
                
                if ogg1_path and ogg2_path and ogg1_path.exists() and ogg2_path.exists():
                    self.logger.info("Comparing OGG file content...")
                    ogg_comparison = self._compare_ogg_content(ogg1_path, ogg2_path)
            
            # Generate comparison report based on file types
            comparison_report = self._generate_comparison_report(file_infos, file_types, detailed, ogg_comparison)
            self.logger.info(f"File comparison report:\n{comparison_report}")
            
            # Create single processed file entry for the comparison
            processed_file = ProcessedFile(
                input_path=Path("comparison"),
                status=ProcessingStatus.COMPLETED,
                metadata={
                    'comparison_report': comparison_report, 
                    'file_infos': file_infos,
                    'file_types': file_types,
                    'detailed': detailed,
                    'ogg_comparison': ogg_comparison
                }
            )
            result.add_processed_file(processed_file)
            
            if progress_callback:
                progress_callback({
                    'operation': 'Comparison complete',
                    'progress': 1.0,
                    'files_completed': len(input_files),
                    'total_files': len(input_files)
                })
        
        finally:
            # Cleanup temporary directories
            import shutil
            for temp_dir in temp_dirs:
                try:
                    if Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
                        self.logger.debug(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup temp directory {temp_dir}: {str(e)}")
    
    def _execute_convert_to_mp3(self, operation: ProcessingOperation,
                              input_files: List[Path], result: ProcessingResult,
                              progress_callback: Optional[Callable] = None,
                              separate: bool = True) -> None:
        """Execute MP3 conversion operation."""
        format_desc = "separate MP3 files" if separate else "single MP3 file"
        self.logger.info(f"Converting to {format_desc}")
        
        for i, input_file in enumerate(input_files):
            if progress_callback:
                progress_callback({
                    'operation': f'Converting {input_file.name}',
                    'progress': i / len(input_files),
                    'files_completed': i,
                    'total_files': len(input_files)
                })
            
            try:
                if separate:
                    output_path = operation.output_spec.resolve_output_path(f"{input_file.stem}.mp3")
                else:
                    # For single file, use combined name
                    output_path = operation.output_spec.resolve_output_path("combined.mp3")
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                start_time = time.time()
                
                success = self.media_converter.convert_from_taf(
                    input_file,
                    output_path,
                    'mp3',
                    operation.options
                )
                
                processing_time = time.time() - start_time
                
                processed_file = ProcessedFile(
                    input_path=input_file,
                    output_path=output_path if success else None,
                    status=ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED,
                    processing_time=processing_time,
                    file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                    file_size_output=output_path.stat().st_size if success and output_path.exists() else 0,
                    error=None if success else Exception("MP3 conversion failed")
                )
                result.add_processed_file(processed_file)
                
            except Exception as e:
                self.logger.error(f"Failed to convert {input_file} to MP3: {str(e)}")
                
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
    
    def _execute_play_analysis(self, operation: ProcessingOperation,
                             input_files: List[Path], result: ProcessingResult,
                             progress_callback: Optional[Callable] = None) -> None:
        """Execute play analysis operation."""
        self.logger.info("Starting playback operation")
        
        # For playback, we typically handle only the first file or create a playlist
        if len(input_files) == 1:
            input_file = input_files[0]
            
            if progress_callback:
                progress_callback({
                    'operation': f'Playing {input_file.name}',
                    'progress': 0.0,
                    'files_completed': 0,
                    'total_files': 1
                })
            
            try:
                # Validate the audio file first
                is_valid = self.media_converter.validate_audio_file(input_file)
                if not is_valid:
                    raise ValueError("Invalid audio file")
                
                # Get audio info for playback metadata
                audio_info = self.media_converter.get_audio_info(input_file)
                
                # Note: Actual playback would be handled by a separate GUI component
                # This use case just prepares the file for playback
                
                processed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.COMPLETED,
                    file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                    metadata={
                        'playback_ready': True,
                        'audio_info': audio_info,
                        'play_mode': 'single'
                    }
                )
                result.add_processed_file(processed_file)
                
                self.logger.info(f"File ready for playback: {input_file}")
                
            except Exception as e:
                self.logger.error(f"Failed to prepare {input_file} for playback: {str(e)}")
                
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
        else:
            # Multiple files - prepare playlist
            self.logger.info(f"Preparing playlist with {len(input_files)} files")
            
            valid_files = []
            for input_file in input_files:
                try:
                    if self.media_converter.validate_audio_file(input_file):
                        valid_files.append(input_file)
                except Exception:
                    self.logger.warning(f"Skipping invalid file: {input_file}")
            
            processed_file = ProcessedFile(
                input_path=Path("playlist"),
                status=ProcessingStatus.COMPLETED,
                metadata={
                    'playback_ready': True,
                    'play_mode': 'playlist',
                    'playlist_files': [str(f) for f in valid_files],
                    'total_files': len(valid_files)
                }
            )
            result.add_processed_file(processed_file)
            
            self.logger.info(f"Playlist ready with {len(valid_files)} valid files")
        
        if progress_callback:
            progress_callback({
                'operation': 'Playback preparation complete',
                'progress': 1.0,
                'files_completed': 1,
                'total_files': 1
            })
    
    def _format_audio_info(self, file_path: Path, audio_info: Dict[str, Any]) -> str:
        """Format audio information for display."""
        lines = []
        lines.append(f"File: {file_path.name}")
        lines.append(f"Path: {file_path}")
        
        if 'error' in audio_info:
            lines.append(f"Error: {audio_info['error']}")
        else:
            lines.append(f"Format: {audio_info.get('format', 'Unknown')}")
            lines.append(f"Duration: {audio_info.get('duration', 'Unknown')} seconds")
            lines.append(f"Bitrate: {audio_info.get('bitrate', 'Unknown')} kbps")
            lines.append(f"Channels: {audio_info.get('channels', 'Unknown')}")
            lines.append(f"Sample Rate: {audio_info.get('sample_rate', 'Unknown')} Hz")
            
            if 'size' in audio_info:
                size_mb = audio_info['size'] / (1024 * 1024)
                lines.append(f"Size: {size_mb:.2f} MB")
        
        return '\n'.join(lines)
    
    def _format_taf_info(self, file_path: Path, taf_analysis) -> str:
        """Format TAF analysis information for display."""
        lines = []
        lines.append(f"File: {file_path.name}")
        lines.append(f"Path: {file_path}")
        lines.append(f"Type: TAF (Tonie Audio Format)")
        
        # File size information
        size_mb = taf_analysis.file_size / (1024 * 1024)
        audio_size_mb = taf_analysis.audio_size / (1024 * 1024)
        lines.append(f"Total Size: {size_mb:.2f} MB")
        lines.append(f"Audio Size: {audio_size_mb:.2f} MB")
        lines.append(f"Valid: {'Yes' if taf_analysis.valid else 'No'}")
        
        if taf_analysis.sha1_hash:
            lines.append(f"SHA1 Hash: {taf_analysis.sha1_hash}")
        
        # Tonie header information
        if taf_analysis.tonie_header:
            lines.append(f"\nTonie Information:")
            lines.append(f"  Timestamp: {taf_analysis.tonie_header.timestamp}")
            lines.append(f"  Data Length: {taf_analysis.tonie_header.data_length}")
            lines.append(f"  Chapters: {taf_analysis.tonie_header.chapter_count}")
            
            # Chapter details
            if taf_analysis.tonie_header.chapters:
                lines.append(f"  Chapter Details:")
                for i, chapter in enumerate(taf_analysis.tonie_header.chapters, 1):
                    lines.append(f"    {i}. {chapter.title} ({chapter.duration_formatted})")
        
        # Opus audio information
        if taf_analysis.opus_info:
            lines.append(f"\nAudio Information:")
            lines.append(f"  Sample Rate: {taf_analysis.opus_info.sample_rate} Hz")
            lines.append(f"  Channels: {taf_analysis.opus_info.channels}")
            
            if hasattr(taf_analysis.opus_info, 'comments') and taf_analysis.opus_info.comments:
                lines.append(f"  Comments:")
                for key, value in taf_analysis.opus_info.comments.items():
                    lines.append(f"    {key}: {value}")
        
        # Audio analysis information
        if taf_analysis.audio_analysis:
            lines.append(f"\nTechnical Analysis:")
            if hasattr(taf_analysis.audio_analysis, 'duration_seconds') and taf_analysis.audio_analysis.duration_seconds:
                duration = taf_analysis.audio_analysis.duration_seconds
                minutes = int(duration // 60)
                seconds = duration % 60
                lines.append(f"  Duration: {minutes:02d}:{seconds:06.3f}")
            
            if hasattr(taf_analysis.audio_analysis, 'bitrate_kbps') and taf_analysis.audio_analysis.bitrate_kbps:
                lines.append(f"  Bitrate: {taf_analysis.audio_analysis.bitrate_kbps} kbps")
            
            if hasattr(taf_analysis.audio_analysis, 'page_count'):
                lines.append(f"  Page Count: {taf_analysis.audio_analysis.page_count}")
            
            if hasattr(taf_analysis.audio_analysis, 'alignment_okay'):
                lines.append(f"  Alignment OK: {'Yes' if taf_analysis.audio_analysis.alignment_okay else 'No'}")
            
            if hasattr(taf_analysis.audio_analysis, 'page_size_okay'):
                lines.append(f"  Page Size OK: {'Yes' if taf_analysis.audio_analysis.page_size_okay else 'No'}")
        
        return '\n'.join(lines)
    
    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension."""
        suffix = file_path.suffix.lower()
        if suffix == '.taf':
            return 'taf'
        elif suffix in ['.mp3', '.wav', '.ogg', '.opus', '.flac', '.m4a', '.aac']:
            return 'media'
        else:
            return 'unknown'
    
    def _analyze_taf_for_comparison(self, file_path: Path, detailed: bool = False) -> Dict[str, Any]:
        """
        Analyze TAF file for comparison.
        
        Args:
            file_path: Path to TAF file
            detailed: If True, extract and analyze internal OGG streams
            
        Returns:
            Dictionary with TAF analysis data
        """
        from ....analysis.taf_analyzer import analyze_taf_file
        
        info = {'type': 'taf', 'path': str(file_path)}
        
        try:
            # Analyze TAF structure
            taf_analysis = analyze_taf_file(file_path)
            
            if not taf_analysis:
                info['error'] = 'Failed to analyze TAF file'
                return info
            
            # Extract header information
            if taf_analysis.tonie_header:
                header = taf_analysis.tonie_header
                info['tonie_header'] = {
                    'sha1_hash': taf_analysis.sha1_hash if hasattr(taf_analysis, 'sha1_hash') else None,
                    'valid': taf_analysis.valid if hasattr(taf_analysis, 'valid') else False,
                    'num_chapters': len(header.chapters) if hasattr(header, 'chapters') else 0,
                    'timestamp': header.timestamp if hasattr(header, 'timestamp') else None,
                    'data_length': header.data_length if hasattr(header, 'data_length') else None,
                }
                
                # Extract chapter information directly from header.chapters
                if hasattr(header, 'chapters') and header.chapters:
                    info['chapters'] = [
                        {
                            'title': ch.title if hasattr(ch, 'title') else f"Chapter {ch.id}",
                            'duration': ch.duration_formatted if hasattr(ch, 'duration_formatted') else 'Unknown'
                        }
                        for ch in header.chapters
                    ]
            
            # Extract Opus information
            if taf_analysis.opus_info:
                opus = taf_analysis.opus_info
                info['opus_info'] = {
                    'sample_rate': opus.sample_rate if hasattr(opus, 'sample_rate') else None,
                    'channels': opus.channels if hasattr(opus, 'channels') else None,
                    'comments': opus.comments if hasattr(opus, 'comments') else {},
                }
            
            # Extract audio analysis
            if taf_analysis.audio_analysis:
                audio = taf_analysis.audio_analysis
                info['audio_analysis'] = {
                    'duration_seconds': audio.duration_seconds if hasattr(audio, 'duration_seconds') else None,
                    'bitrate_kbps': audio.bitrate_kbps if hasattr(audio, 'bitrate_kbps') else None,
                    'page_count': audio.page_count if hasattr(audio, 'page_count') else None,
                    'alignment_okay': audio.alignment_okay if hasattr(audio, 'alignment_okay') else None,
                    'page_size_okay': audio.page_size_okay if hasattr(audio, 'page_size_okay') else None,
                }
            
            # Detailed mode: Extract and analyze internal OGG streams
            if detailed:
                info['detailed_ogg_analysis'] = self._extract_and_analyze_ogg_streams(file_path, taf_analysis)
            
        except Exception as e:
            self.logger.error(f"Error analyzing TAF file {file_path}: {str(e)}")
            info['error'] = str(e)
        
        return info
    
    def _analyze_media_for_comparison(self, file_path: Path) -> Dict[str, Any]:
        """
        Analyze media file (MP3, etc.) for comparison using FFprobe.
        
        Args:
            file_path: Path to media file
            
        Returns:
            Dictionary with media file information
        """
        info = {'type': 'media', 'path': str(file_path)}
        
        try:
            audio_info = self.media_converter.get_audio_info(file_path)
            info.update(audio_info)
        except Exception as e:
            self.logger.error(f"Error analyzing media file {file_path}: {str(e)}")
            info['error'] = str(e)
        
        return info
    
    def _extract_and_analyze_ogg_streams(self, taf_file: Path, taf_analysis) -> Dict[str, Any]:
        """
        Extract OGG streams from TAF file and analyze with FFprobe.
        Keeps temporary files for content comparison.
        
        Args:
            taf_file: Path to TAF file
            taf_analysis: TAF analysis object
            
        Returns:
            Dictionary with OGG stream analysis and temp file path
        """
        import tempfile
        
        ogg_analysis = {
            'extracted': False,
            'streams': [],
            'ogg_file_path': None,
            'temp_dir': None
        }
        
        try:
            # Create temporary directory for extraction (don't auto-delete)
            temp_dir = tempfile.mkdtemp(prefix='tonietoolbox_compare_')
            temp_path = Path(temp_dir)
            ogg_analysis['temp_dir'] = temp_dir
            
            # Extract OGG content from TAF file
            self.logger.debug(f"Extracting OGG streams from {taf_file} to {temp_path}")
            
            # Read TAF file and extract OGG portion
            with open(taf_file, 'rb') as f:
                # Skip Tonie header (first 4096 bytes typically)
                header_size = 4096
                f.seek(header_size)
                ogg_data = f.read()
            
            # Write OGG data to temporary file
            ogg_temp_file = temp_path / f"{taf_file.stem}.ogg"
            with open(ogg_temp_file, 'wb') as f:
                f.write(ogg_data)
            
            ogg_analysis['ogg_file_path'] = ogg_temp_file
            
            # Analyze extracted OGG with FFprobe
            try:
                ogg_info = self.media_converter.get_audio_info(ogg_temp_file)
                ogg_analysis['extracted'] = True
                ogg_analysis['streams'].append({
                    'filename': ogg_temp_file.name,
                    'duration': ogg_info.get('duration'),
                    'bitrate': ogg_info.get('bitrate'),
                    'codec': ogg_info.get('codec'),
                    'sample_rate': ogg_info.get('sample_rate'),
                    'channels': ogg_info.get('channels'),
                })
            except Exception as e:
                self.logger.warning(f"Failed to analyze extracted OGG: {str(e)}")
                ogg_analysis['error'] = str(e)
            
        except Exception as e:
            self.logger.error(f"Failed to extract OGG streams: {str(e)}")
            ogg_analysis['error'] = str(e)
        
        return ogg_analysis
    
    def _compare_ogg_content(self, ogg_file1: Path, ogg_file2: Path) -> Dict[str, Any]:
        """
        Compare the content of two OGG files.
        
        Args:
            ogg_file1: Path to first OGG file
            ogg_file2: Path to second OGG file
            
        Returns:
            Dictionary with comparison results
        """
        import hashlib
        
        comparison = {
            'files_identical': False,
            'size_match': False,
            'hash_match': False,
            'file1_size': 0,
            'file2_size': 0,
            'file1_hash': None,
            'file2_hash': None,
        }
        
        try:
            # Compare file sizes
            size1 = ogg_file1.stat().st_size
            size2 = ogg_file2.stat().st_size
            comparison['file1_size'] = size1
            comparison['file2_size'] = size2
            comparison['size_match'] = (size1 == size2)
            
            # Calculate SHA256 hashes for content comparison
            def calculate_hash(file_path):
                sha256 = hashlib.sha256()
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        sha256.update(chunk)
                return sha256.hexdigest()
            
            hash1 = calculate_hash(ogg_file1)
            hash2 = calculate_hash(ogg_file2)
            comparison['file1_hash'] = hash1
            comparison['file2_hash'] = hash2
            comparison['hash_match'] = (hash1 == hash2)
            comparison['files_identical'] = comparison['hash_match']
            
            self.logger.debug(f"OGG comparison: size_match={comparison['size_match']}, hash_match={comparison['hash_match']}")
            
        except Exception as e:
            self.logger.error(f"Failed to compare OGG content: {str(e)}")
            comparison['error'] = str(e)
        
        return comparison
    
    def _generate_comparison_report(self, file_infos: Dict[Path, Dict[str, Any]], 
                                   file_types: List[str] = None, 
                                   detailed: bool = False,
                                   ogg_comparison: Dict[str, Any] = None) -> str:
        """
        Generate comparison report for multiple files.
        
        Args:
            file_infos: Dictionary mapping file paths to analysis info
            file_types: List of file types for each file
            detailed: Whether to include detailed comparison
        """
        # Determine comparison mode
        if file_types:
            all_taf = all(ft == 'taf' for ft in file_types)
            all_media = all(ft == 'media' for ft in file_types)
            mixed = not (all_taf or all_media)
        else:
            all_taf = all_media = mixed = False
        
        # Use table format for TAF vs TAF comparison
        if all_taf:
            return self._generate_taf_table_comparison(file_infos, detailed, ogg_comparison)
        
        # Use legacy format for other modes
        lines = []
        lines.append("File Comparison Report")
        lines.append("=" * 120)
        
        if all_media:
            lines.append("Comparison Mode: Media vs Media (FFprobe)")
        elif mixed:
            lines.append("Comparison Mode: Mixed (TAF + Media)")
        
        if detailed:
            lines.append("Detail Level: DETAILED")
        else:
            lines.append("Detail Level: STANDARD")
        
        lines.append("=" * 120)
        
        # Display individual file info
        for file_path, info in file_infos.items():
            lines.append(f"\n📄 {file_path.name}")
            lines.append("-" * 120)
            
            if 'error' in info:
                lines.append(f"  ❌ Error: {info['error']}")
                continue
            
            file_type = info.get('type', 'unknown')
            
            if file_type == 'media':
                lines.extend(self._format_media_comparison_info(info))
            else:
                lines.append(f"  Type: {file_type}")
        
        # Add summary comparison
        lines.append("\n" + "=" * 120)
        lines.append("COMPARISON SUMMARY")
        lines.append("=" * 120)
        
        if all_media:
            lines.extend(self._generate_media_comparison_summary(file_infos))
        else:
            lines.append("Mixed file types - limited comparison available")
        
        return '\n'.join(lines)
    
    def _generate_taf_table_comparison(self, file_infos: Dict[Path, Dict[str, Any]], 
                                       detailed: bool,
                                       ogg_comparison: Dict[str, Any] = None) -> str:
        """
        Generate side-by-side table comparison for TAF files.
        
        Args:
            file_infos: Dictionary mapping file paths to analysis info
            detailed: Whether to include detailed OGG analysis
        """
        files = list(file_infos.items())
        ind_width = 3   # Width for indicator column
        label_width = 28  # Width for label column
        col_width = 43  # Width for each data column
        
        lines = []
        lines.append("TAF File Comparison")
        total_width = ind_width + label_width + col_width * 2 + 9
        lines.append("=" * total_width)
        
        # Header with filenames
        file1_name = files[0][0].name[:col_width]
        file2_name = files[1][0].name[:col_width] if len(files) > 1 else "N/A"
        lines.append(f"{'':>{ind_width}} │ {'Property':<{label_width}} │ {file1_name:<{col_width}} │ {file2_name:<{col_width}}")
        lines.append("─" * ind_width + "─┼─" + "─" * label_width + "─┼─" + "─" * col_width + "─┼─" + "─" * col_width)
        
        # Helper function to add table row with proper alignment
        def add_row(label: str, val1: str, val2: str = "N/A", indicator: str = ""):
            # Determine indicator symbol
            if indicator == "warn" and val1 != val2 and val2 != "N/A":
                symbol = "⚠"
            elif indicator == "ok":
                symbol = "✓"
            else:
                symbol = ""
            
            # Format the row with fixed-width columns
            lines.append(f"{symbol:>{ind_width}} │ {label:<{label_width}} │ {str(val1):<{col_width}} │ {str(val2):<{col_width}}")
        
        info1 = files[0][1]
        info2 = files[1][1] if len(files) > 1 else {}
        
        # Tonie Header section
        lines.append("🎵 Tonie Header")
        if 'tonie_header' in info1:
            h1 = info1['tonie_header']
            h2 = info2.get('tonie_header', {})
            
            # SHA1 Hash (full hash)
            sha1_1 = str(h1.get('sha1_hash', 'None'))
            sha1_2 = str(h2.get('sha1_hash', 'None'))
            add_row("  SHA1 Hash", sha1_1, sha1_2)
            
            add_row("  Valid", str(h1.get('valid', 'Unknown')), str(h2.get('valid', 'N/A')),
                   "ok" if h1.get('valid') and h2.get('valid') else "warn")
            add_row("  Chapters (header)", str(h1.get('num_chapters', 0)), str(h2.get('num_chapters', 'N/A')))
            
            # Add timestamp if available
            if h1.get('timestamp') or h2.get('timestamp'):
                # Show both unix timestamp and readable date
                from datetime import datetime
                ts1 = h1.get('timestamp')
                ts2 = h2.get('timestamp')
                
                try:
                    date1 = datetime.fromtimestamp(ts1).strftime('%Y-%m-%d %H:%M:%S') if ts1 else 'N/A'
                    ts1_display = f"{ts1} ({date1})" if ts1 else 'N/A'
                except (ValueError, OSError, TypeError):
                    ts1_display = str(ts1) if ts1 else 'N/A'
                
                try:
                    date2 = datetime.fromtimestamp(ts2).strftime('%Y-%m-%d %H:%M:%S') if ts2 else 'N/A'
                    ts2_display = f"{ts2} ({date2})" if ts2 else 'N/A'
                except (ValueError, OSError, TypeError):
                    ts2_display = str(ts2) if ts2 else 'N/A'
                
                add_row("  Timestamp", ts1_display, ts2_display)
        
        # Chapters section
        lines.append("")
        lines.append("📖 Chapters")
        ch1_count = len(info1.get('chapters', []))
        ch2_count = len(info2.get('chapters', []))
        add_row("  Total Chapters", str(ch1_count), str(ch2_count), "warn" if ch1_count != ch2_count else "ok")
        
        # Show all chapters
        for i in range(max(ch1_count, ch2_count)):
            ch1 = info1.get('chapters', [])[i] if i < ch1_count else None
            ch2 = info2.get('chapters', [])[i] if i < ch2_count else None
            
            if ch1 or ch2:
                ch1_str = f"{ch1.get('title', 'Untitled')[:30]} ({ch1.get('duration', '?')})" if ch1 else "—"
                ch2_str = f"{ch2.get('title', 'Untitled')[:30]} ({ch2.get('duration', '?')})" if ch2 else "—"
                add_row(f"  Chapter {i+1}", ch1_str, ch2_str)
        
        # Opus Stream section
        lines.append("")
        lines.append("🎧 Opus Stream")
        if 'opus_info' in info1:
            o1 = info1['opus_info']
            o2 = info2.get('opus_info', {})
            add_row("  Sample Rate", f"{o1.get('sample_rate', 'N/A')} Hz", 
                   f"{o2.get('sample_rate', 'N/A')} Hz",
                   "ok" if o1.get('sample_rate') == o2.get('sample_rate') else "warn")
            add_row("  Channels", str(o1.get('channels', 'N/A')), str(o2.get('channels', 'N/A')),
                   "ok" if o1.get('channels') == o2.get('channels') else "warn")
            
            # Add comments in detailed mode
            if detailed:
                comments1 = o1.get('comments', {})
                comments2 = o2.get('comments', {})
                
                if comments1 or comments2:
                    lines.append("")
                    lines.append("💬 Opus Comments")
                    
                    # Get all unique comment keys
                    all_keys = set(comments1.keys()) | set(comments2.keys())
                    for key in sorted(all_keys):
                        val1 = comments1.get(key, '—')
                        val2 = comments2.get(key, '—')
                        # Truncate long values
                        val1_str = str(val1)[:40] + "..." if len(str(val1)) > 40 else str(val1)
                        val2_str = str(val2)[:40] + "..." if len(str(val2)) > 40 else str(val2)
                        add_row(f"  {key}", val1_str, val2_str)
        
        # Audio Analysis section
        lines.append("")
        lines.append("⏱️  Audio Analysis")
        if 'audio_analysis' in info1:
            a1 = info1['audio_analysis']
            a2 = info2.get('audio_analysis', {})
            
            # Duration
            dur1 = a1.get('duration_seconds')
            dur2 = a2.get('duration_seconds')
            if dur1:
                m1, s1 = int(dur1 // 60), dur1 % 60
                dur1_str = f"{m1}:{s1:06.3f}"
            else:
                dur1_str = "N/A"
            if dur2:
                m2, s2 = int(dur2 // 60), dur2 % 60
                dur2_str = f"{m2}:{s2:06.3f}"
            else:
                dur2_str = "N/A"
            
            diff_indicator = "ok"
            if dur1 and dur2 and abs(dur1 - dur2) > 1.0:
                diff_indicator = "warn"
            
            add_row("  Duration", dur1_str, dur2_str, diff_indicator)
            add_row("  Bitrate", f"{a1.get('bitrate_kbps', 'N/A')} kbps", 
                   f"{a2.get('bitrate_kbps', 'N/A')} kbps")
            add_row("  Pages", str(a1.get('page_count', 'N/A')), str(a2.get('page_count', 'N/A')))
            add_row("  Alignment OK", str(a1.get('alignment_okay', 'N/A')), 
                   str(a2.get('alignment_okay', 'N/A')),
                   "ok" if a1.get('alignment_okay') and a2.get('alignment_okay') else "warn")
        
        # Detailed OGG Analysis (if requested)
        if detailed:
            lines.append("")
            lines.append("🔍 Extracted OGG Analysis")
            if 'detailed_ogg_analysis' in info1:
                ogg1 = info1['detailed_ogg_analysis']
                ogg2 = info2.get('detailed_ogg_analysis', {})
                
                if ogg1.get('extracted') and ogg1.get('streams'):
                    stream1 = ogg1['streams'][0]
                    stream2 = ogg2.get('streams', [{}])[0] if ogg2.get('extracted') else {}
                    
                    add_row("  Extracted", "✓ Yes", "✓ Yes" if ogg2.get('extracted') else "✗ Failed")
                    add_row("  Duration", f"{stream1.get('duration', 'N/A')}s", 
                           f"{stream2.get('duration', 'N/A')}s")
                    add_row("  Codec", str(stream1.get('codec', 'N/A')), str(stream2.get('codec', 'N/A')))
                    add_row("  Bitrate", f"{stream1.get('bitrate', 'N/A')} kbps", 
                           f"{stream2.get('bitrate', 'N/A')} kbps")
                    add_row("  Sample Rate", f"{stream1.get('sample_rate', 'N/A')} Hz",
                           f"{stream2.get('sample_rate', 'N/A')} Hz")
                    add_row("  Channels", str(stream1.get('channels', 'N/A')),
                           str(stream2.get('channels', 'N/A')))
                    
                    # Add OGG content comparison to table if available
                    if ogg_comparison:
                        lines.append("")
                        lines.append("🔬 OGG Content Comparison")
                        
                        # File sizes
                        size1 = ogg_comparison.get('file1_size', 0)
                        size2 = ogg_comparison.get('file2_size', 0)
                        size1_str = f"{size1:,} bytes ({size1/1024/1024:.2f} MB)"
                        size2_str = f"{size2:,} bytes ({size2/1024/1024:.2f} MB)"
                        add_row("  File Size", size1_str, size2_str, 
                               "ok" if ogg_comparison.get('size_match') else "warn")
                        
                        # SHA256 hashes - compact format (first 16 + last 16 chars)
                        hash1_full = ogg_comparison.get('file1_hash', 'N/A')
                        hash2_full = ogg_comparison.get('file2_hash', 'N/A')
                        
                        # Format: first16...last16 (fits in 35 chars)
                        if len(hash1_full) == 64:
                            hash1_display = f"{hash1_full[:16]}...{hash1_full[-16:]}"
                        else:
                            hash1_display = hash1_full
                        
                        if len(hash2_full) == 64:
                            hash2_display = f"{hash2_full[:16]}...{hash2_full[-16:]}"
                        else:
                            hash2_display = hash2_full
                        
                        add_row("  SHA256 (compact)", hash1_display, hash2_display,
                               "ok" if ogg_comparison.get('hash_match') else "warn")
                        
                        # Content match summary
                        if ogg_comparison.get('files_identical'):
                            add_row("  Content Match", "✓ IDENTICAL", "✓ IDENTICAL", "ok")
                        else:
                            add_row("  Content Match", "⚠ DIFFERENT", "⚠ DIFFERENT", "warn")
                        
                        # Add full hashes below table for reference
                        if hash1_full != 'N/A' and hash2_full != 'N/A':
                            lines.append("")
                            lines.append(f"  Full SHA256 Hashes:")
                            lines.append(f"  File 1: {hash1_full}")
                            lines.append(f"  File 2: {hash2_full}")
                else:
                    add_row("  Extracted", "✗ Failed", "✗ Failed" if ogg2.get('error') else "N/A")
                    if ogg1.get('error'):
                        lines.append(f"  Error (File 1): {ogg1['error']}")
                    if ogg2.get('error'):
                        lines.append(f"  Error (File 2): {ogg2['error']}")
        
        # Summary
        lines.append("")
        lines.append("=" * total_width)
        lines.append("SUMMARY")
        lines.append("=" * total_width)
        
        # Duration difference
        if 'audio_analysis' in info1 and 'audio_analysis' in info2:
            dur1 = info1['audio_analysis'].get('duration_seconds')
            dur2 = info2['audio_analysis'].get('duration_seconds')
            if dur1 and dur2:
                diff = abs(dur1 - dur2)
                if diff > 1.0:
                    lines.append(f"⚠️  Duration difference: {diff:.2f}s ({diff/60:.2f} minutes)")
                else:
                    lines.append(f"✓ Duration difference: {diff:.2f}s (similar)")
        
        # Chapter count difference
        if ch1_count == ch2_count:
            lines.append(f"✓ Both files have {ch1_count} chapters")
        else:
            lines.append(f"⚠️  Chapter count differs: {ch1_count} vs {ch2_count}")
        
        # Alignment check
        if info1.get('audio_analysis', {}).get('alignment_okay') and \
           info2.get('audio_analysis', {}).get('alignment_okay'):
            lines.append("✓ Both files have proper alignment")
        
        return '\n'.join(lines)
    
    def _format_taf_comparison_info(self, info: Dict[str, Any], detailed: bool) -> List[str]:
        """Format TAF file information for comparison."""
        lines = []
        
        # Tonie Header
        if 'tonie_header' in info:
            header = info['tonie_header']
            lines.append(f"  🎵 Tonie Header:")
            lines.append(f"     Audio ID: {header.get('audio_id', 'N/A')}")
            lines.append(f"     Chapters: {header.get('num_chapters', 0)}")
        
        # Chapters
        if 'chapters' in info and info['chapters']:
            lines.append(f"  📖 Chapters ({len(info['chapters'])}):")
            for i, ch in enumerate(info['chapters'][:5], 1):  # Show first 5
                lines.append(f"     {i}. {ch.get('title', 'Untitled')} - {ch.get('duration', 'Unknown')}")
            if len(info['chapters']) > 5:
                lines.append(f"     ... and {len(info['chapters']) - 5} more")
        
        # Opus Info
        if 'opus_info' in info:
            opus = info['opus_info']
            lines.append(f"  🎧 Opus Stream:")
            lines.append(f"     Sample Rate: {opus.get('sample_rate', 'N/A')} Hz")
            lines.append(f"     Channels: {opus.get('channels', 'N/A')}")
        
        # Audio Analysis
        if 'audio_analysis' in info:
            audio = info['audio_analysis']
            duration = audio.get('duration_seconds')
            if duration:
                minutes = int(duration // 60)
                seconds = duration % 60
                lines.append(f"  ⏱️  Duration: {minutes}:{seconds:06.3f}")
            lines.append(f"  📊 Bitrate: {audio.get('bitrate_kbps', 'N/A')} kbps")
            lines.append(f"  📄 Pages: {audio.get('page_count', 'N/A')}")
            lines.append(f"  ✓  Alignment OK: {audio.get('alignment_okay', 'N/A')}")
        
        # Detailed OGG Analysis
        if detailed and 'detailed_ogg_analysis' in info:
            ogg = info['detailed_ogg_analysis']
            lines.append(f"  🔍 Extracted OGG Analysis:")
            if ogg.get('extracted'):
                for stream in ogg.get('streams', []):
                    lines.append(f"     Duration: {stream.get('duration', 'N/A')}s")
                    lines.append(f"     Codec: {stream.get('codec', 'N/A')}")
                    lines.append(f"     Bitrate: {stream.get('bitrate', 'N/A')} kbps")
            else:
                lines.append(f"     Error: {ogg.get('error', 'Failed to extract')}")
        
        return lines
    
    def _format_media_comparison_info(self, info: Dict[str, Any]) -> List[str]:
        """Format media file information for comparison."""
        lines = []
        lines.append(f"  🎵 Media File (FFprobe):")
        lines.append(f"     Duration: {info.get('duration', 'Unknown')}s")
        lines.append(f"     Bitrate: {info.get('bitrate', 'Unknown')} kbps")
        lines.append(f"     Format: {info.get('format', 'Unknown')}")
        lines.append(f"     Codec: {info.get('codec', 'Unknown')}")
        lines.append(f"     Sample Rate: {info.get('sample_rate', 'Unknown')} Hz")
        lines.append(f"     Channels: {info.get('channels', 'Unknown')}")
        return lines
    
    def _generate_taf_comparison_summary(self, file_infos: Dict[Path, Dict[str, Any]], 
                                        detailed: bool) -> List[str]:
        """Generate summary for TAF file comparison."""
        lines = []
        
        # Compare durations
        durations = []
        for info in file_infos.values():
            if 'audio_analysis' in info and info['audio_analysis'].get('duration_seconds'):
                durations.append(info['audio_analysis']['duration_seconds'])
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            lines.append(f"Duration Range: {min(durations):.2f}s - {max(durations):.2f}s (avg: {avg_duration:.2f}s)")
            if max(durations) - min(durations) > 1.0:
                lines.append(f"⚠️  Duration difference: {max(durations) - min(durations):.2f}s")
        
        # Compare bitrates
        bitrates = []
        for info in file_infos.values():
            if 'audio_analysis' in info and info['audio_analysis'].get('bitrate_kbps'):
                bitrates.append(info['audio_analysis']['bitrate_kbps'])
        
        if bitrates:
            lines.append(f"Bitrate Range: {min(bitrates)} - {max(bitrates)} kbps")
        
        # Compare chapter counts
        chapter_counts = []
        for info in file_infos.values():
            if 'tonie_header' in info:
                chapter_counts.append(info['tonie_header'].get('num_chapters', 0))
        
        if chapter_counts:
            if len(set(chapter_counts)) == 1:
                lines.append(f"✓ All files have {chapter_counts[0]} chapters")
            else:
                lines.append(f"⚠️  Chapter count varies: {min(chapter_counts)} - {max(chapter_counts)}")
        
        # Compare alignment
        alignments = []
        for info in file_infos.values():
            if 'audio_analysis' in info:
                alignments.append(info['audio_analysis'].get('alignment_okay', False))
        
        if alignments:
            if all(alignments):
                lines.append("✓ All files have proper alignment")
            else:
                lines.append("⚠️  Some files have alignment issues")
        
        return lines
    
    def _generate_media_comparison_summary(self, file_infos: Dict[Path, Dict[str, Any]]) -> List[str]:
        """Generate summary for media file comparison."""
        lines = []
        
        # Compare durations
        durations = [info.get('duration') for info in file_infos.values() 
                    if 'duration' in info and info['duration'] is not None]
        if durations:
            avg_duration = sum(durations) / len(durations)
            lines.append(f"Duration Range: {min(durations):.2f}s - {max(durations):.2f}s (avg: {avg_duration:.2f}s)")
            if max(durations) - min(durations) > 1.0:
                lines.append(f"⚠️  Duration difference: {max(durations) - min(durations):.2f}s")
        
        # Compare bitrates
        bitrates = [info.get('bitrate') for info in file_infos.values() 
                   if 'bitrate' in info and info['bitrate'] is not None]
        if bitrates:
            lines.append(f"Bitrate Range: {min(bitrates)} - {max(bitrates)} kbps")
        
        # Compare formats
        formats = [info.get('format') for info in file_infos.values() if 'format' in info]
        if formats:
            if len(set(formats)) == 1:
                lines.append(f"✓ All files are {formats[0]} format")
            else:
                lines.append(f"⚠️  Different formats: {', '.join(set(formats))}")
        
        # Compare codecs
        codecs = [info.get('codec') for info in file_infos.values() if 'codec' in info]
        if codecs:
            if len(set(codecs)) == 1:
                lines.append(f"✓ All files use {codecs[0]} codec")
            else:
                lines.append(f"⚠️  Different codecs: {', '.join(set(codecs))}")
        
        return lines