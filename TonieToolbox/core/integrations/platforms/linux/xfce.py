#!/usr/bin/python3
"""
XFCE integration using the new modular system.
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


class XFCEIntegration(LinuxBaseIntegration):
    """XFCE custom actions integration using the modular system."""
    
    def _setup_desktop_specific_paths(self):
        """Set up XFCE-specific paths."""
        # XFCE configuration directory
        xfce_config_home = os.environ.get('XDG_CONFIG_HOME', 
                                        os.path.expanduser('~/.config'))
        self.custom_actions_dir = os.path.join(xfce_config_home, 'Thunar', 'uca.xml')
        
        # Ensure Thunar directory exists
        os.makedirs(os.path.dirname(self.custom_actions_dir), exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for XFCE."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install XFCE custom actions integration."""
        try:
            self.logger.info("Installing XFCE custom actions integration")
            
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
            
            # Generate custom actions
            success &= self._create_custom_actions(command_builder, command_set)
            
            # Create desktop application for TAF file associations
            success &= self._create_taf_application_file(command_builder)
            
            # Update desktop database to make file associations take effect
            success &= self._update_desktop_database()
            
            # Install shell completions
            success &= self.install_shell_completions()
            
            if success:
                self.logger.info("XFCE integration installed successfully")
            else:
                self.logger.error("XFCE integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install XFCE integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall XFCE custom actions integration."""
        try:
            self.logger.info("Uninstalling XFCE custom actions integration")
            
            # Remove our custom actions from uca.xml
            success = self._remove_custom_actions()
            
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
                self.logger.info("XFCE integration uninstalled successfully")
            else:
                self.logger.warning("XFCE integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall XFCE integration: %s", e)
            return False
    
    def _create_custom_actions(self, command_builder: CommandBuilder, 
                             command_set) -> bool:
        """Create XFCE custom actions XML."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('xfce_custom_actions')
            
            if not template:
                self.logger.error("XFCE custom actions template not found")
                return False
            
            # Collect all actions
            all_actions = []
            
            # Audio file actions
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
                
                all_actions.append({
                    'name': f"TonieToolbox: {cmd.description}",
                    'description': f"Process audio files with {cmd.description}",
                    'icon': self.icon_path,
                    'command': f'{command_line} %F',
                    'patterns': ';'.join([f'*{ext}' for ext in SUPPORTED_EXTENSIONS])
                })
            
            # TAF file actions
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
                
                all_actions.append({
                    'name': f"TonieToolbox: {cmd.description}",
                    'description': f"Process TAF files with {cmd.description}",
                    'icon': self.icon_path,
                    'command': f'{command_line} %F',
                    'patterns': '*.taf'
                })
            
            # Folder actions
            folder_commands = command_set.get_commands_for_folders()
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=cmd.is_recursive
                ))
                
                all_actions.append({
                    'name': f"TonieToolbox: {cmd.description}",
                    'description': f"Process folders with {cmd.description}",
                    'icon': self.icon_path,
                    'command': f'{command_line} %F',
                    'directories': True
                })
            
            # Read existing uca.xml if it exists
            existing_content = ""
            if os.path.exists(self.custom_actions_dir):
                with open(self.custom_actions_dir, 'r') as f:
                    existing_content = f.read()
            
            # Merge our actions with existing ones
            content = template.merge_actions(existing_content, all_actions)
            
            # Write updated uca.xml
            with open(self.custom_actions_dir, 'w') as f:
                f.write(content)
            
            self.logger.debug("Created XFCE custom actions: %s", self.custom_actions_dir)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create XFCE custom actions: %s", e)
            return False
    
    def _remove_custom_actions(self) -> bool:
        """Remove our custom actions from uca.xml."""
        try:
            if not os.path.exists(self.custom_actions_dir):
                return True  # Nothing to remove
            
            template_manager = get_template_manager()
            template = template_manager.get_template('xfce_custom_actions')
            
            if not template:
                self.logger.warning("XFCE template not found for removal")
                return False
            
            # Read existing content
            with open(self.custom_actions_dir, 'r') as f:
                existing_content = f.read()
            
            # Remove our actions
            updated_content = template.remove_actions(existing_content)
            
            # Write back if there's still content, otherwise remove file
            if updated_content.strip():
                with open(self.custom_actions_dir, 'w') as f:
                    f.write(updated_content)
            else:
                os.remove(self.custom_actions_dir)
            
            self.logger.debug("Removed XFCE custom actions")
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove XFCE custom actions: %s", e)
            return False