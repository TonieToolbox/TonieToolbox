#!/usr/bin/env python3
"""
Plugin scaffolding generator for creating new TonieToolbox plugins.

Generates complete plugin structure with templates for all plugin types.
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from ..utils import get_logger
from .base import PluginType

logger = get_logger(__name__)


# Template files
PLUGIN_PY_TEMPLATE = '''"""
{name} - {description}

Author: {author}
"""
from pathlib import Path
from TonieToolbox.core.plugins import BasePlugin, PluginManifest, PluginContext, load_manifest_from_json
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class {class_name}(BasePlugin):
    """{description}"""
    
    def get_manifest(self) -> PluginManifest:
        """Return plugin manifest from manifest.json."""
        return load_manifest_from_json(Path(__file__).parent / "manifest.json")
    
    def initialize(self, context: PluginContext) -> bool:
        """
        Initialize the plugin with application context.
        
        Args:
            context: Plugin execution context
            
        Returns:
            True if initialization successful
        """
        self._context = context
        logger.info(f"{{self.get_manifest().metadata.name}} initialized")
        
        # TODO: Add your initialization logic here
        # - Subscribe to events: context.event_bus.subscribe(EventType, handler)
        # - Access config: context.config_manager
        # - Register components (GUI plugins)
        
        return True
    
    def enable(self) -> bool:
        """Enable the plugin."""
        logger.info(f"{{self.get_manifest().metadata.name}} enabled")
        # TODO: Start plugin activities
        return super().enable()
    
    def disable(self) -> bool:
        """Disable the plugin."""
        logger.info(f"{{self.get_manifest().metadata.name}} disabled")
        # TODO: Stop plugin activities
        return super().disable()
    
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        logger.info(f"{{self.get_manifest().metadata.name}} cleaned up")
        # TODO: Release resources, unsubscribe events
        super().cleanup()
'''

GUI_PLUGIN_TEMPLATE = '''"""
{name} - {description}

