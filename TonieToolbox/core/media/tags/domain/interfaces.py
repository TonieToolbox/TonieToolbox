#!/usr/bin/python3
"""
Domain interfaces for media tag processing.
Define contracts for infrastructure implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from .entities import MediaTagCollection, ArtworkData


class TagReader(ABC):
    """
    Abstract interface for reading tags from media files.
    Infrastructure layer must implement this.
    """
    
    @abstractmethod
    def read_tags(self, file_path: str) -> MediaTagCollection:
        """
        Read all tags from a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            MediaTagCollection containing all found tags
            
        Raises:
            FileNotFoundError: If file doesn't exist
            UnsupportedFormatError: If file format not supported
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        """Check if reader supports the given file format."""
        pass


class ArtworkExtractor(ABC):
    """
    Abstract interface for extracting artwork from media files.
    """
    
    @abstractmethod
    def extract_artwork(self, file_path: str) -> Optional[ArtworkData]:
        """
        Extract artwork from a media file.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            ArtworkData if found, None otherwise
        """
        pass
    
    @abstractmethod
    def supports_format(self, file_path: str) -> bool:
        """Check if extractor supports the given file format."""
        pass


class TagReaderFactory(ABC):
    """
    Abstract factory for creating format-specific tag readers.
    """
    
    @abstractmethod
    def create_reader(self, file_path: str) -> Optional[TagReader]:
        """
        Create appropriate tag reader for the given file.
        
        Args:
            file_path: Path to media file
            
        Returns:
            TagReader instance if format is supported, None otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported file extensions."""
        pass


class FileSystemService(ABC):
    """
    Abstract interface for file system operations.
    Allows mocking in tests.
    """
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if file exists."""
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
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory matching pattern."""
        pass
    
    @abstractmethod
    def get_file_extension(self, file_path: str) -> str:
        """Get file extension."""
        pass


class CoverImageFinder(ABC):
    """
    Abstract interface for finding cover images in directories.
    """
    
    @abstractmethod
    def find_cover_image(self, directory: str) -> Optional[str]:
        """
        Find cover image file in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Path to cover image file if found, None otherwise
        """
        pass