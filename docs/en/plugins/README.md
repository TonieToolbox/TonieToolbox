# TonieToolbox Plugin System Documentation

## Overview

The TonieToolbox plugin system provides a powerful, flexible way to extend the application's functionality without modifying core code. Plugins can add GUI components, custom processors, integrations with external services, and standalone tools.

## Quick Start

### Creating Your First Plugin

1. **Create plugin directory**:
```bash
mkdir ~/.tonietoolbox/plugins/my_first_plugin
cd ~/.tonietoolbox/plugins/my_first_plugin
```

2. **Create `plugin.py`**:
```python
from TonieToolbox.core.plugins import BasePlugin, PluginManifest, PluginMetadata, PluginType

class MyFirstPlugin(BasePlugin):
    """My first TonieToolbox plugin."""
    
    def get_manifest(self) -> PluginManifest:
        return PluginManifest(
            metadata=PluginMetadata(
                id="com.example.myfirstplugin",
                name="My First Plugin",
                version="1.0.0",
                author="Your Name",
                description="A simple example plugin",
                plugin_type=PluginType.TOOL
            )
        )
    
    def initialize(self, context) -> bool:
        self._context = context
        context.logger.info("My First Plugin initialized!")
        return True
```

3. **Test your plugin**: Launch TonieToolbox GUI to see your plugin loaded in the Plugin Manager (GUI → Tools → Plugin Manager).

## Plugin Types

### 1. GUI Plugins
Add custom UI components, menus, dialogs, and panels.

**Use cases**:
- Custom file viewers
- Batch processing dialogs
- Settings panels
- Visualization tools

**Example**:
```python
from TonieToolbox.core.plugins import GUIPlugin

class BatchConverterPlugin(GUIPlugin):
    def register_components(self, gui_registry):
        gui_registry.register(
            "menu_items",
            "batch_converter",
            {
                "menu": "Tools",
                "label": "Batch Converter...",
                "callback": self.show_batch_converter
            }
        )
    
    def show_batch_converter(self):
        # Show your custom dialog
        pass
```

### 2. Processor Plugins
Add custom file processors and converters.

**Use cases**:
- Custom audio format support
- Advanced audio processing
- Metadata extraction
- File validation

**Example**:
```python
from TonieToolbox.core.plugins import ProcessorPlugin

class CustomFormatPlugin(ProcessorPlugin):
    def register_processors(self, processor_registry):
        processor_registry.register(
            "custom_format",
            CustomFormatProcessor
        )
```

### 3. Integration Plugins
Integrate with external services and APIs.

**Use cases**:
- Cloud storage integration
- External API connections
- Database integration
- Third-party service integration

**Example**:
```python
from TonieToolbox.core.plugins import IntegrationPlugin

class CloudStoragePlugin(IntegrationPlugin):
    def register_integration(self, integration_registry):
        integration_registry.register(
            "cloud_storage",
            CloudStorageIntegration
        )
```

### 4. Tool Plugins
Add standalone utilities and tools.

**Use cases**:
- Analysis tools
- Diagnostic utilities
- Data export/import
- Automation scripts

## Plugin Architecture

### Plugin Lifecycle

1. **Discovery**: Plugin manager scans plugin directories
2. **Loading**: Plugin module is imported and instantiated
3. **Registration**: Plugin is registered in the plugin registry
4. **Initialization**: Plugin receives context and registers components
5. **Enable**: Plugin becomes active and functional
6. **Disable**: Plugin stops activities but remains loaded
7. **Unload**: Plugin is removed and resources cleaned up

### Plugin Context

Every plugin receives a `PluginContext` during initialization:

```python
class PluginContext:
    app_version: str          # TonieToolbox version
    config_manager            # Access to configuration
    event_bus                 # Publish/subscribe events
    logger                    # Logging instance
    plugin_dir: Path          # Plugin's directory
```

### Component Registry

Plugins register components through the component registry:

```python
# GUI components
gui_registry.register("menu_items", "my_item", {...})
gui_registry.register("toolbar_buttons", "my_button", {...})
gui_registry.register("dialogs", "my_dialog", MyDialog)

# Processors
processor_registry.register("my_format", MyProcessor)

# Integrations
integration_registry.register("my_service", MyIntegration)
```

## Advanced Topics

### Event Communication

Plugins can publish and subscribe to events:

```python
def initialize(self, context):
    # Subscribe to events
    context.event_bus.subscribe(FileProcessedEvent, self._on_file_processed)
    
    # Publish events
    context.event_bus.publish(MyCustomEvent(data="value"))
    return True

def _on_file_processed(self, event):
    self._context.logger.info(f"File processed: {event.file_path}")
```

### Configuration Management

Plugins can store and retrieve configuration:

