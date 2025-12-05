#!/usr/bin/env python3
"""
Base interface adapter for processing operations.

This module provides the foundation for interface adapters that coordinate
between external interfaces (CLI, GUI) and application services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from ....events import get_event_bus
    from ...application.services.processing_application_service import ProcessingApplicationService
    from ...domain import ProcessingMode, ProcessingOptions
    from ...domain.value_objects.processing_mode import SINGLE_FILE_MODE, RECURSIVE_MODE, FILES_TO_TAF_MODE, ANALYSIS_MODE
except ImportError:
    # Fallback during import updates
    get_event_bus = None
    ProcessingApplicationService = Any
    ProcessingMode = Any
    ProcessingOptions = Any
    SINGLE_FILE_MODE = None
    RECURSIVE_MODE = None 
    FILES_TO_TAF_MODE = None
    ANALYSIS_MODE = None


class BaseInterfaceAdapter(ABC):
    """
    Base class for interface adapters.
    
    Interface adapters coordinate between external interfaces (CLI, GUI)
    and application services, translating external requests into domain operations.
    """
    
    def __init__(self, processing_service: ProcessingApplicationService,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize interface adapter.
        
        Args:
            processing_service: Application service for processing operations
            logger: Optional logger instance
        """
        self.processing_service = processing_service
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.event_bus = get_event_bus()
    
    @abstractmethod
    def execute(self, request: Dict[str, Any]) -> int:
        """
        Execute processing request from external interface.
        
        Args:
            request: Processing request from external interface
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass
    
    def _translate_request_to_options(self, request: Dict[str, Any]) -> ProcessingOptions:
        """
        Translate external request to domain ProcessingOptions.
        
        Args:
            request: External processing request
            
        Returns:
            ProcessingOptions configured from request
        """
        try:
            # Extract common options from request  
            quality_level = self._parse_quality_level(request.get('quality', 'MEDIUM'))
            compression_mode = self._parse_compression_mode(request.get('compression', 'OPTIMAL'))
            
            # Map request parameters to valid ProcessingOptions parameters
            options = ProcessingOptions(
                quality_level=quality_level,
                compression_mode=compression_mode,
                normalize_audio=request.get('normalize_audio', False),
                fade_in_duration=float(request.get('fade_in_duration', 0.0)),
                fade_out_duration=float(request.get('fade_out_duration', 0.0)),
                preserve_timestamps=request.get('preserve_timestamps', True),
                preserve_metadata=request.get('preserve_metadata', True),
                create_backup=request.get('create_backup', False),
                cleanup_temp_files=request.get('cleanup_temp_files', True),
                continue_on_error=request.get('continue_on_error', True),
                max_parallel_jobs=int(request.get('max_parallel_jobs', 1)),
                timeout_seconds=int(request.get('timeout_seconds', 300)) if request.get('timeout_seconds') else None,
                upload_enabled=request.get('upload_enabled', False),
                upload_after_processing=request.get('upload_after_processing', True),
                validate_input=request.get('validate_input', True),
                validate_output=request.get('validate_output', True),
                strict_validation=request.get('strict_validation', False),
                show_progress=request.get('show_progress', True),
                verbose_logging=request.get('verbose_logging', False),
                custom_options=request.get('custom_options', {})
            )
            
            self.logger.debug(f"Translated request to ProcessingOptions: {options}")
            return options
            
        except Exception as e:
            self.logger.error(f"Failed to translate request to options: {str(e)}")
            # Return default options on error
            return ProcessingOptions()
    
    def _parse_quality_level(self, quality_str: str):
        """Parse quality level string to enum."""
        try:
            from ...domain.value_objects.processing_options import QualityLevel
        except ImportError:
            # Fallback during transition
            return quality_str
        
        quality_map = {
            'low': QualityLevel.LOW,
            'medium': QualityLevel.MEDIUM,
            'high': QualityLevel.HIGH,
            'lossless': QualityLevel.LOSSLESS
        }
        
        return quality_map.get(quality_str.lower(), QualityLevel.MEDIUM)
    
    def _parse_compression_mode(self, compression_str: str):
        """Parse compression mode string to enum."""
        try:
            from ...domain.value_objects.processing_options import CompressionMode
        except ImportError:
            # Fallback during transition
            return compression_str
        
        compression_map = {
            'none': CompressionMode.NONE,
            'fast': CompressionMode.FAST,
            'optimal': CompressionMode.OPTIMAL,
            'maximum': CompressionMode.MAXIMUM
        }
        
        return compression_map.get(compression_str.lower(), CompressionMode.OPTIMAL)
    
    def _determine_processing_mode(self, request: Dict[str, Any]):
        """
        Determine processing mode from request.
        
        Args:
            request: External processing request
            
        Returns:
            Appropriate ProcessingMode
        """
        try:
            input_path = Path(request.get('input_path', ''))
            output_path = Path(request.get('output_path', '')) if request.get('output_path') else None
            
            # Explicit mode specification
            if 'mode' in request:
                mode_str = request['mode'].upper()
                try:
                    return ProcessingMode[mode_str]
                except KeyError:
                    self.logger.warning(f"Unknown processing mode '{mode_str}', using auto-detection")
            
            # Auto-detect mode based on inputs
            if not input_path.exists():
                return SINGLE_FILE_MODE  # Default
            
            if input_path.is_file():
                # Check if it's an analysis request
                if request.get('analyze_only', False) or request.get('info', False):
                    return ANALYSIS_MODE
                
                # Check output format to determine conversion type
                if output_path and output_path.suffix.lower() == '.taf':
                    return SINGLE_FILE_MODE  # Convert to TAF
                elif output_path and output_path.suffix.lower() != '.taf':
                    return ANALYSIS_MODE  # Convert from TAF or analyze
                else:
                    return SINGLE_FILE_MODE  # Default for files
            
            elif input_path.is_dir():
                # Directory processing
                if request.get('recursive', False):
                    return RECURSIVE_MODE
                else:
                    return FILES_TO_TAF_MODE
            
            else:
                # Pattern or list file
                if str(input_path).endswith('.lst'):
                    return ProcessingMode.LIST_FILE
                else:
                    return ProcessingMode.FILES_TO_TAF
                    
        except Exception as e:
            self.logger.error(f"Failed to determine processing mode: {str(e)}")
            return SINGLE_FILE_MODE
    
    def _validate_request(self, request: Dict[str, Any]) -> bool:
        """
        Validate external processing request.
        
        Args:
            request: External processing request
            
        Returns:
            True if request is valid
        """
        try:
            # Check required fields
            if 'input_path' not in request:
                self.logger.error("Missing required field: input_path")
                return False
            
            input_path = Path(request['input_path'])
            
            # Validate input path exists (unless it's a pattern)
            if not ('*' in str(input_path) or '?' in str(input_path)):
                if not input_path.exists():
                    self.logger.error(f"Input path does not exist: {input_path}")
                    return False
            
            # Validate output path if provided
            if 'output_path' in request:
                output_path = Path(request['output_path'])
                
                # Check if we can write to output directory
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.logger.error(f"Cannot create output directory: {str(e)}")
                    return False
            
            # Validate numeric parameters
            numeric_params = ['fade_in_duration', 'fade_out_duration', 'timeout_seconds']
            for param in numeric_params:
                if param in request:
                    try:
                        float(request[param])
                    except ValueError:
                        self.logger.error(f"Invalid numeric value for {param}: {request[param]}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Request validation failed: {str(e)}")
            return False
    
    def _handle_processing_error(self, error: Exception, request: Dict[str, Any]) -> int:
        """
        Handle processing errors and return appropriate exit code.
        
        Args:
            error: The processing error that occurred
            request: The original processing request
            
        Returns:
            Non-zero exit code indicating error type
        """
        error_msg = str(error)
        self.logger.error(f"Processing failed: {error_msg}")
        
        # Classify errors and return appropriate exit codes
        if "not found" in error_msg.lower():
            return 2  # File not found
        elif "permission" in error_msg.lower():
            return 3  # Permission error
        elif "timeout" in error_msg.lower():
            return 4  # Timeout error
        elif "validation" in error_msg.lower():
            return 5  # Validation error
        elif "format" in error_msg.lower() or "codec" in error_msg.lower():
            return 6  # Format/codec error
        else:
            return 1  # General error
    
    def _log_processing_summary(self, result: Any, request: Dict[str, Any]):
        """
        Log summary of processing operation.
        
        Args:
            result: Processing result
            request: Original processing request
        """
        try:
            # Try multiple path keys for better logging
            input_path = (request.get('input_path') or 
                         request.get('original_input_path') or 
                         request.get('input_pattern') or 
                         request.get('input_directory') or 
                         'unknown')
            processing_mode = self._determine_processing_mode(request)
            
            if hasattr(result, 'is_successful') and result.is_successful:
                self.logger.info(f"Processing completed successfully: {input_path} (mode: {processing_mode.name})")
                
                if hasattr(result, 'output_files'):
                    self.logger.info(f"Generated {len(result.output_files)} output files")
                    for output_file in result.output_files[:3]:  # Log first 3 files
                        self.logger.debug(f"Output: {output_file}")
                    if len(result.output_files) > 3:
                        self.logger.debug(f"... and {len(result.output_files) - 3} more files")
            else:
                self.logger.warning(f"Processing completed with issues: {input_path}")
                
                if hasattr(result, 'errors') and result.errors:
                    for error in result.errors[:3]:  # Log first 3 errors
                        self.logger.error(f"Error: {error}")
                        
        except Exception as e:
            self.logger.debug(f"Failed to log processing summary: {str(e)}")


class ProgressTrackingMixin:
    """
    Mixin for adapters that need progress tracking capabilities.
    
    Provides methods for tracking and reporting processing progress
    to external interfaces.
    """
    
    def __init__(self):
        """Initialize progress tracking."""
        self._progress_callbacks = []
        self._current_operation = ""
        self._current_progress = 0.0
    
    def add_progress_callback(self, callback):
        """Add progress callback function."""
        self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback):
        """Remove progress callback function."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def _update_progress(self, operation: str, progress: float, details: str = ""):
        """Update progress and notify callbacks."""
        self._current_operation = operation
        self._current_progress = progress
        
        progress_info = {
            'operation': operation,
            'progress': progress,
            'details': details
        }
        
        for callback in self._progress_callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                if hasattr(self, 'logger'):
                    self.logger.debug(f"Progress callback error: {str(e)}")
    
    def get_current_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        return {
            'operation': self._current_operation,
            'progress': self._current_progress
        }