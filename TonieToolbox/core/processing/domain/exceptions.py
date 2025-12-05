#!/usr/bin/env python3
"""
Domain exceptions for processing operations.

This module defines domain-specific exceptions that represent business rule violations
and domain-level errors in the processing system.
"""

from typing import List, Optional, Any


class ProcessingDomainError(Exception):
    """Base exception for processing domain errors.
    
    This is the root exception for all domain-level processing errors. Provides
    structured error information with error codes and additional details for
    better error handling and debugging.
    
    Example:
        Raising a domain error with error code and details::
        
            raise ProcessingDomainError(
                "Failed to process audio file",
                error_code="AUDIO_PROCESSING_FAILED",
                details={'file': 'input.mp3', 'format': 'unsupported'}
            )
        
        Catching and handling domain errors::
        
            try:
                # Processing operation
                result = process_audio_file(path)
            except ProcessingDomainError as e:
                logger.error(f"Domain error: {e}")
                logger.error(f"Error code: {e.error_code}")
                logger.error(f"Details: {e.details}")
    """
    
    def __init__(self, message: str, error_code: str = None, details: Any = None):
        """Initialize domain error with message and optional details."""
        super().__init__(message)
        self.error_code = error_code
        self.details = details


class ValidationError(ProcessingDomainError):
    """Exception for validation rule violations.
    
    Raised when input data fails validation rules. Captures the field that failed,
    the validation message, and the invalid value for detailed error reporting.
    
    Example:
        Validating file path existence::
        
            if not os.path.exists(file_path):
                raise ValidationError(
                    field='file_path',
                    message='File does not exist',
                    value=file_path
                )
        
        Validating numeric range::
        
            if bitrate < 32 or bitrate > 320:
                raise ValidationError(
                    field='bitrate',
                    message='Bitrate must be between 32 and 320 kbps',
                    value=bitrate
                )
        
        Handling validation errors::
        
            try:
                validate_processing_request(request)
            except ValidationError as e:
                print(f"Invalid {e.field}: {e.value}")
                # Output: Invalid bitrate: 512
    """
    
    def __init__(self, field: str, message: str, value: Any = None):
        """Initialize validation error for specific field."""
        super().__init__(f"Validation failed for {field}: {message}", "VALIDATION_ERROR")
        self.field = field
        self.value = value


class ProcessingOperationError(ProcessingDomainError):
    """Exception for invalid processing operations."""
    pass


class InsufficientInputError(ProcessingOperationError):
    """Exception for insufficient input data.
    
    Raised when a processing operation requires certain inputs but they are missing
    or incomplete. Tracks what was required versus what was actually provided.
    
    Example:
        Requiring at least one input file::
        
            if not input_files:
                raise InsufficientInputError(
                    required='at least one audio file',
                    provided='0 files'
                )
        
        Requiring TAF file for extraction::
        
            if not taf_file_path:
                raise InsufficientInputError(
                    required='TAF file path for chapter extraction'
                )
        
        Handling insufficient input::
        
            try:
                combine_files_to_taf([])
            except InsufficientInputError as e:
                print(f"Error: {e.required}")
                if e.provided:
                    print(f"Got: {e.provided}")
    """
    
    def __init__(self, required: str, provided: str = None):
        message = f"Insufficient input: requires {required}"
        if provided:
            message += f", provided {provided}"
        super().__init__(message, "INSUFFICIENT_INPUT")
        self.required = required
        self.provided = provided


class UnsupportedOperationError(ProcessingOperationError):
    """Exception for unsupported processing operations.
    
    Raised when attempting an operation that is not supported in the current context,
    configuration, or for the given file type.
    
    Example:
        Unsupported format conversion::
        
            if source_format == 'mp4' and target_format == 'taf':
                raise UnsupportedOperationError(
                    operation='MP4 to TAF conversion',
                    context='video files not supported'
                )
        
        Unsupported processing mode::
        
            if mode == 'combine' and len(files) == 1:
                raise UnsupportedOperationError(
                    operation='combine mode',
                    context='requires multiple files'
                )
        
        Handling unsupported operations::
        
            try:
                processor.process(request)
            except UnsupportedOperationError as e:
                print(f"Cannot perform: {e.operation}")
                if e.context:
                    print(f"Reason: {e.context}")
    """
    
    def __init__(self, operation: str, context: str = None):
        message = f"Unsupported operation: {operation}"
        if context:
            message += f" in {context}"
        super().__init__(message, "UNSUPPORTED_OPERATION")
        self.operation = operation
        self.context = context


