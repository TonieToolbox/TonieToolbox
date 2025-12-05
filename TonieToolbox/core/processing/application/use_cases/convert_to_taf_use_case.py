#!/usr/bin/env python3
"""
Convert to TAF use case.

This use case handles conversion of audio files to TAF format,
supporting both single file and combined file scenarios.
"""

from pathlib import Path
from typing import Optional, Callable, List
import time

from ...domain import ProcessingOperation, ProcessingResult, ProcessingModeType
from ...domain.models.processing_result import ProcessedFile, ProcessingStatus
from ..interfaces.media_converter import ConversionProgress
from .base_use_case import BaseUseCase


class ConvertToTafUseCase(BaseUseCase):
    """
    Use case for converting audio files to TAF format.
    
    Handles both single file conversion and combining multiple files into one TAF.
    """
    
    def execute(self, operation: ProcessingOperation,
               progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute TAF conversion operation.
        
        Args:
            operation: Processing operation to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with conversion results
        """
        # Validate operation
        if not self.validate_operation(operation):
            result = self._create_result(operation)
            result.mark_failed(ValueError("Operation validation failed"))
            return result
        
        # Start processing
        result = self._create_result(operation)
        result.mark_started()
        operation.mark_started()
        
        self.logger.info(f"Starting TAF conversion: {operation.operation_id}")
        self._publish_started_event(operation)
        
        try:
            # Resolve input files
            input_files = operation.input_spec.resolve_files()
            if not input_files:
                raise ValueError("No input files found")
            
            self.logger.info(f"Converting {len(input_files)} files to TAF")
            
            # Determine if this is single file or combined operation
            if (operation.processing_mode.mode_type == ProcessingModeType.SINGLE_FILE or 
                len(input_files) > 1 and operation.output_spec.output_mode.name == 'SINGLE_FILE'):
                
                # Combined conversion - multiple files to single TAF
                self._execute_combined_conversion(operation, input_files, result, progress_callback)
            else:
                # Individual conversion - each file to separate TAF
                self._execute_individual_conversions(operation, input_files, result, progress_callback)
            
            operation.mark_completed()
            self._publish_completed_event(operation, result)
            
        except Exception as e:
            self.logger.error(f"TAF conversion failed: {str(e)}")
            result.mark_failed(e)
            operation.mark_completed()
            self._publish_failed_event(operation, e)
        
        return self._finalize_result(operation, result)
    
    def _execute_combined_conversion(self, operation: ProcessingOperation, 
                                   input_files: List[Path], result: ProcessingResult,
                                   progress_callback: Optional[Callable] = None) -> None:
        """Execute combined conversion (multiple files to single TAF)."""
        output_path = operation.output_spec.resolve_output_path("combined")
        
        # Prepare output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if output already exists and should be skipped
        if operation.output_spec.should_skip_existing(output_path):
            self.logger.info(f"Skipping existing output file: {output_path}")
            
            # Create processed file entry
            processed_file = ProcessedFile(
                input_path=Path("combined"),
                output_path=output_path,
                status=ProcessingStatus.COMPLETED,
                file_size_output=output_path.stat().st_size if output_path.exists() else 0
            )
            result.add_processed_file(processed_file)
            return
        
        self.logger.info(f"Combining {len(input_files)} files into {output_path}")
        
        # Publish initial progress for combination
        self._publish_progress_event(operation, 0.0, "Starting file combination",
                                   f"Combining {len(input_files)} files to {output_path.name}")
        
        # Calculate total input size
        total_input_size = sum(f.stat().st_size for f in input_files if f.exists())
        
        # Create conversion progress callback
        def conversion_progress_callback(progress: ConversionProgress):
            # Publish progress events
            self._publish_progress_event(operation, progress.overall_progress, "Combining files", 
                                       f"Processing: {progress.current_file}")
            
            if progress_callback:
                progress_callback({
                    'operation': 'Combining files',
                    'current_file': progress.current_file,
                    'progress': progress.overall_progress,
                    'files_completed': 0,
                    'total_files': 1
                })
        
        # Perform conversion
        start_time = time.time()
        
        success = self.media_converter.combine_files_to_taf(
            input_files,
            output_path,
            operation.options,
            conversion_progress_callback
        )
        
        processing_time = time.time() - start_time
        
        # Create processed file entry
        processed_file = ProcessedFile(
            input_path=Path(f"combined_{len(input_files)}_files"),
            output_path=output_path if success else None,
            status=ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED,
            processing_time=processing_time,
            file_size_input=total_input_size,
            file_size_output=output_path.stat().st_size if success and output_path.exists() else 0,
            error=None if success else Exception("Combination failed")
        )
        
        result.add_processed_file(processed_file)
        
        if success:
            self.logger.info(f"Successfully combined files to {output_path}")
        else:
            self.logger.error(f"Failed to combine files to {output_path}")
    
    def _execute_individual_conversions(self, operation: ProcessingOperation,
                                      input_files: List[Path], result: ProcessingResult,
                                      progress_callback: Optional[Callable] = None) -> None:
        """Execute individual conversions (each file to separate TAF)."""
        total_files = len(input_files)
        completed_files = 0
        
        # Publish initial progress
        self._publish_progress_event(operation, 0.0, "Starting individual conversions", 
                                   f"Processing {total_files} files")
        
        for i, input_file in enumerate(input_files):
            # Publish file started event
            self._publish_file_started_event(operation, input_file, i, total_files)
            
            # Update overall progress
            progress = i / total_files
            self._publish_progress_event(operation, progress, "Converting files", 
                                       f"Processing {input_file.name} ({i+1}/{total_files})")
            
            if progress_callback:
                progress_callback({
                    'operation': 'Converting files',
                    'current_file': str(input_file),
                    'progress': progress,
                    'files_completed': completed_files,
                    'total_files': total_files
                })
            
            try:
                processed_file = self._convert_single_file(operation, input_file, progress_callback)
                result.add_processed_file(processed_file)
                
                # Publish file completed event
                self._publish_file_completed_event(
                    operation, 
                    input_file,
                    processed_file.output_path or input_file,
                    processed_file.is_successful,
                    processed_file.processing_time
                )
                
                if processed_file.is_successful:
                    completed_files += 1
                    self.logger.debug(f"Converted {input_file} successfully")
                else:
                    self.logger.warning(f"Failed to convert {input_file}: {processed_file.error}")
                
                # Continue on error if configured
                if not operation.options.continue_on_error and not processed_file.is_successful:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error processing {input_file}: {str(e)}")
                
                # Create failed processed file entry
                failed_file = ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
                result.add_processed_file(failed_file)
                
                # Publish file completed event for failure
                self._publish_file_completed_event(
                    operation, input_file, input_file, False, 0.0
                )
                
                if not operation.options.continue_on_error:
                    break
        
        if progress_callback:
            progress_callback({
                'operation': 'Conversion complete',
                'current_file': '',
                'progress': 1.0,
                'files_completed': completed_files,
                'total_files': total_files
            })
        
        self.logger.info(f"Completed individual conversions: {completed_files}/{total_files} successful")
    
    def _convert_single_file(self, operation: ProcessingOperation, 
                           input_file: Path,
                           progress_callback: Optional[Callable] = None) -> ProcessedFile:
        """Convert single input file to TAF."""
        # Resolve output path for this specific file
        output_path = operation.output_spec.resolve_output_path(input_file.name)
        
        # Prepare output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if output already exists and should be skipped
        if operation.output_spec.should_skip_existing(output_path):
            self.logger.debug(f"Skipping existing output file: {output_path}")
            return ProcessedFile(
                input_path=input_file,
                output_path=output_path,
                status=ProcessingStatus.COMPLETED,
                file_size_input=input_file.stat().st_size if input_file.exists() else 0,
                file_size_output=output_path.stat().st_size if output_path.exists() else 0
            )
        
        # Get input file size
        input_size = input_file.stat().st_size if input_file.exists() else 0
        
        # Create conversion progress callback
        def conversion_progress_callback(progress: ConversionProgress):
            if progress_callback:
                # This is called for the single file progress within the overall batch
                pass  # Individual file progress is handled by the batch progress
        
        # Perform conversion
        start_time = time.time()
        
        try:
            success = self.media_converter.convert_to_taf(
                input_file,
                output_path,
                operation.options,
                conversion_progress_callback
            )
            
            processing_time = time.time() - start_time
            
            # Get output file size
            output_size = output_path.stat().st_size if success and output_path.exists() else 0
            
            return ProcessedFile(
                input_path=input_file,
                output_path=output_path if success else None,
                status=ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED,
                processing_time=processing_time,
                file_size_input=input_size,
                file_size_output=output_size,
                error=None if success else Exception("Conversion failed")
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return ProcessedFile(
                input_path=input_file,
                status=ProcessingStatus.FAILED,
                processing_time=processing_time,
                file_size_input=input_size,
                error=e
            )