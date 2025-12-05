#!/usr/bin/python3
"""
KDE integration using the new modular system.
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


class KDEIntegration(LinuxBaseIntegration):
    """KDE service menu integration using the modular system.
    
    Creates context menu entries for audio files and TAF files in KDE's Dolphin
    file manager, supporting both KDE 5 and KDE 6. Provides file associations,
    custom icons, and MIME type handling for seamless integration.
    
    Example:
        Install KDE integration with default settings::
        
            from TonieToolbox.core.integrations.platforms.linux.kde import KDEIntegration
            
            integration = KDEIntegration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
            )
            if integration.install():
                print("KDE integration installed")
                print("Right-click on audio files in Dolphin to convert to TAF")
        
        Install with TeddyCloud upload support::
        
            from TonieToolbox.core.teddycloud.domain.models import UploadConfiguration
            
            upload_config = UploadConfiguration(
                server_url="http://teddycloud.local",
                username="admin",
                password="secret"
            )
            integration = KDEIntegration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox'),
                upload_config=upload_config
            )
            integration.install()  # Context menu includes "Upload to TeddyCloud"
        
        Uninstall KDE integration::
        
            integration = KDEIntegration(
                exe_path='/usr/local/bin/tonietoolbox',
                output_dir=os.path.expanduser('~/.local/share/tonietoolbox')
            )
            integration.uninstall()
            print("KDE service menus and file associations removed")
    """
    
    def __init__(self, exe_path: str = None, output_dir: str = None, 
                 upload_config=None, log_level: str = "INFO", log_to_file: bool = False):
        """Initialize KDE integration with provided configuration."""
        # Call parent constructor which handles common Linux setup
        super().__init__(exe_path, output_dir, upload_config, log_level, log_to_file)
    
    def _setup_desktop_specific_paths(self):
        """Set up KDE-specific paths."""
        # Determine KDE version and appropriate directory
        kde_version = os.environ.get('KDE_SESSION_VERSION', '5')
        if kde_version == '6':
            self.service_menu_dir = os.path.join(
                os.path.expanduser('~'), '.local', 'share', 'kio', 'servicemenus'
            )
        else:
            self.service_menu_dir = os.path.join(
                os.path.expanduser('~'), '.local', 'share', 'kservices5', 'ServiceMenus'
            )
        
        # Ensure directories exist
        os.makedirs(self.service_menu_dir, exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for KDE."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install KDE service menu integration."""
        try:
            self.logger.info("Installing KDE service menu integration")
            
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
            
            # Generate service menus
            success &= self._create_audio_service_menu(command_builder, command_set)
            success &= self._create_taf_service_menu(command_builder, command_set)
            success &= self._create_folder_service_menu(command_builder, command_set)
            
            # Create desktop application for TAF file associations
            success &= self._create_taf_application_file(command_builder)
            
            # Update desktop database to make file associations take effect
            success &= self._update_desktop_database()
            
            # Install shell completions
            success &= self.install_shell_completions()
            
            if success:
                self.logger.info("KDE integration installed successfully")
            else:
                self.logger.error("KDE integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install KDE integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall KDE service menu integration."""
        try:
            self.logger.info("Uninstalling KDE service menu integration")
            
            # Remove service menu files
            service_files = [
                'tonietoolbox-audio.desktop',
                'tonietoolbox-taf.desktop', 
                'tonietoolbox-folder.desktop'
            ]
            
            success = True
            for filename in service_files:
                filepath = os.path.join(self.service_menu_dir, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        self.logger.debug("Removed service menu file: %s", filepath)
                    except Exception as e:
                        self.logger.warning("Failed to remove %s: %s", filepath, e)
                        success = False
            
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
                self.logger.info("KDE integration uninstalled successfully")
            else:
                self.logger.warning("KDE integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall KDE integration: %s", e)
            return False
    
    def _create_audio_service_menu(self, command_builder: CommandBuilder, 
                                 command_set) -> bool:
        """Create service menu for audio files."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('kde_service_menu')
            
            if not template:
                self.logger.error("KDE service menu template not found")
                return False
            
            # Get audio commands
            audio_commands = command_set.get_commands_for_audio_files()
            
            # Build actions for template
            actions = []
            for cmd in audio_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue  # Skip upload commands if upload not configured
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_artwork=cmd.use_artwork,
                    use_json=cmd.use_json,
                    is_recursive=cmd.is_recursive
                ))
                
                actions.append({
                    'name': cmd.description,
                    'icon_path': self.icon_path,
                    'command': f'{command_line} %F'
                })
            
            # Get MIME types for audio files
            mime_types = self._get_audio_mime_types()
            
            # Render template
            content = template.render_with_actions(
                actions=actions,
                mime_types=';'.join(mime_types),
                icon_path=self.icon_path
            )
            
            # Write service menu file
            filepath = os.path.join(self.service_menu_dir, 'tonietoolbox-audio.desktop')
            with open(filepath, 'w') as f:
                f.write(content)
            
            # Set executable permissions
            os.chmod(filepath, 0o755)
            
            self.logger.debug("Created audio service menu: %s", filepath)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create audio service menu: %s", e)
            return False
    
    def _create_taf_service_menu(self, command_builder: CommandBuilder, 
                               command_set) -> bool:
        """Create service menu for TAF files."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('kde_service_menu')
            
            if not template:
                return False
            
            # Get TAF commands
            taf_commands = command_set.get_commands_for_taf_files()
            
            # Build actions
            actions = []
            for cmd in taf_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_info=cmd.use_info,
                    use_play=cmd.use_play,
                    is_split=cmd.is_split
                ))
                
                actions.append({
                    'name': cmd.description,
                    'icon_path': self.icon_path,
                    'command': f'{command_line} %F'
                })
            
            # Render and write
            content = template.render_with_actions(
                actions=actions,
                mime_types='application/x-tonie-audio-file',
                icon_path=self.icon_path
            )
            
            filepath = os.path.join(self.service_menu_dir, 'tonietoolbox-taf.desktop')
            with open(filepath, 'w') as f:
                f.write(content)
            
            # Set executable permissions
            os.chmod(filepath, 0o755)
            
            self.logger.debug("Created TAF service menu: %s", filepath)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create TAF service menu: %s", e)
            return False
    
    def _create_folder_service_menu(self, command_builder: CommandBuilder,
                                  command_set) -> bool:
        """Create service menu for folders."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('kde_service_menu')
            
            if not template:
                return False
            
            # Get folder commands
            folder_commands = command_set.get_commands_for_folders()
            
            # Build actions
            actions = []
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=cmd.is_recursive
                ))
                
                actions.append({
                    'name': cmd.description,
                    'icon_path': self.icon_path,
                    'command': f'{command_line} %F'
                })
            
            # Render and write
            content = template.render_with_actions(
                actions=actions,
                mime_types='inode/directory',
                icon_path=self.icon_path
            )
            
            filepath = os.path.join(self.service_menu_dir, 'tonietoolbox-folder.desktop')
            with open(filepath, 'w') as f:
                f.write(content)
            
            # Set executable permissions
            os.chmod(filepath, 0o755)
            
            self.logger.debug("Created folder service menu: %s", filepath)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create folder service menu: %s", e)
            return False