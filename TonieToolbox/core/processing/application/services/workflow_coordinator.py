#!/usr/bin/env python3
"""
Workflow coordinator service.

This service handles complex workflows that involve multiple processing steps,
such as recursive directory processing and batch operations.
"""

from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
import logging
import time

from ...domain import ProcessingOperation, ProcessingResult, ProcessingModeType
from ...domain.models.processing_result import ProcessedFile, ProcessingStatus
from ....events import FileProcessingCompletedEvent
from ..interfaces.file_repository import FileRepository
from ..interfaces.media_converter import MediaConverter
from ..interfaces.upload_service import UploadService
from ..use_cases.base_use_case import BaseUseCase
from ...infrastructure.parallel_executor import ParallelExecutor, create_parallel_executor


class WorkflowCoordinator(BaseUseCase):
    """
    Coordinates complex workflows involving multiple processing steps.
    
    Handles recursive directory processing, batch operations, and multi-step processing
    workflows. Provides progress tracking, error handling, and event publishing for
    long-running operations that process multiple files or directories.
    
    Supports both sequential and parallel execution modes. Parallel execution can be
    configured via the operation's parallel_workers option and uses a ParallelExecutor
    that works in both CLI and GUI contexts.
    
    Example:
        >>> from pathlib import Path
        >>> from TonieToolbox.core.processing.domain import ProcessingOperation, ProcessingMode
        >>> from TonieToolbox.core.processing.domain import InputSpecification, OutputSpecification
        >>> from TonieToolbox.core.utils import get_logger
        >>> 
        >>> # Setup coordinator with dependencies
        >>> logger = get_logger(__name__)
        >>> coordinator = WorkflowCoordinator(
        ...     file_repository=file_repo,
        ...     media_converter=converter,
        ...     logger=logger,
        ...     event_bus=event_bus
        ... )
        >>> 
        >>> # Create recursive processing operation with parallel workers
        >>> operation = ProcessingOperation(
        ...     input_spec=InputSpecification(input_path=Path('/music/audiobooks')),
        ...     output_spec=OutputSpecification(output_directory=Path('/output')),
        ...     processing_mode=ProcessingMode.RECURSIVE,
        ...     options={'parallel_workers': 4}
        ... )
        >>> 
        >>> # Execute with progress tracking
        >>> def on_progress(info):
        ...     print(f"Progress: {info['progress']*100:.1f}% - {info['operation']}")
        >>> 
        >>> result = coordinator.execute(operation, progress_callback=on_progress)
        >>> print(f"Processed {len(result.processed_files)} files")
        Progress: 33.3% - Processing folder Book1
        Progress: 66.7% - Processing folder Book2
        Progress: 100.0% - Recursive processing complete
        Processed 2 files
    """
    
    def __init__(self, file_repository: FileRepository, media_converter: MediaConverter,
                 logger: logging.Logger, event_bus, dependencies: Optional[Dict[str, Any]] = None,
                 parallel_executor: Optional[ParallelExecutor] = None):
        """
        Initialize workflow coordinator.
        
        Args:
            file_repository: File repository for file operations
            media_converter: Media converter for audio processing
            logger: Logger instance
            event_bus: Event bus for publishing events
            dependencies: Optional dependencies dictionary
            parallel_executor: Optional ParallelExecutor for parallel processing.
                             If not provided, will create one when needed based on worker count.
        """
        super().__init__(logger, event_bus, dependencies)
        self.file_repository = file_repository
        self.media_converter = media_converter
        self.parallel_executor = parallel_executor
    
    def execute(self, operation: ProcessingOperation,
               progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Execute workflow coordination.
        
        Args:
            operation: Processing operation to execute
            progress_callback: Optional callback for progress updates
            
        Returns:
            ProcessingResult with workflow results
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
        
        self.logger.info(f"Starting workflow coordination: {operation.operation_id}")
        self._publish_started_event(operation)
        
        try:
            # Route to appropriate workflow based on processing mode
            if operation.processing_mode.mode_type == ProcessingModeType.RECURSIVE:
                self._execute_recursive_workflow(operation, result, progress_callback)
            else:
                raise ValueError(f"Unsupported workflow mode: {operation.processing_mode.name}")
            
            operation.mark_completed()
            self._publish_completed_event(operation, result)
            
        except Exception as e:
            self.logger.error(f"Workflow coordination failed: {str(e)}")
            result.mark_failed(e)
            operation.mark_completed()
            self._publish_failed_event(operation, e)
        
        return self._finalize_result(operation, result)
    
    def _execute_recursive_workflow(self, operation: ProcessingOperation, 
                                   result: ProcessingResult,
                                   progress_callback: Optional[Callable] = None) -> None:
        """
        Execute recursive directory processing workflow.
        
        Automatically selects between sequential and parallel execution based on
        the parallel_workers option in the operation.
        """
        worker_count = operation.options.get_custom_option('parallel_workers', 1)
        
        if worker_count > 1:
            self.logger.info(f"Executing recursive workflow with {worker_count} parallel workers")
            self._execute_recursive_workflow_parallel(
                operation, result, progress_callback, worker_count
            )
        else:
            self.logger.info("Executing recursive workflow sequentially")
            self._execute_recursive_workflow_sequential(
                operation, result, progress_callback
            )
    
    def _execute_recursive_workflow_sequential(self, operation: ProcessingOperation, 
                                              result: ProcessingResult,
                                              progress_callback: Optional[Callable] = None) -> None:
        """Execute recursive directory processing workflow sequentially (original implementation)."""
        self.logger.info("Executing sequential recursive directory processing workflow")
        
        # Start timing
        start_time = time.time()
        
        # Discover directory structure
        directory_structure = self._discover_directory_structure(operation)
        
        if not directory_structure:
            raise ValueError("No processing folders found in directory structure")
        
        self.logger.info(f"Found {len(directory_structure)} folders to process")
        
        # Process each folder
        total_folders = len(directory_structure)
        completed_folders = 0
        
        for folder_info in directory_structure:
            if progress_callback:
                progress_callback({
                    'operation': f'Processing folder {folder_info["name"]}',
                    'progress': completed_folders / total_folders,
                    'folders_completed': completed_folders,
                    'total_folders': total_folders,
                    'current_folder': folder_info['name']
                })
            
            try:
                folder_result = self._process_folder(operation, folder_info, progress_callback)
                
                # Merge folder result into overall result
                for processed_file in folder_result.processed_files:
                    result.add_processed_file(processed_file)
                
                completed_folders += 1
                self.logger.debug(f"Processed folder {folder_info['name']} successfully")
                
            except Exception as e:
                self.logger.error(f"Error processing folder {folder_info['name']}: {str(e)}")
                
                # Create failed processed file entry for the folder
                failed_file = ProcessedFile(
                    input_path=Path(folder_info['path']),
                    status=ProcessingStatus.FAILED,
                    error=e,
                    metadata={'folder_name': folder_info['name']}
                )
                result.add_processed_file(failed_file)
                
                completed_folders += 1
                
                # Continue processing other folders if configured
                if not operation.options.continue_on_error:
                    break
        
        if progress_callback:
            progress_callback({
                'operation': 'Recursive processing complete',
                'progress': 1.0,
                'folders_completed': completed_folders,
                'total_folders': total_folders
            })
        
        # Calculate duration
        duration = time.time() - start_time
        
        self.logger.info(f"Sequential recursive workflow complete: {completed_folders}/{total_folders} folders processed")
        
        # Print beautiful summary table
        self._print_processing_summary(result, worker_count=1, duration=duration)
    
    def _execute_recursive_workflow_parallel(self, operation: ProcessingOperation, 
                                            result: ProcessingResult,
                                            progress_callback: Optional[Callable] = None,
                                            worker_count: int = 4) -> None:
        """
        Execute recursive directory processing workflow with parallel workers.
        
        Uses ParallelExecutor to process multiple folders concurrently, providing
        significant performance improvements for batch processing operations.
        
        Args:
            operation: Processing operation
            result: Processing result to populate
            progress_callback: Optional progress callback
            worker_count: Number of parallel workers to use
        """
        self.logger.info(f"Executing parallel recursive workflow with {worker_count} workers")
        
        # Start timing
        start_time = time.time()
        
        # Discover directory structure
        directory_structure = self._discover_directory_structure(operation)
        
        if not directory_structure:
            raise ValueError("No processing folders found in directory structure")
        
        self.logger.info(f"Found {len(directory_structure)} folders to process in parallel")
        
        # Create or use injected parallel executor
        executor = self.parallel_executor or create_parallel_executor(max_workers=worker_count)
        
        try:
            # Define progress handler
            def on_progress(completed: int, total: int):
                if progress_callback:
                    progress_callback({
                        'operation': f'Processing folders in parallel ({worker_count} workers)',
                        'progress': completed / total,
                        'folders_completed': completed,
                        'total_folders': total
                    })
            
            # Define completion handler for each folder
            def on_folder_complete(folder_result_dict: Dict[str, Any]):
                """Handle completion of individual folder processing."""
                # Convert dict result to ProcessedFile
                processed_file = ProcessedFile(
                    input_path=Path(folder_result_dict['input_path']),
                    output_path=Path(folder_result_dict['output_path']) if folder_result_dict.get('output_path') else None,
                    status=ProcessingStatus[folder_result_dict['status'].upper()],
                    file_size_input=folder_result_dict.get('file_size_input', 0),
                    file_size_output=folder_result_dict.get('file_size_output', 0),
                    metadata=folder_result_dict.get('metadata', {})
                )
                result.add_processed_file(processed_file)
                
                # Publish event for this folder
                self.event_bus.publish(FileProcessingCompletedEvent(
                    source='WorkflowCoordinator',
                    operation_id=operation.operation_id,
                    input_file=Path(folder_result_dict['input_path']),
                    output_file=Path(folder_result_dict['output_path']) if folder_result_dict.get('output_path') else Path('/dev/null'),
                    success=folder_result_dict['status'] == 'completed'
                ))
            
            # Execute batch processing
            folder_results = executor.execute_batch(
                task=lambda folder_info: self._process_folder_for_parallel(operation, folder_info),
                items=directory_structure,
                on_progress=on_progress,
                on_item_complete=on_folder_complete,
                continue_on_error=operation.options.continue_on_error
            )
            
            # Final progress callback
            if progress_callback:
                progress_callback({
                    'operation': 'Parallel recursive processing complete',
                    'progress': 1.0,
                    'folders_completed': len(folder_results),
                    'total_folders': len(directory_structure)
                })
            
            # Calculate duration
            duration = time.time() - start_time
            
            self.logger.info(f"Parallel recursive workflow complete: {len(folder_results)}/{len(directory_structure)} folders processed")
            
            # Print beautiful summary table
            self._print_processing_summary(result, worker_count, duration)
            
        finally:
            # Only shutdown if we created the executor (not injected)
            if not self.parallel_executor:
                executor.shutdown()
    
    def _process_folder_for_parallel(self, operation: ProcessingOperation, 
                                    folder_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single folder and return serializable result dictionary.
        
        This method wraps _process_folder() to return a plain dictionary suitable
        for parallel processing. The dictionary can be serialized and passed between
        threads/processes.
        
        Args:
            operation: Processing operation
            folder_info: Folder information dictionary
            
        Returns:
            Dictionary with processing result (status, paths, metadata)
        """
        try:
            # Process folder using existing method
            folder_result = self._process_folder(operation, folder_info, None)
            
            # Extract first processed file from result
            processed_file = folder_result.processed_files[0] if folder_result.processed_files else None
            
            if processed_file:
                return {
                    'status': 'completed' if processed_file.status == ProcessingStatus.COMPLETED else 'failed',
                    'folder_name': folder_info['name'],
                    'input_path': str(folder_info['path']),
                    'output_path': str(processed_file.output_path) if processed_file.output_path else None,
                    'file_count': folder_info['file_count'],
                    'file_size_input': processed_file.file_size_input or 0,
                    'file_size_output': processed_file.file_size_output or 0,
                    'metadata': {
                        'folder_info': folder_info,
                        'relative_path': folder_info['relative_path']
                    }
                }
            else:
                # No files processed
                return {
                    'status': 'failed',
                    'folder_name': folder_info['name'],
                    'input_path': str(folder_info['path']),
                    'output_path': None,
                    'file_count': folder_info['file_count'],
                    'error': 'No files processed'
                }
                
        except Exception as e:
            self.logger.error(f"Folder processing failed for {folder_info['name']}: {e}")
            return {
                'status': 'failed',
                'folder_name': folder_info['name'],
                'input_path': str(folder_info['path']),
                'output_path': None,
                'file_count': folder_info['file_count'],
                'error': str(e),
                'metadata': {'folder_info': folder_info}
            }
    
    def _discover_directory_structure(self, operation: ProcessingOperation) -> List[Dict[str, Any]]:
        """
        Discover directory structure for recursive processing.
        
        Args:
            operation: Processing operation
            
        Returns:
            List of folder information dictionaries
        """
        root_directory = Path(operation.input_spec.input_path)
        
        if not root_directory.exists() or not root_directory.is_dir():
            raise ValueError(f"Root directory does not exist: {root_directory}")
        
        folders = []
        
        # Find all directories that contain audio files
        for item in root_directory.rglob('*'):
            if item.is_dir():
                # Check if directory contains audio files
                audio_files = self._find_audio_files_in_directory(item)
                
                if audio_files:
                    folder_info = {
                        'path': str(item),
                        'name': item.name,
                        'relative_path': str(item.relative_to(root_directory)),
                        'audio_files': audio_files,
                        'file_count': len(audio_files),
                        'total_size': sum(f.stat().st_size for f in audio_files if f.exists())
                    }
                    folders.append(folder_info)
        
        # Sort folders by path to ensure consistent processing order
        folders.sort(key=lambda f: f['relative_path'])
        
        # Apply folder filtering logic (similar to original recursive.py)
        filtered_folders = self._filter_processing_folders(folders)
        
        return filtered_folders
    
    def _find_audio_files_in_directory(self, directory: Path) -> List[Path]:
        """Find audio files in a specific directory (non-recursive)."""
        audio_extensions = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus'}
        audio_files = []
        
        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix.lower() in audio_extensions:
                    audio_files.append(item)
        except Exception as e:
            self.logger.warning(f"Error reading directory {directory}: {str(e)}")
        
        return sorted(audio_files)
    
    def _filter_processing_folders(self, folders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter folders to determine which should be processed.
        
        This implements logic similar to determine_processing_folders from recursive.py
        to avoid processing parent folders when child folders exist.
        """
        if not folders:
            return []
        
        # Create path-based lookup
        folder_by_path = {f['path']: f for f in folders}
        
        # Find parent-child relationships
        for folder in folders:
            folder_path = Path(folder['path'])
            folder['children'] = []
            
            # Find direct children
            for other_folder in folders:
                other_path = Path(other_folder['path'])
                
                # Check if other_path is a direct child of folder_path
                try:
                    relative = other_path.relative_to(folder_path)
                    # It's a child if it's not the same path and has only one parent
                    if str(relative) != '.' and len(relative.parts) == 1:
                        folder['children'].append(other_folder['path'])
                except ValueError:
                    # Not a child
                    pass
        
        # Determine which folders to process
        to_process = set()
        
        # First pass: mark leaf folders (no children)
        for folder in folders:
            if not folder['children']:
                to_process.add(folder['path'])
                self.logger.debug(f"Marking leaf folder for processing: {folder['path']}")
        
        # Second pass: mark parent folders if they have additional files
        for folder in folders:
            if folder['children']:
                # Count files in child folders
                child_file_count = sum(folder_by_path[child]['file_count'] 
                                     for child in folder['children'] 
                                     if child in folder_by_path)
                
                # If parent has more files than just those in processed children
                if folder['file_count'] > child_file_count:
                    to_process.add(folder['path'])
                    self.logger.debug(f"Marking parent folder for processing: {folder['path']} "
                                    f"(files: {folder['file_count']}, child files: {child_file_count})")
        
        # Return filtered list
        result = [folder for folder in folders if folder['path'] in to_process]
        
        self.logger.info(f"Filtered {len(result)} folders for processing from {len(folders)} total")
        
        return result
    
    def _process_folder(self, operation: ProcessingOperation, folder_info: Dict[str, Any],
                       progress_callback: Optional[Callable] = None) -> ProcessingResult:
        """
        Process a single folder.
        
        Args:
            operation: Processing operation
            folder_info: Folder information dictionary
            progress_callback: Optional progress callback
            
        Returns:
            ProcessingResult for the folder
        """
        folder_path = Path(folder_info['path'])
        audio_files = folder_info['audio_files']
        
        self.logger.info(f"Processing folder: {folder_path} ({len(audio_files)} files)")
        
        # Create folder-specific result
        folder_result = ProcessingResult(operation_id=f"{operation.operation_id}_folder_{folder_info['name']}")
        folder_result.mark_started()
        
        # Determine output path for this folder
        output_filename = self._determine_folder_output_filename(folder_info, operation)
        output_path = operation.output_spec.resolve_output_path(output_filename)
        
        # Prepare output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if output already exists and should be skipped
        if operation.output_spec.should_skip_existing(output_path):
            self.logger.info(f"Skipping existing output file: {output_path}")
            
            processed_file = ProcessedFile(
                input_path=folder_path,
                output_path=output_path,
                status=ProcessingStatus.COMPLETED,
                file_size_output=output_path.stat().st_size if output_path.exists() else 0,
                metadata={'folder_name': folder_info['name'], 'skipped': True}
            )
            folder_result.add_processed_file(processed_file)
            folder_result.mark_completed()
            return folder_result
        
        # Combine all audio files in the folder into single TAF
        try:
            def folder_progress_callback(conv_progress):
                if progress_callback:
                    # This is called for progress within the folder processing
                    progress_callback({
                        'operation': f'Processing {folder_info["name"]} - {conv_progress.current_operation}',
                        'folder_progress': conv_progress.overall_progress,
                        'current_file': conv_progress.current_file
                    })
            
            success = self.media_converter.combine_files_to_taf(
                audio_files,
                output_path,
                operation.options,
                folder_progress_callback
            )
            
            if success:
                # Calculate total input size
                total_input_size = sum(f.stat().st_size for f in audio_files if f.exists())
                output_size = output_path.stat().st_size if output_path.exists() else 0
                
                processed_file = ProcessedFile(
                    input_path=folder_path,
                    output_path=output_path,
                    status=ProcessingStatus.COMPLETED,
                    file_size_input=total_input_size,
                    file_size_output=output_size,
                    metadata={
                        'folder_name': folder_info['name'],
                        'input_files': [str(f) for f in audio_files],
                        'file_count': len(audio_files)
                    }
                )
                folder_result.add_processed_file(processed_file)
                
                self.logger.info(f"Successfully processed folder {folder_path} -> {output_path}")
            else:
                raise Exception("Folder processing failed")
                
        except Exception as e:
            self.logger.error(f"Failed to process folder {folder_path}: {str(e)}")
            
            failed_file = ProcessedFile(
                input_path=folder_path,
                status=ProcessingStatus.FAILED,
                error=e,
                metadata={'folder_name': folder_info['name']}
            )
            folder_result.add_processed_file(failed_file)
        
        folder_result.mark_completed()
        return folder_result
    
    def _determine_folder_output_filename(self, folder_info: Dict[str, Any], 
                                        operation: ProcessingOperation) -> str:
        """
        Determine output filename for a folder.
        
        Args:
            folder_info: Folder information dictionary
            operation: Processing operation
            
        Returns:
            Output filename string
        """
        # Try to extract meaningful name from folder
        folder_name = folder_info['name']
        
        # Clean up folder name for use as filename
        clean_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_name = clean_name.replace(' ', '_')
        
        if not clean_name:
            clean_name = f"folder_{hash(folder_info['path']) % 10000}"
        
        return f"{clean_name}.taf"    
    def _print_processing_summary(self, result: ProcessingResult, 
                                 worker_count: int, 
                                 duration: float) -> None:
        """
        Print beautiful summary table after recursive processing.
        
        Args:
            result: Processing result with all processed files
            worker_count: Number of parallel workers used
            duration: Total processing time in seconds
        """
        # Calculate statistics
        total_files = len(result.processed_files)
        successful = sum(1 for f in result.processed_files if f.status == ProcessingStatus.COMPLETED)
        failed = sum(1 for f in result.processed_files if f.status == ProcessingStatus.FAILED)
        cancelled = sum(1 for f in result.processed_files if f.status == ProcessingStatus.CANCELLED)
        
        total_input_size = sum(f.file_size_input or 0 for f in result.processed_files) / (1024 * 1024)  # MB
        total_output_size = sum(f.file_size_output or 0 for f in result.processed_files) / (1024 * 1024)  # MB
        
        # Format time
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        # Build table
        separator = "═" * 70
        line = "─" * 70
        
        # Build and print summary table directly to stdout (not through logger)
        # Using print() preserves the beautiful table formatting without logger prefix
        print()  # Blank line before table
        print(f"╔{separator}╗")
        print(f"║{'PROCESSING SUMMARY':^70}║")
        print(f"╠{separator}╣")
        print(f"║ {'Metric':<35} │ {'Value':>30} ║")
        print(f"╠{line}╣")
        print(f"║ {'Total Folders Processed':<35} │ {total_files:>30} ║")
        print(f"║ {'  ✓ Successful':<35} │ {successful:>30} ║")
        print(f"║ {'  ✗ Failed':<35} │ {failed:>30} ║")
        print(f"║ {'  ⊝ Cancelled':<35} │ {cancelled:>30} ║")
        print(f"╠{line}╣")
        print(f"║ {'Total Input Size':<35} │ {total_input_size:>27.2f} MB ║")
        print(f"║ {'Total Output Size':<35} │ {total_output_size:>27.2f} MB ║")
        print(f"║ {'Compression Ratio':<35} │ {(total_output_size / total_input_size * 100 if total_input_size > 0 else 0):>26.1f} % ║")
        print(f"╠{line}╣")
        print(f"║ {'Processing Time':<35} │ {time_str:>30} ║")
        print(f"║ {'Parallel Workers':<35} │ {worker_count:>30} ║")
        print(f"║ {'Average Time per Folder':<35} │ {(duration / total_files if total_files > 0 else 0):>27.2f} s ║")
        print(f"║ {'Throughput':<35} │ {(total_files / duration if duration > 0 else 0):>24.2f} f/min ║")
        print(f"╚{separator}╝")
        print()  # Blank line after table
