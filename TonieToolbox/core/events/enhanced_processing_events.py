"""
Enhanced Processing Domain Events

This module defines events related to file processing operations that work
with the new Clean Architecture domain models. These events allow UI components
and other modules to react to processing state changes.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from .base_events import DomainEvent

# Import domain models for type hints
try:
    from ..processing.domain.models import ProcessingOperation, ProcessingResult
    from ..processing.domain import ProcessingMode, InputSpecification, OutputSpecification
except ImportError:
    # Fallback for when imports are being updated
    ProcessingOperation = Any
    ProcessingResult = Any
    ProcessingMode = Any
    InputSpecification = Any
    OutputSpecification = Any


class ProcessingOperationStartedEvent(DomainEvent):
    """Event fired when a processing operation starts."""
    
    def __init__(self, source: str, operation: ProcessingOperation, 
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize processing operation started event.
        
        Args:
            source: Source component that started the operation
            operation: The processing operation that started
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation.operation_id,
            'processing_mode': operation.processing_mode.name if hasattr(operation.processing_mode, 'name') else str(operation.processing_mode),
            'input_paths': [str(path) for path in operation.input_spec.resolve_files()] if hasattr(operation, 'input_spec') else [],
            'output_path': str(operation.output_spec.output_path) if hasattr(operation, 'output_spec') and operation.output_spec.output_path else None,
            'estimated_duration': operation.estimated_duration_seconds if hasattr(operation, 'estimated_duration_seconds') else None
        })
        super().__init__(source, data)
        self.operation = operation
    
    @property
    def event_type(self) -> str:
        return "processing.operation.started"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def processing_mode(self) -> str:
        return self.get_data('processing_mode')
    
    @property
    def input_paths(self) -> List[Path]:
        return [Path(p) for p in self.get_data('input_paths', [])]
    
    @property
    def output_path(self) -> Optional[Path]:
        output = self.get_data('output_path')
        return Path(output) if output else None


class ProcessingOperationCompletedEvent(DomainEvent):
    """Event fired when a processing operation completes."""
    
    def __init__(self, source: str, operation: ProcessingOperation, result: ProcessingResult,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize processing operation completed event.
        
        Args:
            source: Source component that completed the operation
            operation: The processing operation that completed
            result: The processing result
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation.operation_id,
            'processing_mode': operation.processing_mode.name if hasattr(operation.processing_mode, 'name') else str(operation.processing_mode),
            'success': result.is_successful,
            'output_files': [str(f) for f in result.output_files] if hasattr(result, 'output_files') else [],
            'processed_files': getattr(result, 'processed_files', []),
            'duration_seconds': result.processing_duration_seconds if hasattr(result, 'processing_duration_seconds') else None,
            'error_count': len(result.errors) if hasattr(result, 'errors') else 0
        })
        super().__init__(source, data)
        self.operation = operation
        self.result = result
    
    @property
    def event_type(self) -> str:
        return "processing.operation.completed"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def processing_mode(self) -> str:
        return self.get_data('processing_mode')
    
    @property
    def success(self) -> bool:
        return self.get_data('success', False)
    
    @property
    def output_files(self) -> List[Path]:
        return [Path(f) for f in self.get_data('output_files', [])]
    
    @property
    def duration_seconds(self) -> Optional[float]:
        return self.get_data('duration_seconds')


class ProcessingOperationFailedEvent(DomainEvent):
    """Event fired when a processing operation fails."""
    
    def __init__(self, source: str, operation: ProcessingOperation, error: Exception,
                 partial_result: Optional[ProcessingResult] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize processing operation failed event.
        
        Args:
            source: Source component where the failure occurred
            operation: The processing operation that failed
            error: The exception that caused the failure
            partial_result: Partial result if any processing was completed
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation.operation_id,
            'processing_mode': operation.processing_mode.name if hasattr(operation.processing_mode, 'name') else str(operation.processing_mode),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'partial_files': partial_result.output_files if partial_result and hasattr(partial_result, 'output_files') else [],
            'duration_seconds': partial_result.processing_duration_seconds if partial_result and hasattr(partial_result, 'processing_duration_seconds') else None
        })
        super().__init__(source, data)
        self.operation = operation
        self.error = error
        self.partial_result = partial_result
    
    @property
    def event_type(self) -> str:
        return "processing.operation.failed"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def processing_mode(self) -> str:
        return self.get_data('processing_mode')
    
    @property
    def error_type(self) -> str:
        return self.get_data('error_type')
    
    @property
    def error_message(self) -> str:
        return self.get_data('error_message')


class ProcessingProgressEvent(DomainEvent):
    """Event fired to report processing progress."""
    
    def __init__(self, source: str, operation_id: str, progress: float,
                 current_operation: str, details: str = "",
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize processing progress event.
        
        Args:
            source: Source component reporting progress
            operation_id: ID of the processing operation
            progress: Progress value between 0.0 and 1.0
            current_operation: Description of current operation
            details: Additional details about the progress
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation_id,
            'progress': max(0.0, min(1.0, progress)),  # Clamp to valid range
            'current_operation': current_operation,
            'details': details
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "processing.progress"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def progress(self) -> float:
        return self.get_data('progress', 0.0)
    
    @property
    def current_operation(self) -> str:
        return self.get_data('current_operation', '')
    
    @property
    def details(self) -> str:
        return self.get_data('details', '')


class FileProcessingStartedEvent(DomainEvent):
    """Event fired when processing of an individual file starts."""
    
    def __init__(self, source: str, operation_id: str, file_path: Path,
                 file_index: int, total_files: int,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize file processing started event.
        
        Args:
            source: Source component processing the file
            operation_id: ID of the parent processing operation
            file_path: Path of the file being processed
            file_index: Index of this file in the processing queue (0-based)
            total_files: Total number of files to process
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation_id,
            'file_path': str(file_path),
            'file_index': file_index,
            'total_files': total_files,
            'file_name': file_path.name
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "processing.file.started"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def file_path(self) -> Path:
        return Path(self.get_data('file_path'))
    
    @property
    def file_index(self) -> int:
        return self.get_data('file_index', 0)
    
    @property
    def total_files(self) -> int:
        return self.get_data('total_files', 1)


class FileProcessingCompletedEvent(DomainEvent):
    """Event fired when processing of an individual file completes."""
    
    def __init__(self, source: str, operation_id: str, input_file: Path, output_file: Path,
                 success: bool, duration_seconds: float = 0.0,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize file processing completed event.
        
        Args:
            source: Source component that processed the file
            operation_id: ID of the parent processing operation
            input_file: Input file path
            output_file: Output file path
            success: Whether the processing was successful
            duration_seconds: Time taken to process this file
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation_id,
            'input_file': str(input_file),
            'output_file': str(output_file),
            'success': success,
            'duration_seconds': duration_seconds,
            'input_name': input_file.name,
            'output_name': output_file.name
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "processing.file.completed"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def input_file(self) -> Path:
        return Path(self.get_data('input_file'))
    
    @property
    def output_file(self) -> Path:
        return Path(self.get_data('output_file'))
    
    @property
    def success(self) -> bool:
        return self.get_data('success', False)
    
    @property
    def duration_seconds(self) -> float:
        return self.get_data('duration_seconds', 0.0)


class ValidationEvent(DomainEvent):
    """Event fired when validation occurs during processing."""
    
    def __init__(self, source: str, operation_id: str, validation_type: str,
                 target: str, is_valid: bool, errors: List[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """
        Initialize validation event.
        
        Args:
            source: Source component performing validation
            operation_id: ID of the processing operation
            validation_type: Type of validation (input, output, format, etc.)
            target: What is being validated (file path, specification, etc.)
            is_valid: Whether validation passed
            errors: List of validation error messages
            event_data: Additional event data
        """
        data = event_data or {}
        data.update({
            'operation_id': operation_id,
            'validation_type': validation_type,
            'target': target,
            'is_valid': is_valid,
            'errors': errors or []
        })
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        return "processing.validation"
    
    @property
    def operation_id(self) -> str:
        return self.get_data('operation_id')
    
    @property
    def validation_type(self) -> str:
        return self.get_data('validation_type')
    
    @property
    def target(self) -> str:
        return self.get_data('target')
    
    @property
    def is_valid(self) -> bool:
        return self.get_data('is_valid', False)
    
    @property
    def errors(self) -> List[str]:
        return self.get_data('errors', [])


