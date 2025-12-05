#!/usr/bin/python3
"""
Windows registry integration using the new modular system.
"""
import os
import subprocess
import tempfile
from typing import List, Dict, Any, Optional

# Import winreg only on Windows
try:
    import winreg
except ImportError:
    winreg = None
from ...base import (
    CommandBuilder, StandardCommandFactory, 
    get_template_manager
)
from .base import WindowsBaseIntegration
from ....config.application_constants import ICON_ICO_BASE64, SUPPORTED_EXTENSIONS
from ....utils.icons import base64_to_ico
from ....utils import get_logger

logger = get_logger(__name__)


class WindowsIntegration(WindowsBaseIntegration):
    """Windows context menu integration using the modular system."""
    
    def _setup_platform_specific_paths(self):
        """Set up Windows-specific registry paths."""
        # Registry paths for context menus
        self.registry_roots = {
            'audio_files': r'SOFTWARE\Classes\*\shell',
            'directories': r'SOFTWARE\Classes\Directory\shell',
            'directory_background': r'SOFTWARE\Classes\Directory\Background\shell'
        }
    
    def _extract_icon_if_needed(self):
        """Extract ICO icon for Windows."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_ico(ICON_ICO_BASE64, self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install Windows context menu integration."""
        try:
            self.logger.info("Installing Windows context menu integration")
            
            # Create command builder
            command_builder = CommandBuilder(
                exe_path=self.exe_path,
                upload_config=self.upload_config,
                log_level=self.log_level,
                log_to_file=self.log_to_file
            )
            
            # Get standard commands
            command_set = StandardCommandFactory.create_standard_commands()
            
            # Install TAF file association and registry entries
            success = True
            success &= self._install_taf_file_association(command_builder)
            success &= self._install_audio_context_menus(command_builder, command_set)
            success &= self._install_directory_context_menus(command_builder, command_set)
            success &= self._install_background_context_menus(command_builder, command_set)
            
            # Refresh file associations
            success &= self._refresh_file_associations()
            
            # Install shell completions (optional - don't fail if no shells available)
            completion_success = self.install_shell_completions()
            if not completion_success:
                self.logger.debug("Shell completion installation skipped (no compatible shells found)")
            
            if success:
                self.logger.info("Windows integration installed successfully")
            else:
                self.logger.error("Windows integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install Windows integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall Windows context menu integration."""
        try:
            self.logger.info("Uninstalling Windows context menu integration")
            
            success = True
            
            # Remove TAF file association
            success &= self._remove_taf_file_association()
            
            # Remove registry entries
            success &= self._remove_registry_entries()
            
            # Uninstall shell completions (optional - don't fail if no shells available)
            completion_success = self.uninstall_shell_completions()
            if not completion_success:
                self.logger.debug("Shell completion uninstallation skipped (no compatible shells found)")
            
            if success:
                self.logger.info("Windows integration uninstalled successfully")
            else:
                self.logger.warning("Windows integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall Windows integration: %s", e)
            return False
    
    def _install_audio_context_menus(self, command_builder: CommandBuilder,
                                   command_set) -> bool:
        """Install context menus for audio files."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('windows_registry')
            
            if not template:
                self.logger.error("Windows registry template not found")
                return False
            
            # Get audio commands
            audio_commands = command_set.get_commands_for_audio_files()
            
            success = True
            for cmd in audio_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_artwork=cmd.use_artwork,
                    use_json=cmd.use_json,
                    is_recursive=cmd.is_recursive
                ))
                
                # Create registry entry for this command
                registry_key = f"TonieToolbox_{cmd.name}"
                
                entry_data = {
                    'key_name': registry_key,
                    'display_name': f"TonieToolbox: {cmd.description}",
                    'command': f'"{command_line}" "%1"',
                    'icon_path': self.icon_path
                }
                
                success &= self._create_registry_entry(
                    self.registry_roots['audio_files'], 
                    entry_data,
                    template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install audio context menus: %s", e)
            return False
    
    def _install_directory_context_menus(self, command_builder: CommandBuilder,
                                       command_set) -> bool:
        """Install context menus for directories."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('windows_registry')
            
            if not template:
                return False
            
            # Get folder commands
            folder_commands = command_set.get_commands_for_folders()
            
            success = True
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=cmd.is_recursive
                ))
                
                registry_key = f"TonieToolbox_{cmd.name}"
                
                entry_data = {
                    'key_name': registry_key,
                    'display_name': f"TonieToolbox: {cmd.description}",
                    'command': f'"{command_line}" "%1"',
                    'icon_path': self.icon_path
                }
                
                success &= self._create_registry_entry(
                    self.registry_roots['directories'], 
                    entry_data,
                    template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install directory context menus: %s", e)
            return False
    
    def _install_background_context_menus(self, command_builder: CommandBuilder,
                                        command_set) -> bool:
        """Install context menus for directory backgrounds."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('windows_registry')
            
            if not template:
                return False
            
            # Get folder commands suitable for background
            folder_commands = command_set.get_commands_for_folders()
            
            success = True
            for cmd in folder_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                if not cmd.is_recursive:
                    continue  # Only recursive commands make sense for background
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    is_recursive=True
                ))
                
                registry_key = f"TonieToolbox_{cmd.name}_bg"
                
                entry_data = {
                    'key_name': registry_key,
                    'display_name': f"TonieToolbox: {cmd.description} (Here)",
                    'command': f'"{command_line}" "%V"',
                    'icon_path': self.icon_path
                }
                
                success &= self._create_registry_entry(
                    self.registry_roots['directory_background'], 
                    entry_data,
                    template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install background context menus: %s", e)
            return False
    
    def _create_registry_entry(self, root_path: str, entry_data: Dict[str, str],
                             template) -> bool:
        """Create a single registry entry."""
        try:
            # Generate registry content
            content = template.render_context_menu_entry(
                root_path=root_path,
                **entry_data
            )
            
            # Write to temporary .reg file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.reg', 
                                           delete=False, encoding='utf-16le') as f:
                f.write('\ufeff')  # BOM for UTF-16LE
                f.write(content)
                reg_file = f.name
            
            try:
                # Import registry file
                result = subprocess.run([
                    'reg', 'import', reg_file
                ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
                
                self.logger.debug("Created registry entry: %s", entry_data['key_name'])
                return True
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(reg_file)
                except:
                    pass
            
        except subprocess.CalledProcessError as e:
            self.logger.error("Failed to import registry entry %s: %s", 
                            entry_data['key_name'], e)
            return False
        except Exception as e:
            self.logger.error("Failed to create registry entry %s: %s", 
                            entry_data['key_name'], e)
            return False
    
    def _remove_registry_entries(self) -> bool:
        """Remove all TonieToolbox registry entries."""
        try:
            success = True
            
            # Remove from all registry roots
            for root_name, root_path in self.registry_roots.items():
                success &= self._remove_from_registry_root(root_path)
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove registry entries: %s", e)
            return False
    
    def _remove_from_registry_root(self, root_path: str) -> bool:
        """Remove TonieToolbox entries from a specific registry root."""
        try:
            # Open the registry key
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root_path) as parent_key:
                    # Enumerate subkeys to find TonieToolbox entries
                    i = 0
                    keys_to_delete = []
                    
                    try:
                        while True:
                            key_name = winreg.EnumKey(parent_key, i)
                            if key_name.startswith('TonieToolbox_'):
                                keys_to_delete.append(key_name)
                            i += 1
                    except OSError:
                        pass  # End of enumeration
                    
                    # Delete found keys
                    for key_name in keys_to_delete:
                        try:
                            winreg.DeleteKey(parent_key, key_name)
                            self.logger.debug("Removed registry key: %s\\%s", 
                                            root_path, key_name)
                        except Exception as e:
                            self.logger.warning("Failed to delete key %s: %s", 
                                              key_name, e)
                
                return True
                
            except FileNotFoundError:
                # Registry path doesn't exist, nothing to remove
                return True
            
        except Exception as e:
            self.logger.error("Failed to remove from registry root %s: %s", 
                            root_path, e)
            return False