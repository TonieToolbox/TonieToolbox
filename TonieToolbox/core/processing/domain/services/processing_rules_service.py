#!/usr/bin/env python3
"""
Processing rules domain service.

This module contains business rules and validation logic for processing operations.
All business logic related to what constitutes valid processing operations
is centralized here.
"""

from typing import List, Optional, Dict, Any, Set
from pathlib import Path
import os

from ..models.processing_operation import ProcessingOperation
from ..value_objects.processing_mode import ProcessingModeType
from ..value_objects.input_specification import InputSpecification, InputType, ContentType
from ..value_objects.output_specification import OutputSpecification, OutputFormat, OutputMode
from ..value_objects.processing_options import ProcessingOptions
from ..exceptions import (
    ValidationError, 
    ProcessingConstraintViolationError, 
    UnsupportedOperationError,
    InvalidProcessingModeError
)


class ProcessingRulesService:
    """
    Domain service containing business rules for processing operations.
    
    This service centralizes all business logic related to processing validation,
    constraints, and business rules that don't belong in individual domain objects.
    """
    
    # Business constants
    MAX_BATCH_SIZE = 1000
    MAX_FILE_SIZE_MB = 500
    MAX_TOTAL_SIZE_GB = 10
    
    SUPPORTED_AUDIO_EXTENSIONS = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus'}
    SUPPORTED_ANALYSIS_OPERATIONS = {'info', 'split', 'extract', 'compare', 'convert_to_separate_mp3', 
                                   'convert_to_single_mp3', 'play'}
    
    def validate_operation_business_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """
        Validate business rules for a processing operation.
        
        Args:
            operation: The processing operation to validate
            
        Returns:
            List of validation errors, empty if all rules pass
        """
        errors = []
        
        # Validate file count limits
        errors.extend(self._validate_file_count_limits(operation))
        
        # Validate file size limits
        errors.extend(self._validate_file_size_limits(operation))
        
        # Validate mode-specific rules
        errors.extend(self._validate_mode_specific_rules(operation))
        
        # Validate input/output compatibility
        errors.extend(self._validate_input_output_compatibility(operation))
        
        # Validate upload constraints
        errors.extend(self._validate_upload_constraints(operation))
        
        return errors
    
    def _validate_file_count_limits(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate file count against business limits."""
        errors = []
        
        estimated_count = operation.estimated_file_count
        
        if estimated_count > self.MAX_BATCH_SIZE:
            errors.append(ValidationError(
                "file_count",
                f"Operation would process {estimated_count} files, "
                f"which exceeds maximum batch size of {self.MAX_BATCH_SIZE}",
                estimated_count
            ))
        
        # Mode-specific limits
        if operation.processing_mode.mode_type == ProcessingModeType.SINGLE_FILE:
            if estimated_count > 50:  # Reasonable limit for combining files
                errors.append(ValidationError(
                    "file_count",
                    f"Single file mode with {estimated_count} input files may cause memory issues",
                    estimated_count
                ))
        
        return errors
    
    def _validate_file_size_limits(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate file sizes against business limits."""
        errors = []
        
        try:
            files = operation.input_spec.resolve_files()
            total_size_bytes = 0
            
            for file_path in files:
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_size_mb = file_size / (1024 * 1024)
                    
                    # Check individual file size
                    if file_size_mb > self.MAX_FILE_SIZE_MB:
                        errors.append(ValidationError(
                            "file_size",
                            f"File {file_path.name} ({file_size_mb:.1f}MB) exceeds "
                            f"maximum size of {self.MAX_FILE_SIZE_MB}MB",
                            file_size_mb
                        ))
                    
                    total_size_bytes += file_size
            
            # Check total size
            total_size_gb = total_size_bytes / (1024 * 1024 * 1024)
            if total_size_gb > self.MAX_TOTAL_SIZE_GB:
                errors.append(ValidationError(
                    "total_size",
                    f"Total input size ({total_size_gb:.1f}GB) exceeds "
                    f"maximum of {self.MAX_TOTAL_SIZE_GB}GB",
                    total_size_gb
                ))
        
        except Exception as e:
            errors.append(ValidationError(
                "file_access",
                f"Could not validate file sizes: {str(e)}",
                str(e)
            ))
        
        return errors
    
    def _validate_mode_specific_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate rules specific to each processing mode."""
        errors = []
        mode_type = operation.processing_mode.mode_type
        
        if mode_type == ProcessingModeType.ANALYSIS:
            errors.extend(self._validate_analysis_mode_rules(operation))
        
        elif mode_type == ProcessingModeType.RECURSIVE:
            errors.extend(self._validate_recursive_mode_rules(operation))
        
        elif mode_type == ProcessingModeType.FILES_TO_TAF:
            errors.extend(self._validate_files_to_taf_rules(operation))
        
        elif mode_type == ProcessingModeType.SINGLE_FILE:
            errors.extend(self._validate_single_file_rules(operation))
        
        return errors
    
    def _validate_analysis_mode_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate rules specific to analysis mode."""
        errors = []
        
        # Analysis must work with TAF files, except for info operations which can analyze any file
        from ..value_objects.output_specification import OutputFormat
        is_info_operation = (operation.output_spec and 
                           operation.output_spec.output_format == OutputFormat.INFO)
        
        if operation.input_spec.content_type != ContentType.TAF and not is_info_operation:
            errors.append(ValidationError(
                "input_content",
                "Analysis mode requires TAF files as input",
                operation.input_spec.content_type.name
            ))
        
        # Validate analysis operation type
        analysis_type = operation.options.get_custom_option('analysis_type')
        if analysis_type and analysis_type not in self.SUPPORTED_ANALYSIS_OPERATIONS:
            errors.append(ValidationError(
                "analysis_type",
                f"Unsupported analysis operation: {analysis_type}",
                analysis_type
            ))
        
        # Info and play operations should not have file output
        if analysis_type in ['info', 'play']:
            if (operation.output_spec.output_mode != OutputMode.CONSOLE_ONLY and
                operation.output_spec.output_path):
                errors.append(ValidationError(
                    "output_mode",
                    f"Analysis operation '{analysis_type}' should output to console only",
                    analysis_type
                ))
        
        return errors
    
    def _validate_recursive_mode_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate rules specific to recursive mode."""
        errors = []
        
        # Recursive mode requires directory input
        if operation.input_spec.input_type != InputType.DIRECTORY:
            errors.append(ValidationError(
                "input_type",
                "Recursive mode requires directory input",
                operation.input_spec.input_type.name
            ))
        
        # Output should support multiple files
        if operation.output_spec.output_mode != OutputMode.MULTIPLE_FILES:
            errors.append(ValidationError(
                "output_mode",
                "Recursive mode requires multiple file output mode",
                operation.output_spec.output_mode.name
            ))
        
        return errors
    
    def _validate_files_to_taf_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate rules specific to files-to-TAF mode."""
        errors = []
        
        # Should produce TAF files
        if operation.output_spec.output_format != OutputFormat.TAF:
            errors.append(ValidationError(
                "output_format",
                "Files-to-TAF mode must produce TAF format output",
                operation.output_spec.output_format.name
            ))
        
        # Should produce multiple files
        if operation.output_spec.output_mode != OutputMode.MULTIPLE_FILES:
            errors.append(ValidationError(
                "output_mode",
                "Files-to-TAF mode requires multiple file output mode",
                operation.output_spec.output_mode.name
            ))
        
        return errors
    
    def _validate_single_file_rules(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate rules specific to single file mode."""
        errors = []
        
        # Should produce single file output
        if operation.output_spec.output_mode == OutputMode.MULTIPLE_FILES:
            # This might be intentional for some cases, so just warn
            pass
        
        return errors
    
    def _validate_input_output_compatibility(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate compatibility between input and output specifications."""
        errors = []
        
        # Check audio file extensions for non-analysis modes
        if operation.processing_mode.mode_type != ProcessingModeType.ANALYSIS:
            try:
                files = operation.input_spec.resolve_files()
                unsupported_files = []
                
                for file_path in files:
                    if file_path.suffix.lower() not in self.SUPPORTED_AUDIO_EXTENSIONS:
                        unsupported_files.append(file_path.name)
                
                if unsupported_files:
                    errors.append(ValidationError(
                        "file_extensions",
                        f"Unsupported file types: {', '.join(unsupported_files[:5])}",
                        unsupported_files
                    ))
            
            except Exception:
                # Skip validation if files can't be resolved
                pass
        
        return errors
    
    def _validate_upload_constraints(self, operation: ProcessingOperation) -> List[ValidationError]:
        """Validate upload-related constraints."""
        errors = []
        
        if not operation.options.upload_enabled:
            return errors
        
        # Upload requires TAF output format
        if operation.output_spec.output_format != OutputFormat.TAF:
            errors.append(ValidationError(
                "upload_format",
                "Upload operations require TAF output format",
                operation.output_spec.output_format.name
            ))
        
        # Upload should not be used with console-only output
        if operation.output_spec.output_mode == OutputMode.CONSOLE_ONLY:
            errors.append(ValidationError(
                "upload_output",
                "Upload operations require file output, not console-only",
                "console_only"
            ))
        
        return errors
    
    def can_operation_be_parallelized(self, operation: ProcessingOperation) -> bool:
        """
        Determine if operation can be safely parallelized.
        
        Args:
            operation: Processing operation to check
            
        Returns:
            True if operation supports parallel processing
        """
        # Analysis operations typically can't be parallelized (especially play)
        if operation.processing_mode.mode_type == ProcessingModeType.ANALYSIS:
            analysis_type = operation.options.get_custom_option('analysis_type')
            return analysis_type not in ['play', 'info']
        
        # Single file operations that combine files can't be parallelized
        if (operation.processing_mode.mode_type == ProcessingModeType.SINGLE_FILE and
            operation.estimated_file_count > 1):
            return False
        
        # Upload operations need coordination
        if operation.options.upload_enabled:
            return operation.options.max_parallel_jobs <= 2
        
        return True
    
    def get_recommended_parallel_jobs(self, operation: ProcessingOperation) -> int:
        """
        Get recommended number of parallel jobs for an operation.
        
        Args:
            operation: Processing operation
            
        Returns:
            Recommended number of parallel jobs (1 for sequential)
        """
        if not self.can_operation_be_parallelized(operation):
            return 1
        
        file_count = operation.estimated_file_count
        
        # For small batches, sequential is often faster
        if file_count <= 3:
            return 1
        
        # Scale with file count but cap at reasonable limit
        recommended = min(file_count // 4, 8)
        
        # Respect user's maximum setting
        user_max = operation.options.max_parallel_jobs
        
        return min(recommended, user_max)
    
    def validate_operation_constraints(self, operation: ProcessingOperation) -> None:
        """
        Validate operation against all business constraints.
        Raises exceptions for constraint violations.
        
        Args:
            operation: Processing operation to validate
            
        Raises:
            ProcessingConstraintViolationError: If constraints are violated
        """
        errors = self.validate_operation_business_rules(operation)
        
        if errors:
            # Group errors by severity
            critical_errors = [e for e in errors if e.field in ['file_count', 'total_size']]
            
            if critical_errors:
                raise ProcessingConstraintViolationError(
                    "critical_limits",
                    f"Operation violates critical constraints: {'; '.join(str(e) for e in critical_errors)}"
                )
    
    def suggest_operation_optimizations(self, operation: ProcessingOperation) -> List[str]:
        """
        Suggest optimizations for the processing operation.
        
        Args:
            operation: Processing operation to analyze
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Parallel processing suggestion
        if (self.can_operation_be_parallelized(operation) and 
            operation.options.max_parallel_jobs == 1 and
            operation.estimated_file_count > 5):
            recommended_jobs = self.get_recommended_parallel_jobs(operation)
            suggestions.append(
                f"Consider enabling parallel processing with {recommended_jobs} jobs "
                f"for {operation.estimated_file_count} files"
            )
        
        # Quality optimization
        if (operation.estimated_file_count > 20 and
            operation.options.quality_level.name == 'HIGH'):
            suggestions.append(
                "Consider using MEDIUM quality for batch operations to improve speed"
            )
        
        # Output directory optimization
        if (operation.processing_mode.produces_multiple_outputs() and
            not operation.output_spec.preserve_structure and
            operation.estimated_file_count > 50):
            suggestions.append(
                "Consider enabling preserve_structure for better organization of many output files"
            )
        
        return suggestions