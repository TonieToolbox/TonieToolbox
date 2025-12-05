#!/usr/bin/env python3
"""
Processing result domain model.

This module defines the ProcessingResult domain model that represents
the outcome of a processing operation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from enum import Enum, auto

from ..exceptions import ProcessingDomainError


class ProcessingStatus(Enum):
    """Status of a processing operation."""
    
    NOT_STARTED = auto()     # Operation not yet started
    IN_PROGRESS = auto()     # Operation currently running
    COMPLETED = auto()       # Operation completed successfully
    FAILED = auto()          # Operation failed with errors
    CANCELLED = auto()       # Operation was cancelled
    PARTIALLY_COMPLETED = auto()  # Some files processed, others failed


@dataclass
class ProcessedFile:
    """Information about a single processed file."""
    
    input_path: Path
    output_path: Optional[Path] = None
    status: ProcessingStatus = ProcessingStatus.NOT_STARTED
    error: Optional[Exception] = None
    processing_time: Optional[float] = None
    file_size_input: Optional[int] = None
    file_size_output: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_successful(self) -> bool:
        """Check if file processing was successful."""
        return self.status == ProcessingStatus.COMPLETED and self.error is None
    
    @property
    def compression_ratio(self) -> Optional[float]:
        """Calculate compression ratio if sizes are available."""
        if self.file_size_input and self.file_size_output:
            return self.file_size_output / self.file_size_input
        return None
    
    def __str__(self) -> str:
        """String representation of processed file."""
        status_str = self.status.name.lower().replace('_', ' ')
        return f"{self.input_path.name}: {status_str}"


@dataclass
class ProcessingResult:
    """
    Domain model representing the result of a processing operation.
    
    This aggregate contains all information about what was processed,
    what succeeded, what failed, and any relevant metrics.
    """
    
    operation_id: str
    status: ProcessingStatus = ProcessingStatus.NOT_STARTED
    processed_files: List[ProcessedFile] = field(default_factory=list)
    
    # Timing information
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error information
    operation_error: Optional[Exception] = None
    error_count: int = 0
    
    # Performance metrics
    total_input_size: int = 0
    total_output_size: int = 0
    
    # Upload information (if applicable)
    upload_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Additional result data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_processed_file(self, processed_file: ProcessedFile):
        """Add a processed file to the results."""
        self.processed_files.append(processed_file)
        
        # Update metrics
        if processed_file.file_size_input:
            self.total_input_size += processed_file.file_size_input
        
        if processed_file.file_size_output:
            self.total_output_size += processed_file.file_size_output
        
        # Update error count
        if not processed_file.is_successful:
            self.error_count += 1
    
    def mark_started(self):
        """Mark processing as started."""
        self.started_at = datetime.now()
        self.status = ProcessingStatus.IN_PROGRESS
    
    def mark_completed(self):
        """Mark processing as completed and determine final status."""
        self.completed_at = datetime.now()
        
        if self.operation_error:
            self.status = ProcessingStatus.FAILED
        elif self.error_count == 0:
            self.status = ProcessingStatus.COMPLETED
        elif self.error_count < len(self.processed_files):
            self.status = ProcessingStatus.PARTIALLY_COMPLETED
        else:
            self.status = ProcessingStatus.FAILED
    
    def mark_failed(self, error: Exception):
        """Mark processing as failed with error."""
        self.completed_at = datetime.now()
        self.status = ProcessingStatus.FAILED
        self.operation_error = error
    
    def mark_cancelled(self):
        """Mark processing as cancelled."""
        self.completed_at = datetime.now()
        self.status = ProcessingStatus.CANCELLED
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def success_count(self) -> int:
        """Get count of successfully processed files."""
        return len([f for f in self.processed_files if f.is_successful])
    
    @property
    def failure_count(self) -> int:
        """Get count of failed file processing attempts."""
        return self.error_count
    
    @property
    def total_files(self) -> int:
        """Get total count of files processed."""
        return len(self.processed_files)
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.success_count / self.total_files) * 100
    
    @property
    def compression_ratio(self) -> Optional[float]:
        """Get overall compression ratio."""
        if self.total_input_size > 0 and self.total_output_size > 0:
            return self.total_output_size / self.total_input_size
        return None
    
    @property
    def is_successful(self) -> bool:
        """Check if overall processing was successful."""
        return self.status == ProcessingStatus.COMPLETED
    
    @property
    def is_partial_success(self) -> bool:
        """Check if processing had partial success."""
        return self.status == ProcessingStatus.PARTIALLY_COMPLETED
    
    @property
    def is_failed(self) -> bool:
        """Check if processing failed completely."""
        return self.status == ProcessingStatus.FAILED
    
    @property
    def is_cancelled(self) -> bool:
        """Check if processing was cancelled."""
        return self.status == ProcessingStatus.CANCELLED
    
    def get_successful_files(self) -> List[ProcessedFile]:
        """Get list of successfully processed files."""
        return [f for f in self.processed_files if f.is_successful]
    
    def get_failed_files(self) -> List[ProcessedFile]:
        """Get list of failed file processing attempts."""
        return [f for f in self.processed_files if not f.is_successful]
    
    def get_output_paths(self) -> List[Path]:
        """Get list of all output file paths."""
        return [f.output_path for f in self.processed_files 
                if f.output_path and f.is_successful]
    
    def add_upload_result(self, file_path: Path, upload_info: Dict[str, Any]):
        """Add upload result information."""
        upload_result = {
            'file_path': str(file_path),
            'upload_info': upload_info,
            'uploaded_at': datetime.now().isoformat()
        }
        self.upload_results.append(upload_result)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary."""
        return {
            'total_files': self.total_files,
            'successful_files': self.success_count,
            'failed_files': self.failure_count,
            'success_rate_percent': round(self.success_rate, 2),
            'duration_seconds': self.duration,
            'total_input_size_bytes': self.total_input_size,
            'total_output_size_bytes': self.total_output_size,
            'compression_ratio': self.compression_ratio,
            'average_processing_time': self._calculate_average_processing_time()
        }
    
    def _calculate_average_processing_time(self) -> Optional[float]:
        """Calculate average processing time per file."""
        processing_times = [f.processing_time for f in self.processed_files 
                          if f.processing_time is not None]
        
        if not processing_times:
            return None
        
        return sum(processing_times) / len(processing_times)
    
    def get_error_summary(self) -> Optional[str]:
        """Get summary of all errors encountered."""
        if self.error_count == 0 and not self.operation_error:
            return None
        
        error_parts = []
        
        if self.operation_error:
            error_parts.append(f"Operation error: {self.operation_error}")
        
        file_errors = [f"- {f.input_path.name}: {f.error}" 
                      for f in self.processed_files if f.error]
        
        if file_errors:
            error_parts.append(f"File errors ({len(file_errors)}):")
            error_parts.extend(file_errors)
        
        return "\n".join(error_parts)
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert result to summary dictionary for serialization."""
        return {
            'operation_id': self.operation_id,
            'status': self.status.name,
            'performance': self.get_performance_summary(),
            'errors': self.get_error_summary(),
            'output_files': [str(path) for path in self.get_output_paths()],
            'upload_count': len(self.upload_results),
            'metadata': self.metadata
        }
    
    def __str__(self) -> str:
        """String representation of processing result."""
        status_str = self.status.name.lower().replace('_', ' ')
        if self.total_files > 0:
            return f"ProcessingResult: {status_str} ({self.success_count}/{self.total_files} files)"
        else:
            return f"ProcessingResult: {status_str}"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (f"ProcessingResult(id={self.operation_id}, "
                f"status={self.status.name}, "
                f"files={self.total_files}, "
                f"success={self.success_count}, "
                f"errors={self.error_count})")