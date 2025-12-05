#!/usr/bin/env python3
"""
Base use case class.

This module provides the abstract base class for all processing use cases.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable
import logging

from ...domain import ProcessingOperation, ProcessingResult, ValidationService
from ..interfaces.file_repository import FileRepository
from ..interfaces.media_converter import MediaConverter
from ..interfaces.upload_service import UploadService
from ....events import get_event_bus


class BaseUseCase(ABC):
    """
    Abstract base class for all processing use cases.
    
    Provides common functionality and enforces the use case contract.
    """
    
    def __init__(self, 
                 file_repo: FileRepository,
                 media_converter: MediaConverter,
                 upload_service: Optional[UploadService] = None,
                 validation_service: Optional[ValidationService] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize base use case.
        
        Args:
            file_repo: File repository for file operations
            media_converter: Media converter for audio processing
            upload_service: Optional upload service for uploading results
            validation_service: Optional validation service
            logger: Optional logger instance
        """
        self.file_repo = file_repo
        self.media_converter = media_converter
        self.upload_service = upload_service
        self.validation_service = validation_service or ValidationService()
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.event_bus = get_event_bus()
    
    @abstractmethod
    def execute(self, operation: ProcessingOperation,
               progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute the use case.
        
        Args:
            operation: Processing operation to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with execution results
        """
        pass
    
    def validate_operation(self, operation: ProcessingOperation) -> bool:
        """
        Validate operation before execution.
        
        Args:
            operation: Processing operation to validate
            
        Returns:
            True if operation is valid, False otherwise
        """
        errors = self.validation_service.validate_operation_full(operation)
        
        if len(errors) > 0:
            self.logger.error(f"Operation validation failed: {errors}")
            return False
        
        return True
    
    def _publish_started_event(self, operation: ProcessingOperation):
        """Publish processing started event.""" 
        from ....events import ProcessingOperationStartedEvent
        
        event = ProcessingOperationStartedEvent(
            source=self.__class__.__name__,
            operation=operation,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
        self.logger.debug(f"Published processing operation started event: {event.event_id}")
    
    def _publish_completed_event(self, operation: ProcessingOperation, result: ProcessingResult):
        """Publish processing completed event."""
        from ....events import ProcessingOperationCompletedEvent
        
        event = ProcessingOperationCompletedEvent(
            source=self.__class__.__name__,
            operation=operation,
            result=result,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
        self.logger.debug(f"Published processing operation completed event: {event.event_id}")
    
    def _publish_failed_event(self, operation: ProcessingOperation, error: Exception):
        """Publish processing failed event."""
        from ....events import ProcessingOperationFailedEvent
        
        event = ProcessingOperationFailedEvent(
            source=self.__class__.__name__,
            operation=operation,
            error=error,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
        self.logger.debug(f"Published processing operation failed event: {event.event_id}")
    
    def _publish_file_started_event(self, operation: ProcessingOperation, file_path, file_index: int, total_files: int):
        """Publish file processing started event."""
        from ....events import FileProcessingStartedEvent
        from pathlib import Path
        
        event = FileProcessingStartedEvent(
            source=self.__class__.__name__,
            operation_id=operation.operation_id,
            file_path=Path(file_path),
            file_index=file_index,
            total_files=total_files,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
    
    def _publish_file_completed_event(self, operation: ProcessingOperation, input_file, output_file, 
                                    success: bool, duration: float = 0.0):
        """Publish file processing completed event."""
        from ....events import FileProcessingCompletedEvent
        from pathlib import Path
        
        event = FileProcessingCompletedEvent(
            source=self.__class__.__name__,
            operation_id=operation.operation_id,
            input_file=Path(input_file),
            output_file=Path(output_file),
            success=success,
            duration_seconds=duration,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
    
    def _publish_progress_event(self, operation: ProcessingOperation, progress: float, 
                              current_operation: str, details: str = ""):
        """Publish processing progress event."""
        from ....events import ProcessingProgressEvent
        
        event = ProcessingProgressEvent(
            source=self.__class__.__name__,
            operation_id=operation.operation_id,
            progress=progress,
            current_operation=current_operation,
            details=details,
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
    
    def _publish_validation_event(self, operation: ProcessingOperation, validation_type: str,
                                target: str, is_valid: bool, errors: list = None):
        """Publish validation event."""
        from ....events import ValidationEvent
        
        event = ValidationEvent(
            source=self.__class__.__name__,
            operation_id=operation.operation_id,
            validation_type=validation_type,
            target=target,
            is_valid=is_valid,
            errors=errors or [],
            event_data={
                'use_case': self.__class__.__name__
            }
        )
        self.event_bus.publish(event)
    
    def _handle_upload_if_enabled(self, operation: ProcessingOperation, result: ProcessingResult) -> None:
        """Handle upload of results if upload is enabled."""
        if not operation.options.upload_enabled or not self.upload_service:
            return
        
        if not operation.options.upload_after_processing:
            return
        
        successful_files = result.get_output_paths()
        if not successful_files:
            self.logger.warning("No successful output files to upload")
            return
        
        try:
            if not self.upload_service.is_connected():
                self.logger.warning("Upload service not connected, skipping upload")
                return
            
            self.logger.info(f"Uploading {len(successful_files)} files")
            
            upload_metadata = {
                'operation_id': operation.operation_id,
                'processing_mode': operation.processing_mode.name,
                'upload_timestamp': operation.completed_at.isoformat() if operation.completed_at else None
            }
            
            upload_results = self.upload_service.upload_files(
                successful_files, 
                metadata=upload_metadata
            )
            
            # Add upload results to processing result
            for upload_result in upload_results:
                result.add_upload_result(upload_result.file_path, {
                    'success': upload_result.success,
                    'upload_url': upload_result.upload_url,
                    'upload_id': upload_result.upload_id,
                    'error': upload_result.error_message
                })
            
            successful_uploads = sum(1 for ur in upload_results if ur.success)
            self.logger.info(f"Successfully uploaded {successful_uploads}/{len(upload_results)} files")
            
        except Exception as e:
            self.logger.error(f"Upload failed: {str(e)}")
            # Don't fail the entire operation due to upload errors
    
    def _create_result(self, operation: ProcessingOperation) -> ProcessingResult:
        """Create initial processing result for operation."""
        from ...domain.models.processing_result import ProcessingResult
        
        return ProcessingResult(operation_id=operation.operation_id)
    
    def _finalize_result(self, operation: ProcessingOperation, result: ProcessingResult) -> ProcessingResult:
        """Finalize processing result after execution."""
        result.mark_completed()
        
        # Handle uploads if enabled
        self._handle_upload_if_enabled(operation, result)
        
        return result