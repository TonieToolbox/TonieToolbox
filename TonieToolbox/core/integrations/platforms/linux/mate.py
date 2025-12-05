#!/usr/bin/python3
"""
MATE desktop (Caja file manager) integration using the new modular system.
"""
import os
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


class MATEIntegration(LinuxBaseIntegration):
    """MATE desktop Caja integration using the modular system."""
    
    def _setup_desktop_specific_paths(self):
        """Set up MATE-specific paths."""
        # Caja script directories
        self.caja_scripts_dir = os.path.expanduser('~/.local/share/caja/scripts')
        
        # Ensure directories exist
        os.makedirs(self.caja_scripts_dir, exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for MATE."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install MATE Caja integration."""
        try:
            self.logger.info("Installing MATE Caja integration")
            
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
            
            # Generate Caja scripts
            success &= self._create_caja_scripts(command_builder, command_set)
            
            # Create desktop application for TAF file associations
            success &= self._create_taf_application_file(command_builder)
            
            # Update desktop database to make file associations take effect
            success &= self._update_desktop_database()
            
            # Install shell completions
            success &= self.install_shell_completions()
            
            if success:
                self.logger.info("MATE integration installed successfully")
            else:
                self.logger.error("MATE integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install MATE integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall MATE Caja integration."""
        try:
            self.logger.info("Uninstalling MATE Caja integration")
            
            # Remove Caja scripts
            success = self._remove_caja_scripts()
            
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
                self.logger.info("MATE integration uninstalled successfully")
            else:
                self.logger.warning("MATE integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall MATE integration: %s", e)
            return False
    
    def _create_caja_scripts(self, command_builder: CommandBuilder, 
                           command_set) -> bool:
        """Create Caja scripts."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('caja_script')
            
            if not template:
                # Fallback to generic script template
                template = template_manager.get_template('nautilus_script')
                if not template:
                    self.logger.error("Caja/Nautilus script template not found")
                    return False
            
            # Create TonieToolbox subdirectory
            tonietoolbox_dir = os.path.join(self.caja_scripts_dir, 'TonieToolbox')
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
            
            self.logger.debug("Created Caja scripts in: %s", tonietoolbox_dir)
            return success
            
        except Exception as e:
            self.logger.error("Failed to create Caja scripts: %s", e)
            return False
    
    def _remove_caja_scripts(self) -> bool:
        """Remove TonieToolbox Caja scripts."""
        try:
            tonietoolbox_dir = os.path.join(self.caja_scripts_dir, 'TonieToolbox')
            
            if os.path.exists(tonietoolbox_dir):
                import shutil
                shutil.rmtree(tonietoolbox_dir)
                self.logger.debug("Removed Caja scripts directory: %s", tonietoolbox_dir)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove Caja scripts: %s", e)
            return False