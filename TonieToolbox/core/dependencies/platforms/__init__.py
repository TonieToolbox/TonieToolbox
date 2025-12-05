#!/usr/bin/python3
"""
Platform-Specific Dependency Management Implementations.

This module contains platform-specific implementations for dependency management across
Windows, Linux, and macOS. Handles platform-specific download URLs, installation paths,
binary execution strategies, and system integration patterns for external dependencies
like FFmpeg and other required tools.
"""
import os
import platform
import subprocess
import shutil
from typing import Optional
from ..base import BasePlatform
from ...utils import get_logger

logger = get_logger(__name__)


class WindowsPlatform(BasePlatform):
    """Windows-specific platform operations."""
    
    def get_platform_name(self) -> str:
        return 'windows'
    
    def find_system_binary(self, binary_name: str) -> Optional[str]:
        """Find a binary in Windows PATH."""
        try:
            binary_path = shutil.which(binary_name)
            if binary_path:
                self.logger.debug("Found %s at %s", binary_name, binary_path)
                return binary_path
        except Exception as e:
            self.logger.warning("Error finding %s: %s", binary_name, e)
        return None
    
    def install_package(self, package_name: str) -> bool:
        """
        Windows doesn't have a universal package manager.
        This would require chocolatey or winget, not implemented yet.
        """
        self.logger.warning("Automatic package installation not implemented for Windows")
        return False
    
    def make_executable(self, binary_path: str) -> bool:
        """On Windows, executable permission is not needed."""
        return True


class LinuxPlatform(BasePlatform):
    """Linux-specific platform operations."""
    
    def get_platform_name(self) -> str:
        return 'linux'
    
    def find_system_binary(self, binary_name: str) -> Optional[str]:
        """Find a binary in Linux PATH."""
        try:
            result = subprocess.run(['which', binary_name], 
                                 capture_output=True, text=True, check=True)
            binary_path = result.stdout.strip()
            if binary_path:
                self.logger.debug("Found %s at %s", binary_name, binary_path)
                return binary_path
        except subprocess.CalledProcessError:
            self.logger.debug("Binary %s not found in PATH", binary_name)
        except Exception as e:
            self.logger.warning("Error finding %s: %s", binary_name, e)
        return None
    
    def install_package(self, package_name: str) -> bool:
        """Install package using available Linux package manager."""
        self.logger.info("Attempting to install %s on Linux", package_name)
        
        try:
            # Try apt-get (Debian/Ubuntu)
            if shutil.which('apt-get'):
                self.logger.info("Installing %s using apt-get", package_name)
                subprocess.run(['sudo', 'apt-get', 'update'], check=True, 
                             capture_output=True)
                subprocess.run(['sudo', 'apt-get', 'install', '-y', package_name], 
                             check=True, capture_output=True)
                return True
            
            # Try yum (RedHat/CentOS)
            elif shutil.which('yum'):
                self.logger.info("Installing %s using yum", package_name)
                subprocess.run(['sudo', 'yum', 'install', '-y', package_name], 
                             check=True, capture_output=True)
                return True
            
            # Try dnf (Modern Fedora)
            elif shutil.which('dnf'):
                self.logger.info("Installing %s using dnf", package_name)
                subprocess.run(['sudo', 'dnf', 'install', '-y', package_name], 
                             check=True, capture_output=True)
                return True
            
            # Try pacman (Arch Linux)
            elif shutil.which('pacman'):
                self.logger.info("Installing %s using pacman", package_name)
                subprocess.run(['sudo', 'pacman', '-S', '--noconfirm', package_name], 
                             check=True, capture_output=True)
                return True
            
            else:
                self.logger.warning("No supported package manager found")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to install %s: %s", package_name, e)
            return False
    
    def make_executable(self, binary_path: str) -> bool:
        """Set executable permissions on Linux."""
        try:
            os.chmod(binary_path, 0o755)
            self.logger.debug("Set executable permissions on %s", binary_path)
            return True
        except Exception as e:
            self.logger.error("Failed to set executable permissions on %s: %s", 
                            binary_path, e)
            return False


class DarwinPlatform(BasePlatform):
    """macOS-specific platform operations."""
    
    def get_platform_name(self) -> str:
        return 'darwin'
    
    def find_system_binary(self, binary_name: str) -> Optional[str]:
        """Find a binary in macOS PATH."""
        try:
            result = subprocess.run(['which', binary_name], 
                                 capture_output=True, text=True, check=True)
            binary_path = result.stdout.strip()
            if binary_path:
                self.logger.debug("Found %s at %s", binary_name, binary_path)
                return binary_path
        except subprocess.CalledProcessError:
            self.logger.debug("Binary %s not found in PATH", binary_name)
        except Exception as e:
            self.logger.warning("Error finding %s: %s", binary_name, e)
        return None
    
    def install_package(self, package_name: str) -> bool:
        """Install package using Homebrew on macOS."""
        self.logger.info("Attempting to install %s on macOS", package_name)
        
        try:
            if shutil.which('brew'):
                self.logger.info("Installing %s using homebrew", package_name)
                subprocess.run(['brew', 'install', package_name], 
                             check=True, capture_output=True)
                return True
            else:
                self.logger.warning("Homebrew not found, cannot install packages automatically")
                return False
                
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to install %s: %s", package_name, e)
            return False
    
    def make_executable(self, binary_path: str) -> bool:
        """Set executable permissions on macOS."""
        try:
            os.chmod(binary_path, 0o755)
            self.logger.debug("Set executable permissions on %s", binary_path)
            return True
        except Exception as e:
            self.logger.error("Failed to set executable permissions on %s: %s", 
                            binary_path, e)
            return False


class PlatformFactory:
    """Factory for creating platform-specific instances."""
    
    _platforms = {
        'Windows': WindowsPlatform,
        'Linux': LinuxPlatform, 
        'Darwin': DarwinPlatform
    }
    
    @classmethod
    def get_current_platform(cls) -> BasePlatform:
        """Get the current platform instance."""
        system_name = platform.system()
        platform_class = cls._platforms.get(system_name)
        
        if platform_class is None:
            logger.error("Unsupported platform: %s", system_name)
            raise ValueError(f"Unsupported platform: {system_name}")
        
        return platform_class()
    
    @classmethod
    def get_platform_name(cls) -> str:
        """Get the current platform name in lowercase."""
        return platform.system().lower()