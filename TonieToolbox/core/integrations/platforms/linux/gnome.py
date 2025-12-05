#!/usr/bin/python3
"""
GNOME/Ubuntu (Nautilus) integration using the new modular system.
"""
import os
import subprocess
from typing import List, Dict, Any
from ...base import (
    CommandBuilder, StandardCommandFactory, 
    get_template_manager
)
from .base import LinuxBaseIntegration
from ....config.application_constants import ICON_ICO_BASE64, SUPPORTED_EXTENSIONS
from ....utils.icons import base64_to_png
from ....utils import get_logger

logger = get_logger(__name__)


class GNOMEIntegration(LinuxBaseIntegration):
    """GNOME/Ubuntu Nautilus integration using the modular system."""
    
    def _setup_desktop_specific_paths(self):
        """Set up GNOME/Ubuntu-specific paths."""
        # Nautilus script directories
        self.nautilus_scripts_dir = os.path.expanduser('~/.local/share/nautilus/scripts')
        
        # Ensure directories exist
        os.makedirs(self.nautilus_scripts_dir, exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for GNOME."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install GNOME/Ubuntu Nautilus integration."""
        try:
            self.logger.info("Installing GNOME/Ubuntu Nautilus integration")
            
            # Create command builder
            command_builder = CommandBuilder(
                exe_path=self.exe_path,
                upload_config=self.upload_config,
                log_level=self.log_level,
                log_to_file=self.log_to_file
            )
            
            # Get standard commands
            command_set = StandardCommandFactory.create_standard_commands()
            
            # Install MIME icon and create custom MIME type for TAF files
            success = True
            success &= self._remove_old_mime_types()  # Clean up old MIME types first
            success &= self._install_mime_icon()
            success &= self._create_taf_mime_type()
            
            # Generate Nautilus scripts and desktop entries
            success &= self._create_nautilus_scripts(command_builder, command_set)
            success &= self._create_desktop_entries(command_builder, command_set)
            
            # Create desktop application for TAF file associations
            success &= self._create_taf_application_file(command_builder)
            
            # Update desktop database to make file associations take effect
            success &= self._update_desktop_database()
            
            # Install shell completions
            success &= self.install_shell_completions()
            
            if success:
                self.logger.info("GNOME integration installed successfully")
            else:
                self.logger.error("GNOME integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install GNOME integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall GNOME/Ubuntu Nautilus integration."""
        try:
            self.logger.info("Uninstalling GNOME/Ubuntu Nautilus integration")
            
            # Remove Nautilus scripts
            success = self._remove_nautilus_scripts()
            
            # Remove desktop entries
            success &= self._remove_desktop_entries()
            
            # Remove desktop application file
            success &= self._remove_taf_application_file()
            
            # Remove custom MIME type, old MIME types, and MIME icon
            success &= self._remove_taf_mime_type()
            success &= self._remove_old_mime_types()
            success &= self._remove_mime_icon()
            
            # Update desktop database
            success &= self._update_desktop_database()
            
            # Uninstall shell completions
            success &= self.uninstall_shell_completions()
            
            if success:
                self.logger.info("GNOME integration uninstalled successfully")
            else:
                self.logger.warning("GNOME integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall GNOME integration: %s", e)
            return False
    
    def _create_nautilus_scripts(self, command_builder: CommandBuilder, 
                               command_set) -> bool:
        """Create Nautilus scripts."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('nautilus_script')
            
            if not template:
                self.logger.error("Nautilus script template not found")
                return False
            
            # Create TonieToolbox subdirectory
            tonietoolbox_dir = os.path.join(self.nautilus_scripts_dir, 'TonieToolbox')
            os.makedirs(tonietoolbox_dir, exist_ok=True)
            
            success = True
            
            # Create scripts for audio files
            audio_commands = command_set.get_commands_for_audio_files()
            for cmd in audio_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_artwork=cmd.use_artwork,
                    use_json=cmd.use_json,
                    is_recursive=cmd.is_recursive
                ))
                
                script_content = template.render_script(
                    command=command_line,
                    description=cmd.description
                )
                
                script_path = os.path.join(tonietoolbox_dir, f"{cmd.id}_audio")
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                # Make executable
                os.chmod(script_path, 0o755)
                success &= True
            
            # Create scripts for TAF files
            taf_commands = command_set.get_commands_for_taf_files()
            for cmd in taf_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_info=cmd.use_info,
                    use_play=cmd.use_play,
                    is_split=cmd.is_split
                ))
                
                script_content = template.render_script(
                    command=command_line,
                    description=cmd.description
                )
                
                script_path = os.path.join(tonietoolbox_dir, f"{cmd.id}_taf")
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                os.chmod(script_path, 0o755)
                success &= True
            
            # Create scripts for folders
            folder_commands = command_set.get_commands_for_folders()
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=cmd.is_recursive
                ))
                
                script_content = template.render_script(
                    command=command_line,
                    description=cmd.description
                )
                
                script_path = os.path.join(tonietoolbox_dir, f"{cmd.id}_folder")
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                os.chmod(script_path, 0o755)
                success &= True
            
            self.logger.debug("Created Nautilus scripts in: %s", tonietoolbox_dir)
            return success
            
        except Exception as e:
            self.logger.error("Failed to create Nautilus scripts: %s", e)
            return False
    
    def _create_desktop_entries(self, command_builder: CommandBuilder,
                              command_set) -> bool:
        """Create desktop entries for file associations."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('desktop_entry')
            
            if not template:
                self.logger.warning("Desktop entry template not found, skipping")
                return True  # Not critical
            
            # Create main TonieToolbox desktop entry
            main_command = ' '.join(command_builder.build_base_command())
            
            desktop_content = template.render_application_entry(
                name="TonieToolbox",
                description="Audio processing tool for Tonie boxes",
                command=main_command,
                icon_path=self.icon_path,
                mime_types=self._get_audio_mime_types() + ['application/octet-stream']
            )
            
            desktop_path = os.path.join(self.desktop_apps_dir, 'tonietoolbox.desktop')
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            self.logger.debug("Created desktop entry: %s", desktop_path)
            return True
            
        except Exception as e:
            self.logger.warning("Failed to create desktop entries: %s", e)
            return True  # Non-critical
    
    def _remove_nautilus_scripts(self) -> bool:
        """Remove TonieToolbox Nautilus scripts."""
        try:
            tonietoolbox_dir = os.path.join(self.nautilus_scripts_dir, 'TonieToolbox')
            
            if os.path.exists(tonietoolbox_dir):
                import shutil
                shutil.rmtree(tonietoolbox_dir)
                self.logger.debug("Removed Nautilus scripts directory: %s", tonietoolbox_dir)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove Nautilus scripts: %s", e)
            return False
    
    def _remove_desktop_entries(self) -> bool:
        """Remove TonieToolbox desktop entries."""
        try:
            desktop_files = ['tonietoolbox.desktop']
            
            success = True
            for filename in desktop_files:
                filepath = os.path.join(self.desktop_apps_dir, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        self.logger.debug("Removed desktop entry: %s", filepath)
                    except Exception as e:
                        self.logger.warning("Failed to remove %s: %s", filepath, e)
                        success = False
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove desktop entries: %s", e)
            return False
    
    def _get_audio_mime_types(self) -> List[str]:
        """Get MIME types for supported audio formats."""
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


# Alias for Ubuntu compatibility
UbuntuIntegration = GNOMEIntegration