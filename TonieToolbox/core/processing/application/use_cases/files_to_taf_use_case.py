#!/usr/bin/env python3
"""
Files to TAF use case.

This use case handles converting multiple individual files to separate TAF files.
"""

from pathlib import Path
from typing import Optional, Callable, List
import time
import concurrent.futures
from threading import Lock

from ...domain import ProcessingOperation, ProcessingResult
from ...domain.models.processing_result import ProcessedFile, ProcessingStatus
from ..interfaces.media_converter import ConversionProgress
from .base_use_case import BaseUseCase


class FilesToTafUseCase(BaseUseCase):
    """
    Use case for converting multiple files to separate TAF files.
    
    Supports parallel processing and batch optimization.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize with thread safety for parallel processing."""
        super().__init__(*args, **kwargs)
        self._progress_lock = Lock()
        self._current_progress = {
            'completed_files': 0,
            'total_files': 0,
            'current_operations': {}
        }
    
    def execute(self, operation: ProcessingOperation,
               progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute files-to-TAF conversion operation.
        
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
        
        self.logger.info(f"Starting files-to-TAF conversion: {operation.operation_id}")
        self._publish_started_event(operation)
        
        try:
            # Resolve input files
            input_files = operation.input_spec.resolve_files()
            if not input_files:
                raise ValueError("No input files found")
            
            self.logger.info(f"Converting {len(input_files)} files to separate TAF files")
            
            # Initialize progress tracking
            with self._progress_lock:
                self._current_progress = {
                    'completed_files': 0,
                    'total_files': len(input_files),
                    'current_operations': {}
                }
            
            # Determine if we should use parallel processing
            max_workers = min(operation.options.max_parallel_jobs, len(input_files))
            use_parallel = max_workers > 1 and len(input_files) > 1
            
            if use_parallel:
                self.logger.info(f"Using parallel processing with {max_workers} workers")
                self._execute_parallel_conversions(operation, input_files, result, progress_callback, max_workers)
            else:
                self.logger.info("Using sequential processing")
                self._execute_sequential_conversions(operation, input_files, result, progress_callback)
            
            operation.mark_completed()
            self._publish_completed_event(operation, result)
            
        except Exception as e:
            self.logger.error(f"Files-to-TAF conversion failed: {str(e)}")
            result.mark_failed(e)
            operation.mark_completed()
            self._publish_failed_event(operation, e)
        
        return self._finalize_result(operation, result)
    
    def _execute_sequential_conversions(self, operation: ProcessingOperation,
                                      input_files: List[Path], result: ProcessingResult,
                                      progress_callback: Optional[Callable] = None) -> None:
        """Execute sequential file conversions."""
        total_files = len(input_files)
        
        for i, input_file in enumerate(input_files):
            self._update_progress(progress_callback, f"Processing {input_file.name}", i / total_files)
            
            try:
                processed_file = self._convert_single_file(
                    operation, 
                    input_file, 
                    lambda p: self._update_file_progress(progress_callback, input_file.name, p)
                )
                result.add_processed_file(processed_file)
                
                with self._progress_lock:
                    self._current_progress['completed_files'] += 1
                
                if processed_file.is_successful:
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
                
                with self._progress_lock:
                    self._current_progress['completed_files'] += 1
                
                if not operation.options.continue_on_error:
                    break
        
        self._update_progress(progress_callback, "Conversion complete", 1.0)
        
        completed = sum(1 for f in result.processed_files if f.is_successful)
        self.logger.info(f"Sequential conversion complete: {completed}/{total_files} successful")
    
    def _execute_parallel_conversions(self, operation: ProcessingOperation,
                                    input_files: List[Path], result: ProcessingResult,
                                    progress_callback: Optional[Callable] = None,
                                    max_workers: int = 4) -> None:
        """Execute parallel file conversions."""
        total_files = len(input_files)
        results_lock = Lock()
        
        def process_file(input_file: Path) -> ProcessedFile:
            """Process single file in parallel."""
            try:
                return self._convert_single_file(
                    operation,
                    input_file,
                    lambda p: self._update_parallel_file_progress(progress_callback, input_file.name, p)
                )
            except Exception as e:
                return ProcessedFile(
                    input_path=input_file,
                    status=ProcessingStatus.FAILED,
                    error=e
                )
        
        # Execute conversions in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {executor.submit(process_file, f): f for f in input_files}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                input_file = future_to_file[future]
                
                try:
                    processed_file = future.result()
                    
                    with results_lock:
                        result.add_processed_file(processed_file)
                    
                    with self._progress_lock:
                        self._current_progress['completed_files'] += 1
                        completed = self._current_progress['completed_files']
                        progress = completed / total_files
                    
                    self._update_progress(
                        progress_callback, 
                        f"Completed {input_file.name}", 
                        progress
                    )
                    
                    if processed_file.is_successful:
                        self.logger.debug(f"Converted {input_file} successfully")
                    else:
                        self.logger.warning(f"Failed to convert {input_file}: {processed_file.error}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing {input_file}: {str(e)}")
                    
                    with results_lock:
                        failed_file = ProcessedFile(
                            input_path=input_file,
                            status=ProcessingStatus.FAILED,
                            error=e
                        )
                        result.add_processed_file(failed_file)
                    
                    with self._progress_lock:
                        self._current_progress['completed_files'] += 1
        
        self._update_progress(progress_callback, "Parallel conversion complete", 1.0)
        
        completed = sum(1 for f in result.processed_files if f.is_successful)
        self.logger.info(f"Parallel conversion complete: {completed}/{total_files} successful")
    
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
                progress_callback(progress)
        
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
    
    def _update_progress(self, progress_callback: Optional[Callable], 
                        operation: str, progress: float):
        """Update overall progress."""
        if not progress_callback:
            return
        
        with self._progress_lock:
            progress_callback({
                'operation': operation,
                'progress': progress,
                'files_completed': self._current_progress['completed_files'],
                'total_files': self._current_progress['total_files']
            })
    
    def _update_file_progress(self, progress_callback: Optional[Callable],
                            filename: str, file_progress: ConversionProgress):
        """Update progress for single file conversion."""
        if not progress_callback:
            return
        
        with self._progress_lock:
            overall_progress = (
                self._current_progress['completed_files'] + file_progress.overall_progress
            ) / self._current_progress['total_files']
            
            progress_callback({
                'operation': f"Converting {filename}",
                'progress': overall_progress,
                'files_completed': self._current_progress['completed_files'],
                'total_files': self._current_progress['total_files'],
                'current_file': filename,
                'current_file_progress': file_progress.overall_progress
            })
    
    def _update_parallel_file_progress(self, progress_callback: Optional[Callable],
                                     filename: str, file_progress: ConversionProgress):
        """Update progress for parallel file conversion."""
        if not progress_callback:
            return
        
        with self._progress_lock:
            # Track individual file progress
            self._current_progress['current_operations'][filename] = file_progress.overall_progress
            
            # Calculate overall progress including in-progress files
            completed = self._current_progress['completed_files']
            in_progress = sum(self._current_progress['current_operations'].values())
            total = self._current_progress['total_files']
            
            overall_progress = (completed + in_progress) / total if total > 0 else 0
            
            progress_callback({
                'operation': f"Converting {len(self._current_progress['current_operations'])} files in parallel",
                'progress': overall_progress,
                'files_completed': completed,
                'total_files': total,
                'parallel_operations': len(self._current_progress['current_operations'])
            })