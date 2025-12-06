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
        # Use SystemFileAssociations for extension-specific menus (matches legacy behavior)
        self.registry_roots = {
            'audio_files_base': r'SOFTWARE\Classes\SystemFileAssociations',  # Will append \.{ext}\shell
            'taf_files': r'SOFTWARE\Classes\SystemFileAssociations\.taf\shell',
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
            
            # Install TAF file association and context menus
            success = True
            success &= self._install_taf_file_association(command_builder)
            success &= self._install_taf_context_menus(command_builder, command_set)
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
        """Uninstall Windows context menu integration (including legacy entries)."""
        try:
            self.logger.info("Uninstalling Windows context menu integration")
            
            success = True
            
            # Remove TAF file association
            success &= self._remove_taf_file_association()
            
            # Remove current registry entries
            success &= self._remove_registry_entries()
            
            # Remove legacy registry entries (from old integration system)
            legacy_success = self._remove_legacy_registry_entries()
            if legacy_success:
                self.logger.info("Legacy registry entries removed successfully")
            else:
                self.logger.debug("No legacy registry entries found or already removed")
            
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
        """Install context menus for audio files (per extension, like legacy)."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('windows_registry')
            
            if not template:
                self.logger.error("Windows registry template not found")
                return False
            
            # Get audio commands (conversion commands only)
            audio_commands = command_set.get_commands_for_audio_files()
            
            # Get audio extensions
            from ....config.application_constants import SUPPORTED_EXTENSIONS
            
            success = True
            # Create context menus for each audio extension
            for ext in SUPPORTED_EXTENSIONS:
                ext = ext.lower().lstrip('.')
                ext_root_path = f"{self.registry_roots['audio_files_base']}\\.{ext}\\shell"
                
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
                        ext_root_path, 
                        entry_data,
                        template
                    )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install audio context menus: %s", e)
            return False
    
    def _install_taf_context_menus(self, command_builder: CommandBuilder,
                                  command_set) -> bool:
        """Install context menus for TAF files (info, split, upload - NO conversion)."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('windows_registry')
            
            if not template:
                self.logger.error("Windows registry template not found")
                return False
            
            # Get TAF-specific commands (no conversion commands)
            taf_commands = command_set.get_commands_for_taf_files()
            
            success = True
            for cmd in taf_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_info=cmd.use_info,
                    use_play=cmd.use_play,
                    is_split=cmd.is_split,
                    use_upload=cmd.use_upload,
                    use_artwork=cmd.use_artwork,
                    use_json=cmd.use_json
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
                    self.registry_roots['taf_files'], 
                    entry_data,
                    template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install TAF context menus: %s", e)
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
        """Remove all TonieToolbox registry entries using UAC-elevated .reg file."""
        try:
            # Build list of registry keys to remove
            reg_content = ['Windows Registry Editor Version 5.00', '']
            
            # Remove from audio extension-specific paths
            from ....config.application_constants import SUPPORTED_EXTENSIONS
            for ext in SUPPORTED_EXTENSIONS:
                ext = ext.lower().lstrip('.')
                ext_root_path = f"{self.registry_roots['audio_files_base']}\\.{ext}\\shell"
                keys_to_remove = self._find_tonietoolbox_keys(ext_root_path)
                
                self.logger.info(f"Found {len(keys_to_remove)} TonieToolbox keys in {ext_root_path}: {keys_to_remove}")
                
                for key_name in keys_to_remove:
                    full_path = f"HKEY_CURRENT_USER\\{ext_root_path}\\{key_name}"
                    reg_content.append(f"[-{full_path}]")
                    reg_content.append('')
                    self.logger.info(f"Marked for removal: {full_path}")
            
            # Remove from TAF, directories, and directory_background paths
            for root_name in ['taf_files', 'directories', 'directory_background']:
                root_path = self.registry_roots[root_name]
                keys_to_remove = self._find_tonietoolbox_keys(root_path)
                
                self.logger.info(f"Found {len(keys_to_remove)} TonieToolbox keys in {root_path}: {keys_to_remove}")
                
                # Add deletion entries to registry content
                for key_name in keys_to_remove:
                    full_path = f"HKEY_CURRENT_USER\\{root_path}\\{key_name}"
                    reg_content.append(f"[-{full_path}]")
                    reg_content.append('')
                    self.logger.info(f"Marked for removal: {full_path}")
            
            # Remove Windows ApplicationAssociationToasts entries for TAF file association
            # These are created automatically by Windows when file associations are registered
            toast_path = r"Software\Microsoft\Windows\CurrentVersion\ApplicationAssociationToasts"
            self.logger.info(f"Removing TAF association toast entries from {toast_path}")
            reg_content.append(f'[HKEY_CURRENT_USER\\{toast_path}]')
            reg_content.append('"TonieToolbox.TAF_.taf"=-')
            reg_content.append('')
            
            # Remove Windows Explorer FileExts entries for TAF files
            # These track "Open With" history and are created automatically by Windows Explorer
            fileexts_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.taf"
            self.logger.info(f"Removing TAF file extension history from {fileexts_path}")
            reg_content.append(f'[-HKEY_CURRENT_USER\\{fileexts_path}]')
            reg_content.append('')
            
            # Remove old wildcard context menu entries (SOFTWARE\Classes\*\shell)
            # These are from older versions that used wildcard paths instead of per-extension paths
            wildcard_shell_path = r"SOFTWARE\Classes\*\shell"
            wildcard_keys = self._find_tonietoolbox_keys(wildcard_shell_path)
            if wildcard_keys:
                self.logger.info(f"Found {len(wildcard_keys)} old wildcard TonieToolbox keys in {wildcard_shell_path}: {wildcard_keys}")
                for key_name in wildcard_keys:
                    full_path = f"HKEY_CURRENT_USER\\{wildcard_shell_path}\\{key_name}"
                    reg_content.append(f"[-{full_path}]")
                    reg_content.append('')
                    self.logger.info(f"Marked for removal: {full_path}")
            
            # If no keys to remove, return success
            if len(reg_content) <= 2:
                self.logger.info("No TonieToolbox registry keys found to remove")
                return True
            
            # Log the .reg file content for debugging
            self.logger.info(f"Registry removal file content ({len(reg_content)} lines):")
            for line in reg_content[:20]:  # Log first 20 lines
                self.logger.info(f"  {line}")
            if len(reg_content) > 20:
                self.logger.info(f"  ... ({len(reg_content) - 20} more lines)")
            
            # Create temporary .reg file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.reg', 
                                           delete=False, encoding='utf-16le') as f:
                f.write('\ufeff')  # BOM for UTF-16LE
                f.write('\n'.join(reg_content))
                reg_file = f.name
            
            self.logger.info(f"Created registry removal file: {reg_file}")
            
            try:
                # Import registry file with reg import
                result = subprocess.run([
                    'reg', 'import', reg_file
                ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
                
                self.logger.info("Registry removal file imported successfully")
                self.logger.debug(f"reg import output: {result.stdout}")
                return True
                
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Failed to import registry removal file: {e.stderr if e.stderr else str(e)}")
                self.logger.error(f"Registry file location: {reg_file} (kept for debugging)")
                return False
                
            # Keep file for debugging on success too
            self.logger.info(f"Registry removal successful. File kept for inspection: {reg_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove registry entries: {e}", exc_info=True)
            return False
    
    def _find_tonietoolbox_keys(self, root_path: str) -> List[str]:
        """Find all TonieToolbox entries in a specific registry root."""
        keys_to_delete = []
        
        self.logger.debug(f"Searching for TonieToolbox keys in: {root_path}")
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, root_path) as parent_key:
                # Enumerate subkeys to find TonieToolbox entries
                i = 0
                try:
                    while True:
                        key_name = winreg.EnumKey(parent_key, i)
                        self.logger.debug(f"  Found subkey: {key_name}")
                        if key_name.startswith('TonieToolbox_'):
                            keys_to_delete.append(key_name)
                            self.logger.debug(f"    -> Matches TonieToolbox pattern")
                        i += 1
                except OSError:
                    pass  # End of enumeration
                    
        except FileNotFoundError:
            # Registry path doesn't exist, nothing to remove
            self.logger.debug(f"Registry path not found: {root_path}")
        except Exception as e:
            self.logger.warning(f"Failed to enumerate keys in {root_path}: {e}")
        
        self.logger.debug(f"Found {len(keys_to_delete)} TonieToolbox keys in {root_path}")
        return keys_to_delete
    
    def _remove_legacy_registry_entries(self) -> bool:
        """
        Remove legacy registry entries from the old WindowsClassicContextMenuIntegration.
        
        The legacy integration used HKEY_CLASSES_ROOT\\SystemFileAssociations with
        cascade menus named "TonieToolbox" for audio files, .taf files, and directories.
        
        Returns:
            bool: True if removal was successful or no entries found, False on error.
        """
        try:
            # Build list of legacy registry keys to remove
            reg_content = ['Windows Registry Editor Version 5.00', '']
            
            # Legacy used SystemFileAssociations for audio extensions
            for ext in SUPPORTED_EXTENSIONS:
                ext = ext.lower().lstrip('.')
                reg_content.append(f'[-HKEY_CLASSES_ROOT\\SystemFileAssociations\\.{ext}\\shell\\TonieToolbox]')
                reg_content.append('')
            
            # Legacy .taf file entries
            reg_content.append('[-HKEY_CLASSES_ROOT\\SystemFileAssociations\\.taf\\shell\\TonieToolbox]')
            reg_content.append('')
            
            # Legacy folder entries
            reg_content.append('[-HKEY_CLASSES_ROOT\\Directory\\shell\\TonieToolbox]')
            reg_content.append('')
            
            # Create temporary .reg file for legacy cleanup
            with tempfile.NamedTemporaryFile(mode='w', suffix='.reg', 
                                           delete=False, encoding='utf-16le') as f:
                f.write('\ufeff')  # BOM for UTF-16LE
                f.write('\n'.join(reg_content))
                reg_file = f.name
            
            try:
                # Import registry file to remove legacy entries
                result = subprocess.run([
                    'reg', 'import', reg_file
                ], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
                
                self.logger.debug("Legacy registry removal file imported successfully")
                
                # Notify Windows Shell to refresh after removing legacy entries
                self._refresh_shell_associations()
                
                return True
                
            except subprocess.CalledProcessError as e:
                # If the keys don't exist, reg import might fail - that's OK
                if "cannot find the file" not in str(e.stderr).lower():
                    self.logger.debug("Legacy registry entries may not exist: %s", 
                                    e.stderr if e.stderr else str(e))
                return True  # Not an error if legacy entries don't exist
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(reg_file)
                except Exception:
                    pass
            
        except Exception as e:
            self.logger.warning("Failed to remove legacy registry entries: %s", e)
            return False  # Non-fatal, return False but don't fail uninstall