Author: {author}
"""
from pathlib import Path
from TonieToolbox.core.plugins import GUIPlugin, PluginManifest, PluginContext, load_manifest_from_json
from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class {class_name}(GUIPlugin):
    """{description}"""
    
    def get_manifest(self) -> PluginManifest:
        """Return plugin manifest from manifest.json."""
        return load_manifest_from_json(Path(__file__).parent / "manifest.json")
    
    def initialize(self, context: PluginContext) -> bool:
        """
        Initialize the plugin with application context.
        
        Args:
            context: Plugin execution context
            
        Returns:
            True if initialization successful
        """
        self._context = context
        logger.info(f"{{self.get_manifest().metadata.name}} initialized")
        
        return True
    
    def register_components(self, gui_registry) -> None:
        """
        Register GUI components with the application.
        
        Args:
            gui_registry: GUI component registry
        """
        # Example: Add menu item
        # gui_registry.register(
        #     "menu_items",
        #     "my_action",
        #     {{
        #         "menu": "Tools",
        #         "label": "My Tool",
        #         "callback": self.show_dialog,
        #         "shortcut": "Ctrl+Shift+M"
        #     }}
        # )
        
        # Example: Add toolbar button
        # gui_registry.register(
        #     "toolbar_buttons",
        #     "my_button",
        #     {{
        #         "icon": "path/to/icon.png",
        #         "tooltip": "My Tool",
        #         "callback": self.show_dialog
        #     }}
        # )
        
        logger.info(f"{{self.get_manifest().metadata.name}} components registered")
    
    def enable(self) -> bool:
        """Enable the plugin."""
        logger.info(f"{{self.get_manifest().metadata.name}} enabled")
        return super().enable()
    
    def disable(self) -> bool:
        """Disable the plugin."""
        logger.info(f"{{self.get_manifest().metadata.name}} disabled")
        return super().disable()
    
    def cleanup(self) -> None:
        """Clean up plugin resources."""
        logger.info(f"{{self.get_manifest().metadata.name}} cleaned up")
        super().cleanup()
'''

MANIFEST_TEMPLATE = {
    "id": "{plugin_id}",
    "name": "{name}",
    "version": "0.1.0",
    "author": "{author}",
    "description": "{description}",
    "plugin_type": "{plugin_type}",
    "entry_point": "plugin:{class_name}",
    "homepage": "{homepage}",
    "repository": "{repository}",
    "license": "GPL-3.0-or-later",
    "min_tonietoolbox_version": "1.0.0",
    "dependencies": {
        "plugins": []
    },
    "config_schema": {},
    "permissions": []
}

README_TEMPLATE = '''# {name}

{description}

## Installation

```bash
# From TonieToolbox plugin manager (GUI)
# Or via CLI:
tonietoolbox plugin install {plugin_id}
```

## Usage

{usage_instructions}

## Configuration

{config_instructions}

## Development

```bash
# Test the plugin
tonietoolbox plugin test .

# Install locally for testing
tonietoolbox plugin install . --local
```

## License

{license}

## Author

{author}
'''

GITIGNORE_TEMPLATE = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg
*.egg-info/
dist/
build/

# Virtual environments
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
'''


class PluginScaffolder:
    """Generate plugin scaffolding from templates."""
    
    def create_plugin(
        self,
        output_dir: Path,
        plugin_id: str,
        name: str,
        author: str,
        description: str,
        plugin_type: PluginType,
        homepage: str = "",
        repository: str = "",
        license: str = "MIT"
    ) -> Path:
        """
        Create a new plugin from templates.
        
        Args:
            output_dir: Directory to create plugin in
            plugin_id: Plugin ID (e.g., com.author.plugin)
            name: Plugin display name
            author: Plugin author
            description: Plugin description
            plugin_type: Type of plugin
            homepage: Plugin homepage URL
            repository: Plugin repository URL
            license: Plugin license
            
        Returns:
            Path to created plugin directory
        """
        # Create plugin directory
        plugin_dir = output_dir / plugin_id.split('.')[-1]
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating plugin in {plugin_dir}")
        
        # Generate class name from plugin name
        class_name = ''.join(word.capitalize() for word in name.split())
        class_name = class_name.replace(' ', '').replace('-', '').replace('_', '')
        
        # Create plugin.py
        template = GUI_PLUGIN_TEMPLATE if plugin_type == PluginType.GUI else PLUGIN_PY_TEMPLATE
        plugin_py = template.format(
            name=name,
            description=description,
            author=author,
            class_name=class_name
        )
        (plugin_dir / "plugin.py").write_text(plugin_py, encoding='utf-8')
        logger.debug(f"Created plugin.py with class {class_name}")
        
        # Create manifest.json
        manifest = json.loads(json.dumps(MANIFEST_TEMPLATE))
        manifest_content = json.dumps(manifest, indent=2).format(
            plugin_id=plugin_id,
            name=name,
            author=author,
            description=description,
            plugin_type=plugin_type.value,
            class_name=class_name,
            homepage=homepage,
            repository=repository
        )
        (plugin_dir / "manifest.json").write_text(manifest_content, encoding='utf-8')
        logger.debug("Created manifest.json")
        
        # Create README.md
        usage = self._get_usage_instructions(plugin_type)
        config = self._get_config_instructions(plugin_type)
        readme = README_TEMPLATE.format(
            name=name,
            description=description,
            plugin_id=plugin_id,
            usage_instructions=usage,
            config_instructions=config,
            license=license,
            author=author
        )
        (plugin_dir / "README.md").write_text(readme, encoding='utf-8')
        logger.debug("Created README.md")
        
        # Create .gitignore
        (plugin_dir / ".gitignore").write_text(GITIGNORE_TEMPLATE, encoding='utf-8')
        logger.debug("Created .gitignore")
        
        # Create __init__.py
        init_content = f'''"""
{name} plugin for TonieToolbox.

