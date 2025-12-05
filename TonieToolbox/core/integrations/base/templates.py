#!/usr/bin/python3
"""
Template system for integration configurations.
"""
from typing import Dict, Any, List, Optional
from string import Template
from ...utils import get_logger

logger = get_logger(__name__)


class IntegrationTemplate:
    """Manages template-based configuration for integrations."""
    
    def __init__(self, template_content: str):
        self.template = Template(template_content)
        self.logger = get_logger(f"{__name__}.IntegrationTemplate")
    
    def render(self, **variables) -> str:
        """Render the template with the provided variables."""
        try:
            return self.template.safe_substitute(**variables)
        except Exception as e:
            self.logger.error("Failed to render template: %s", e)
            return ""


class DesktopEntryTemplate(IntegrationTemplate):
    """Template for Linux .desktop files."""
    
    DEFAULT_TEMPLATE = """[Desktop Entry]
Type=Action
Name=${name}
Comment=${description}
Icon=${icon_path}
Profiles=profile-zero;

[X-Action-Profile profile-zero]
Exec=${command}
MimeTypes=${mime_types}
Name=${name}
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)


class ServiceMenuTemplate(IntegrationTemplate):
    """Template for KDE service menu .desktop files."""
    
    DEFAULT_TEMPLATE = """[Desktop Entry]
Type=Service
ServiceTypes=KonqPopupMenu/Plugin
MimeType=${mime_types}
Actions=${actions}
Icon=${icon_path}
X-KDE-Submenu=TonieToolbox

${action_sections}
"""
    
    ACTION_SECTION_TEMPLATE = """[Desktop Action ${action_id}]
Name=${name}
Icon=${icon_path}
Exec=${command}
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)
        self.action_template = Template(self.ACTION_SECTION_TEMPLATE)
    
    def render_with_actions(self, actions: List[Dict[str, str]], **variables) -> str:
        """Render template with multiple actions."""
        action_ids = []
        action_sections = []
        
        for i, action in enumerate(actions):
            action_id = f"action{i}"
            action_ids.append(action_id)
            
            action_section = self.action_template.safe_substitute(
                action_id=action_id,
                **action
            )
            action_sections.append(action_section)
        
        variables['actions'] = ';'.join(action_ids)
        variables['action_sections'] = '\n'.join(action_sections)
        
        return self.render(**variables)


class ThunarActionTemplate(IntegrationTemplate):
    """Template for XFCE Thunar custom actions."""
    
    ACTION_TEMPLATE = """    <action>
        <icon>${icon_path}</icon>
        <name>${name}</name>
        <unique-id>${unique_id}</unique-id>
        <command>${command}</command>
        <description>${description}</description>
        <patterns>${patterns}</patterns>
        <startup-notify/>
        <directories/>
    </action>"""
    
    def __init__(self):
        super().__init__(self.ACTION_TEMPLATE)


class RegistryTemplate(IntegrationTemplate):
    """Template for Windows registry entries."""
    
    DEFAULT_TEMPLATE = """Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\${file_extension}\\shell\\TonieToolbox]
@="${menu_text}"

[HKEY_CLASSES_ROOT\\${file_extension}\\shell\\TonieToolbox\\command]
@="${command}"
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)


class MacOSActionTemplate(IntegrationTemplate):
    """Template for macOS Automator actions."""
    
    DEFAULT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMAccepts</key>
    <dict>
        <key>Container</key>
        <string>List</string>
        <key>Optional</key>
        <true/>
        <key>Types</key>
        <array>
            ${accepted_types}
        </array>
    </dict>
    <key>AMActionVersion</key>
    <string>1.0</string>
    <key>AMApplication</key>
    <dict>
        <key>CFBundleIdentifier</key>
        <string>com.apple.Automator</string>
    </dict>
    <key>AMParameterProperties</key>
    <dict/>
    <key>AMProvides</key>
    <dict>
        <key>Container</key>
        <string>List</string>
        <key>Types</key>
        <array>
            <string>com.apple.cocoa.string</string>
        </array>
    </dict>
    <key>ActionBundlePath</key>
    <string>/System/Library/Automator/Run Shell Script.action</string>
    <key>ActionName</key>
    <string>${name}</string>
    <key>ActionParameters</key>
    <dict>
        <key>COMMAND_STRING</key>
        <string>${command}</string>
        <key>CheckedForUserDefaultShell</key>
        <true/>
        <key>inputMethod</key>
        <integer>1</integer>
        <key>shell</key>
        <string>/bin/bash</string>
        <key>source</key>
        <string></string>
    </dict>
</dict>
</plist>
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)


class NautilusScriptTemplate(IntegrationTemplate):
    """Template for Nautilus/GNOME scripts."""
    
    DEFAULT_TEMPLATE = """#!/bin/bash
