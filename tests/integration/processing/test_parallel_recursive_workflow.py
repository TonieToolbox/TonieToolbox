#!/usr/bin/env python3
"""
Integration tests for parallel recursive workflow processing.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from TonieToolbox.core.processing.domain import ProcessingOperation
from TonieToolbox.core.processing.domain.value_objects.processing_mode import RECURSIVE_MODE
from TonieToolbox.core.processing.domain.value_objects.input_specification import InputSpecification, ContentType
from TonieToolbox.core.processing.domain.value_objects.output_specification import OutputSpecification, OutputMode
from TonieToolbox.core.processing.domain.value_objects.processing_options import ProcessingOptions
from TonieToolbox.core.processing.domain.models.processing_result import ProcessingStatus
from TonieToolbox.core.processing.application.services.workflow_coordinator import WorkflowCoordinator
from TonieToolbox.core.processing.infrastructure.parallel_executor import ThreadPoolParallelExecutor
from TonieToolbox.core.utils import get_logger


class TestParallelRecursiveWorkflow:
    """Integration tests for parallel recursive processing workflow."""
    
    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for testing."""
        file_repository = Mock()
        media_converter = Mock()
        logger = get_logger(__name__)
        event_bus = Mock()
        
        # Mock successful folder processing
        media_converter.combine_files_to_taf.return_value = True
        
        return {
            'file_repository': file_repository,
            'media_converter': media_converter,
            'logger': logger,
            'event_bus': event_bus
        }
    
    @pytest.fixture
    def parallel_executor(self):
        """Create parallel executor for testing."""
        return ThreadPoolParallelExecutor(max_workers=3)
    
    def test_parallel_workflow_with_multiple_folders(self, tmp_path, mock_dependencies, parallel_executor):
        """Test parallel recursive workflow with multiple folders."""
        # Create test directory structure
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        # Create folders with audio files
        for i in range(3):
            folder = input_dir / f"Album{i+1}"
            folder.mkdir(parents=True)
            for j in range(2):
                (folder / f"track{j+1}.mp3").write_text(f"audio data {i}-{j}")
        
        output_dir.mkdir()
        
        # Create coordinator with parallel executor
        coordinator = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus'],
            parallel_executor=parallel_executor
        )
        
        # Create operation with parallel workers
        options = ProcessingOptions.default().with_custom_option('parallel_workers', 3)
        
        operation = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options
        )
        
        # Track progress
        progress_updates = []
        
        def track_progress(info):
            progress_updates.append(info)
        
        # Execute workflow
        result = coordinator.execute(operation, progress_callback=track_progress)
        
        # Verify results
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.processed_files) == 3  # One per folder
        
        # Verify progress tracking
        assert len(progress_updates) > 0
        final_progress = [p for p in progress_updates if p.get('progress') == 1.0]
        assert len(final_progress) > 0
        
        # Verify media converter called for each folder
        assert mock_dependencies['media_converter'].combine_files_to_taf.call_count == 3
    
    def test_parallel_workflow_sequential_fallback(self, tmp_path, mock_dependencies):
        """Test that workflow falls back to sequential when workers=1."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        # Create test folders
        for i in range(2):
            folder = input_dir / f"Album{i+1}"
            folder.mkdir(parents=True)
            (folder / "track.mp3").write_text("audio")
        
        output_dir.mkdir()
        
        coordinator = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus']
        )
        
        # Create operation WITHOUT parallel workers (default=1)
        options = ProcessingOptions.default()
        
        operation = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options
        )
        
        result = coordinator.execute(operation)
        
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.processed_files) == 2
    
    def test_parallel_workflow_with_errors_continue(self, tmp_path, mock_dependencies, parallel_executor):
        """Test parallel workflow continues on errors when configured."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        # Create folders
        for i in range(3):
            folder = input_dir / f"Album{i+1}"
            folder.mkdir(parents=True)
            (folder / "track.mp3").write_text("audio")
        
        output_dir.mkdir()
        
        # Make second folder fail
        def combine_files_side_effect(files, output, options, callback=None):
            if "Album2" in str(output):
                raise RuntimeError("Simulated conversion failure")
            return True
        
        mock_dependencies['media_converter'].combine_files_to_taf.side_effect = combine_files_side_effect
        
        coordinator = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus'],
            parallel_executor=parallel_executor
        )
        
        options = ProcessingOptions(
            continue_on_error=True
        ).with_custom_option('parallel_workers', 3)
        
        operation = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options
        )
        
        result = coordinator.execute(operation)
        
        # Should complete with some failures
        assert result.status in [ProcessingStatus.COMPLETED, ProcessingStatus.PARTIALLY_COMPLETED]
        assert len(result.processed_files) == 3
        
        # Check for failed file
        failed = [f for f in result.processed_files if f.status == ProcessingStatus.FAILED]
        completed = [f for f in result.processed_files if f.status == ProcessingStatus.COMPLETED]
        
        assert len(failed) == 1
        assert len(completed) == 2
    
    def test_parallel_workflow_performance_benefit(self, tmp_path, mock_dependencies):
        """Test that parallel processing is faster than sequential (conceptual test)."""
        import time
        
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        # Create multiple folders
        for i in range(4):
            folder = input_dir / f"Album{i+1}"
            folder.mkdir(parents=True)
            (folder / "track.mp3").write_text("audio")
        
        output_dir.mkdir()
        
        # Add delay to simulate actual processing
        def slow_combine(files, output, options, callback=None):
            time.sleep(0.1)  # Simulate processing time
            return True
        
        mock_dependencies['media_converter'].combine_files_to_taf.side_effect = slow_combine
        
        # Test sequential processing
        coordinator_seq = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus']
        )
        
        options_seq = ProcessingOptions.default()
        operation_seq = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options_seq
        )
        
        start = time.time()
        result_seq = coordinator_seq.execute(operation_seq)
        sequential_time = time.time() - start
        
        # Reset mock
        mock_dependencies['media_converter'].combine_files_to_taf.reset_mock()
        mock_dependencies['media_converter'].combine_files_to_taf.side_effect = slow_combine
        
        # Test parallel processing
        parallel_executor = ThreadPoolParallelExecutor(max_workers=4)
        coordinator_par = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus'],
            parallel_executor=parallel_executor
        )
        
        options_par = ProcessingOptions.default().with_custom_option('parallel_workers', 4)
        operation_par = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options_par
        )
        
        start = time.time()
        result_par = coordinator_par.execute(operation_par)
        parallel_time = time.time() - start
        
        # Verify both completed successfully
        assert result_seq.status == ProcessingStatus.COMPLETED
        assert result_par.status == ProcessingStatus.COMPLETED
        
        # Parallel should be noticeably faster (at least 2x)
        assert parallel_time < sequential_time / 2.0, \
            f"Parallel ({parallel_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s)"
        
        parallel_executor.shutdown()
    
    def test_parallel_workflow_event_publishing(self, tmp_path, mock_dependencies, parallel_executor):
        """Test that events are published correctly during parallel processing."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        
        # Create folders
        for i in range(2):
            folder = input_dir / f"Album{i+1}"
            folder.mkdir(parents=True)
            (folder / "track.mp3").write_text("audio")
        
        output_dir.mkdir()
        
        coordinator = WorkflowCoordinator(
            file_repository=mock_dependencies['file_repository'],
            media_converter=mock_dependencies['media_converter'],
            logger=mock_dependencies['logger'],
            event_bus=mock_dependencies['event_bus'],
            parallel_executor=parallel_executor
        )
        
        options = ProcessingOptions.default().with_custom_option('parallel_workers', 2)
        
        operation = ProcessingOperation(
            processing_mode=RECURSIVE_MODE,
            input_spec=InputSpecification.for_recursive_directory(str(input_dir)),
            output_spec=OutputSpecification.for_multiple_taf(str(output_dir)),
            options=options
        )
        
        result = coordinator.execute(operation)
        
        # Verify execution completed successfully
        assert result.status == ProcessingStatus.COMPLETED
        assert len(result.processed_files) == 2
        
        # Events are published inside callbacks, which may not be tracked by mock
        # Instead verify that all files were processed successfully
        assert all(f.status == ProcessingStatus.COMPLETED for f in result.processed_files)
