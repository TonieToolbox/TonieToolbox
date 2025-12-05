#!/usr/bin/python3
"""
Windows base integration providing common functionality for file associations and icons.
"""
import os
import tempfile
from typing import Optional, List, TYPE_CHECKING
from ...base import BaseIntegration
from ....config.application_constants import ICON_ICO_BASE64
from ....media import base64_to_ico
from ....utils import get_logger

if TYPE_CHECKING:
    from ...base.integration import CommandBuilder

# Import winreg only on Windows
try:
    import winreg
except ImportError:
    winreg = None


class WindowsBaseIntegration(BaseIntegration):
    """Base class for Windows desktop integrations with file association support.
    
    Provides registry-based file associations for TAF files, context menu entries
    for audio file conversion, and custom icon handling. Uses Windows Registry
    Editor (.reg files) with UAC elevation for system-wide integration.
    
    Example:
        Install Windows integration with file associations::
        
            from TonieToolbox.core.integrations.platforms.windows.base import WindowsBaseIntegration
            
            integration = WindowsBaseIntegration(
                exe_path='C:\\Program Files\\TonieToolbox\\tonietoolbox.exe',
                output_dir=os.path.expanduser('~\\AppData\\Local\\TonieToolbox')
            )
            if integration.install():
                print("Windows integration installed")
                print("Double-click .taf files to play them")
                print("Right-click audio files for conversion options")
        
        Install with custom output directory::
        
            integration = WindowsBaseIntegration(
                exe_path='C:\\Tools\\tonietoolbox.exe',
                output_dir='C:\\Users\\Public\\TonieToolbox'
            )
            integration.install()
        
        Uninstall file associations and context menus::
        
            integration = WindowsBaseIntegration(
                exe_path='C:\\Program Files\\TonieToolbox\\tonietoolbox.exe',
                output_dir=os.path.expanduser('~\\AppData\\Local\\TonieToolbox')
            )
            integration.uninstall()
            print("File associations and context menus removed")
    """
    
    def __init__(self, exe_path: str = None, output_dir: str = None, 
                 upload_config=None, log_level: str = "INFO", log_to_file: bool = False):
        """Initialize Windows base integration."""
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
        """Set up platform-specific paths for Windows."""
        # Icon path for Windows (ICO format)
        self.icon_path = os.path.join(self.output_dir, 'icon.ico')
        
        # Registry paths for file associations
        self.registry_paths = {
            'file_types': r'SOFTWARE\Classes',
            'applications': r'SOFTWARE\Classes\Applications'
        }
        
        # Call subclass-specific setup if it exists
        if hasattr(self, '_setup_platform_specific_paths'):
            self._setup_platform_specific_paths()
    
    def _setup_windows_paths(self):
        """
        Set up common Windows paths.
        
        .. deprecated:: 0.6.0
            Use :meth:`_setup_platform_paths` instead. This method will be removed in version 1.0.0.
        """
        import warnings
        warnings.warn(
            "_setup_windows_paths() is deprecated and will be removed in version 1.0.0. "
            "Use _setup_platform_paths() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._setup_platform_paths()
    
    def _install_taf_file_association(self, command_builder: 'CommandBuilder') -> bool:
        """
        Install file association for TAF files in Windows registry.
        This enables double-click functionality for TAF files.
        Uses UAC elevation to write to HKEY_CLASSES_ROOT.
        
        Args:
            command_builder: Command builder for generating command lines
            
        Returns:
            True if association was installed successfully
        """
        try:
            # Extract icon if needed
            self._extract_icon_if_needed()
            
            # Build command for TAF file playback
            command_line = ' '.join(command_builder.build_base_command(use_play=True))
            
            # Registry keys for TAF file association
            taf_file_type = 'TonieToolbox.TAF'
            
            # Escape paths for registry file format
            command_line_escaped = self._reg_escape(f'"{command_line}" "%1"')
            icon_path_escaped = self._reg_escape(f'"{self.icon_path}",0')
            
            # Create registry file content for file association
            reg_content = [
                'Windows Registry Editor Version 5.00',
                '',
                '[HKEY_CLASSES_ROOT\\.taf]',
                f'@="{taf_file_type}"',
                '"Content Type"="application/x-tonie-audio-file"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}]',
                '@="Tonie Audio File"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\DefaultIcon]',
                f'@="{icon_path_escaped}"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\shell]',
                '@="play"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\shell\\play]',
                '@="Play"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\shell\\play\\command]',
                f'@="{command_line_escaped}"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\shell\\open]',
                '@="Play with TonieToolbox"',
                '',
                f'[HKEY_CLASSES_ROOT\\{taf_file_type}\\shell\\open\\command]',
                f'@="{command_line_escaped}"',
                ''
            ]
            
            # Write registry file and import with UAC elevation
            success = self._import_registry_file_with_uac(reg_content)
            
            if success:
                self.logger.debug("Installed TAF file association")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install TAF file association: %s", e)
            return False
            
    def _reg_escape(self, value: str) -> str:
        """Escape a string value for use in registry files."""
        # Escape backslashes and quotes for registry file format
        return value.replace('\\', '\\\\').replace('"', '\\"')
    
    def _import_registry_file_with_uac(self, reg_content: list) -> bool:
        """
        Create a temporary registry file and import it with UAC elevation.
        """
        import tempfile
        import subprocess
        
        try:
            # Create temporary registry file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.reg', 
                                           encoding='utf-8', delete=False) as reg_file:
                reg_file.write('\n'.join(reg_content))
                reg_file_path = reg_file.name
            
            try:
                # Import registry file with UAC elevation using PowerShell
                ps_command = (
                    f"Start-Process reg.exe -ArgumentList @('import', '{reg_file_path}') "
                    "-Verb RunAs -Wait -PassThru"
                )
                
                result = subprocess.run([
                    "powershell.exe", "-Command", ps_command
                ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
                
                if result.returncode == 0:
                    self.logger.debug("Registry file imported successfully with UAC")
                    return True
                else:
                    self.logger.warning("Registry import failed with return code %s", result.returncode)
                    if result.stderr:
                        self.logger.debug("Registry import stderr: %s", result.stderr)
                    return False
                    
            finally:
                # Clean up temp file
                try:
                    os.unlink(reg_file_path)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error("Failed to import registry file: %s", e)
            return False
    
    def _remove_taf_file_association(self) -> bool:
        """
        Remove file association for TAF files from Windows registry.
        Uses UAC elevation to remove from HKEY_CLASSES_ROOT.
        """
        try:
            # Create registry file content for removal
            reg_content = [
                'Windows Registry Editor Version 5.00',
                '',
                '[-HKEY_CLASSES_ROOT\\.taf]',
                '',
                '[-HKEY_CLASSES_ROOT\\TonieToolbox.TAF]',
                ''
            ]
            
            # Import removal registry file with UAC elevation
            success = self._import_registry_file_with_uac(reg_content)
            
            if success:
                self.logger.debug("Removed TAF file association")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove TAF file association: %s", e)
            return False
    
    def _extract_icon_if_needed(self):
        """Extract ICO icon for Windows."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_ico(ICON_ICO_BASE64, self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def _refresh_file_associations(self) -> bool:
        """
        Refresh Windows file associations to make changes take effect.
        """
        try:
            import subprocess
            
            # Notify Windows that file associations have changed
            result = subprocess.run([
                'cmd', '/c', 'assoc', '.taf'
            ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=False)
            
            self.logger.debug("Refreshed file associations")
            return True
            
        except Exception as e:
            self.logger.warning("Failed to refresh file associations: %s", e)
            return False