# TonieToolbox: ${description}

if [ -z "$NAUTILUS_SCRIPT_SELECTED_FILE_PATHS" ]; then
    echo "No files selected"
    exit 1
fi

# Execute TonieToolbox command
${command} $NAUTILUS_SCRIPT_SELECTED_FILE_PATHS
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)
    
    def render_script(self, command: str, description: str) -> str:
        """Render a script with command and description."""
        return self.render(command=command, description=description)


class NemoActionTemplate(IntegrationTemplate):
    """Template for Nemo action files."""
    
    DEFAULT_TEMPLATE = """[Nemo Action]
Name=${name}
Comment=${comment}
Exec=${command}
Icon-Name=${icon_path}
Selection=any
Extensions=${extensions}
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)
    
    def render_action(self, name: str, comment: str, command: str, 
                     icon_path: str, mime_types: List[str] = None,
                     extensions: List[str] = None, selection_type: List[str] = None) -> str:
        """Render a Nemo action file."""
        if extensions:
            ext_str = ';'.join(extensions)
        elif mime_types:
            # Convert MIME types to extensions (simplified)
            ext_str = 'any'
        else:
            ext_str = 'any'
        
        return self.render(
            name=name,
            comment=comment,
            command=command,
            icon_path=icon_path,
            extensions=ext_str
        )


class XFCECustomActionsTemplate:
    """Template for XFCE Thunar custom actions (uca.xml)."""
    
    UCA_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<actions>"""
    
    UCA_FOOTER = """</actions>"""
    
    ACTION_TEMPLATE = """    <action>
        <icon>${icon}</icon>
        <name>${name}</name>
        <unique-id>tonietoolbox-${action_id}</unique-id>
        <command>${command}</command>
        <description>${description}</description>
        <patterns>${patterns}</patterns>
        <startup-notify/>
        ${directories}
    </action>"""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.XFCECustomActionsTemplate")
        self.action_template = Template(self.ACTION_TEMPLATE)
    
    def merge_actions(self, existing_content: str, new_actions: List[Dict[str, Any]]) -> str:
        """Merge new actions into existing uca.xml content."""
        # Remove existing TonieToolbox actions
        cleaned_content = self.remove_actions(existing_content)
        
        # Generate new actions
        action_xml = []
        for i, action in enumerate(new_actions):
            directories = "<directories/>" if action.get('directories') else ""
            patterns = action.get('patterns', '*')
            
            action_content = self.action_template.safe_substitute(
                icon=action.get('icon', ''),
                name=action.get('name', ''),
                action_id=f"{i}",
                command=action.get('command', ''),
                description=action.get('description', ''),
                patterns=patterns,
                directories=directories
            )
            action_xml.append(action_content)
        
        # Merge with existing content
        if not cleaned_content.strip() or cleaned_content.strip() == self.UCA_HEADER.strip() + self.UCA_FOOTER.strip():
            # No existing content or empty
            return self.UCA_HEADER + '\n' + '\n'.join(action_xml) + '\n' + self.UCA_FOOTER
        
        # Insert before closing tag
        if cleaned_content.endswith('</actions>'):
            base_content = cleaned_content[:-10]  # Remove </actions>
            return base_content + '\n'.join(action_xml) + '\n</actions>'
        
        return cleaned_content + '\n' + '\n'.join(action_xml)
    
    def remove_actions(self, content: str) -> str:
        """Remove all TonieToolbox actions from uca.xml content."""
        import re
        # Remove actions with tonietoolbox unique-id
        pattern = r'<action>.*?<unique-id>tonietoolbox-.*?</unique-id>.*?</action>'
        return re.sub(pattern, '', content, flags=re.DOTALL)


class WindowsRegistryTemplate(IntegrationTemplate):
    """Template for Windows registry context menu entries."""
    
    DEFAULT_TEMPLATE = """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\${root_path}\\${key_name}]
@="${display_name}"
"Icon"="${icon_path}"

[HKEY_CURRENT_USER\\${root_path}\\${key_name}\\command]
@="${command}"
"""
    
    def __init__(self, custom_template: Optional[str] = None):
        super().__init__(custom_template or self.DEFAULT_TEMPLATE)
    
    def render_context_menu_entry(self, root_path: str, key_name: str, 
                                 display_name: str, command: str, icon_path: str) -> str:
        """Render a Windows context menu registry entry."""
        return self.render(
            root_path=root_path,
            key_name=key_name,
            display_name=display_name,
            command=command,
            icon_path=icon_path.replace('\\', '\\\\')  # Escape backslashes
        )


