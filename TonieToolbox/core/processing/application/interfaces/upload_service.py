#!/usr/bin/env python3
"""
Upload service interface.

This interface defines operations for uploading processed files to external services.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from ...domain import ProcessingOperation, ProcessingResult


@dataclass
class UploadProgress:
    """Progress information for upload operations."""
    
    current_file: str
    files_completed: int
    total_files: int
    bytes_uploaded: int
    total_bytes: int
    upload_speed: float  # bytes per second
    estimated_time_remaining: Optional[float] = None  # seconds


@dataclass
class UploadResult:
    """Result of an upload operation."""
    
    file_path: Path
    upload_url: Optional[str] = None
    upload_id: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None
    upload_time: Optional[float] = None  # seconds
    file_size: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UploadService(ABC):
    """Abstract interface for file upload operations."""
    
    @abstractmethod
    def connect(self, connection_params: Dict[str, Any]) -> bool:
        """
        Establish connection to upload service.
        
        Args:
            connection_params: Connection parameters (host, credentials, etc.)
            
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from upload service."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if currently connected to upload service."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test connection to upload service."""
        pass
    
    @abstractmethod
    def upload_file(self, file_path: Path, 
                   destination_path: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None,
                   progress_callback: Optional[Callable[[UploadProgress], None]] = None) -> UploadResult:
        """
        Upload single file.
        
        Args:
            file_path: Path to file to upload
            destination_path: Optional destination path on service
            metadata: Optional metadata to associate with file
            progress_callback: Optional callback for progress updates
            
        Returns:
            UploadResult with upload information
        """
        pass
    
    @abstractmethod
    def upload_files(self, file_paths: List[Path],
                    destination_directory: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    progress_callback: Optional[Callable[[UploadProgress], None]] = None) -> List[UploadResult]:
        """
        Upload multiple files.
        
        Args:
            file_paths: List of file paths to upload
            destination_directory: Optional destination directory on service
            metadata: Optional metadata to associate with files
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of UploadResult for each file
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from upload service.
        
        Args:
            file_id: ID of file to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_files(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files on upload service.
        
        Args:
            directory: Optional directory to list (None for root)
            
        Returns:
            List of file information dictionaries
        """
        pass
    
    @abstractmethod
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about uploaded file.
        
        Args:
            file_id: ID of file
            
        Returns:
            File information dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def download_file(self, file_id: str, local_path: Path,
                     progress_callback: Optional[Callable[[UploadProgress], None]] = None) -> bool:
        """
        Download file from upload service.
        
        Args:
            file_id: ID of file to download
            local_path: Local path to save file
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if download successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information (used space, available space, etc.).
        
        Returns:
            Storage information dictionary
        """
        pass
    
    @abstractmethod
    def create_directory(self, path: str) -> bool:
        """
        Create directory on upload service.
        
        Args:
            path: Directory path to create
            
        Returns:
            True if creation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_upload_url(self, filename: str, 
                      metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get upload URL for direct file upload.
        
        Args:
            filename: Name of file to upload
            metadata: Optional metadata for the file
            
        Returns:
            Upload URL or None if not supported
        """
        pass


class UploadQueue(ABC):
    """Abstract interface for managing upload queues."""
    
    @abstractmethod
    def add_to_queue(self, file_path: Path, 
                    priority: int = 0,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add file to upload queue.
        
        Args:
            file_path: Path to file to upload
            priority: Upload priority (higher = more urgent)
            metadata: Optional metadata for the file
            
        Returns:
            Queue item ID
        """
        pass
    
    @abstractmethod
    def remove_from_queue(self, item_id: str) -> bool:
        """
        Remove item from upload queue.
        
        Args:
            item_id: Queue item ID
            
        Returns:
            True if removal successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start_processing(self, max_concurrent: int = 3) -> None:
        """
        Start processing upload queue.
        
        Args:
            max_concurrent: Maximum concurrent uploads
        """
        pass
    
    @abstractmethod
    def stop_processing(self) -> None:
        """Stop processing upload queue."""
        pass
    
    @abstractmethod
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Queue status information
        """
        pass