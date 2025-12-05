#!/usr/bin/env python3
"""
Unit tests for processing domain models.

Tests ProcessingResult, ProcessedFile, and ProcessingStatus.
"""

import pytest
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Mock aiofiles to avoid import errors from infrastructure layer
sys.modules['aiofiles'] = MagicMock()

from TonieToolbox.core.processing.domain.models.processing_result import (
    ProcessingResult,
    ProcessedFile,
    ProcessingStatus
)


class TestProcessingStatus:
    """Test ProcessingStatus enum."""
    
    def test_status_values_exist(self):
        """Test all expected status values exist."""
        assert ProcessingStatus.NOT_STARTED
        assert ProcessingStatus.IN_PROGRESS
        assert ProcessingStatus.COMPLETED
        assert ProcessingStatus.FAILED
        assert ProcessingStatus.CANCELLED
        assert ProcessingStatus.PARTIALLY_COMPLETED
    
    def test_status_comparison(self):
        """Test status enum comparison."""
        assert ProcessingStatus.COMPLETED != ProcessingStatus.FAILED
        assert ProcessingStatus.NOT_STARTED == ProcessingStatus.NOT_STARTED


class TestProcessedFile:
    """Test ProcessedFile model."""
    
    def test_create_processed_file(self):
        """Test creating a ProcessedFile instance."""
        input_path = Path("/test/input.mp3")
        file = ProcessedFile(input_path=input_path)
        
        assert file.input_path == input_path
        assert file.status == ProcessingStatus.NOT_STARTED
        assert file.error is None
    
    def test_is_successful_when_completed(self):
        """Test is_successful returns True for completed file."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            status=ProcessingStatus.COMPLETED
        )
        
        assert file.is_successful is True
    
    def test_is_successful_when_failed(self):
        """Test is_successful returns False for failed file."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            status=ProcessingStatus.FAILED,
            error=ValueError("Test error")
        )
        
        assert file.is_successful is False
    
    def test_is_successful_with_error(self):
        """Test is_successful returns False even if completed with error."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            status=ProcessingStatus.COMPLETED,
            error=ValueError("Test error")
        )
        
        assert file.is_successful is False
    
    def test_compression_ratio_with_sizes(self):
        """Test compression ratio calculation."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            file_size_input=1000,
            file_size_output=500
        )
        
        assert file.compression_ratio == 0.5
    
    def test_compression_ratio_without_sizes(self):
        """Test compression ratio returns None without sizes."""
        file = ProcessedFile(input_path=Path("/test/input.mp3"))
        assert file.compression_ratio is None
    
    def test_string_representation(self):
        """Test string representation of processed file."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            status=ProcessingStatus.COMPLETED
        )
        
        str_repr = str(file)
        assert "input.mp3" in str_repr
        assert "completed" in str_repr.lower()


class TestProcessingResult:
    """Test ProcessingResult model."""
    
    def test_create_processing_result(self):
        """Test creating a ProcessingResult instance."""
        result = ProcessingResult(operation_id="test-123")
        
        assert result.operation_id == "test-123"
        assert result.status == ProcessingStatus.NOT_STARTED
        assert len(result.processed_files) == 0
        assert result.error_count == 0
    
    def test_add_processed_file(self):
        """Test adding processed files to result."""
        result = ProcessingResult(operation_id="test-123")
        
        file1 = ProcessedFile(input_path=Path("/test/file1.mp3"))
        file2 = ProcessedFile(input_path=Path("/test/file2.mp3"))
        
        result.add_processed_file(file1)
        result.add_processed_file(file2)
        
        assert len(result.processed_files) == 2
    
    def test_add_processed_file_updates_metrics(self):
        """Test adding file updates metrics."""
        result = ProcessingResult(operation_id="test-123")
        
        file = ProcessedFile(
            input_path=Path("/test/file.mp3"),
            file_size_input=1000,
            file_size_output=500
        )
        
        result.add_processed_file(file)
        
        assert result.total_input_size == 1000
        assert result.total_output_size == 500
    
    def test_started_at_timestamp(self):
        """Test setting started_at timestamp."""
        result = ProcessingResult(
            operation_id="test-123",
            started_at=datetime.now()
        )
        
        assert result.started_at is not None
        assert isinstance(result.started_at, datetime)
    
    def test_completed_at_timestamp(self):
        """Test setting completed_at timestamp."""
        now = datetime.now()
        result = ProcessingResult(
            operation_id="test-123",
            completed_at=now
        )
        
        assert result.completed_at == now
    
    def test_operation_error(self):
        """Test setting operation error."""
        error = ValueError("Test error")
        result = ProcessingResult(
            operation_id="test-123",
            operation_error=error
        )
        
        assert result.operation_error == error
    
    def test_error_count(self):
        """Test tracking error count."""
        result = ProcessingResult(
            operation_id="test-123",
            error_count=3
        )
        
        assert result.error_count == 3


class TestProcessingResultMethods:
    """Test ProcessingResult computed properties and methods."""
    
    def test_mark_started(self):
        """Test marking operation as started."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        assert result.status == ProcessingStatus.IN_PROGRESS
        assert result.started_at is not None
        assert isinstance(result.started_at, datetime)
    
    def test_mark_completed_success(self):
        """Test marking completed with all success."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        file = ProcessedFile(
            input_path=Path("/test/file.mp3"),
            status=ProcessingStatus.COMPLETED
        )
        result.add_processed_file(file)
        
        result.mark_completed()
        
        assert result.status == ProcessingStatus.COMPLETED
        assert result.completed_at is not None
    
    def test_mark_completed_partial(self):
        """Test marking completed with partial success."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        file1 = ProcessedFile(
            input_path=Path("/test/file1.mp3"),
            status=ProcessingStatus.COMPLETED
        )
        file2 = ProcessedFile(
            input_path=Path("/test/file2.mp3"),
            status=ProcessingStatus.FAILED,
            error=ValueError("Error")
        )
        
        result.add_processed_file(file1)
        result.add_processed_file(file2)
        
        result.mark_completed()
        
        assert result.status == ProcessingStatus.PARTIALLY_COMPLETED
    
    def test_mark_failed(self):
        """Test marking operation as failed."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        error = ValueError("Test error")
        result.mark_failed(error)
        
        assert result.status == ProcessingStatus.FAILED
        assert result.operation_error == error
        assert result.completed_at is not None
    
    def test_mark_cancelled(self):
        """Test marking operation as cancelled."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        result.mark_cancelled()
        
        assert result.status == ProcessingStatus.CANCELLED
        assert result.completed_at is not None
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        result = ProcessingResult(operation_id="test-123")
        result.mark_started()
        
        # Simulate some processing time
        import time
        time.sleep(0.1)
        
        result.mark_completed()
        
        assert result.duration is not None
        assert result.duration >= 0.1
    
    def test_duration_none_without_timestamps(self):
        """Test duration returns None without timestamps."""
        result = ProcessingResult(operation_id="test-123")
        assert result.duration is None
    
    def test_success_count(self):
        """Test counting successful files."""
        result = ProcessingResult(operation_id="test-123")
        
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file1.mp3"),
            status=ProcessingStatus.COMPLETED
        ))
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file2.mp3"),
            status=ProcessingStatus.FAILED,
            error=ValueError("Error")
        ))
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file3.mp3"),
            status=ProcessingStatus.COMPLETED
        ))
        
        assert result.success_count == 2
    
    def test_failure_count(self):
        """Test counting failed files."""
        result = ProcessingResult(operation_id="test-123")
        
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file1.mp3"),
            status=ProcessingStatus.COMPLETED
        ))
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file2.mp3"),
            status=ProcessingStatus.FAILED,
            error=ValueError("Error")
        ))
        result.add_processed_file(ProcessedFile(
            input_path=Path("/test/file3.mp3"),
            status=ProcessingStatus.FAILED,
            error=ValueError("Error")
        ))
        
        assert result.failure_count == 2
        assert result.error_count == 2


class TestProcessedFileMetadata:
    """Test ProcessedFile metadata handling."""
    
    def test_metadata_empty_by_default(self):
        """Test metadata dictionary is empty by default."""
        file = ProcessedFile(input_path=Path("/test/input.mp3"))
        assert file.metadata == {}
    
    def test_add_metadata(self):
        """Test adding metadata to processed file."""
        file = ProcessedFile(
            input_path=Path("/test/input.mp3"),
            metadata={"bitrate": 320, "duration": 180}
        )
        
        assert file.metadata["bitrate"] == 320
        assert file.metadata["duration"] == 180
    
    def test_modify_metadata(self):
        """Test modifying metadata after creation."""
        file = ProcessedFile(input_path=Path("/test/input.mp3"))
        file.metadata["format"] = "mp3"
        file.metadata["codec"] = "libmp3lame"
        
        assert len(file.metadata) == 2
        assert file.metadata["format"] == "mp3"
