#!/usr/bin/python3
"""
Base Linux integration class providing common functionality for all Linux desktop environments.
"""
import os
from typing import List, Dict, Any
from ...base import BaseIntegration, CommandBuilder
from ....utils import get_logger

logger = get_logger(__name__)


class LinuxBaseIntegration(BaseIntegration):
    """
    Base class for Linux desktop environment integrations.
    Provides common functionality like desktop file associations.
    """
    
    def __init__(self, exe_path: str = None, output_dir: str = None, 
                 upload_config=None, log_level: str = "INFO", log_to_file: bool = False):
        """Initialize Linux base integration."""
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
        
        # Call parent constructor
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
        """Set up common Linux paths, then call subclass-specific setup."""
        # Set up common Linux paths used by all desktop environments
        self.icon_path = os.path.join(self.output_dir, 'icon.png')
        
        # Desktop applications directory (common to all Linux desktop environments)
        self.application_dir = os.path.join(
            os.path.expanduser('~'), '.local', 'share', 'applications'
        )
        
        # MIME packages directory for custom MIME types
        self.mime_packages_dir = os.path.join(
            os.path.expanduser('~'), '.local', 'share', 'mime', 'packages'
        )
        
        # Ensure directories exist
        os.makedirs(self.application_dir, exist_ok=True)
        os.makedirs(self.mime_packages_dir, exist_ok=True)
        
        # Call subclass-specific setup if it exists
        if hasattr(self, '_setup_desktop_specific_paths'):
            self._setup_desktop_specific_paths()
    
    def _install_mime_icon(self) -> bool:
        """
        Install TonieToolbox icon for MIME type system.
        Installs the icon in the user's local icon theme directory.
        """
        try:
            from ....utils.icons import base64_to_png
            
            # Define icon theme directory
            icon_theme_dir = os.path.join(
                os.path.expanduser('~'), '.local', 'share', 'icons', 'hicolor'
            )
            
            # Install icon in multiple sizes for better compatibility
            icon_sizes = ['16x16', '22x22', '32x32', '48x48', '64x64', '128x128']
            
            for size in icon_sizes:
                size_dir = os.path.join(icon_theme_dir, size, 'mimetypes')
                os.makedirs(size_dir, exist_ok=True)
                
                icon_path = os.path.join(size_dir, 'tonietoolbox.png')
                
                if not os.path.exists(icon_path):
                    try:
                        base64_to_png(icon_path)
                        self.logger.debug("Installed MIME icon: %s", icon_path)
                    except Exception as e:
                        self.logger.warning("Failed to install MIME icon %s: %s", icon_path, e)
            
            # Update icon cache
            import subprocess
            try:
                result = subprocess.run(
                    ['gtk-update-icon-cache', '-f', '-t', icon_theme_dir],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.logger.debug("Icon cache updated successfully")
                else:
                    self.logger.debug("Failed to update icon cache (this is usually not critical): %s", result.stderr)
            except Exception as e:
                self.logger.debug("Failed to update icon cache (this is usually not critical): %s", e)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to install MIME icon: %s", e)
            return False
    
    def _remove_mime_icon(self) -> bool:
        """
        Remove TonieToolbox icon from MIME type system.
        """
        try:
            icon_theme_dir = os.path.join(
                os.path.expanduser('~'), '.local', 'share', 'icons', 'hicolor'
            )
            
            icon_sizes = ['16x16', '22x22', '32x32', '48x48', '64x64', '128x128']
            
            success = True
            for size in icon_sizes:
                icon_path = os.path.join(icon_theme_dir, size, 'mimetypes', 'tonietoolbox.png')
                if os.path.exists(icon_path):
                    try:
                        os.remove(icon_path)
                        self.logger.debug("Removed MIME icon: %s", icon_path)
                    except Exception as e:
                        self.logger.warning("Failed to remove MIME icon %s: %s", icon_path, e)
                        success = False
            
            # Update icon cache
            import subprocess
            try:
                result = subprocess.run(
                    ['gtk-update-icon-cache', '-f', '-t', icon_theme_dir],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.logger.debug("Icon cache updated after removal")
                else:
                    self.logger.debug("Failed to update icon cache after removal (this is usually not critical): %s", result.stderr)
            except Exception as e:
                self.logger.debug("Failed to update icon cache after removal (this is usually not critical): %s", e)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove MIME icon: %s", e)
            return False
    
    def _create_taf_mime_type(self) -> bool:
        """
        Create custom MIME type definition for TAF files.
        This method is common to all Linux desktop environments.
        """
        try:
            # Create MIME type XML definition
            mime_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
    <mime-type type="application/x-tonie-audio-file">
        <comment>Tonie Audio File</comment>
        <comment xml:lang="de">Tonie Audio Datei</comment>
        <icon name="tonietoolbox"/>
        <glob pattern="*.taf" weight="100"/>
        <glob pattern="*.TAF" weight="100"/>
        <magic priority="50">
            <match value="OggS" type="string" offset="0"/>
        </magic>
        <sub-class-of type="application/ogg"/>
    </mime-type>
</mime-info>
"""
            
            # Write MIME type definition file
            mime_filepath = os.path.join(self.mime_packages_dir, 'tonietoolbox-taf.xml')
            with open(mime_filepath, 'w') as f:
                f.write(mime_content)
            
            self.logger.debug("Created MIME type definition: %s", mime_filepath)
            
            # Update MIME database
            import subprocess
            try:
                result = subprocess.run(
                    ['update-mime-database', os.path.join(os.path.expanduser('~'), '.local', 'share', 'mime')],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.logger.debug("MIME database updated successfully")
                else:
                    self.logger.warning("Failed to update MIME database: %s", result.stderr)
            except Exception as e:
                self.logger.warning("Failed to update MIME database: %s", e)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to create TAF MIME type: %s", e)
            return False
    
    def _remove_taf_mime_type(self) -> bool:
        """
        Remove custom MIME type definition for TAF files.
        This method is common to all Linux desktop environments.
        """
        try:
            mime_filepath = os.path.join(self.mime_packages_dir, 'tonietoolbox-taf.xml')
            if os.path.exists(mime_filepath):
                os.remove(mime_filepath)
                self.logger.debug("Removed MIME type definition: %s", mime_filepath)
                
                # Update MIME database
                import subprocess
                try:
                    result = subprocess.run(
                        ['update-mime-database', os.path.join(os.path.expanduser('~'), '.local', 'share', 'mime')],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.logger.debug("MIME database updated after removal")
                    else:
                        self.logger.warning("Failed to update MIME database after removal: %s", result.stderr)
                except Exception as e:
                    self.logger.warning("Failed to update MIME database after removal: %s", e)
            
            return True
        except Exception as e:
            self.logger.error("Failed to remove TAF MIME type: %s", e)
            return False
    
    def _remove_old_mime_types(self) -> bool:
        """
        Remove old MIME type definitions that conflict with our custom type.
        This removes the audio/x-tonie MIME type if it exists.
        """
        try:
            success = True
            old_mime_files = [
                'audio-x-tonie.xml',
            ]
            
            for filename in old_mime_files:
                mime_filepath = os.path.join(self.mime_packages_dir, filename)
                if os.path.exists(mime_filepath):
                    try:
                        os.remove(mime_filepath)
                        self.logger.debug("Removed old MIME type definition: %s", mime_filepath)
                    except Exception as e:
                        self.logger.warning("Failed to remove old MIME type %s: %s", mime_filepath, e)
                        success = False
            
            # Also remove generated MIME files from the system database
            mime_db_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'mime')
            old_generated_files = [
                os.path.join(mime_db_dir, 'audio', 'x-tonie.xml'),
                os.path.join(mime_db_dir, 'application', 'x-tonie-audio-file.xml'),
            ]
            
            for filepath in old_generated_files:
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        self.logger.debug("Removed old generated MIME file: %s", filepath)
                    except Exception as e:
                        self.logger.warning("Failed to remove old generated MIME file %s: %s", filepath, e)
                        success = False
            
            if success:
                # Update MIME database
                import subprocess
                try:
                    result = subprocess.run(
                        ['update-mime-database', mime_db_dir],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.logger.debug("MIME database updated after removing old types")
                    else:
                        self.logger.warning("Failed to update MIME database after removing old types: %s", result.stderr)
                except Exception as e:
                    self.logger.warning("Failed to update MIME database after removing old types: %s", e)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove old MIME types: %s", e)
            return False
    
    def _create_taf_application_file(self, command_builder: CommandBuilder) -> bool:
        """
        Create desktop application file for TAF file associations (double-click).
        This method is common to all Linux desktop environments.
        """
        try:
            # Build command for TAF file playback
            command_line = ' '.join(command_builder.build_base_command(use_play=True))
            
            # Create desktop entry content - use our custom MIME type
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=TonieToolbox TAF Player
Comment=Play Tonie Audio Files with TonieToolbox
Exec={command_line} %f
Icon={self.icon_path}
Categories=AudioVideo;Audio;Player;
MimeType=application/x-tonie-audio-file;
NoDisplay=true
Terminal=false
StartupNotify=true
"""
            
            # Write desktop file
            filepath = os.path.join(self.application_dir, 'tonietoolbox-taf-player.desktop')
            with open(filepath, 'w') as f:
                f.write(desktop_content)
            
            # Set executable permissions
            os.chmod(filepath, 0o755)
            
            self.logger.debug("Created TAF application file: %s", filepath)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create TAF application file: %s", e)
            return False
    
    def _remove_taf_application_file(self) -> bool:
        """
        Remove desktop application file for TAF file associations.
        This method is common to all Linux desktop environments.
        """
        try:
            filepath = os.path.join(self.application_dir, 'tonietoolbox-taf-player.desktop')
            if os.path.exists(filepath):
                os.remove(filepath)
                self.logger.debug("Removed TAF application file: %s", filepath)
            return True
        except Exception as e:
            self.logger.error("Failed to remove TAF application file: %s", e)
            return False
    
    def _update_desktop_database(self) -> bool:
        """
        Update the desktop database to make file associations take effect.
        This method is common to all Linux desktop environments.
        """
        try:
            import subprocess
            # Try to update desktop database if available
            result = subprocess.run(
                ['update-desktop-database', self.application_dir],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.debug("Desktop database updated successfully")
            else:
                self.logger.debug("update-desktop-database not available or failed (this is not critical)")
            return True
        except Exception as e:
            self.logger.debug("Failed to update desktop database: %s (this is not critical)", e)
            return True  # Not critical if this fails
    
    def _get_audio_mime_types(self) -> List[str]:
        """
        Get MIME types for supported audio formats.
        This method is common to all Linux desktop environments.
        """
        from ....config.application_constants import SUPPORTED_EXTENSIONS
        
        mime_map = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav', 
            'flac': 'audio/flac',
            'ogg': 'audio/ogg',
            'opus': 'audio/opus',
            'aac': 'audio/aac',
            'm4a': 'audio/mp4',
            'wma': 'audio/x-ms-wma',
            'aiff': 'audio/x-aiff',
            'mp2': 'audio/mpeg',
            'mp4': 'audio/mp4',
            'webm': 'audio/webm',
            'mka': 'audio/x-matroska',
            'ape': 'audio/x-ape'
        }
        
        mime_types = set()
        for ext in SUPPORTED_EXTENSIONS:
            ext_clean = ext.lower().lstrip('.')
            if ext_clean in mime_map:
                mime_types.add(mime_map[ext_clean])
        
        return sorted(list(mime_types))