#!/usr/bin/python3
"""
Integration manager for the new modular integration system.
"""
import os
import platform
import sys
from typing import Optional, Dict, Any, List
from .base import BaseIntegration, UploadConfiguration
from ..utils import get_logger

logger = get_logger(__name__)


class IntegrationManager:
    """Manages platform-specific integrations using the modular system."""
    
    def __init__(self, exe_path: Optional[str] = None, output_dir: str = None, 
                 upload_config: Optional[UploadConfiguration] = None,
                 log_level: str = "INFO", log_to_file: bool = False):
        """
        Initialize the integration manager.
        
        Args:
            exe_path: Path to the TonieToolbox executable (None = auto-detect)
            output_dir: Directory for integration files
            upload_config: Upload configuration (optional)
            log_level: Logging level
            log_to_file: Whether to log to file
        """
        self.exe_path = exe_path
        self.output_dir = output_dir
        self.upload_config = upload_config or UploadConfiguration({})
        self.log_level = log_level
        self.log_to_file = log_to_file
        self.logger = logger
        
        # Platform detection
        self.system = platform.system().lower()
        self.desktop_env = self._detect_desktop_environment()
        
        # Available integrations cache
        self._available_integrations: Optional[Dict[str, type]] = None
    
    def _detect_desktop_environment(self) -> Optional[str]:
        """Detect the desktop environment on Linux systems."""
        if self.system != 'linux':
            return None
        
        # Check environment variables
        desktop_session = (
            os.environ.get('DESKTOP_SESSION', '') or
            os.environ.get('XDG_CURRENT_DESKTOP', '') or
            os.environ.get('XDG_SESSION_DESKTOP', '')
        ).lower()
        
        # Map common values to our integration names
        desktop_map = {
            'kde': 'kde',
            'plasma': 'kde',
            'xfce': 'xfce', 
            'xfce4': 'xfce',
            'gnome': 'gnome',
            'unity': 'ubuntu',
            'ubuntu': 'ubuntu',
            'mate': 'mate',
            'cinnamon': 'cinnamon',
            'lxqt': 'lxqt'
        }
        
        # Check for exact matches first
        for key, integration in desktop_map.items():
            if key in desktop_session:
                return integration
        
        # Fallback: check for running processes
        try:
            import subprocess
            processes = subprocess.check_output(['ps', 'aux'], 
                                              universal_newlines=True)
            
            if 'kwin' in processes or 'plasmashell' in processes:
                return 'kde'
            elif 'xfwm4' in processes or 'xfce4-panel' in processes:
                return 'xfce'
            elif 'gnome-shell' in processes:
                return 'gnome'
            elif 'mate-panel' in processes:
                return 'mate'
            elif 'cinnamon' in processes:
                return 'cinnamon'
            elif 'lxqt-panel' in processes:
                return 'lxqt'
        except:
            pass
        
        return None
    
    def get_available_integrations(self) -> Dict[str, type]:
        """Get all available integrations for the current platform."""
        if self._available_integrations is not None:
            return self._available_integrations
        
        integrations = {}
        
        try:
            if self.system == 'windows':
                from .platforms.windows.registry import WindowsIntegration
                integrations['windows'] = WindowsIntegration
            
            elif self.system == 'darwin':
                from .platforms.macos.automator import MacOSIntegration
                integrations['macos'] = MacOSIntegration
            
            elif self.system == 'linux':
                # Import Linux desktop environment integrations
                try:
                    from .platforms.linux.kde import KDEIntegration
                    integrations['kde'] = KDEIntegration
                except ImportError:
                    pass
                
                try:
                    from .platforms.linux.xfce import XFCEIntegration
                    integrations['xfce'] = XFCEIntegration
                except ImportError:
                    pass
                
                try:
                    from .platforms.linux.gnome import GNOMEIntegration, UbuntuIntegration
                    integrations['gnome'] = GNOMEIntegration
                    integrations['ubuntu'] = UbuntuIntegration  # Alias for GNOME
                except ImportError:
                    pass
                
                try:
                    from .platforms.linux.mate import MATEIntegration
                    integrations['mate'] = MATEIntegration
                except ImportError:
                    pass
                
                try:
                    from .platforms.linux.cinnamon import CinnamonIntegration
                    integrations['cinnamon'] = CinnamonIntegration
                except ImportError:
                    pass
                
                try:
                    from .platforms.linux.lxqt import LXQTIntegration
                    integrations['lxqt'] = LXQTIntegration
                except ImportError:
                    pass
        
        except Exception as e:
            self.logger.warning("Error loading integrations: %s", e)
        
        self._available_integrations = integrations
        return integrations
    
    def get_recommended_integration(self) -> Optional[str]:
        """Get the recommended integration for the current platform."""
        available = self.get_available_integrations()
        
        if self.system == 'windows' and 'windows' in available:
            return 'windows'
        elif self.system == 'darwin' and 'macos' in available:
            return 'macos'
        elif self.system == 'linux':
            # Use detected desktop environment
            if self.desktop_env and self.desktop_env in available:
                return self.desktop_env
            # Fallback to first available Linux integration
            linux_integrations = ['kde', 'xfce', 'gnome', 'ubuntu', 'mate', 'cinnamon', 'lxqt']
            for integration in linux_integrations:
                if integration in available:
                    return integration
        
        return None
    
    def create_integration(self, integration_name: str) -> Optional[BaseIntegration]:
        """Create an integration instance by name."""
        available = self.get_available_integrations()
        
        if integration_name not in available:
            self.logger.error("Integration '%s' not available. Available: %s", 
                            integration_name, list(available.keys()))
            return None
        
        integration_class = available[integration_name]
        
        try:
            # Try the new constructor signature first
            try:
                return integration_class(
                    exe_path=self.exe_path,
                    output_dir=self.output_dir,
                    upload_config=self.upload_config,
                    log_level=self.log_level,
                    log_to_file=self.log_to_file
                )
            except TypeError as e:
                # Integration class doesn't support new constructor signature
                self.logger.warning(f"Integration '{integration_name}' doesn't support modern constructor: {e}")
                return integration_class()
                
        except Exception as e:
            self.logger.error("Failed to create integration '%s': %s", 
                            integration_name, e)
            return None
    
    def install_integration(self, integration_name: Optional[str] = None) -> bool:
        """Install an integration (auto-detect if not specified).
        
        Installs desktop integration for the current platform, creating context menu
        entries, file associations, and shell completions. If no integration name is
        provided, automatically selects the most appropriate one for the current
        desktop environment.
        
        Args:
            integration_name: Name of integration to install ('kde', 'gnome', 'windows', etc.).
                            If None, automatically detects the recommended integration.
        
        Returns:
            True if installation succeeded, False otherwise.
        
        Example:
            Auto-detect and install recommended integration::
            
                manager = IntegrationManager(
                    exe_path='/usr/local/bin/tonietoolbox',
                    output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
                )
                if manager.install_integration():
                    print("Integration installed successfully")
            
            Install specific integration (KDE on Linux)::
            
                manager = IntegrationManager(
                    exe_path='/usr/local/bin/tonietoolbox',
                    output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
                )
                if manager.install_integration('kde'):
                    print("KDE integration installed")
                    print("Right-click on audio files to see TonieToolbox options")
            
            Install with TeddyCloud upload support::
            
                from TonieToolbox.core.teddycloud.domain.models import UploadConfiguration
                
                upload_config = UploadConfiguration(
                    server_url="http://teddycloud.local",
                    username="admin",
                    password="secret"
                )
                manager = IntegrationManager(
                    exe_path='/usr/local/bin/tonietoolbox',
                    output_dir=os.path.expanduser('~/.local/share/tonietoolbox'),
                    upload_config=upload_config
                )
                manager.install_integration()  # Context menu will include upload option
        """
        if not integration_name:
            integration_name = self.get_recommended_integration()
            if not integration_name:
                self.logger.error("No suitable integration found for this platform")
                return False
        
        integration = self.create_integration(integration_name)
        if not integration:
            return False
        
        return integration.install()
    
    def uninstall_integration(self, integration_name: Optional[str] = None) -> bool:
        """Uninstall an integration (auto-detect if not specified).
        
        Removes desktop integration including context menu entries, file associations,
        and shell completions. If no integration name is provided, automatically
        detects and removes the recommended integration for the current platform.
        
        Args:
            integration_name: Name of integration to remove. If None, auto-detects.
        
        Returns:
            True if uninstallation succeeded, False otherwise.
        
        Example:
            Remove auto-detected integration::
            
                manager = IntegrationManager(
                    exe_path='/usr/local/bin/tonietoolbox',
                    output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
                )
                if manager.uninstall_integration():
                    print("Integration removed successfully")
            
            Remove specific integration::
            
                manager = IntegrationManager(
                    exe_path='/usr/local/bin/tonietoolbox',
                    output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
                )
                manager.uninstall_integration('kde')  # Remove KDE-specific integration
        """
        if not integration_name:
            integration_name = self.get_recommended_integration()
            if not integration_name:
                self.logger.error("No suitable integration found for this platform")
                return False
        
        integration = self.create_integration(integration_name)
        if not integration:
            return False
        
        return integration.uninstall()
    
    def list_integrations(self) -> Dict[str, Dict[str, Any]]:
        """List all available integrations with their info."""
        available = self.get_available_integrations()
        recommended = self.get_recommended_integration()
        
        result = {}
        for name, integration_class in available.items():
            try:
                # Try to get description without creating instance (safer)
                class_name = integration_class.__name__
                description = f"{class_name} integration for {name}"
                
                # Try to determine supported platforms from class name
                if 'Windows' in class_name:
                    platforms = ['Windows']
                elif 'MacOS' in class_name or 'macOS' in class_name:
                    platforms = ['macOS']
                else:
                    platforms = ['Linux']
                
                result[name] = {
                    'name': name,
                    'description': description,
                    'supported_platforms': platforms,
                    'is_recommended': name == recommended,
                    'is_available': True
                }
            except Exception as e:
                result[name] = {
                    'name': name,
                    'description': f"Error: {e}",
                    'supported_platforms': [],
                    'is_recommended': False,
                    'is_available': False
                }
        
        return result
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get information about the current platform."""
        return {
            'system': self.system,
            'platform': platform.platform(),
            'desktop_environment': self.desktop_env,
            'recommended_integration': self.get_recommended_integration(),
            'available_integrations': list(self.get_available_integrations().keys()),
            'python_version': sys.version
        }


# Convenience helper functions
def install_integration(exe_path: Optional[str] = None, output_dir: str = None, 
                       upload_config: Optional[UploadConfiguration] = None,
                       integration_name: Optional[str] = None,
                       log_level: str = "INFO", log_to_file: bool = False) -> bool:
    """Install platform integration (convenience function).
    
    Simplified function for installing desktop integration without creating
    an IntegrationManager instance. Automatically detects the appropriate
    integration for the current platform if not specified.
    
    Args:
        exe_path: Path to the tonietoolbox executable (None = auto-detect)
        output_dir: Directory for integration files (icons, service menus, etc.)
        upload_config: Optional TeddyCloud upload configuration
        integration_name: Optional specific integration to install
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file
    
    Returns:
        True if installation succeeded, False otherwise.
    
    Example:
        Simple integration installation::
        
            from TonieToolbox.core.integrations.manager import install_integration
            
            success = install_integration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
            )
            if success:
                print("Desktop integration installed")
        
        Installation with debug logging::
        
            success = install_integration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox'),
                log_level="DEBUG",
                log_to_file=True
            )
    """
    manager = IntegrationManager(
        exe_path=exe_path,
        output_dir=output_dir,
        upload_config=upload_config,
        log_level=log_level,
        log_to_file=log_to_file
    )
    return manager.install_integration(integration_name)


def uninstall_integration(exe_path: Optional[str] = None, output_dir: str = None,
                         upload_config: Optional[UploadConfiguration] = None,
                         integration_name: Optional[str] = None,
                         log_level: str = "INFO", log_to_file: bool = False) -> bool:
    """Uninstall platform integration (convenience function).
    
    Simplified function for removing desktop integration without creating
    an IntegrationManager instance. Removes context menus, file associations,
    and shell completions.
    
    Args:
        exe_path: Path to the tonietoolbox executable (None = auto-detect, not used for uninstall)
        output_dir: Directory containing integration files
        upload_config: Optional upload configuration (not used for uninstall)
        integration_name: Optional specific integration to remove
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Whether to log to file
    
    Returns:
        True if uninstallation succeeded, False otherwise.
    
    Example:
        Remove desktop integration::
        
            from TonieToolbox.core.integrations.manager import uninstall_integration
            
            success = uninstall_integration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
            )
            if success:
                print("Desktop integration removed")
    """
    manager = IntegrationManager(
        exe_path=exe_path,
        output_dir=output_dir,
        upload_config=upload_config,
        log_level=log_level,
        log_to_file=log_to_file
    )
    return manager.uninstall_integration(integration_name)