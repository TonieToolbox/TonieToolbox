#!/usr/bin/python3
"""
Cinnamon desktop (Nemo file manager) integration using the new modular system.
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


class CinnamonIntegration(LinuxBaseIntegration):
    """Cinnamon desktop Nemo integration using the modular system."""
    
    def _setup_desktop_specific_paths(self):
        """Set up Cinnamon-specific paths."""
        # Nemo script directories
        self.nemo_scripts_dir = os.path.expanduser('~/.local/share/nemo/scripts')
        
        # Nemo actions directory (for context menus)
        self.nemo_actions_dir = os.path.expanduser('~/.local/share/nemo/actions')
        
        # Ensure directories exist
        os.makedirs(self.nemo_scripts_dir, exist_ok=True)
        os.makedirs(self.nemo_actions_dir, exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for Cinnamon."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install Cinnamon Nemo integration."""
        try:
            self.logger.info("Installing Cinnamon Nemo integration")
            
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
            
            # Generate Nemo scripts and actions
            success &= self._create_nemo_scripts(command_builder, command_set)
            success &= self._create_nemo_actions(command_builder, command_set)
            
            # Create desktop application for TAF file associations
            success &= self._create_taf_application_file(command_builder)
            
            # Update desktop database to make file associations take effect
            success &= self._update_desktop_database()
            
            # Install shell completions
            success &= self.install_shell_completions()
            
            if success:
                self.logger.info("Cinnamon integration installed successfully")
            else:
                self.logger.error("Cinnamon integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install Cinnamon integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall Cinnamon Nemo integration."""
        try:
            self.logger.info("Uninstalling Cinnamon Nemo integration")
            
            # Remove Nemo scripts and actions
            success = True
            success &= self._remove_nemo_scripts()
            success &= self._remove_nemo_actions()
            
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
                self.logger.info("Cinnamon integration uninstalled successfully")
            else:
                self.logger.warning("Cinnamon integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall Cinnamon integration: %s", e)
            return False
    
    def _create_nemo_scripts(self, command_builder: CommandBuilder, 
                           command_set) -> bool:
        """Create Nemo scripts."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('nemo_script')
            
            if not template:
                # Fallback to generic script template
                template = template_manager.get_template('nautilus_script')
                if not template:
                    self.logger.error("Nemo/Nautilus script template not found")
                    return False
            
            # Create TonieToolbox subdirectory
            tonietoolbox_dir = os.path.join(self.nemo_scripts_dir, 'TonieToolbox')
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
            
            self.logger.debug("Created Nemo scripts in: %s", tonietoolbox_dir)
            return success
            
        except Exception as e:
            self.logger.error("Failed to create Nemo scripts: %s", e)
            return False
    
    def _create_nemo_actions(self, command_builder: CommandBuilder,
                           command_set) -> bool:
        """Create Nemo action files for context menu integration."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('nemo_action')
            
            if not template:
                self.logger.warning("Nemo action template not found, skipping actions")
                return True  # Non-critical
            
            success = True
            
            # Create actions for audio files
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
                
                action_content = template.render_action(
                    name=f"TonieToolbox: {cmd.description}",
                    comment=f"Process audio files with {cmd.description}",
                    command=f'{command_line} %F',
                    icon_path=self.icon_path,
                    mime_types=self._get_audio_mime_types()
                )
                
                action_path = os.path.join(self.nemo_actions_dir, f"tonietoolbox_{cmd.id}_audio.nemo_action")
                with open(action_path, 'w') as f:
                    f.write(action_content)
                
                success &= True
            
            # Create actions for TAF files
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
                
                action_content = template.render_action(
                    name=f"TonieToolbox: {cmd.description}",
                    comment=f"Process TAF files with {cmd.description}",
                    command=f'{command_line} %F',
                    icon_path=self.icon_path,
                    mime_types=['application/octet-stream']
                )
                
                action_path = os.path.join(self.nemo_actions_dir, f"tonietoolbox_{cmd.id}_taf.nemo_action")
                with open(action_path, 'w') as f:
                    f.write(action_content)
                
                success &= True
            
            # Create actions for folders
            folder_commands = command_set.get_commands_for_folders()
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=cmd.is_recursive
                ))
                
                action_content = template.render_action(
                    name=f"TonieToolbox: {cmd.description}",
                    comment=f"Process folders with {cmd.description}",
                    command=f'{command_line} %F',
                    icon_path=self.icon_path,
                    selection_type=['any'],
                    extensions=['dir']
                )
                
                action_path = os.path.join(self.nemo_actions_dir, f"tonietoolbox_{cmd.id}_folder.nemo_action")
                with open(action_path, 'w') as f:
                    f.write(action_content)
                
                success &= True
            
            self.logger.debug("Created Nemo actions in: %s", self.nemo_actions_dir)
            return success
            
        except Exception as e:
            self.logger.warning("Failed to create Nemo actions: %s", e)
            return True  # Non-critical
    
    def _remove_nemo_scripts(self) -> bool:
        """Remove TonieToolbox Nemo scripts."""
        try:
            tonietoolbox_dir = os.path.join(self.nemo_scripts_dir, 'TonieToolbox')
            
            if os.path.exists(tonietoolbox_dir):
                import shutil
                shutil.rmtree(tonietoolbox_dir)
                self.logger.debug("Removed Nemo scripts directory: %s", tonietoolbox_dir)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to remove Nemo scripts: %s", e)
            return False
    
    def _remove_nemo_actions(self) -> bool:
        """Remove TonieToolbox Nemo actions."""
        try:
            if not os.path.exists(self.nemo_actions_dir):
                return True
            
            success = True
            for item in os.listdir(self.nemo_actions_dir):
                if item.startswith('tonietoolbox_') and item.endswith('.nemo_action'):
                    action_path = os.path.join(self.nemo_actions_dir, item)
                    try:
                        os.remove(action_path)
                        self.logger.debug("Removed Nemo action: %s", item)
                    except Exception as e:
                        self.logger.warning("Failed to remove action %s: %s", item, e)
                        success = False
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove Nemo actions: %s", e)
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