```python
def initialize(self, context):
    # Get plugin config
    config = context.config_manager.get_plugin_config(self.get_manifest().metadata.id)
    
    # Save plugin config
    context.config_manager.set_plugin_config(
        self.get_manifest().metadata.id,
        {"setting1": "value1"}
    )
    return True
```

### Resource Management

Register resources for automatic cleanup:

```python
def initialize(self, context):
    # Create a resource
    my_resource = MyResource()
    
    # Register for cleanup
    context.register_resource("my_resource", my_resource)
    return True

# Resource will be automatically cleaned up on plugin unload
```

### Dependencies

Declare plugin dependencies in manifest:

```python
PluginMetadata(
    id="com.example.advancedplugin",
    dependencies=[
        "requests>=2.28.0",
        "Pillow>=9.0.0"
    ],
    min_tonietoolbox_version="1.0.0",
    max_tonietoolbox_version="2.0.0"
)
```

## GUI Plugin Development

### Adding Menu Items

```python
gui_registry.register(
    "menu_items",
    "my_tool",
    {
        "menu": "Tools",          # Parent menu
        "label": "My Tool...",    # Menu item text
        "callback": self.show_tool,  # Function to call
        "shortcut": "Ctrl+T",     # Keyboard shortcut (optional)
        "icon": "path/to/icon.png"  # Icon (optional)
    }
)
```

### Creating Custom Dialogs

```python
from TonieToolbox.core.gui.components.base import QtBaseDialog

class MyDialog(QtBaseDialog):
    def _create_layout(self):
        # Create layout
        pass
    
    def _setup_ui(self):
        # Create UI elements
        pass
    
    def _connect_signals(self):
        # Connect signals
        pass
```

### Accessing Main Window

```python
def initialize(self, context):
    # Subscribe to window ready event
    context.event_bus.subscribe(
        MainWindowReadyEvent,
        self._on_window_ready
    )
    return True

def _on_window_ready(self, event):
    # Access main window through event
    main_window = event.main_window
```

## Best Practices

### 1. Plugin Isolation
- Don't directly import TonieToolbox core modules
- Use provided context for all app interactions
- Keep plugin self-contained

### 2. Error Handling
```python
def initialize(self, context) -> bool:
    try:
        # Plugin initialization code
        return True
    except Exception as e:
        context.logger.error(f"Failed to initialize: {e}")
        return False
```

### 3. Resource Cleanup
```python
def cleanup(self):
    # Stop timers
    if self._timer:
        self._timer.stop()
    
    # Close connections
    if self._connection:
        self._connection.close()
    
    # Call parent cleanup
    super().cleanup()
```

### 4. Testing
```python
import pytest
from TonieToolbox.core.plugins import PluginContext

def test_plugin_initialization():
    plugin = MyPlugin()
    context = create_test_context()
    assert plugin.initialize(context) == True
```

### 5. Documentation
- README.md with usage instructions
- Docstrings for all public methods
- Example configurations
- Troubleshooting section

## Plugin Distribution

### Directory Structure
```
my_plugin/
├── plugin.py              # Main plugin class
├── __init__.py           # Plugin exports
├── manifest.json         # Metadata (optional)
├── requirements.txt      # Dependencies
├── README.md            # Documentation
├── LICENSE              # License file
├── tests/               # Unit tests
│   └── test_plugin.py
├── components/          # GUI components (if GUI plugin)
│   └── my_dialog.py
├── i18n/               # Translations (if applicable)
│   ├── en_US.json
│   └── de_DE.json
└── assets/             # Icons, images, etc.
    └── icon.png
```

### Publishing
1. **Test thoroughly**: Run all tests and manual testing
2. **Document**: Complete README with examples
3. **Package**: Create distributable archive
4. **Share**: GitHub, PyPI, or TonieToolbox plugin repository

## Troubleshooting

### Plugin Not Loading
- Check plugin directory location
- Verify `plugin.py` or `__init__.py` exists
- Check logs: `~/.tonietoolbox/logs/plugins.log`
- Validate manifest structure

### Plugin Crashes
- Check error logs
- Verify all dependencies installed
- Test plugin in isolation
- Check TonieToolbox version compatibility

### Component Not Registering
- Verify registry key is correct
- Check initialization return value
- Ensure plugin is enabled
- Check component registry directly

## Examples

See official plugin examples in the `TonieToolbox/core/plugins/builtin/` directory of the repository.

## API Reference

Full API documentation available at: [TonieToolbox API Reference](../reference/api.md)

## Support

- Issues: https://github.com/TonieToolbox/TonieToolbox/issues
- Discussions: https://github.com/TonieToolbox/TonieToolbox/discussions
- Documentation: https://tonietoolbox.readthedocs.io