class InvalidProcessingModeError(ProcessingOperationError):
    """Exception for invalid processing mode combinations.
    
    Raised when processing mode is invalid or incompatible with other options,
    such as conflicting flags or mutually exclusive operations.
    
    Example:
        Conflicting processing modes::
        
            if request.convert_to_taf and request.extract_from_taf:
                raise InvalidProcessingModeError(
                    mode='convert+extract',
                    reason='Cannot convert to TAF and extract from TAF simultaneously'
                )
        
        Invalid output configuration::
        
            if request.combine_chapters and not request.output_format == 'taf':
                raise InvalidProcessingModeError(
                    mode='combine_chapters',
                    reason='Chapter combining requires TAF output format'
                )
        
        Handling mode errors::
        
            try:
                validate_processing_mode(options)
            except InvalidProcessingModeError as e:
                print(f"Invalid mode '{e.mode}': {e.reason}")
    """
    
    def __init__(self, mode: str, reason: str):
        message = f"Invalid processing mode '{mode}': {reason}"
        super().__init__(message, "INVALID_PROCESSING_MODE")
        self.mode = mode
        self.reason = reason


class ProcessingConstraintViolationError(ProcessingOperationError):
    """Exception for business constraint violations.
    
    Raised when an operation violates business rules or domain constraints,
    such as file size limits, format requirements, or codec restrictions.
    
    Example:
        File size constraint::
        
            if file_size > MAX_TAF_FILE_SIZE:
                raise ProcessingConstraintViolationError(
                    constraint='max_taf_file_size',
                    violation=f'File size {file_size} exceeds limit {MAX_TAF_FILE_SIZE}'
                )
        
        Audio format constraint::
        
            if sample_rate != 48000:
                raise ProcessingConstraintViolationError(
                    constraint='taf_sample_rate',
                    violation=f'TAF format requires 48kHz, got {sample_rate}Hz'
                )
        
        Handling constraint violations::
        
            try:
                create_taf_file(audio_data, codec_params)
            except ProcessingConstraintViolationError as e:
                print(f"Constraint '{e.constraint}' violated: {e.violation}")
    """
    
    def __init__(self, constraint: str, violation: str):
        message = f"Constraint violation '{constraint}': {violation}"
        super().__init__(message, "CONSTRAINT_VIOLATION")
        self.constraint = constraint
        self.violation = violation


class ValidationErrorCollection(ProcessingDomainError):
    """Collection of multiple validation errors.
    
    Used to aggregate multiple validation errors that occur during batch validation,
    allowing all errors to be reported at once instead of failing on the first one.
    
    Example:
        Collecting multiple validation errors::
        
            errors = []
            if not os.path.exists(file_path):
                errors.append(ValidationError('file_path', 'File not found', file_path))
            if bitrate < 32:
                errors.append(ValidationError('bitrate', 'Too low', bitrate))
            if sample_rate not in [44100, 48000]:
                errors.append(ValidationError('sample_rate', 'Invalid rate', sample_rate))
            
            if errors:
                raise ValidationErrorCollection(errors)
        
        Handling multiple validation errors::
        
            try:
                validate_all_inputs(request)
            except ValidationErrorCollection as e:
                print(f"Found {len(e)} validation errors:")
                for error in e:
                    print(f"  - {error.field}: {error}")
        
        Checking for specific field errors::
        
            try:
                validate_processing_options(options)
            except ValidationErrorCollection as e:
                if e.has_field_error('bitrate'):
                    bitrate_errors = e.get_field_errors('bitrate')
                    print(f"Bitrate issues: {bitrate_errors}")
    """
    
    def __init__(self, errors: List[ValidationError]):
        """Initialize with list of validation errors."""
        messages = [str(error) for error in errors]
        super().__init__(f"Multiple validation errors: {'; '.join(messages)}", "MULTIPLE_VALIDATION_ERRORS")
        self.errors = errors
        
    def __len__(self):
        return len(self.errors)
        
    def __iter__(self):
        return iter(self.errors)
        
    def has_field_error(self, field: str) -> bool:
        """Check if collection contains error for specific field."""
        return any(error.field == field for error in self.errors)
        
    def get_field_errors(self, field: str) -> List[ValidationError]:
        """Get all errors for specific field."""
        return [error for error in self.errors if error.field == field]