#!/usr/bin/python3
"""
Main dependency manager that orchestrates all dependency operations.
"""
import os
import sys
import time
import shutil
from typing import Optional, Dict, Any
from .base import DependencyInfo
from ..config import get_config_manager
from .platforms import PlatformFactory
from .downloaders.http import HttpDownloader
from .extractors import ExtractorManager
from .validators import ValidatorFactory
from ..utils import get_logger

logger = get_logger(__name__)

# Basic dependency configurations - simplified from old dependency_config
DEPENDENCIES = {
    'ffmpeg': {
        'windows': {'url': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'},
        'linux': {'url': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz'},
        'darwin': {'url': 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.tar.xz'}
    }
}

FFMPEG_DEPENDENCIES = {
    'windows': {'binary_name': 'ffmpeg.exe'},
    'linux': {'binary_name': 'ffmpeg'},
    'darwin': {'binary_name': 'ffmpeg'}
}

FFPROBE_DEPENDENCIES = {
    'windows': {'binary_name': 'ffprobe.exe'},
    'linux': {'binary_name': 'ffprobe'},
    'darwin': {'binary_name': 'ffprobe'}
}

FFPLAY_DEPENDENCIES = {
    'windows': {'binary_name': 'ffplay.exe'},
    'linux': {'binary_name': 'ffplay'},
    'darwin': {'binary_name': 'ffplay'}
}


class DependencyManager:
    """Main dependency manager for handling external tool dependencies."""
    
    def __init__(self):
        self.platform = PlatformFactory.get_current_platform()
        self.downloader = HttpDownloader()
        self.extractor = ExtractorManager()
        self.logger = get_logger(f"{__name__}.DependencyManager")
        self.config_manager = get_config_manager()
        
        # Ensure cache directories exist
        cache_dir = self.config_manager.get_setting('dependencies.cache.cache_dir')
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(libs_dir, exist_ok=True)
    
    def ensure_dependency(self, dependency_name: str, auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
        """
        Ensure that a dependency is available, downloading it if necessary.
        
        Args:
            dependency_name: Name of the dependency ('ffmpeg', etc.)
            auto_download: Whether to automatically download or install the dependency if not found
            force_creation: Force re-download even if dependency exists (requires auto_download=True)
            
        Returns:
            str: Path to the binary if available, None otherwise
        """
        self.logger.debug("Ensuring dependency: %s (auto_download=%s, force_creation=%s)", 
                         dependency_name, auto_download, force_creation)
        
        if dependency_name not in DEPENDENCIES:
            self.logger.error("Unknown dependency: %s", dependency_name)
            return None
        
        platform_name = self.platform.get_platform_name()
        dependency_config = DEPENDENCIES[dependency_name].get(platform_name, {})
        
        if not dependency_config:
            self.logger.error("No configuration for %s on %s", dependency_name, platform_name)
            return None
        
        dependency_info = DependencyInfo(dependency_name, dependency_config)
        
        # Check for existing installation first (unless force_creation is set)
        if not force_creation:
            existing_path = self._find_existing_dependency(dependency_name, dependency_info)
            if existing_path:
                self.logger.debug("Using existing %s: %s", dependency_name, existing_path)
                return existing_path
        
        # If auto_download is enabled, download/install the dependency
        if auto_download:
            if force_creation:
                self.logger.info("Force creation enabled, re-downloading %s", dependency_name)
            else:
                self.logger.info("Auto-download enabled, downloading %s", dependency_name)
            return self._install_dependency(dependency_info, force_download=force_creation)
        
        # If not found and auto_download is disabled, show warning
        self.logger.warning("%s not found in libs directory or PATH and auto-download is disabled. "
                          "Use --auto-download to enable automatic installation.", dependency_name)
        return None
    
    def _find_existing_dependency(self, dependency_name: str, dependency_info: DependencyInfo) -> Optional[str]:
        """Find an existing installation of the dependency."""
        
        # Get the platform-specific binary name
        platform_name = self.platform.get_platform_name()
        binary_name = dependency_name
        
        # For FFmpeg, use the platform-specific binary name
        if dependency_name == 'ffmpeg' and platform_name in FFMPEG_DEPENDENCIES:
            binary_name = FFMPEG_DEPENDENCIES[platform_name].get('binary_name', dependency_name)
        
        # Check previously downloaded version in libs directory
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        dependency_dir = os.path.join(libs_dir, dependency_name)
        if os.path.exists(dependency_dir):
            binary_path = self._find_binary_in_dir(dependency_dir, dependency_info.bin_path or binary_name)
            if binary_path and self._validate_binary(dependency_name, binary_path):
                self.logger.debug("Found previously downloaded %s: %s", dependency_name, binary_path)
                return binary_path
        
        # Check system PATH
        system_path = self.platform.find_system_binary(binary_name)
        if system_path and self._validate_binary(dependency_name, system_path):
            self.logger.debug("Found %s in PATH: %s", dependency_name, system_path)
            return system_path
        
        return None
    
    def _install_dependency(self, dependency_info: DependencyInfo, force_download: bool = False) -> Optional[str]:
        """Install a dependency by downloading or using package manager."""
        
        dependency_name = dependency_info.name
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        dependency_dir = os.path.join(libs_dir, dependency_name)
        
        # Clean up existing installation if forcing download
        if force_download and os.path.exists(dependency_dir):
            try:
                backup_dir = f"{dependency_dir}_backup_{int(time.time())}"
                self.logger.debug("Moving existing dependency directory to: %s", backup_dir)
                os.rename(dependency_dir, backup_dir)
            except Exception as e:
                self.logger.warning("Failed to rename existing dependency directory: %s", e)
                try:
                    shutil.rmtree(dependency_dir, ignore_errors=True)
                except Exception as e:
                    self.logger.warning("Failed to remove existing dependency directory: %s", e)
        
        # Try package manager installation first if available
        if dependency_info.package_name and not dependency_info.is_python_package:
            if self.platform.install_package(dependency_info.package_name):
                # Check if installation was successful
                system_path = self.platform.find_system_binary(dependency_name)
                if system_path and self._validate_binary(dependency_name, system_path):
                    self.logger.info("Successfully installed %s: %s", dependency_name, system_path)
                    return system_path
        
        # Handle Python packages
        if dependency_info.is_python_package:
            return self._install_python_package(dependency_info)
        
        # Download and install binary
        if dependency_info.url:
            return self._download_and_install(dependency_info)
        
        self.logger.error("Cannot install %s: no download URL or package available", dependency_name)
        return None
    
    def _download_and_install(self, dependency_info: DependencyInfo) -> Optional[str]:
        """Download and install a binary dependency."""
        
        dependency_name = dependency_info.name
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        dependency_dir = os.path.join(libs_dir, dependency_name)
        
        # Create dependency directory
        os.makedirs(dependency_dir, exist_ok=True)
        
        # Determine archive extension and path
        download_url = dependency_info.url
        archive_ext = '.zip' if download_url.endswith('zip') else '.tar.xz'
        archive_path = os.path.join(dependency_dir, f"{dependency_name}{archive_ext}")
        
        self.logger.debug("Using archive path: %s", archive_path)
        
        # Download the archive
        print(f"Downloading {dependency_name}...")
        if not self.downloader.download_with_mirrors(download_url, archive_path, dependency_info.mirrors):
            self.logger.error("Failed to download %s", dependency_name)
            return None
        
        # Extract the archive
        print(f"Extracting {dependency_name}...")
        if not self.extractor.extract_archive(archive_path, dependency_dir):
            self.logger.error("Failed to extract %s", dependency_name)
            return None
        
        # Get the platform-specific binary name
        platform_name = self.platform.get_platform_name()
        binary_name = dependency_name
        
        # For FFmpeg, use the platform-specific binary name
        if dependency_name == 'ffmpeg' and platform_name in FFMPEG_DEPENDENCIES:
            binary_name = FFMPEG_DEPENDENCIES[platform_name].get('binary_name', dependency_name)
        
        # Find the extracted binary (fallback to dependency name if bin_path not specified)
        binary_path = self._find_binary_in_dir(dependency_dir, dependency_info.bin_path or binary_name)
        if not binary_path:
            self.logger.error("Binary not found after extraction: %s", dependency_info.bin_path or binary_name)
            return None
        
        # Make executable on Unix-like systems
        if not self.platform.make_executable(binary_path):
            self.logger.warning("Failed to set executable permissions on %s", binary_path)
        
        # Validate the binary
        if not self._validate_binary(dependency_name, binary_path):
            self.logger.error("Binary validation failed: %s", binary_path)
            return None
        
        self.logger.info("Successfully set up %s: %s", dependency_name, binary_path)
        return binary_path
    
    def _install_python_package(self, dependency_info: DependencyInfo) -> Optional[str]:
        """Install a Python package using pip."""
        package_name = dependency_info.package_name
        
        if self._check_python_package(package_name):
            self.logger.debug("Python package %s is already installed", package_name)
            return package_name  # Return package name as success indicator
        
        self.logger.info("Attempting to install Python package: %s", package_name)
        
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            self.logger.info("Successfully installed Python package: %s", package_name)
            
            # Verify installation
            if self._check_python_package(package_name):
                return package_name
            else:
                self.logger.error("Package was installed but could not be imported: %s", package_name)
                return None
                
        except Exception as e:
            self.logger.error("Failed to install Python package %s: %s", package_name, str(e))
            return None
    
    def _find_binary_in_dir(self, directory: str, binary_path: str) -> Optional[str]:
        """Find a binary file in the directory structure."""
        if not binary_path:
            return None
            
        self.logger.debug("Looking for binary %s in %s", binary_path, directory)
        
        # On Windows, ensure we search for .exe extension
        platform_name = self.platform.get_platform_name()
        search_names = [binary_path]
        if platform_name == 'windows' and not binary_path.endswith('.exe'):
            search_names.append(binary_path + '.exe')
        
        # Try direct path first
        for search_name in search_names:
            direct_path = os.path.join(directory, search_name)
            if os.path.exists(direct_path):
                self.logger.debug("Found binary at direct path: %s", direct_path)
                return direct_path
        
        # Search in directory tree
        self.logger.debug("Searching for binary in directory tree")
        for root, _, files in os.walk(directory):
            for f in files:
                # Check if filename matches (with or without .exe on Windows)
                for search_name in search_names:
                    if f == os.path.basename(search_name) or f == search_name:
                        full_path = os.path.join(root, f)
                        self.logger.debug("Found binary at: %s", full_path)
                        return full_path
        
        self.logger.warning("Binary %s not found in %s", binary_path, directory)
        return None
    
    def _validate_binary(self, tool_name: str, binary_path: str) -> bool:
        """Validate that a binary is working correctly."""
        validator = ValidatorFactory.get_validator(tool_name)
        if validator:
            return validator.validate(binary_path)
        
        # If no validator available, just check if file exists and is executable
        if not os.path.exists(binary_path):
            return False
            
        if self.platform.get_platform_name() != 'windows':
            return os.access(binary_path, os.X_OK)
        
        return True
    
    def _check_python_package(self, package_name: str) -> bool:
        """Check if a Python package is installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    # Public convenience methods for specific tools
    
    def get_ffmpeg_binary(self, auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
        """Get the path to the FFmpeg binary."""
        return self.ensure_dependency('ffmpeg', auto_download, force_creation)
    
    def get_ffprobe_binary(self, auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
        """Get the path to the FFprobe binary."""
        platform_name = self.platform.get_platform_name()
        ffprobe_config = FFPROBE_DEPENDENCIES.get(platform_name, {})
        
        if not ffprobe_config:
            self.logger.error("No FFprobe configuration for platform: %s", platform_name)
            return None
        
        # FFprobe is typically bundled with FFmpeg
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        ffmpeg_dir = os.path.join(libs_dir, 'ffmpeg')
        
        # Check if FFprobe exists in the FFmpeg directory (unless force_creation is set)
        if not force_creation:
            ffprobe_binary_name = ffprobe_config.get('binary_name', 'ffprobe')
            
            # Search in the FFmpeg directory tree
            if os.path.exists(ffmpeg_dir):
                ffprobe_path = self._find_binary_in_dir(ffmpeg_dir, ffprobe_binary_name)
                if ffprobe_path and self._validate_binary('ffprobe', ffprobe_path):
                    self.logger.debug("FFprobe found in FFmpeg directory: %s", ffprobe_path)
                    return ffprobe_path
            
            # Check system PATH
            system_path = self.platform.find_system_binary(ffprobe_binary_name)
            if system_path and self._validate_binary('ffprobe', system_path):
                self.logger.info("Found FFprobe in PATH: %s", system_path)
                return system_path
        
        # If auto_download is enabled, try to get FFmpeg (which includes FFprobe)
        if auto_download:
            self.logger.info("FFprobe not found, attempting to get FFmpeg (which includes FFprobe)")
            ffmpeg_path = self.get_ffmpeg_binary(auto_download=True, force_creation=force_creation)
            if ffmpeg_path:
                # Check again for FFprobe after FFmpeg download
                ffprobe_binary_name = ffprobe_config.get('binary_name', 'ffprobe')
                if os.path.exists(ffmpeg_dir):
                    ffprobe_path = self._find_binary_in_dir(ffmpeg_dir, ffprobe_binary_name)
                    if ffprobe_path and self._validate_binary('ffprobe', ffprobe_path):
                        self.logger.info("FFprobe found after FFmpeg download: %s", ffprobe_path)
                        return ffprobe_path
            
            self.logger.warning("FFprobe not available even after FFmpeg download")
            return None
        
        self.logger.warning("FFprobe is not available and --auto-download is not used.")
        return None
    
    def get_ffplay_binary(self, auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
        """Get the path to the FFplay binary."""
        platform_name = self.platform.get_platform_name()
        ffplay_config = FFPLAY_DEPENDENCIES.get(platform_name, {})
        
        if not ffplay_config:
            self.logger.error("No FFplay configuration for platform: %s", platform_name)
            return None
        
        # FFplay is typically bundled with FFmpeg
        libs_dir = self.config_manager.get_setting('dependencies.cache.libs_dir')
        ffmpeg_dir = os.path.join(libs_dir, 'ffmpeg')
        
        # Check if FFplay exists in the FFmpeg directory (unless force_creation is set)
        if not force_creation:
            ffplay_binary_name = ffplay_config.get('binary_name', 'ffplay')
            
            # Search in the FFmpeg directory tree
            if os.path.exists(ffmpeg_dir):
                ffplay_path = self._find_binary_in_dir(ffmpeg_dir, ffplay_binary_name)
                if ffplay_path and self._validate_binary('ffplay', ffplay_path):
                    self.logger.debug("FFplay found in FFmpeg directory: %s", ffplay_path)
                    return ffplay_path
            
            # Check system PATH
            system_path = self.platform.find_system_binary(ffplay_binary_name)
            if system_path and self._validate_binary('ffplay', system_path):
                self.logger.info("Found FFplay in PATH: %s", system_path)
                return system_path
        
        # If auto_download is enabled, try to get FFmpeg (which includes FFplay)
        if auto_download:
            self.logger.info("FFplay not found, attempting to get FFmpeg (which includes FFplay)")
            ffmpeg_path = self.get_ffmpeg_binary(auto_download=True, force_creation=force_creation)
            if ffmpeg_path:
                # Check again for FFplay after FFmpeg download
                ffplay_binary_name = ffplay_config.get('binary_name', 'ffplay')
                if os.path.exists(ffmpeg_dir):
                    ffplay_path = self._find_binary_in_dir(ffmpeg_dir, ffplay_binary_name)
                    if ffplay_path and self._validate_binary('ffplay', ffplay_path):
                        self.logger.info("FFplay found after FFmpeg download: %s", ffplay_path)
                        return ffplay_path
            
            self.logger.warning("FFplay not available even after FFmpeg download")
            return None
        
        self.logger.warning("FFplay is not available and --auto-download is not used.")
        return None


# Global singleton instance
_global_manager = None

def get_dependency_manager() -> DependencyManager:
    """Get the global dependency manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = DependencyManager()
    return _global_manager


# Convenience helper functions
def get_ffmpeg_binary(auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
    """Get the path to the FFmpeg binary."""
    return get_dependency_manager().get_ffmpeg_binary(auto_download, force_creation)

def get_ffprobe_binary(auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
    """Get the path to the FFprobe binary."""
    return get_dependency_manager().get_ffprobe_binary(auto_download, force_creation)

def get_ffplay_binary(auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
    """Get the path to the FFplay binary."""
    return get_dependency_manager().get_ffplay_binary(auto_download, force_creation)

def ensure_dependency(dependency_name: str, auto_download: bool = False, force_creation: bool = False) -> Optional[str]:
    """Ensure a dependency is available."""
    return get_dependency_manager().ensure_dependency(dependency_name, auto_download, force_creation)
