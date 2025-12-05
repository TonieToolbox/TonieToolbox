#!/usr/bin/python3
"""
File system operations implementation.
"""
import os
import glob
from typing import List

from ..domain import FileSystemService, CoverImageFinder


class StandardFileSystemService(FileSystemService):
    """
    Standard implementation of file system operations.
    """
    
    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        return os.path.exists(path)
    
    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        return os.path.isfile(path)
    
    def is_directory(self, path: str) -> bool:
        """Check if path is a directory."""
        return os.path.isdir(path)
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory matching pattern."""
        if not self.is_directory(directory):
            return []
        
        search_pattern = os.path.join(directory, pattern)
        return glob.glob(search_pattern)
    
    def get_file_extension(self, file_path: str) -> str:
        """Get file extension."""
        return os.path.splitext(file_path.lower())[1]


class StandardCoverImageFinder(CoverImageFinder):
    """
    Standard implementation for finding cover images in directories.
    """
    
    def __init__(self, cover_names: List[str], image_extensions: List[str], logger):
        """
        Initialize cover image finder.
        
        Args:
            cover_names: List of potential cover image names (without extension)
            image_extensions: List of supported image file extensions
            logger: Logger instance
        """
        self.cover_names = cover_names
        self.image_extensions = image_extensions
        self.logger = logger
        self.fs_service = StandardFileSystemService()
    
    def find_cover_image(self, directory: str) -> str | None:
        """
        Find cover image file in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Path to cover image file if found, None otherwise
        """
        if not self.fs_service.is_directory(directory):
            return None
        
        # First pass: exact matches
        for name in self.cover_names:
            for ext in self.image_extensions:
                cover_path = os.path.join(directory, name + ext)
                if self.fs_service.exists(cover_path):
                    self.logger.debug("Found cover image: %s", cover_path)
                    return cover_path
                
                # Case-insensitive search
                try:
                    for file in os.listdir(directory):
                        if file.lower() == (name + ext).lower():
                            cover_path = os.path.join(directory, file)
                            self.logger.debug("Found cover image: %s", cover_path)
                            return cover_path
                except OSError:
                    continue
        
        # Second pass: partial matches
        try:
            for file in os.listdir(directory):
                file_lower = file.lower()
                file_ext = self.fs_service.get_file_extension(file)
                
                if file_ext in self.image_extensions:
                    for name in self.cover_names:
                        if name in file_lower:
                            cover_path = os.path.join(directory, file)
                            self.logger.debug("Found cover image: %s", cover_path)
                            return cover_path
        except OSError:
            pass
        
        self.logger.debug("No cover image found in directory: %s", directory)
        return None