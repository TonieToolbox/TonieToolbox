#!/usr/bin/env python3
"""
Single file processing adapter.

This module provides interface adapter for single file processing operations,
coordinating between CLI/GUI interfaces and application services.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .base_adapter import BaseInterfaceAdapter, ProgressTrackingMixin
from ...application.services.processing_application_service import ProcessingApplicationService
from ...domain import ProcessingMode, InputSpecification, OutputSpecification, ProcessingOperation
from ...domain.value_objects.processing_mode import SINGLE_FILE_MODE, ANALYSIS_MODE
from ...domain.value_objects.input_specification import ContentType
from ...domain.value_objects.output_specification import OutputFormat, OutputMode
from ...domain.services import OutputPathResolver


class SingleFileProcessingAdapter(BaseInterfaceAdapter, ProgressTrackingMixin):
    """
    Adapter for single file processing operations.
    
    Handles conversion of single audio files to TAF format or between formats,
    coordinating with the application layer services.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """Initialize single file processing adapter."""
        BaseInterfaceAdapter.__init__(self, processing_service, logger)
        ProgressTrackingMixin.__init__(self)
        
        # Initialize domain service for output path resolution
        self.path_resolver = OutputPathResolver(logger)
    
    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute single file processing request.
        
        Args:
            request: Processing request containing:
                - input_path: Path to input file
                - output_path: Path for output file (optional)
                - quality: Quality level (LOW, MEDIUM, HIGH, LOSSLESS)
                - normalize_audio: Whether to normalize audio levels
                - fade_in_duration: Fade in duration in seconds
                - fade_out_duration: Fade out duration in seconds
                - custom_ffmpeg_args: Custom FFmpeg arguments
                - preserve_metadata: Whether to preserve metadata
                - overwrite_existing: Whether to overwrite existing files
                
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"Starting single file processing: {request.get('input_path')}")
            
            # Validate request
            if not self._validate_request(request):
                return 1
            
            # Setup progress tracking
            self._update_progress("Initializing", 0.0, "Preparing single file processing")
            
            # Translate request to domain objects
            input_spec = self._create_input_specification(request)
            output_spec = self._create_output_specification(request)
            options = self._translate_request_to_options(request)
            
            self._update_progress("Processing", 0.2, "Converting audio file")
            
            # Determine processing mode based on input/output formats
            processing_mode = self._determine_single_file_mode(input_spec, output_spec)
            
            # Create processing operation
            operation = ProcessingOperation(
                processing_mode=processing_mode,
                input_spec=input_spec,
                output_spec=output_spec,
                options=options
            )
            
            # Execute processing through application service
            result = self.processing_service.execute_operation(
                operation, 
                progress_callback=self._create_progress_callback()
            )
            
            self._update_progress("Finalizing", 0.9, "Processing complete")
            
            # Log results and return
            self._log_processing_summary(result, request)
            
            if result.is_successful:
                output_files = result.get_output_paths()
                self._update_progress("Complete", 1.0, f"Successfully processed: {output_files[0] if output_files else 'file'}")
                return 0
            else:
                error_summary = result.get_error_summary()
                error_msg = error_summary.split('\n')[0] if error_summary else 'unknown error'
                self._update_progress("Failed", 1.0, f"Processing failed: {error_msg}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Single file processing failed: {str(e)}")
            self._update_progress("Failed", 1.0, f"Error: {str(e)}")
            return self._handle_processing_error(e, request)
    
    def _create_input_specification(self, request: Dict[str, Any]) -> InputSpecification:
        """Create input specification from request."""
        input_path = str(request['input_path'])
        
        # Determine content type based on file extension
        path = Path(input_path)
        if path.suffix.lower() == '.taf':
            content_type = ContentType.TAF
        else:
            content_type = ContentType.AUDIO
        
        return InputSpecification.from_path(
            input_path=input_path,
            content_type=content_type,
            recursive=False
        )
    
    def _create_output_specification(self, request: Dict[str, Any]) -> OutputSpecification:
        """Create output specification from request."""
        input_path = Path(request['input_path'])
        
        # Determine output format first to handle info operations
        temp_output_path = input_path  # Temporary for format detection
        output_format = self._determine_output_format(temp_output_path, request)
        
        # For info operations, don't create a real output file
        if output_format == OutputFormat.INFO or request.get('info', False):
            output_path = None  # No output file for info operations
            output_mode = OutputMode.CONSOLE_ONLY  # Console output only
            overwrite_existing = True  # Info operations don't create files
        else:
            # Generate actual output path for conversion operations
            if 'output_path' in request:
                output_path = Path(request['output_path'])
            else:
                output_path = self._generate_default_output_path(input_path, request)
            output_mode = OutputMode.SINGLE_FILE
            overwrite_existing = request.get('overwrite_existing', False)
        
        return OutputSpecification(
            output_format=output_format,
            output_mode=output_mode,
            output_path=str(output_path) if output_path else None,
            overwrite_existing=overwrite_existing,
            create_directories=not (output_format == OutputFormat.INFO)
        )
    
    def _determine_single_file_mode(self, input_spec: InputSpecification, 
                                  output_spec: OutputSpecification) -> ProcessingMode:
        """Determine specific processing mode for single file operation."""
        # Get input format from path extension
        input_path = Path(input_spec.input_path)
        input_format = input_path.suffix.lower()
        
        # Determine processing mode based on operation type
        if output_spec.output_format == OutputFormat.INFO:
            return ANALYSIS_MODE  # Info display - no output file creation
        elif output_spec.output_format == OutputFormat.TAF and input_format != '.taf':
            return SINGLE_FILE_MODE  # Convert audio TO TAF
        elif input_format == '.taf' and output_spec.output_format != OutputFormat.TAF:
            return SINGLE_FILE_MODE  # Convert FROM TAF to other format
        else:
            return SINGLE_FILE_MODE  # Default single file processing
    
    def _detect_format_hint(self, file_path: Path) -> Optional[str]:
        """Detect audio format hint from file extension."""
        extension = file_path.suffix.lower()
        format_map = {
            '.taf': 'taf',
            '.mp3': 'mp3',
            '.ogg': 'ogg',
            '.wav': 'wav',
            '.flac': 'flac',
            '.m4a': 'm4a',
            '.aac': 'aac'
        }
        return format_map.get(extension)
    
    def _determine_output_format(self, output_path: Path, request: Dict[str, Any]) -> OutputFormat:
        """Determine output format from output path extension and request parameters."""
        extension = output_path.suffix.lower()
        
        # Check for specific flags in request
        if request.get('info', False):
            return OutputFormat.INFO
        elif request.get('convert_to_single_mp3', False):
            return OutputFormat.MP3_SINGLE
        elif request.get('convert_to_separate_mp3', False):
            return OutputFormat.MP3_SEPARATE
        elif extension == '.taf':
            return OutputFormat.TAF
        elif extension == '.mp3':
            return OutputFormat.MP3_SINGLE
        else:
            # Default behavior - if input is TAF and output is not TAF, convert from TAF
            # Otherwise, default to TAF creation
            input_path = Path(request.get('input_path', ''))
            if input_path.suffix.lower() == '.taf' and extension != '.taf':
                return OutputFormat.MP3_SINGLE  # Convert from TAF
            else:
                return OutputFormat.TAF  # Default to TAF creation
    
    def _generate_default_output_path(self, input_path: Path, request: Dict[str, Any] = None) -> Path:
        """
        Generate default output path based on input path and request parameters.
        
        Delegates to domain service for all business logic.
        """
        if not request:
            # Simple case - no templates, use default
            return self.path_resolver.resolve_output_path(input_path=input_path)
        
        # Extract template parameters from request
        use_templates = request.get('use_media_tags', False)
        output_dir_template = request.get('output_to_template')
        filename_template = request.get('name_template')
        
        # Get metadata if templates are requested
        metadata = None
        if use_templates and (output_dir_template or filename_template):
            from ....media.tags import get_media_tag_service
            tag_service = get_media_tag_service()
            metadata = self.path_resolver.resolve_metadata_from_input(input_path, tag_service)
        
        # Delegate to domain service
        return self.path_resolver.resolve_output_path(
            input_path=input_path,
            explicit_output_path=None,
            output_directory_template=output_dir_template,
            filename_template=filename_template,
            metadata=metadata,
            use_templates=use_templates
        )
    
    def _create_progress_callback(self):
        """Create progress callback for use case operations."""
        def progress_callback(progress_info):
            operation = progress_info.get('operation', 'Processing')
            progress = progress_info.get('progress', 0.0)
            details = progress_info.get('details', '')
            
            # Scale progress to fit within processing phase (0.2 to 0.9)
            scaled_progress = 0.2 + (progress * 0.7)
            
            self._update_progress(operation, scaled_progress, details)
        
        return progress_callback


