#!/usr/bin/env python3
"""
Processing application service.

This service orchestrates use cases and provides high-level application logic
for processing operations.
"""

from typing import Optional, Callable, Dict, Any
import logging

from ...domain import (
    ProcessingOperation, ProcessingResult, ValidationService,
    ProcessingModeType, SINGLE_FILE_MODE, FILES_TO_TAF_MODE,
    RECURSIVE_MODE, ANALYSIS_MODE
)
from ..interfaces.file_repository import FileRepository
from ..interfaces.media_converter import MediaConverter
from ..interfaces.upload_service import UploadService
from ..use_cases.convert_to_taf_use_case import ConvertToTafUseCase
from ..use_cases.files_to_taf_use_case import FilesToTafUseCase
from ..use_cases.file_analysis_use_case import FileAnalysisUseCase
from .workflow_coordinator import WorkflowCoordinator


class ProcessingApplicationService:
    """
    Application service for coordinating processing operations.
    
    This service provides the main entry point for executing processing operations,
    selecting appropriate use cases, and coordinating complex workflows.
    """
    
    def __init__(self,
                 file_repo: FileRepository,
                 media_converter: MediaConverter,
                 analysis_service,
                 event_bus,
                 upload_service: Optional[UploadService] = None,
                 validation_service: Optional[ValidationService] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize processing application service.
        
        Args:
            file_repo: File repository for file operations
            media_converter: Media converter for audio processing
            analysis_service: TAF analysis service
            event_bus: Event bus for publishing events
            upload_service: Optional upload service for uploading results
            validation_service: Optional validation service
            logger: Optional logger instance
        """
        self.file_repo = file_repo
        self.media_converter = media_converter
        self.analysis_service = analysis_service
        self.event_bus = event_bus
        self.upload_service = upload_service
        self.validation_service = validation_service or ValidationService()
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        
        # Initialize workflow coordinator first
        self.workflow_coordinator = WorkflowCoordinator(
            file_repository=file_repo,
            media_converter=media_converter,
            logger=self.logger,
            event_bus=event_bus
        )
        
        # Initialize use cases (now that workflow_coordinator exists)
        self._use_cases = self._create_use_cases()
    
    def _create_use_cases(self) -> Dict[ProcessingModeType, Any]:
        """Create and configure use cases."""
        use_case_args = {
            'file_repo': self.file_repo,
            'media_converter': self.media_converter,
            'upload_service': self.upload_service,
            'validation_service': self.validation_service,
            'logger': self.logger
        }
        
        return {
            ProcessingModeType.SINGLE_FILE: ConvertToTafUseCase(**use_case_args),
            ProcessingModeType.FILES_TO_TAF: FilesToTafUseCase(**use_case_args),
            ProcessingModeType.RECURSIVE: self.workflow_coordinator,  # Recursive uses workflow coordinator
            ProcessingModeType.ANALYSIS: FileAnalysisUseCase(
                file_repo=self.file_repo,
                media_converter=self.media_converter,
                analysis_service=self.analysis_service,
                logger=self.logger
            )
        }
    
    def execute_operation(self, operation: ProcessingOperation,
                         progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute a processing operation.
        
        Args:
            operation: Processing operation to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with execution results
        """
        self.logger.info(f"Executing processing operation: {operation.operation_id} "
                        f"(mode: {operation.processing_mode.name})")
        
        try:
            # Validate operation
            if not operation.can_execute():
                error_msg = operation.get_validation_summary() or "Operation validation failed"
                self.logger.error(f"Operation validation failed: {error_msg}")
                
                result = ProcessingResult(operation_id=operation.operation_id)
                result.mark_failed(ValueError(error_msg))
                return result
            
            # Select appropriate use case
            use_case = self._get_use_case(operation)
            if not use_case:
                error_msg = f"No use case available for processing mode: {operation.processing_mode.name}"
                self.logger.error(error_msg)
                
                result = ProcessingResult(operation_id=operation.operation_id)
                result.mark_failed(ValueError(error_msg))
                return result
            
            # Execute use case
            self.logger.debug(f"Executing use case: {use_case.__class__.__name__}")
            result = use_case.execute(operation, progress_callback)
            
            self.logger.info(f"Operation completed: {operation.operation_id} "
                           f"(status: {result.status.name}, "
                           f"files: {result.success_count}/{result.total_files})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Operation execution failed: {str(e)}")
            
            result = ProcessingResult(operation_id=operation.operation_id)
            result.mark_failed(e)
            return result
    
    def _get_use_case(self, operation: ProcessingOperation):
        """Get appropriate use case for processing operation."""
        return self._use_cases.get(operation.processing_mode.mode_type)
    
    def validate_operation(self, operation: ProcessingOperation) -> bool:
        """
        Validate processing operation.
        
        Args:
            operation: Processing operation to validate
            
        Returns:
            True if operation is valid, False otherwise
        """
        try:
            errors = self.validation_service.validate_operation_full(operation)
            
            if len(errors) > 0:
                self.logger.warning(f"Operation validation warnings: {errors}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Operation validation error: {str(e)}")
            return False
    
    def get_operation_estimate(self, operation: ProcessingOperation) -> Dict[str, Any]:
        """
        Get estimates for processing operation.
        
        Args:
            operation: Processing operation to estimate
            
        Returns:
            Dictionary with estimates (file count, size, time, etc.)
        """
        try:
            file_count = operation.estimated_file_count
            
            # Get file sizes if possible
            total_size = 0
            try:
                files = operation.input_spec.resolve_files()
                total_size = sum(f.stat().st_size for f in files if f.exists())
            except Exception:
                pass
            
            # Estimate processing time (very rough)
            estimated_time = None
            if total_size > 0 and operation.processing_mode.mode_type != ProcessingModeType.ANALYSIS:
                # Rough estimate: 1 second per MB for conversion
                size_mb = total_size / (1024 * 1024)
                estimated_time = size_mb * 1.0  # seconds
                
                # Adjust for quality settings
                if operation.options.quality_level.name == 'HIGH':
                    estimated_time *= 2.0
                elif operation.options.quality_level.name == 'LOW':
                    estimated_time *= 0.5
                
                # Adjust for parallel processing
                if operation.options.max_parallel_jobs > 1:
                    estimated_time /= min(operation.options.max_parallel_jobs, file_count)
            
            return {
                'file_count': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024) if total_size > 0 else 0,
                'estimated_time_seconds': estimated_time,
                'processing_mode': operation.processing_mode.name,
                'supports_parallel': operation.options.max_parallel_jobs > 1,
                'upload_enabled': operation.options.upload_enabled
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate operation estimate: {str(e)}")
            return {
                'error': str(e),
                'file_count': 0,
                'total_size_bytes': 0
            }
    
    def create_operation_from_args(self, args) -> ProcessingOperation:
        """
        Create processing operation from command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            ProcessingOperation configured from arguments
        """
        from ...domain.services.mode_determination_service import ModeDeterminationService
        
        mode_service = ModeDeterminationService()
        return mode_service.create_operation_from_args(args)
    
    def get_supported_operations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all supported processing operations.
        
        Returns:
            Dictionary with information about available operations
        """
        operations = {}
        
        for mode_type, use_case in self._use_cases.items():
            operations[mode_type.name] = {
                'name': mode_type.name,
                'description': SINGLE_FILE_MODE.description if mode_type == ProcessingModeType.SINGLE_FILE
                           else FILES_TO_TAF_MODE.description if mode_type == ProcessingModeType.FILES_TO_TAF
                           else RECURSIVE_MODE.description if mode_type == ProcessingModeType.RECURSIVE
                           else ANALYSIS_MODE.description,
                'supports_batch': mode_type in [ProcessingModeType.FILES_TO_TAF, ProcessingModeType.RECURSIVE],
                'supports_upload': mode_type != ProcessingModeType.ANALYSIS,
                'use_case_class': use_case.__class__.__name__
            }
        
        return operations
    
    def cleanup_resources(self):
        """Clean up resources used by the application service."""
        try:
            # Disconnect upload service if connected
            if self.upload_service and self.upload_service.is_connected():
                self.upload_service.disconnect()
                self.logger.debug("Disconnected upload service")
            
            # Clean up temporary files
            temp_count = self.file_repo.cleanup_temp_files("*.tmp")
            if temp_count > 0:
                self.logger.debug(f"Cleaned up {temp_count} temporary files")
                
        except Exception as e:
            self.logger.warning(f"Error during resource cleanup: {str(e)}")
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get status of all services.
        
        Returns:
            Dictionary with service status information
        """
        status = {
            'file_repository': 'available',
            'media_converter': 'available',
            'validation_service': 'available',
            'upload_service': 'not_configured'
        }
        
        # Check upload service
        if self.upload_service:
            try:
                if self.upload_service.is_connected():
                    status['upload_service'] = 'connected'
                elif self.upload_service.test_connection():
                    status['upload_service'] = 'available'
                else:
                    status['upload_service'] = 'unavailable'
            except Exception:
                status['upload_service'] = 'error'
        
        # Check media converter
        try:
            supported_formats = self.media_converter.get_supported_input_formats()
            status['media_converter_formats'] = len(supported_formats)
        except Exception:
            status['media_converter'] = 'error'
        
        return status