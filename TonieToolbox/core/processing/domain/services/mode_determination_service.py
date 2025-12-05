#!/usr/bin/env python3
"""
Mode determination service.

This service determines the appropriate processing mode based on arguments
and creates configured processing operations.
"""

import os
from typing import Dict, Any, Optional
import logging

from ...domain import (
    ProcessingOperation, ProcessingModeType, ProcessingModeRegistry,
    InputSpecification, OutputSpecification, ProcessingOptions,
    ContentType, OutputFormat, OutputMode, QualityLevel, CompressionMode
)


class ModeDeterminationService:
    """
    Service for determining processing modes from arguments and creating operations.
    
    This service encapsulates the logic for analyzing command line arguments
    and user inputs to determine the appropriate processing mode and configuration.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize mode determination service."""
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def determine_mode_from_args(self, args) -> ProcessingModeType:
        """
        Determine processing mode from command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            ProcessingModeType for the arguments
        """
        # Check for explicit mode flags
        if hasattr(args, 'files_to_taf') and args.files_to_taf:
            return ProcessingModeType.FILES_TO_TAF
        
        if hasattr(args, 'recursive') and args.recursive:
            return ProcessingModeType.RECURSIVE
        
        # Check for analysis operations
        analysis_flags = ['info', 'split', 'compare', 'convert_to_separate_mp3', 
                         'convert_to_single_mp3', 'play']
        if any(hasattr(args, flag) and getattr(args, flag) for flag in analysis_flags):
            return ProcessingModeType.ANALYSIS
        
        # Default to single file mode
        return ProcessingModeType.SINGLE_FILE
    
    def create_input_spec_from_args(self, args) -> InputSpecification:
        """
        Create input specification from arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            InputSpecification for the arguments
        """
        input_path = getattr(args, 'input_filename', '')
        
        # Determine content type based on operation
        content_type = ContentType.AUDIO
        if hasattr(args, 'info') and args.info:
            content_type = ContentType.TAF
        elif any(hasattr(args, flag) and getattr(args, flag) 
                for flag in ['split', 'compare', 'convert_to_separate_mp3', 'convert_to_single_mp3', 'play']):
            content_type = ContentType.TAF
        
        # Determine if recursive processing is needed
        recursive = getattr(args, 'recursive', False)
        
        return InputSpecification.from_path(input_path, content_type, recursive)
    
    def create_output_spec_from_args(self, args, mode_type: ProcessingModeType) -> OutputSpecification:
        """
        Create output specification from arguments.
        
        Args:
            args: Parsed command line arguments
            mode_type: Processing mode type
            
        Returns:
            OutputSpecification for the arguments
        """
        # Determine output format
        output_format = OutputFormat.TAF
        if hasattr(args, 'convert_to_separate_mp3') and args.convert_to_separate_mp3:
            output_format = OutputFormat.MP3_SEPARATE
        elif hasattr(args, 'convert_to_single_mp3') and args.convert_to_single_mp3:
            output_format = OutputFormat.MP3_SINGLE
        elif (hasattr(args, 'info') and args.info) or (hasattr(args, 'play') and args.play):
            output_format = OutputFormat.INFO
        
        # Determine output mode
        if output_format == OutputFormat.INFO:
            output_mode = OutputMode.CONSOLE_ONLY
        elif mode_type in [ProcessingModeType.FILES_TO_TAF, ProcessingModeType.RECURSIVE]:
            output_mode = OutputMode.MULTIPLE_FILES
        elif output_format == OutputFormat.MP3_SEPARATE:
            output_mode = OutputMode.MULTIPLE_FILES
        else:
            output_mode = OutputMode.SINGLE_FILE
        
        # Get output path
        output_path = None
        if output_mode != OutputMode.CONSOLE_ONLY:
            output_path = getattr(args, 'output_filename', None)
            
            # Set defaults based on mode
            if not output_path:
                if output_mode == OutputMode.MULTIPLE_FILES:
                    output_path = getattr(args, 'output_dir', './output')
                else:
                    input_path = getattr(args, 'input_filename', 'output')
                    if output_format == OutputFormat.TAF:
                        output_path = f"{os.path.splitext(input_path)[0]}.taf"
                    else:
                        output_path = f"{os.path.splitext(input_path)[0]}.mp3"
        
        # Get other options
        overwrite = getattr(args, 'overwrite', False)
        preserve_structure = mode_type == ProcessingModeType.RECURSIVE
        
        # Create appropriate output specification
        if output_format == OutputFormat.INFO:
            return OutputSpecification.for_info_display()
        elif output_mode == OutputMode.MULTIPLE_FILES:
            if output_format == OutputFormat.TAF:
                return OutputSpecification.for_multiple_taf(
                    output_path, 
                    preserve_structure=preserve_structure,
                    overwrite=overwrite
                )
            else:
                return OutputSpecification.for_mp3_conversion(
                    output_path,
                    separate_files=True,
                    overwrite=overwrite
                )
        else:
            if output_format == OutputFormat.TAF:
                return OutputSpecification.for_single_taf(output_path, overwrite=overwrite)
            else:
                return OutputSpecification.for_mp3_conversion(
                    output_path,
                    separate_files=False,
                    overwrite=overwrite
                )
    
    def create_processing_options_from_args(self, args) -> ProcessingOptions:
        """
        Create processing options from arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            ProcessingOptions for the arguments
        """
        # Quality settings
        quality = QualityLevel.MEDIUM
        if hasattr(args, 'quality'):
            quality_map = {
                'low': QualityLevel.LOW,
                'medium': QualityLevel.MEDIUM,
                'high': QualityLevel.HIGH,
                'lossless': QualityLevel.LOSSLESS
            }
            quality = quality_map.get(getattr(args, 'quality', 'medium').lower(), QualityLevel.MEDIUM)
        
        # Compression settings
        compression = CompressionMode.OPTIMAL
        if hasattr(args, 'compression'):
            compression_map = {
                'none': CompressionMode.NONE,
                'fast': CompressionMode.FAST,
                'optimal': CompressionMode.OPTIMAL,
                'maximum': CompressionMode.MAXIMUM
            }
            compression = compression_map.get(getattr(args, 'compression', 'optimal').lower(), CompressionMode.OPTIMAL)
        
        # Other options
        normalize = getattr(args, 'normalize', False)
        parallel_jobs = getattr(args, 'parallel_jobs', 1)
        continue_on_error = not getattr(args, 'stop_on_error', False)
        upload_enabled = getattr(args, 'upload', False)
        
        # Create base options
        options = ProcessingOptions(
            quality_level=quality,
            compression_mode=compression,
            normalize_audio=normalize,
            max_parallel_jobs=parallel_jobs,
            continue_on_error=continue_on_error,
            upload_enabled=upload_enabled
        )
        
        # Add custom options for specific operations
        custom_options = {}
        
        # Parallel workers for recursive processing
        if hasattr(args, 'workers') and getattr(args, 'workers', 1) > 1:
            custom_options['parallel_workers'] = getattr(args, 'workers')
        
        # Analysis type for analysis operations
        analysis_flags = {
            'info': 'info',
            'split': 'split', 
            'compare': 'compare',
            'convert_to_separate_mp3': 'convert_to_separate_mp3',
            'convert_to_single_mp3': 'convert_to_single_mp3',
            'play': 'play'
        }
        
        for flag, analysis_type in analysis_flags.items():
            if hasattr(args, flag) and getattr(args, flag):
                custom_options['analysis_type'] = analysis_type
                break
        
        # Split points for split operation
        if hasattr(args, 'split_points'):
            custom_options['split_points'] = getattr(args, 'split_points', [])
        
        # Upload configuration
        if upload_enabled:
            upload_config = {}
            for attr in ['host', 'port', 'username', 'password', 'secure']:
                if hasattr(args, attr):
                    upload_config[attr] = getattr(args, attr)
            if upload_config:
                custom_options['upload_config'] = upload_config
        
        # Add custom options to processing options
        if custom_options:
            for key, value in custom_options.items():
                options = options.with_custom_option(key, value)
        
        return options
    
    def create_operation_from_args(self, args) -> ProcessingOperation:
        """
        Create complete processing operation from command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            ProcessingOperation configured from arguments
        """
        # Determine processing mode
        mode_type = self.determine_mode_from_args(args)
        processing_mode = ProcessingModeRegistry.get_mode(mode_type)
        
        # Create specifications
        input_spec = self.create_input_spec_from_args(args)
        output_spec = self.create_output_spec_from_args(args, mode_type)
        options = self.create_processing_options_from_args(args)
        
        # Create and return operation
        operation = ProcessingOperation(
            processing_mode=processing_mode,
            input_spec=input_spec,
            output_spec=output_spec,
            options=options
        )
        
        self.logger.debug(f"Created operation: {operation.operation_id} "
                         f"(mode: {mode_type.name}, input: {input_spec.input_path})")
        
        return operation
    
    def get_mode_recommendations(self, input_path: str) -> Dict[ProcessingModeType, Dict[str, Any]]:
        """
        Get recommendations for processing modes based on input analysis.
        
        Args:
            input_path: Path to analyze
            
        Returns:
            Dictionary with mode recommendations and reasons
        """
        recommendations = {}
        
        # Analyze input path
        is_file = os.path.isfile(input_path)
        is_dir = os.path.isdir(input_path)
        is_pattern = '*' in input_path or '?' in input_path
        
        if is_file:
            # Single file - recommend single file or analysis mode
            if input_path.lower().endswith('.taf'):
                recommendations[ProcessingModeType.ANALYSIS] = {
                    'confidence': 0.9,
                    'reason': 'TAF file detected - suitable for analysis operations'
                }
            else:
                recommendations[ProcessingModeType.SINGLE_FILE] = {
                    'confidence': 0.8,
                    'reason': 'Single audio file - suitable for conversion to TAF'
                }
        
        elif is_dir:
            # Directory - recommend recursive mode
            recommendations[ProcessingModeType.RECURSIVE] = {
                'confidence': 0.9,
                'reason': 'Directory detected - suitable for recursive processing'
            }
            
            # Also suggest files-to-taf if directory contains many files
            try:
                file_count = sum(1 for f in os.listdir(input_path) 
                               if os.path.isfile(os.path.join(input_path, f)))
                if file_count > 5:
                    recommendations[ProcessingModeType.FILES_TO_TAF] = {
                        'confidence': 0.7,
                        'reason': f'Directory with {file_count} files - could use individual processing'
                    }
            except Exception:
                pass
        
        elif is_pattern:
            # Pattern - recommend files-to-taf mode
            recommendations[ProcessingModeType.FILES_TO_TAF] = {
                'confidence': 0.8,
                'reason': 'File pattern detected - suitable for batch processing'
            }
        
        return recommendations