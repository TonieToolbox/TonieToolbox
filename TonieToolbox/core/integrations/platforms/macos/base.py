#!/usr/bin/python3
"""
macOS base integration providing common functionality for file associations and icons.
"""
import os
import plistlib
import subprocess
import tempfile
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...base import BaseIntegration
from ....config.application_constants import ICON_ICO_BASE64, ICON_PNG_BASE64
from ....media import base64_to_png
from ....utils import get_logger

if TYPE_CHECKING:
    from ...base.integration import CommandBuilder


class MacOSBaseIntegration(BaseIntegration):
    """Base class for macOS desktop integrations with file association support.
    
    Creates macOS application bundles for TAF file associations, integrates with
    Finder via Automator workflows, and provides custom icon handling. Supports
    macOS LaunchServices for file type registration and Quick Actions integration.
    
    Example:
        Install macOS integration with file associations::
        
            from TonieToolbox.core.integrations.platforms.macos.base import MacOSBaseIntegration
            
            integration = MacOSBaseIntegration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/Library/Application Support/TonieToolbox')
            )
            if integration.install():
                print("macOS integration installed")
                print("Double-click .taf files to play them")
                print("Right-click audio files for Quick Actions")
        
        Install with custom application bundle location::
        
            integration = MacOSBaseIntegration(
                exe_path='/Applications/TonieToolbox.app/Contents/MacOS/tonietoolbox',
                output_dir=os.path.expanduser('~/Library/Application Support/TonieToolbox')
            )
            integration.install()
        
        Uninstall file associations and Quick Actions::
        
            integration = MacOSBaseIntegration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/Library/Application Support/TonieToolbox')
            )
            integration.uninstall()
            print("File associations and Automator workflows removed")
    """
    
    def __init__(self, exe_path: str = None, output_dir: str = None, 
                 upload_config=None, log_level: str = "INFO", log_to_file: bool = False):
        """Initialize macOS base integration."""
        # Store parameters for use after parent initialization
        if exe_path is not None:
            self._custom_exe_path = exe_path
            self._custom_output_dir = output_dir 
            self._custom_upload_config = upload_config
            self._custom_log_level = log_level
            self._custom_log_to_file = log_to_file
        else:
            # Parameters will be set by BaseIntegration
            self._custom_exe_path = None
            self._custom_output_dir = None
            self._custom_upload_config = None
            self._custom_log_level = None
            self._custom_log_to_file = None
        
        # Call parent constructor - this will call _setup_platform_paths()
        super().__init__()
        
        # Override with custom parameters if provided
        if self._custom_exe_path is not None:
            self.exe_path = self._custom_exe_path
        if self._custom_output_dir is not None:
            self.output_dir = self._custom_output_dir
            os.makedirs(self.output_dir, exist_ok=True)
        if self._custom_upload_config is not None:
            self.upload_config = self._custom_upload_config
        if self._custom_log_level is not None:
            self.log_level = self._custom_log_level
        if self._custom_log_to_file is not None:
            self.log_to_file = self._custom_log_to_file
    
    def _setup_platform_paths(self):
        """Set up platform-specific paths for macOS."""
        # Icon path for macOS (PNG format)
        self.icon_path = os.path.join(self.output_dir, 'icon.png')
        
        # Application bundle path
        self.app_bundle_path = os.path.expanduser(
            '~/Applications/TonieToolbox TAF Player.app'
        )
        
        # LaunchServices database paths
        self.launch_services_dir = os.path.expanduser('~/Library/Preferences')
        
        # Call subclass-specific setup if it exists
        if hasattr(self, '_setup_platform_specific_paths'):
            self._setup_platform_specific_paths()
    
    def _setup_macos_paths(self):
        """
        Set up common macOS paths.
        
        .. deprecated:: 0.6.0
            Use :meth:`_setup_platform_paths` instead. This method will be removed in version 1.0.0.
        """
        import warnings
        warnings.warn(
            "_setup_macos_paths() is deprecated and will be removed in version 1.0.0. "
            "Use _setup_platform_paths() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._setup_platform_paths()
    
    def _create_taf_application_bundle(self, command_builder: 'CommandBuilder') -> bool:
        """
        Create a macOS application bundle for TAF file associations.
        This enables double-click functionality for TAF files.
        
        Args:
            command_builder: Command builder for generating command lines
            
        Returns:
            True if bundle was created successfully
        """
        try:
            # Extract icon if needed
            self._extract_icon_if_needed()
            
            # Build command for TAF file playback
            command_line = ' '.join(command_builder.build_base_command(use_play=True))
            
            # Create application bundle structure
            contents_dir = os.path.join(self.app_bundle_path, 'Contents')
            macos_dir = os.path.join(contents_dir, 'MacOS')
            resources_dir = os.path.join(contents_dir, 'Resources')
            
            os.makedirs(macos_dir, exist_ok=True)
            os.makedirs(resources_dir, exist_ok=True)
            
            # Create Info.plist
            info_plist = {
                'CFBundleName': 'TonieToolbox TAF Player',
                'CFBundleDisplayName': 'TonieToolbox TAF Player',
                'CFBundleIdentifier': 'eu.quentins.tonietoolbox.tafplayer',
                'CFBundleVersion': '1.0',
                'CFBundleShortVersionString': '1.0',
                'CFBundlePackageType': 'APPL',
                'CFBundleSignature': 'TTTF',
                'CFBundleExecutable': 'tonietoolbox-taf-player',
                'CFBundleIconFile': 'icon.png',
                'CFBundleDocumentTypes': [{
                    'CFBundleTypeName': 'Tonie Audio File',
                    'CFBundleTypeRole': 'Editor',
                    'CFBundleTypeIconFile': 'icon.png',
                    'LSItemContentTypes': ['eu.quentins.tonietoolbox.taf'],
                    'CFBundleTypeExtensions': ['taf']
                }],
                'UTExportedTypeDeclarations': [{
                    'UTTypeIdentifier': 'eu.quentins.tonietoolbox.taf',
                    'UTTypeDescription': 'Tonie Audio File',
                    'UTTypeConformsTo': ['public.audio'],
                    'UTTypeTagSpecification': {
                        'public.filename-extension': ['taf'],
                        'public.mime-type': ['application/x-tonie-audio-file']
                    }
                }],
                'LSMinimumSystemVersion': '10.12'
            }
            
            info_plist_path = os.path.join(contents_dir, 'Info.plist')
            with open(info_plist_path, 'wb') as f:
                plistlib.dump(info_plist, f)
            
            # Create executable script
            executable_path = os.path.join(macos_dir, 'tonietoolbox-taf-player')
            executable_content = f"""#!/bin/bash
# TonieToolbox TAF Player Application Bundle
exec {command_line} "$@"
"""
            
            with open(executable_path, 'w') as f:
                f.write(executable_content)
            
            # Make executable
            os.chmod(executable_path, 0o755)
            
            # Copy icon to Resources
            icon_dest = os.path.join(resources_dir, 'icon.png')
            if os.path.exists(self.icon_path):
                import shutil
                shutil.copy2(self.icon_path, icon_dest)
            
            self.logger.debug("Created TAF application bundle: %s", self.app_bundle_path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create TAF application bundle: %s", e)
            return False
    
    def _remove_taf_application_bundle(self) -> bool:
        """
        Remove the macOS application bundle for TAF files.
        """
        try:
            if os.path.exists(self.app_bundle_path):
                import shutil
                shutil.rmtree(self.app_bundle_path)
                self.logger.debug("Removed TAF application bundle: %s", self.app_bundle_path)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove TAF application bundle: %s", e)
            return False
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for macOS."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def _register_file_associations(self) -> bool:
        """
        Register file associations with macOS LaunchServices.
        """
        try:
            # Register the application bundle with LaunchServices
            result = subprocess.run([
                '/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister',
                '-f', self.app_bundle_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.logger.debug("Registered application with LaunchServices")
            else:
                self.logger.warning("Failed to register with LaunchServices: %s", result.stderr)
                return False
            
            # Set default application for .taf files
            try:
                result = subprocess.run([
                    'duti', '-s', 'eu.quentins.tonietoolbox.tafplayer', '.taf', 'all'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.debug("Set default application for .taf files")
                else:
                    self.logger.debug("duti not available, file association may require manual setup")
            except FileNotFoundError:
                self.logger.debug("duti not found, file association may require manual setup")
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to register file associations: %s", e)
            return False
    
    def _unregister_file_associations(self) -> bool:
        """
        Unregister file associations from macOS LaunchServices.
        """
        try:
            # Unregister the application bundle
            if os.path.exists(self.app_bundle_path):
                result = subprocess.run([
                    '/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister',
                    '-u', self.app_bundle_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    self.logger.debug("Unregistered application from LaunchServices")
                else:
                    self.logger.warning("Failed to unregister from LaunchServices: %s", result.stderr)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to unregister file associations: %s", e)
            return False