#!/usr/bin/env python3
"""
File repository interface.

This interface defines operations for file system access in the processing domain.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime

from ...domain import ProcessingOperation


class FileRepository(ABC):
    """Abstract repository for file system operations."""
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        pass
    
    @abstractmethod
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        pass
    
    @abstractmethod
    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        pass
    
    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        pass
    
    @abstractmethod
    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Get file metadata including timestamps, permissions, etc."""
        pass
    
    @abstractmethod
    def list_files(self, directory: str, recursive: bool = False, 
                   extensions: Optional[List[str]] = None) -> List[Path]:
        """List files in directory with optional filtering."""
        pass
    
    @abstractmethod
    def create_directory(self, path: str, parents: bool = True) -> None:
        """Create directory and parent directories if needed."""
        pass
    
    @abstractmethod
    def copy_file(self, source: str, destination: str, 
                  preserve_metadata: bool = True) -> None:
        """Copy file from source to destination."""
        pass
    
    @abstractmethod
    def move_file(self, source: str, destination: str) -> None:
        """Move file from source to destination."""
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete file."""
        pass
    
    @abstractmethod
    def read_file_content(self, path: str, encoding: str = 'utf-8') -> str:
        """Read text file content."""
        pass
    
    @abstractmethod
    def write_file_content(self, path: str, content: str, 
                          encoding: str = 'utf-8') -> None:
        """Write text content to file."""
        pass
    
    @abstractmethod
    def get_free_space(self, path: str) -> int:
        """Get available free space in bytes for given path."""
        pass
    
    @abstractmethod
    def create_backup(self, path: str, backup_suffix: str = '.bak') -> str:
        """Create backup of file and return backup path."""
        pass
    
    @abstractmethod
    def cleanup_temp_files(self, pattern: str) -> int:
        """Clean up temporary files matching pattern, return count cleaned."""
        pass


class FileWatcher(ABC):
    """Abstract interface for watching file system changes."""
    
    @abstractmethod
    def watch_directory(self, path: str, callback: callable) -> str:
        """Start watching directory for changes, return watch ID."""
        pass
    
    @abstractmethod
    def stop_watching(self, watch_id: str) -> None:
        """Stop watching directory."""
        pass


class FileIterator(ABC):
    """Abstract interface for iterating over files."""
    
    @abstractmethod
    def iterate_files(self, operation: ProcessingOperation) -> Iterator[Path]:
        """Iterate over files based on processing operation input specification."""
        pass
    
    @abstractmethod
    def get_estimated_count(self, operation: ProcessingOperation) -> int:
        """Get estimated number of files that would be processed."""
        pass