{description}
"""
from .plugin import {class_name}

__all__ = ['{class_name}']
'''
        (plugin_dir / "__init__.py").write_text(init_content, encoding='utf-8')
        logger.debug("Created __init__.py")
        
        # Create components directory for GUI plugins
        if plugin_type == PluginType.GUI:
            components_dir = plugin_dir / "components"
            components_dir.mkdir(exist_ok=True)
            (components_dir / "__init__.py").write_text('"""GUI components."""\n', encoding='utf-8')
            logger.debug("Created components directory")
        
        logger.info(f"✅ Plugin created successfully at {plugin_dir}")
        logger.info(f"   Plugin ID: {plugin_id}")
        logger.info(f"   Class: {class_name}")
        logger.info(f"   Type: {plugin_type.value}")
        logger.info("")
        logger.info("Next steps:")
        logger.info(f"   1. cd {plugin_dir}")
        logger.info("   2. Edit plugin.py and implement your plugin logic")
        logger.info("   3. Update manifest.json with dependencies and config schema")
        logger.info("   4. Test: tonietoolbox plugin test .")
        logger.info("   5. Install locally: tonietoolbox plugin install . --local")
        
        return plugin_dir
    
    def _get_usage_instructions(self, plugin_type: PluginType) -> str:
        """Get usage instructions based on plugin type."""
        if plugin_type == PluginType.GUI:
            return """Once installed, the plugin will add a new menu item or toolbar button to the TonieToolbox GUI.

Look for it under the Tools menu or in the toolbar."""
        elif plugin_type == PluginType.PROCESSOR:
            return """This processor plugin extends TonieToolbox's audio processing capabilities.

It will be automatically used when processing audio files that match its criteria."""
        elif plugin_type == PluginType.INTEGRATION:
            return """This integration plugin provides connectivity to external services.

Configure the connection details in the plugin settings."""
        else:
            return """This plugin extends TonieToolbox functionality.

Refer to the plugin documentation for specific usage instructions."""
    
    def _get_config_instructions(self, plugin_type: PluginType) -> str:
        """Get configuration instructions based on plugin type."""
        return """Configuration options can be defined in `manifest.json` under `config_schema`.

Example:
```json
"config_schema": {
  "setting_name": {
    "type": "string",
    "default": "default_value",
    "description": "Setting description"
  }
}
```

Access config in your plugin:
```python
value = self._context.config_manager.plugins.get_plugin_config(
    self.get_manifest().metadata.id,
    "setting_name"
)
```"""


def create_plugin_cli(
    output_dir: str,
    plugin_id: str,
    name: str,
    author: str,
    description: str,
    plugin_type: str,
    homepage: str = "",
    repository: str = "",
    license: str = "MIT"
) -> int:
    """
    CLI entry point for creating a new plugin.
    
    Args:
        output_dir: Directory to create plugin in
        plugin_id: Plugin ID (e.g., com.author.plugin)
        name: Plugin display name
        author: Plugin author
        description: Plugin description
        plugin_type: Type of plugin (gui, processor, integration, etc.)
        homepage: Plugin homepage URL
        repository: Plugin repository URL
        license: Plugin license
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse plugin type
        try:
            ptype = PluginType(plugin_type)
        except ValueError:
            print(f"❌ Invalid plugin type: {plugin_type}")
            print(f"   Valid types: {', '.join(t.value for t in PluginType)}")
            return 1
        
        # Create scaffolder
        scaffolder = PluginScaffolder()
        
        # Create plugin
        plugin_dir = scaffolder.create_plugin(
            output_dir=Path(output_dir).resolve(),
            plugin_id=plugin_id,
            name=name,
            author=author,
            description=description,
            plugin_type=ptype,
            homepage=homepage,
            repository=repository,
            license=license
        )
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to create plugin: {e}")
        print(f"❌ Error: {e}")
        return 1
