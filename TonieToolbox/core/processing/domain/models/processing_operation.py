#!/usr/bin/env python3
"""
Processing operation domain model.

This module defines the core ProcessingOperation domain model that represents
a complete processing workflow in the system.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import uuid

from ..value_objects.processing_mode import ProcessingMode, ProcessingModeType
from ..value_objects.input_specification import InputSpecification
from ..value_objects.output_specification import OutputSpecification
from ..value_objects.processing_options import ProcessingOptions
from ..exceptions import ValidationError, ValidationErrorCollection, ProcessingOperationError


@dataclass
class ProcessingOperation:
    """
    Core domain model representing a complete processing operation.
    
    This is the central aggregate that encapsulates all information needed
    to perform a processing operation while maintaining business invariants.
    """
    
    operation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    processing_mode: ProcessingMode = field(default=None)
    input_spec: InputSpecification = field(default=None)
    output_spec: OutputSpecification = field(default=None)
    options: ProcessingOptions = field(default_factory=ProcessingOptions.default)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # State tracking
    is_validated: bool = False
    validation_errors: List[ValidationError] = field(default_factory=list)
    
    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize and validate the operation after creation."""
        # Ensure required fields are set
        if not self.processing_mode:
            raise ProcessingOperationError("Processing mode is required")
        
        if not self.input_spec:
            raise ProcessingOperationError("Input specification is required")
        
        if not self.output_spec:
            raise ProcessingOperationError("Output specification is required")
        
        # Validate compatibility between components
        self._validate_compatibility()
    
    def _validate_compatibility(self):
        """Validate compatibility between processing mode, input, and output specifications."""
        # Check if input type matches processing mode requirements
        # Allow info operations on any file type
        from ..value_objects.output_specification import OutputFormat
        is_info_operation = (self.output_spec and 
                           self.output_spec.output_format == OutputFormat.INFO)
        
        if self.processing_mode.requires_taf_input() and not is_info_operation:
            from ..value_objects.input_specification import ContentType
            if self.input_spec.content_type != ContentType.TAF:
                raise ProcessingOperationError(
                    f"Processing mode {self.processing_mode.name} requires TAF input files"
                )
        
        # Check batch processing compatibility
        if self.processing_mode.supports_batch:
            if self.input_spec.max_files == 1 and self.input_spec.min_files == 1:
                # Single file input with batch mode might be intentional
                pass
        
        # Check output mode compatibility
        if (self.processing_mode.produces_multiple_outputs() and 
            self.output_spec.output_mode.name == 'SINGLE_FILE'):
            raise ProcessingOperationError(
                f"Processing mode {self.processing_mode.name} produces multiple outputs "
                f"but output specification expects single file"
            )
    
    @classmethod
    def create_for_single_file_conversion(cls, input_file: str, output_file: str,
                                        options: Optional[ProcessingOptions] = None) -> 'ProcessingOperation':
        """Create operation for single file to TAF conversion."""
        from ..value_objects.processing_mode import SINGLE_FILE_MODE
        from ..value_objects.input_specification import ContentType
        
        return cls(
            processing_mode=SINGLE_FILE_MODE,
            input_spec=InputSpecification.for_single_file(input_file, ContentType.AUDIO),
            output_spec=OutputSpecification.for_single_taf(output_file),
            options=options or ProcessingOptions.default()
        )
    
    @classmethod
    def create_for_files_to_taf(cls, input_pattern: str, output_dir: str,
                              options: Optional[ProcessingOptions] = None) -> 'ProcessingOperation':
        """Create operation for converting multiple files to separate TAF files."""
        from ..value_objects.processing_mode import FILES_TO_TAF_MODE
        from ..value_objects.input_specification import ContentType
        
        return cls(
            processing_mode=FILES_TO_TAF_MODE,
            input_spec=InputSpecification.for_multiple_files(input_pattern, ContentType.AUDIO),
            output_spec=OutputSpecification.for_multiple_taf(output_dir),
            options=options or ProcessingOptions.for_batch_processing()
        )
    
    @classmethod
    def create_for_recursive_processing(cls, input_dir: str, output_dir: str,
                                      options: Optional[ProcessingOptions] = None) -> 'ProcessingOperation':
        """Create operation for recursive directory processing."""
        from ..value_objects.processing_mode import RECURSIVE_MODE
        from ..value_objects.input_specification import ContentType
        
        return cls(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(input_dir, ContentType.AUDIO),
            output_spec=OutputSpecification.for_multiple_taf(output_dir, preserve_structure=True),
            options=options or ProcessingOptions.for_batch_processing()
        )
    
    @classmethod
    def create_for_analysis(cls, input_file: str, analysis_type: str,
                          options: Optional[ProcessingOptions] = None) -> 'ProcessingOperation':
        """Create operation for file analysis."""
        from ..value_objects.processing_mode import ANALYSIS_MODE
        from ..value_objects.input_specification import ContentType
        
        analysis_options = options or ProcessingOptions.for_analysis_only()
        analysis_options = analysis_options.with_custom_option('analysis_type', analysis_type)
        
        return cls(
            processing_mode=ANALYSIS_MODE,
            input_spec=InputSpecification.for_single_file(input_file, ContentType.TAF),
            output_spec=OutputSpecification.for_info_display(),
            options=analysis_options
        )
    
    def validate(self) -> bool:
        """
        Validate the entire operation and collect any validation errors.
        
        Returns:
            True if validation passes, False otherwise.
            Errors are stored in validation_errors property.
        """
        self.validation_errors.clear()
        
        try:
            # Validate input specification
            input_errors = self.input_spec.validate_requirements()
            self.validation_errors.extend(input_errors)
            
            # Validate output specification
            output_errors = self.output_spec.validate_output_requirements()
            self.validation_errors.extend(output_errors)
            
            # Validate business rules
            business_errors = self._validate_business_rules()
            self.validation_errors.extend(business_errors)
            
            self.is_validated = len(self.validation_errors) == 0
            return self.is_validated
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                "operation",
                f"Validation failed with error: {str(e)}",
                str(e)
            ))
            self.is_validated = False
            return False
    
    def _validate_business_rules(self) -> List[ValidationError]:
        """Validate business-specific rules for the operation."""
        errors = []
        
        # Rule: Analysis operations should not have file output paths
        if (self.processing_mode.mode_type == ProcessingModeType.ANALYSIS and
            self.output_spec.output_path and 
            self.options.get_custom_option('analysis_type') in ['info', 'play']):
            errors.append(ValidationError(
                "output_spec",
                "Analysis operations (info, play) should not specify output files",
                self.output_spec.output_path
            ))
        
        # Rule: Upload operations require network-accessible processing
        if (self.options.upload_enabled and
            not self.processing_mode.supports_upload):
            errors.append(ValidationError(
                "upload",
                f"Processing mode {self.processing_mode.name} does not support upload operations",
                self.processing_mode.name
            ))
        
        # Rule: Batch operations with single file limits
        if (self.processing_mode.supports_batch and 
            self.input_spec.min_files > 100):  # Reasonable batch limit
            errors.append(ValidationError(
                "batch_size",
                f"Batch processing with {self.input_spec.min_files} files may exceed system limits",
                self.input_spec.min_files
            ))
        
        return errors
    
    def can_execute(self) -> bool:
        """
        Check if operation can be executed.
        
        Returns:
            True if operation is ready for execution.
        """
        if not self.is_validated:
            self.validate()
        
        return self.is_validated and len(self.validation_errors) == 0
    
    def get_validation_summary(self) -> Optional[str]:
        """Get summary of validation errors if any exist."""
        if not self.validation_errors:
            return None
        
        error_messages = [f"- {error.field}: {error}" for error in self.validation_errors]
        return f"Validation failed with {len(self.validation_errors)} errors:\n" + "\n".join(error_messages)
    
    def mark_started(self):
        """Mark operation as started."""
        self.started_at = datetime.now()
    
    def mark_completed(self):
        """Mark operation as completed."""
        self.completed_at = datetime.now()
    
    def get_duration(self) -> Optional[float]:
        """Get operation duration in seconds if completed."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    def add_context(self, key: str, value: Any):
        """Add contextual information to the operation."""
        self.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get contextual information from the operation."""
        return self.context.get(key, default)
    
    @property
    def description(self) -> str:
        """Get human-readable description of the operation."""
        return (f"{self.processing_mode.description} from {self.input_spec.description} "
                f"to {self.output_spec.description}")
    
    @property
    def is_batch_operation(self) -> bool:
        """Check if this is a batch processing operation."""
        return (self.processing_mode.supports_batch and 
                (self.input_spec.min_files > 1 or self.input_spec.max_files != 1))
    
    @property
    def estimated_file_count(self) -> int:
        """Get estimated number of files to be processed."""
        try:
            files = self.input_spec.resolve_files()
            return len(files)
        except Exception:
            return self.input_spec.min_files
    
    def __str__(self) -> str:
        """String representation of the operation."""
        return f"ProcessingOperation({self.operation_id[:8]}, {self.processing_mode.name})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"ProcessingOperation(id={self.operation_id}, "
                f"mode={self.processing_mode.name}, "
                f"input={self.input_spec.input_path}, "
                f"output={self.output_spec.output_path}, "
                f"validated={self.is_validated})")