class FileAnalysisAdapter(BaseInterfaceAdapter):
    """
    Adapter for file analysis operations.
    
    Handles analysis of audio files without conversion, providing
    metadata and format information.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """Initialize file analysis adapter."""
        super().__init__(processing_service, logger)
    
    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute file analysis request.
        
        Args:
            request: Analysis request containing:
                - input_path: Path to file to analyze
                - compare: Optional path to second file for comparison
                - output_format: Format for analysis output (json, text)
                - detailed: Whether to perform detailed analysis
                - detailed_compare: Whether to show detailed comparison
                
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            input_path = request.get('input_path', '')
            self.logger.info(f"Starting file analysis: {input_path}")
            
            # Validate request
            if not self._validate_request(request):
                return 1
            
            # Determine analysis type
            analysis_type = request.get('analysis_type', 'info')
            
            # Import domain objects
            from ...domain import (
                InputSpecification, InputType, ContentType,
                ProcessingOptions, OutputSpecification, 
                ProcessingOperation, ANALYSIS_MODE
            )
            
            # For compare operation, we need to handle two files specially
            if 'compare' in request and request['compare']:
                # For compare, we'll use a simple single-file input spec
                # and pass both files via custom options to the use case
                input_spec = InputSpecification.from_path(
                    input_path,
                    content_type=ContentType.TAF,
                    recursive=False
                )
                # Store the second file path for the use case
                compare_file = request['compare']
            else:
                # Single file analysis - determine content type from file extension
                content_type = ContentType.TAF if input_path.lower().endswith('.taf') else ContentType.AUDIO
                input_spec = InputSpecification.from_path(
                    input_path,
                    content_type=content_type,
                    recursive=False
                )
                compare_file = None
            
            # Create processing options with analysis type and detailed flag
            detailed = request.get('detailed', False) or request.get('detailed_compare', False)
            options = ProcessingOptions.default()
            options = options.with_custom_option('analysis_type', analysis_type)
            options = options.with_custom_option('detailed', detailed)
            if compare_file:
                options = options.with_custom_option('compare_file', compare_file)
            
            # Create output specification for analysis
            # Split and extract operations need file output, others use console
            if analysis_type in ['split', 'extract']:
                # Determine output directory from request or use source directory
                if request.get('output_path'):
                    output_path = request['output_path']
                else:
                    # Default to source directory for extract/split
                    input_file_path = Path(input_path)
                    if analysis_type == 'extract':
                        # For extract, create .ogg file with same base name
                        output_path = str(input_file_path.parent / (input_file_path.stem + '.ogg'))
                    else:
                        # For split, use directory for multiple files
                        output_path = str(input_file_path.parent / input_file_path.stem)
                
                output_spec = OutputSpecification(
                    output_path=output_path,
                    output_mode=OutputMode.SINGLE_FILE if analysis_type == 'extract' else OutputMode.MULTIPLE_FILES,
                    output_format=OutputFormat.TAF  # TAF format for both (OGG is contained in TAF)
                )
            else:
                output_spec = OutputSpecification.for_info_display()
            
            # Create processing operation with analysis mode
            operation = ProcessingOperation(
                operation_id=f"analysis_{analysis_type}",
                processing_mode=ANALYSIS_MODE,
                input_spec=input_spec,
                output_spec=output_spec,
                options=options
            )
            
            result = self.processing_service.execute_operation(operation)
            
            # Output results
            self._output_analysis_results(result, request)
            
            # Log results and return
            self._log_processing_summary(result, request)
            
            return 0 if result.is_successful else 1
            
        except Exception as e:
            self.logger.error(f"File analysis failed: {str(e)}")
            return self._handle_processing_error(e, request)
    
    def _output_analysis_results(self, result, request: Dict[str, Any]):
        """Output analysis results in requested format."""
        output_format = request.get('output_format', 'text').lower()
        
        if output_format == 'json':
            self._output_json_results(result)
        else:
            self._output_text_results(result)
    
    def _output_json_results(self, result):
        """Output analysis results in JSON format."""
        import json
        
        output_data = {
            'success': result.is_successful,
            'analysis': result.metadata if hasattr(result, 'metadata') else {},
            'errors': result.errors if hasattr(result, 'errors') else []
        }
        
        print(json.dumps(output_data, indent=2))
    
    def _output_text_results(self, result):
        """Output analysis results in human-readable text format."""
        if hasattr(result, 'metadata') and result.metadata:
            print(f"File Analysis Results:")
            print(f"===================")
            
            for key, value in result.metadata.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        
        if hasattr(result, 'errors') and result.errors:
            print(f"\nErrors:")
            for error in result.errors:
                print(f"  - {error}")


class BatchFileProcessingAdapter(BaseInterfaceAdapter, ProgressTrackingMixin):
    """
    Adapter for batch file processing operations.
    
    Handles processing multiple files in sequence or parallel,
    with progress tracking and error handling.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """Initialize batch file processing adapter."""
        BaseInterfaceAdapter.__init__(self, processing_service, logger)
        ProgressTrackingMixin.__init__(self)
    
    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute batch file processing request.
        
        Args:
            request: Batch processing request containing:
                - input_paths: List of input file paths or patterns
                - output_directory: Directory for output files
                - parallel: Whether to process files in parallel
                - continue_on_error: Whether to continue processing on individual file errors
                
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info(f"Starting batch processing: {len(request.get('input_paths', []))} files")
            
            # Validate request
            if not self._validate_batch_request(request):
                return 1
            
            self._update_progress("Initializing", 0.0, "Preparing batch processing")
            
            # Process files
            total_files = len(request['input_paths'])
            processed = 0
            failed = 0
            
            for i, input_path in enumerate(request['input_paths']):
                try:
                    # Create individual file request
                    file_request = self._create_file_request(input_path, request)
                    
                    # Process single file
                    adapter = SingleFileProcessingAdapter(self.processing_service, self.logger)
                    result = adapter.execute(file_request)
                    
                    if result == 0:
                        processed += 1
                        status = "Success"
                    else:
                        failed += 1
                        status = "Failed"
                        
                        if not request.get('continue_on_error', True):
                            self.logger.error(f"Stopping batch processing due to failure on {input_path}")
                            break
                    
                    # Update progress
                    progress = (i + 1) / total_files
                    self._update_progress(
                        "Processing", progress, 
                        f"{status}: {input_path} ({processed} success, {failed} failed)"
                    )
                    
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Error processing {input_path}: {str(e)}")
                    
                    if not request.get('continue_on_error', True):
                        break
            
            # Final summary
            self._update_progress("Complete", 1.0, f"Batch complete: {processed} success, {failed} failed")
            
            self.logger.info(f"Batch processing complete: {processed} successful, {failed} failed")
            
            return 0 if failed == 0 else 1
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            self._update_progress("Failed", 1.0, f"Batch failed: {str(e)}")
            return self._handle_processing_error(e, request)
    
    def _validate_batch_request(self, request: Dict[str, Any]) -> bool:
        """Validate batch processing request."""
        if 'input_paths' not in request or not request['input_paths']:
            self.logger.error("Missing or empty input_paths for batch processing")
            return False
        
        if 'output_directory' not in request:
            self.logger.error("Missing output_directory for batch processing")
            return False
        
        return True
    
    def _create_file_request(self, input_path: str, batch_request: Dict[str, Any]) -> Dict[str, Any]:
        """Create individual file request from batch request."""
        input_file = Path(input_path)
        output_dir = Path(batch_request['output_directory'])
        
        # Generate output filename
        output_file = output_dir / f"{input_file.stem}.taf"
        
        return {
            'input_path': str(input_file),
            'output_path': str(output_file),
            'quality': batch_request.get('quality', 'MEDIUM'),
            'normalize_audio': batch_request.get('normalize_audio', False),
            'fade_in_duration': batch_request.get('fade_in_duration', 0.0),
            'fade_out_duration': batch_request.get('fade_out_duration', 0.0),
            'preserve_metadata': batch_request.get('preserve_metadata', True),
            'overwrite_existing': batch_request.get('overwrite_existing', False)
        }