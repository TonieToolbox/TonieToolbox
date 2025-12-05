#!/usr/bin/python3
"""
Base classes for dependency management components.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import os
from ..utils import get_logger

logger = get_logger(__name__)


class BaseDownloader(ABC):
    """Abstract base class for dependency downloaders."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def download(self, url: str, destination: str, **kwargs) -> bool:
        """
        Download a file from URL to destination.
        
        Args:
            url: The URL to download from
            destination: Local path to save the file
            **kwargs: Additional downloader-specific options
            
        Returns:
            bool: True if download successful, False otherwise
        """
        pass
    
    @abstractmethod
    def supports_multipart(self) -> bool:
        """Return True if downloader supports multipart downloads."""
        pass


class BaseValidator(ABC):
    """Abstract base class for dependency validators."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def validate(self, binary_path: str) -> bool:
        """
        Validate that a binary is working correctly.
        
        Args:
            binary_path: Path to the binary to validate
            
        Returns:
            bool: True if binary is valid and working, False otherwise
        """
        pass


class BaseExtractor(ABC):
    """Abstract base class for archive extractors."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def can_extract(self, archive_path: str) -> bool:
        """
        Check if this extractor can handle the given archive.
        
        Args:
            archive_path: Path to the archive file
            
        Returns:
            bool: True if this extractor can handle the archive
        """
        pass
    
    @abstractmethod
    def extract(self, archive_path: str, extract_dir: str) -> bool:
        """
        Extract an archive to the specified directory.
        
        Args:
            archive_path: Path to the archive file
            extract_dir: Directory to extract to
            
        Returns:
            bool: True if extraction successful, False otherwise
        """
        pass


class BasePlatform(ABC):
    """Abstract base class for platform-specific operations."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform identifier (e.g., 'windows', 'linux', 'darwin')."""
        pass
    
    @abstractmethod
    def find_system_binary(self, binary_name: str) -> Optional[str]:
        """
        Find a binary in the system PATH.
        
        Args:
            binary_name: Name of the binary to find
            
        Returns:
            str: Path to binary if found, None otherwise
        """
        pass
    
    @abstractmethod
    def install_package(self, package_name: str) -> bool:
        """
        Install a system package using platform package manager.
        
        Args:
            package_name: Name of package to install
            
        Returns:
            bool: True if installation successful, False otherwise
        """
        pass
    
    @abstractmethod
    def make_executable(self, binary_path: str) -> bool:
        """
        Make a binary executable on this platform.
        
        Args:
            binary_path: Path to the binary
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass


class DependencyInfo:
    """Data class to hold dependency information."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        
    @property
    def url(self) -> Optional[str]:
        """Get the download URL for this dependency."""
        return self.config.get('url')
        
    @property
    def bin_path(self) -> Optional[str]:
        """Get the binary path within the extracted directory."""
        return self.config.get('bin_path')
        
    @property
    def extract_dir(self) -> Optional[str]:
        """Get the extraction directory name."""
        return self.config.get('extract_dir')
        
    @property
    def package_name(self) -> Optional[str]:
        """Get the system package name."""
        return self.config.get('package')
        
    @property
    def is_python_package(self) -> bool:
        """Check if this is a Python package."""
        return self.config.get('python_package', False)
        
    @property
    def mirrors(self) -> List[str]:
        """Get the mirror URLs for this dependency."""
        return self.config.get('mirrors', [])