class MacOSAutomatorTemplate:
    """Template for macOS Automator service workflows."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.MacOSAutomatorTemplate")
    
    def render_service_workflow(self, service_name: str, command: str,
                              input_types: List[str], icon_path: str = '') -> Dict[str, Any]:
        """Render a complete macOS Automator service workflow."""
        import uuid
        
        # Generate Info.plist
        info_plist = {
            'CFBundleDisplayName': service_name,
            'CFBundleIdentifier': f'com.tonietoolbox.{service_name.lower().replace(" ", "")}',
            'CFBundleName': service_name,
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1.0',
            'LSMinimumSystemVersion': '10.6',
            'NSServices': [{
                'NSMenuItem': {
                    'default': service_name
                },
                'NSMessage': 'runWorkflowAsService',
                'NSSendTypes': input_types
            }]
        }
        
        # Generate document.wflow
        action_uuid = str(uuid.uuid4()).upper()
        document = {
            'connectors': {},
            'workflowMetaData': {
                'workflowTypeIdentifier': 'com.apple.Automator.servicesMenu'
            },
            'actions': [{
                'ActionBundlePath': '/System/Library/Automator/Run Shell Script.action',
                'ActionParameters': {
                    'COMMAND_STRING': f'exec {command} "$@"',
                    'CheckedForUserDefaultShell': True,
                    'inputMethod': 1,
                    'shell': '/bin/bash',
                    'source': ''
                },
                'BundleIdentifier': 'com.apple.RunShellScript',
                'CFBundleVersion': '2.0.3',
                'CanShowSelectedItemsWhenRun': False,
                'CanShowWhenRun': True,
                'Category': 'AMCategoryUtilities',
                'Class Name': 'RunShellScriptAction',
                'InputUUID': action_uuid,
                'Keywords': ['Shell', 'Script', 'Command', 'Run', 'Unix'],
                'OutputUUID': action_uuid,
                'UUID': action_uuid,
                'UnlocalizedApplications': ['Automator'],
                'arguments': {
                    'COMMAND_STRING': f'exec {command} "$@"',
                    'CheckedForUserDefaultShell': True,
                    'inputMethod': 1,
                    'shell': '/bin/bash',
                    'source': ''
                }
            }]
        }
        
        return {
            'info_plist': info_plist,
            'document': document
        }


class TemplateManager:
    """Manages templates for different platforms and file formats."""
    
    def __init__(self):
        self.templates = {}
        self.logger = get_logger(f"{__name__}.TemplateManager")
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register default templates for all platforms."""
        self.templates.update({
            # Linux desktop environments
            'desktop_entry': DesktopEntryTemplate(),
            'kde_service_menu': ServiceMenuTemplate(),
            'xfce_custom_actions': XFCECustomActionsTemplate(),
            'nautilus_script': NautilusScriptTemplate(),
            'caja_script': NautilusScriptTemplate(),  # Caja uses same format as Nautilus
            'nemo_script': NautilusScriptTemplate(),  # Nemo scripts use same format
            'nemo_action': NemoActionTemplate(),
            'pcmanfm_action': DesktopEntryTemplate(),  # PCManFM uses desktop entry format
            
            # Windows
            'windows_registry': WindowsRegistryTemplate(),
            
            # macOS
            'macos_automator': MacOSAutomatorTemplate(),
            
            # Alternative template names (aliases for convenience)
            'linux_desktop_entry': DesktopEntryTemplate(),
            'thunar_action': ThunarActionTemplate(),
            'macos_action': MacOSActionTemplate()
        })
    
    def get_template(self, template_name: str) -> Optional[IntegrationTemplate]:
        """Get a template by name."""
        template = self.templates.get(template_name)
        if not template:
            self.logger.warning("Template not found: %s", template_name)
        return template
    
    def register_template(self, name: str, template: IntegrationTemplate):
        """Register a custom template."""
        self.templates[name] = template
        self.logger.debug("Registered template: %s", name)
    
    def render_template(self, template_name: str, **variables) -> Optional[str]:
        """Render a template with variables."""
        template = self.get_template(template_name)
        if template:
            return template.render(**variables)
        return None


# Global template manager instance
template_manager = TemplateManager()


def get_template_manager() -> TemplateManager:
    """Get the global template manager instance."""
    return template_manager