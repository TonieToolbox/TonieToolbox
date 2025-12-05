#!/usr/bin/python3
"""
macOS Automator integration using the new modular system.
"""
import os
import plistlib
import subprocess
from typing import List, Dict, Any
from ...base import (
    CommandBuilder, StandardCommandFactory, 
    get_template_manager
)
from .base import MacOSBaseIntegration
from ....config.application_constants import SUPPORTED_EXTENSIONS
from ....media import base64_to_png
from ....utils import get_logger

logger = get_logger(__name__)


class MacOSIntegration(MacOSBaseIntegration):
    """macOS Automator workflow integration using the modular system."""
    
    def _setup_platform_specific_paths(self):
        """Set up macOS-specific paths."""
        # macOS Services directory
        self.services_dir = os.path.expanduser('~/Library/Services')
        
        # Application Support directory for additional files
        self.app_support_dir = os.path.expanduser(
            '~/Library/Application Support/TonieToolbox'
        )
        
        # Ensure directories exist
        os.makedirs(self.services_dir, exist_ok=True)
        os.makedirs(self.app_support_dir, exist_ok=True)
    
    def _extract_icon_if_needed(self):
        """Extract PNG icon for macOS."""
        if not os.path.exists(self.icon_path):
            try:
                base64_to_png(self.icon_path)
                self.logger.debug("Extracted icon to %s", self.icon_path)
            except Exception as e:
                self.logger.warning("Failed to extract icon: %s", e)
    
    def install(self) -> bool:
        """Install macOS Automator services integration."""
        try:
            self.logger.info("Installing macOS Automator services integration")
            
            # Create command builder
            command_builder = CommandBuilder(
                exe_path=self.exe_path,
                upload_config=self.upload_config,
                log_level=self.log_level,
                log_to_file=self.log_to_file
            )
            
            # Get standard commands
            command_set = StandardCommandFactory.create_standard_commands()
            
            # Create TAF application bundle and file associations
            success = True
            success &= self._create_taf_application_bundle(command_builder)
            success &= self._register_file_associations()
            
            # Generate Automator services
            success &= self._create_audio_services(command_builder, command_set)
            success &= self._create_taf_services(command_builder, command_set)
            success &= self._create_folder_services(command_builder, command_set)
            
            # Install shell completions (optional - don't fail if no shells available)
            completion_success = self.install_shell_completions()
            if not completion_success:
                self.logger.debug("Shell completion installation skipped (no compatible shells found)")
            
            # Refresh services cache
            if success:
                self._refresh_services_cache()
            
            if success:
                self.logger.info("macOS integration installed successfully")
            else:
                self.logger.error("macOS integration installation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to install macOS integration: %s", e)
            return False
    
    def uninstall(self) -> bool:
        """Uninstall macOS Automator services integration."""
        try:
            self.logger.info("Uninstalling macOS Automator services integration")
            
            # Remove TAF application bundle and file associations
            success = self._unregister_file_associations()
            success &= self._remove_taf_application_bundle()
            
            # Remove service workflows
            success &= self._remove_service_workflows()
            
            # Uninstall shell completions (optional - don't fail if no shells available)
            completion_success = self.uninstall_shell_completions()
            if not completion_success:
                self.logger.debug("Shell completion uninstallation skipped (no compatible shells found)")
            
            # Refresh services cache
            if success:
                self._refresh_services_cache()
            
            if success:
                self.logger.info("macOS integration uninstalled successfully")
            else:
                self.logger.warning("macOS integration uninstallation had errors")
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to uninstall macOS integration: %s", e)
            return False
    
    def _create_audio_services(self, command_builder: CommandBuilder,
                             command_set) -> bool:
        """Create Automator services for audio files."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('macos_automator')
            
            if not template:
                self.logger.error("macOS Automator template not found")
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
                
                # Create service workflow
                service_name = f"TonieToolbox - {cmd.description}"
                success &= self._create_service_workflow(
                    service_name=service_name,
                    command=command_line,
                    input_types=['public.audio'],
                    template=template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to create audio services: %s", e)
            return False
    
    def _create_taf_services(self, command_builder: CommandBuilder,
                           command_set) -> bool:
        """Create Automator services for TAF files."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('macos_automator')
            
            if not template:
                return False
            
            # Get TAF commands
            taf_commands = command_set.get_commands_for_taf_files()
            
            success = True
            for cmd in taf_commands:
                if not self.upload_config.is_enabled and cmd.use_upload:
                    continue
                
                command_line = ' '.join(command_builder.build_base_command(
                    use_upload=cmd.use_upload,
                    use_info=cmd.use_info,
                    use_play=cmd.use_play,
                    is_split=cmd.is_split
                ))
                
                # Create service workflow
                service_name = f"TonieToolbox - {cmd.description}"
                success &= self._create_service_workflow(
                    service_name=service_name,
                    command=command_line,
                    input_types=['public.data'],  # TAF files are binary
                    template=template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to create TAF services: %s", e)
            return False
    
    def _create_folder_services(self, command_builder: CommandBuilder,
                              command_set) -> bool:
        """Create Automator services for folders."""
        try:
            template_manager = get_template_manager()
            template = template_manager.get_template('macos_automator')
            
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
                
                # Create service workflow
                service_name = f"TonieToolbox - {cmd.description}"
                success &= self._create_service_workflow(
                    service_name=service_name,
                    command=command_line,
                    input_types=['public.folder'],
                    template=template
                )
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to create folder services: %s", e)
            return False
    
    def _create_service_workflow(self, service_name: str, command: str,
                               input_types: List[str], template) -> bool:
        """Create a single Automator service workflow."""
        try:
            # Generate workflow content
            workflow_data = template.render_service_workflow(
                service_name=service_name,
                command=command,
                input_types=input_types,
                icon_path=self.icon_path
            )
            
            # Create .workflow bundle
            workflow_path = os.path.join(self.services_dir, f"{service_name}.workflow")
            contents_dir = os.path.join(workflow_path, "Contents")
            
            # Create bundle structure
            os.makedirs(contents_dir, exist_ok=True)
            
            # Write Info.plist
            info_plist_path = os.path.join(contents_dir, "Info.plist")
            with open(info_plist_path, 'wb') as f:
                plistlib.dump(workflow_data['info_plist'], f)
            
            # Write document.wflow
            document_path = os.path.join(contents_dir, "document.wflow")
            with open(document_path, 'wb') as f:
                plistlib.dump(workflow_data['document'], f)
            
            # Copy icon if available
            if os.path.exists(self.icon_path):
                icon_dest = os.path.join(contents_dir, "Resources", "icon.png")
                os.makedirs(os.path.dirname(icon_dest), exist_ok=True)
                import shutil
                shutil.copy2(self.icon_path, icon_dest)
            
            self.logger.debug("Created Automator service: %s", workflow_path)
            return True
            
        except Exception as e:
            self.logger.error("Failed to create service workflow '%s': %s", 
                            service_name, e)
            return False
    
    def _remove_service_workflows(self) -> bool:
        """Remove all TonieToolbox service workflows."""
        try:
            if not os.path.exists(self.services_dir):
                return True
            
            success = True
            for item in os.listdir(self.services_dir):
                if item.startswith('TonieToolbox') and item.endswith('.workflow'):
                    workflow_path = os.path.join(self.services_dir, item)
                    try:
                        import shutil
                        shutil.rmtree(workflow_path)
                        self.logger.debug("Removed service workflow: %s", item)
                    except Exception as e:
                        self.logger.warning("Failed to remove workflow %s: %s", 
                                          item, e)
                        success = False
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to remove service workflows: %s", e)
            return False
    
    def _refresh_services_cache(self):
        """Refresh the macOS Services cache."""
        try:
            # Use lsregister to refresh services
            subprocess.run([
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister',
                '-kill', '-r', '-domain', 'local', '-domain', 'system', '-domain', 'user'
            ], capture_output=True)
            
            self.logger.debug("Refreshed Services cache")
        except Exception as e:
            self.logger.warning("Failed to refresh Services cache: %s", e)