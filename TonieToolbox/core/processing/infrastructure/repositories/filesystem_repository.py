#!/usr/bin/env python3
"""
File system repository implementation.

This module provides concrete implementation of FileRepository interface
using the standard Python file system operations.
"""

import os
import shutil
import glob
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime
import logging

from ...application.interfaces.file_repository import FileRepository, FileIterator
from ...domain import ProcessingOperation


class FileSystemRepository(FileRepository):
    """
    Concrete implementation of FileRepository using file system operations.
    
    This repository handles all file system interactions for the processing system.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize file system repository."""
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        try:
            return os.path.exists(path)
        except Exception as e:
            self.logger.error(f"Error checking existence of {path}: {str(e)}")
            return False
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        try:
            return os.path.isfile(path)
        except Exception as e:
            self.logger.error(f"Error checking if {path} is file: {str(e)}")
            return False
    
    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        try:
            return os.path.isdir(path)
        except Exception as e:
            self.logger.error(f"Error checking if {path} is directory: {str(e)}")
            return False
    
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(path)
        except Exception as e:
            self.logger.error(f"Error getting size of {path}: {str(e)}")
            return 0
    
    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        """Get file metadata including timestamps, permissions, etc."""
        try:
            stat_info = os.stat(path)
            
            return {
                'size': stat_info.st_size,
                'created': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                'mode': oct(stat_info.st_mode),
                'uid': stat_info.st_uid,
                'gid': stat_info.st_gid,
                'is_file': os.path.isfile(path),
                'is_directory': os.path.isdir(path),
                'is_symlink': os.path.islink(path),
                'absolute_path': os.path.abspath(path)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting metadata for {path}: {str(e)}")
            return {'error': str(e)}
    
    def list_files(self, directory: str, recursive: bool = False, 
                   extensions: Optional[List[str]] = None) -> List[Path]:
        """List files in directory with optional filtering."""
        try:
            files = []
            directory_path = Path(directory)
            
            if not directory_path.exists() or not directory_path.is_dir():
                self.logger.warning(f"Directory does not exist or is not a directory: {directory}")
                return []
            
            # Choose pattern based on recursive flag
            pattern = "**/*" if recursive else "*"
            
            # Get all files
            for item in directory_path.glob(pattern):
                if item.is_file():
                    # Filter by extensions if specified
                    if extensions is None or item.suffix.lower() in [ext.lower() for ext in extensions]:
                        files.append(item)
            
            # Sort for consistent ordering
            return sorted(files)
            
        except Exception as e:
            self.logger.error(f"Error listing files in {directory}: {str(e)}")
            return []
    
    def create_directory(self, path: str, parents: bool = True) -> None:
        """Create directory and parent directories if needed."""
        try:
            os.makedirs(path, exist_ok=parents)
            self.logger.debug(f"Created directory: {path}")
            
        except Exception as e:
            self.logger.error(f"Error creating directory {path}: {str(e)}")
            raise
    
    def copy_file(self, source: str, destination: str, 
                  preserve_metadata: bool = True) -> None:
        """Copy file from source to destination."""
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                self.create_directory(dest_dir)
            
            if preserve_metadata:
                shutil.copy2(source, destination)
            else:
                shutil.copy(source, destination)
                
            self.logger.debug(f"Copied file: {source} -> {destination}")
            
        except Exception as e:
            self.logger.error(f"Error copying file {source} to {destination}: {str(e)}")
            raise
    
    def move_file(self, source: str, destination: str) -> None:
        """Move file from source to destination."""
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination)
            if dest_dir and not os.path.exists(dest_dir):
                self.create_directory(dest_dir)
            
            shutil.move(source, destination)
            self.logger.debug(f"Moved file: {source} -> {destination}")
            
        except Exception as e:
            self.logger.error(f"Error moving file {source} to {destination}: {str(e)}")
            raise
    
    def delete_file(self, path: str) -> None:
        """Delete file."""
        try:
            os.remove(path)
            self.logger.debug(f"Deleted file: {path}")
            
        except Exception as e:
            self.logger.error(f"Error deleting file {path}: {str(e)}")
            raise
    
    def read_file_content(self, path: str, encoding: str = 'utf-8') -> str:
        """Read text file content."""
        try:
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
                
        except Exception as e:
            self.logger.error(f"Error reading file {path}: {str(e)}")
            raise
    
    def write_file_content(self, path: str, content: str, 
                          encoding: str = 'utf-8') -> None:
        """Write text content to file."""
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                self.create_directory(dir_path)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
                
            self.logger.debug(f"Wrote content to file: {path}")
            
        except Exception as e:
            self.logger.error(f"Error writing to file {path}: {str(e)}")
            raise
    
    def get_free_space(self, path: str) -> int:
        """Get available free space in bytes for given path."""
        try:
            if os.name == 'nt':  # Windows
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(path),
                    ctypes.pointer(free_bytes),
                    None,
                    None
                )
                return free_bytes.value
            else:  # Unix-like
                statvfs = os.statvfs(path)
                return statvfs.f_frsize * statvfs.f_bavail
                
        except Exception as e:
            self.logger.error(f"Error getting free space for {path}: {str(e)}")
            return 0
    
    def create_backup(self, path: str, backup_suffix: str = '.bak') -> str:
        """Create backup of file and return backup path."""
        try:
            backup_path = f"{path}{backup_suffix}"
            
            # If backup already exists, create numbered backup
            counter = 1
            while os.path.exists(backup_path):
                backup_path = f"{path}{backup_suffix}.{counter}"
                counter += 1
            
            self.copy_file(path, backup_path, preserve_metadata=True)
            self.logger.debug(f"Created backup: {path} -> {backup_path}")
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup of {path}: {str(e)}")
            raise
    
    def cleanup_temp_files(self, pattern: str) -> int:
        """Clean up temporary files matching pattern, return count cleaned."""
        try:
            temp_files = glob.glob(pattern)
            count = 0
            
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    count += 1
                    self.logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {str(e)}")
            
            if count > 0:
                self.logger.info(f"Cleaned up {count} temporary files")
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error during temp file cleanup: {str(e)}")
            return 0


class FileSystemIterator(FileIterator):
    """File iterator implementation for file system operations."""
    
    def __init__(self, file_repo: FileSystemRepository, 
                 logger: Optional[logging.Logger] = None):
        """Initialize file system iterator."""
        self.file_repo = file_repo
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    def iterate_files(self, operation: ProcessingOperation) -> Iterator[Path]:
        """Iterate over files based on processing operation input specification."""
        try:
            files = operation.input_spec.resolve_files()
            
            for file_path in files:
                if file_path.exists() and file_path.is_file():
                    yield file_path
                else:
                    self.logger.warning(f"Skipping non-existent or invalid file: {file_path}")
                    
        except Exception as e:
            self.logger.error(f"Error iterating files: {str(e)}")
            raise
    
    def get_estimated_count(self, operation: ProcessingOperation) -> int:
        """Get estimated number of files that would be processed."""
        try:
            files = operation.input_spec.resolve_files()
            return len([f for f in files if f.exists() and f.is_file()])
            
        except Exception as e:
            self.logger.error(f"Error estimating file count: {str(e)}")
            return 0