#!/usr/bin/env python3
"""
CLI interface for processing operations.

This module provides command-line interface coordination for processing
operations, translating CLI arguments into processing requests.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from ..adapters.base_adapter import BaseInterfaceAdapter
from ..adapters.single_file_adapter import SingleFileProcessingAdapter, FileAnalysisAdapter
from ..adapters.files_to_taf_adapter import FilesToTafAdapter, RecursiveProcessingAdapter
from ...application.services.processing_application_service import ProcessingApplicationService


class CLIProcessingCoordinator:
    """
    Coordinates CLI processing requests with appropriate adapters.
    
    This class serves as the main entry point for CLI-based processing operations,
    translating command-line arguments into structured processing requests and routing
    them to the appropriate adapter (single file, files-to-TAF, analysis, or recursive).
    Handles progress tracking and error reporting for command-line workflows.
    
    Example:
        >>> from TonieToolbox.core.processing.application.services import ProcessingApplicationService
        >>> from TonieToolbox.core.utils import get_logger
        >>> import argparse
        >>> 
        >>> # Initialize coordinator with processing service
        >>> logger = get_logger(__name__)
        >>> processing_service = ProcessingApplicationService(...)
        >>> coordinator = CLIProcessingCoordinator(processing_service, logger)
        >>> 
        >>> # Single file conversion
        >>> args = argparse.Namespace(
        ...     input_filename='audiobook.mp3',
        ...     output_filename='audiobook.taf',
        ...     quality='HIGH',
        ...     progress=True
        ... )
        >>> exit_code = coordinator.execute_from_args(args)
        >>> print(f"Conversion completed: {exit_code == 0}")
        Conversion completed: True
        >>> 
        >>> # Recursive directory processing
        >>> args = argparse.Namespace(
        ...     input_directory='/music/audiobooks',
        ...     output_directory='/output',
        ...     recursive=True,
        ...     progress=True
        ... )
        >>> exit_code = coordinator.execute_from_args(args)
        >>> print(f"Processed directory: {exit_code == 0}")
        Processed directory: True
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize CLI processing coordinator.
        
        Args:
            processing_service: Application service for processing operations
            logger: Optional logger instance
        """
        self.processing_service = processing_service
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        
        # Initialize adapters
        self._adapters = {
            'single_file': SingleFileProcessingAdapter(processing_service, logger),
            'file_analysis': FileAnalysisAdapter(processing_service, logger),
            'files_to_taf': FilesToTafAdapter(processing_service, logger),
            'recursive': RecursiveProcessingAdapter(processing_service, logger)
        }
    
    def execute_from_args(self, args: argparse.Namespace) -> int:
        """
        Execute processing based on parsed command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Convert args to request dictionary
            request = self._args_to_request(args)
            
            # Determine processing type and get appropriate adapter
            adapter = self._select_adapter(request, args)
            
            if not adapter:
                self.logger.error("Could not determine appropriate processing adapter")
                return 1
            
            # Add progress tracking if requested
            if getattr(args, 'progress', False):
                self._setup_progress_tracking(adapter)
            
            # Execute processing
            return adapter.execute(request)
            
        except Exception as e:
            self.logger.error(f"CLI processing failed: {str(e)}")
            return 1
    
    def _args_to_request(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Convert command-line arguments to processing request."""
        request = {}
        
        # Input/output paths
        if hasattr(args, 'input_filename') and args.input_filename:
            request['input_path'] = args.input_filename
        elif hasattr(args, 'input_pattern') and args.input_pattern:
            request['input_pattern'] = args.input_pattern
        elif hasattr(args, 'input_directory') and args.input_directory:
            request['input_directory'] = args.input_directory
        
        # Handle output path - for recursive mode, treat as directory even if output_filename
        if hasattr(args, 'output_filename') and args.output_filename:
            # If recursive mode and output is a directory (or doesn't exist yet), treat as output_directory
            if getattr(args, 'recursive', False):
                output_path = Path(args.output_filename)
                # Treat as directory if it's an existing directory or doesn't have a file extension
                if output_path.is_dir() or (not output_path.exists() and not output_path.suffix):
                    request['output_directory'] = args.output_filename
                else:
                    request['output_path'] = args.output_filename
            else:
                request['output_path'] = args.output_filename
        elif hasattr(args, 'output_directory') and args.output_directory:
            request['output_directory'] = args.output_directory
        
        # Processing options
        if hasattr(args, 'quality'):
            request['quality'] = args.quality or 'MEDIUM'
        
        if hasattr(args, 'normalize'):
            request['normalize_audio'] = args.normalize
        
        if hasattr(args, 'fade_in'):
            request['fade_in_duration'] = args.fade_in or 0.0
        
        if hasattr(args, 'fade_out'):
            request['fade_out_duration'] = args.fade_out or 0.0
        
        if hasattr(args, 'overwrite'):
            request['overwrite_existing'] = args.overwrite
        
        if hasattr(args, 'preserve_metadata'):
            request['preserve_metadata'] = args.preserve_metadata
        
        # Mode-specific options
        if hasattr(args, 'recursive'):
            request['recursive'] = args.recursive
        
        if hasattr(args, 'workers'):
            request['parallel_workers'] = args.workers
        
        if hasattr(args, 'files_to_taf'):
            request['files_to_taf'] = args.files_to_taf
        
        if hasattr(args, 'sort'):
            request['sort_files'] = args.sort
        
        if hasattr(args, 'chapter_marks'):
            request['chapter_marks'] = args.chapter_marks
        
        if hasattr(args, 'extensions'):
            request['file_extensions'] = args.extensions
        
        if hasattr(args, 'exclude'):
            request['exclude_patterns'] = args.exclude
        
        if hasattr(args, 'continue_on_error'):
            request['continue_on_error'] = args.continue_on_error
        
        if hasattr(args, 'parallel'):
            request['parallel'] = args.parallel
        
        if hasattr(args, 'max_depth'):
            request['max_depth'] = args.max_depth
        
        if hasattr(args, 'preserve_structure'):
            request['preserve_structure'] = args.preserve_structure
        
        # Analysis options
        if hasattr(args, 'analyze_only'):
            request['analyze_only'] = args.analyze_only
        
        if hasattr(args, 'info'):
            request['info'] = args.info
        
        if hasattr(args, 'split'):
            request['split'] = args.split
            if args.split:
                request['analysis_type'] = 'split'
        
        if hasattr(args, 'extract'):
            request['extract'] = args.extract
            if args.extract:
                request['analysis_type'] = 'extract'
        
        if hasattr(args, 'compare') and args.compare:
            request['compare'] = args.compare
            request['analysis_type'] = 'compare'
        
        if hasattr(args, 'detailed_compare'):
            # detailed_compare can be either True (flag), or a file path
            if args.detailed_compare and args.detailed_compare is not True:
                # User used --detailed-compare FILE (shorthand)
                request['compare'] = args.detailed_compare
                request['analysis_type'] = 'compare'
                request['detailed_compare'] = True
            elif args.detailed_compare is True:
                # User used --detailed-compare as a flag with --compare
                request['detailed_compare'] = True
        
        if hasattr(args, 'detailed'):
            request['detailed'] = args.detailed
        
        if hasattr(args, 'output_format'):
            request['output_format'] = args.output_format
        
        # Media tag options
        if hasattr(args, 'use_media_tags'):
            request['use_media_tags'] = args.use_media_tags
        
        if hasattr(args, 'name_template'):
            request['name_template'] = args.name_template
        
        if hasattr(args, 'output_to_template'):
            request['output_to_template'] = args.output_to_template
        
        if hasattr(args, 'show_media_tags'):
            request['show_media_tags'] = args.show_media_tags
        
        # TeddyCloud upload options
        if hasattr(args, 'upload') and args.upload is not None:
            request['upload'] = args.upload
            request['upload_enabled'] = True
        
        if hasattr(args, 'assign_to_tag') and args.assign_to_tag:
            request['assign_to_tag'] = args.assign_to_tag
        
        if hasattr(args, 'create_custom_json') and args.create_custom_json:
            request['create_custom_json'] = args.create_custom_json
        
        if hasattr(args, 'path') and args.path:
            request['path'] = args.path
        
        if hasattr(args, 'include_artwork') and args.include_artwork:
            request['include_artwork'] = args.include_artwork
        
        if hasattr(args, 'special_folder') and args.special_folder:
            request['special_folder'] = args.special_folder
        
        if hasattr(args, 'auto_select_tag') and args.auto_select_tag:
            request['auto_select_tag'] = args.auto_select_tag
        
        return request
    
    def _select_adapter(self, request: Dict[str, Any], args: argparse.Namespace) -> Optional[BaseInterfaceAdapter]:
        """Select appropriate adapter based on request and args."""
        
        # Analysis mode (info, split, extract, compare, convert)
        # Check if comparison is requested via --compare or --detailed-compare with file
        has_comparison = (getattr(args, 'compare', False) or 
                         (hasattr(args, 'detailed_compare') and 
                          args.detailed_compare and args.detailed_compare is not True))
        
        if (request.get('analyze_only', False) or getattr(args, 'analyze_only', False) or
            getattr(args, 'info', False) or getattr(args, 'split', False) or
            getattr(args, 'extract', False) or
            has_comparison or getattr(args, 'convert_to_separate_mp3', False) or
            getattr(args, 'convert_to_single_mp3', False)):
            return self._adapters['file_analysis']
        
        # Recursive processing - check for both input_directory and input_path (if it's a directory)
        if request.get('recursive', False) and (
            'input_directory' in request or 
            ('input_path' in request and Path(request['input_path']).is_dir())
        ):
            # Convert input_path to input_directory for recursive adapter
            if 'input_path' in request and 'input_directory' not in request:
                request['input_directory'] = request['input_path']
                del request['input_path']
            return self._adapters['recursive']
        
        # Files to TAF (multiple files to single output)
        if ('input_pattern' in request or 
            ('input_path' in request and ('*' in request['input_path'] or Path(request['input_path']).is_dir()))):
            # Convert input_path to input_pattern if needed for adapter compatibility
            if 'input_path' in request and 'input_pattern' not in request:
                request['input_pattern'] = request['input_path']
                # Keep original input_path for logging purposes
                request['original_input_path'] = request['input_path']
                # Remove input_path to avoid confusion in adapter
                del request['input_path']
            return self._adapters['files_to_taf']
        
        # Single file processing (default)
        if 'input_path' in request:
            return self._adapters['single_file']
        
        # Could not determine adapter
        return None
    
    def _setup_progress_tracking(self, adapter):
        """Setup progress tracking for adapter if supported."""
        if hasattr(adapter, 'add_progress_callback'):
            adapter.add_progress_callback(self._print_progress)
    
    def _print_progress(self, progress_info: Dict[str, Any]):
        """Print progress information to console."""
        operation = progress_info.get('operation', 'Processing')
        progress = progress_info.get('progress', 0.0)
        details = progress_info.get('details', '')
        
        # Calculate progress bar
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Print progress (overwrite previous line)
        print(f'\r{operation}: |{bar}| {progress:.1%} {details}', end='', flush=True)
        
        # Print newline when complete
        if progress >= 1.0:
            print()


class CLIArgumentValidator:
    """
    Validates command-line arguments for processing operations.
    
    Provides validation logic for CLI arguments to ensure they are
    appropriate for the requested processing operations.
    """
    
    @staticmethod
    def validate_processing_args(args: argparse.Namespace) -> tuple[bool, str]:
        """
        Validate processing arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        
        # Check for required input
        input_sources = [
            getattr(args, 'input_filename', None),
            getattr(args, 'input_pattern', None),
            getattr(args, 'input_directory', None)
        ]
        
        if not any(input_sources):
            return False, "No input source specified (input_filename, input_pattern, or input_directory required)"
        
        # Validate input exists
        for source in input_sources:
            if source and not Path(source).exists() and '*' not in source and '?' not in source:
                return False, f"Input path does not exist: {source}"
        
        # Validate output paths if specified
        if hasattr(args, 'output_filename') and args.output_filename:
            output_path = Path(args.output_filename)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create output directory: {str(e)}"
        
        # Validate numeric parameters
        numeric_validations = [
            ('fade_in', 0.0, 60.0),
            ('fade_out', 0.0, 60.0),
            ('max_depth', 1, 100)
        ]
        
        for param_name, min_val, max_val in numeric_validations:
            if hasattr(args, param_name):
                param_value = getattr(args, param_name)
                if param_value is not None:
                    try:
                        float_value = float(param_value)
                        if not (min_val <= float_value <= max_val):
                            return False, f"{param_name} must be between {min_val} and {max_val}"
                    except ValueError:
                        return False, f"{param_name} must be a valid number"
        
        # Validate quality setting
        if hasattr(args, 'quality') and args.quality:
            valid_qualities = ['LOW', 'MEDIUM', 'HIGH', 'LOSSLESS']
            if args.quality.upper() not in valid_qualities:
                return False, f"Quality must be one of: {', '.join(valid_qualities)}"
        
        # Validate sort method
        if hasattr(args, 'sort') and args.sort:
            valid_sorts = ['name', 'date', 'size', 'path', 'none']
            if args.sort.lower() not in valid_sorts:
                return False, f"Sort method must be one of: {', '.join(valid_sorts)}"
        
        # Validate output format for analysis
        if hasattr(args, 'output_format') and args.output_format:
            valid_formats = ['text', 'json']
            if args.output_format.lower() not in valid_formats:
                return False, f"Output format must be one of: {', '.join(valid_formats)}"
        
        return True, ""
    
    @staticmethod
    def validate_mode_compatibility(args: argparse.Namespace) -> tuple[bool, str]:
        """
        Validate that arguments are compatible with each other.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        
        # Analysis mode compatibility
        if getattr(args, 'analyze_only', False):
            if not hasattr(args, 'input_filename') or not args.input_filename:
                return False, "Analysis mode requires a single input file"
            
            if hasattr(args, 'output_filename') and args.output_filename:
                return False, "Analysis mode does not support output files"
        
        # Recursive mode compatibility
        if getattr(args, 'recursive', False):
            if not (hasattr(args, 'input_directory') and args.input_directory):
                return False, "Recursive mode requires input_directory"
            
            if not Path(args.input_directory).is_dir():
                return False, f"Recursive mode input must be a directory: {args.input_directory}"
        
        # Files to TAF compatibility
        if hasattr(args, 'chapter_marks') and args.chapter_marks:
            # Chapter marks only make sense for multiple file operations
            single_file = (hasattr(args, 'input_filename') and args.input_filename and 
                          Path(args.input_filename).is_file())
            if single_file:
                return False, "Chapter marks option only applies to multi-file operations"
        
        return True, ""


def create_cli_coordinator(processing_service: ProcessingApplicationService,
                          logger: Optional[logging.Logger] = None) -> CLIProcessingCoordinator:
    """
    Factory function to create CLI processing coordinator.
    
    Args:
        processing_service: Application service for processing operations
        logger: Optional logger instance
        
    Returns:
        Configured CLI processing coordinator
    """
    return CLIProcessingCoordinator(processing_service, logger)