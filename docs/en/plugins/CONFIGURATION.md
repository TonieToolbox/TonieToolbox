# Plugin System Configuration

TonieToolbox provides comprehensive configuration options for controlling the plugin system behavior.

## Configuration Settings

All plugin settings are located in the `plugins` section of the configuration. You can access them programmatically via:

```python
from TonieToolbox.core.config import get_config_manager

config = get_config_manager()
config.plugins.enable_plugins = False  # Disable entire plugin system
```

### Available Settings

#### `plugins.enable_plugins` (bool, default: `True`)
**Global toggle to enable/disable the entire plugin system.**

- When `False`: Plugin system is completely disabled, no plugins loaded
- When `True`: Plugin system is active and can load plugins

Example:
```python
config.plugins.enable_plugins = False  # Completely disable plugins
```

#### `plugins.auto_discover` (bool, default: `True`)
**Automatically discover plugins on application startup.**

- When `False`: Plugins must be loaded manually
- When `True`: Plugin directories are scanned automatically

Example:
```python
config.plugins.auto_discover = False  # Disable auto-discovery
```

#### `plugins.auto_enable` (bool, default: `True`)
**Automatically enable discovered plugins.**

- When `False`: Discovered plugins remain disabled until manually enabled
- When `True`: Plugins are enabled immediately after discovery

Example:
```python
config.plugins.auto_enable = False  # Load but don't enable plugins
```

#### `plugins.plugin_directories` (list, default: `[]`)
**Additional directories to scan for plugins.**

Extends the default plugin search paths with custom directories.

Example:
```python
config.plugins.plugin_directories = [
    "/path/to/my/plugins",
    "~/.tonietoolbox/custom_plugins"
]
```

#### `plugins.disabled_plugins` (list, default: `[]`)
**List of plugin IDs to keep disabled.**

Even if auto-enable is `True`, these plugins will remain disabled.

Example:
```python
config.plugins.disabled_plugins = [
    "com.example.problematic_plugin",
    "com.test.debug_plugin"
]
```

#### `plugins.load_builtin_plugins` (bool, default: `True`)
**Load built-in plugins from TonieToolbox/core/plugins/builtin.**

- When `False`: Only external plugins are loaded
- When `True`: Built-in example and utility plugins are loaded

Example:
```python
config.plugins.load_builtin_plugins = False  # Skip built-in plugins
```

## Configuration File Example

Add these settings to your `~/.tonietoolbox/config.json`:

```json
{
  "metadata": {
    "description": "TonieToolbox centralized configuration",
    "config_version": "2.0"
  },
  "plugins": {
    "enable_plugins": true,
    "auto_discover": true,
    "auto_enable": true,
    "plugin_directories": [
      "/home/user/my_tonietoolbox_plugins"
    ],
    "disabled_plugins": [
      "com.example.unwanted_plugin"
    ],
    "load_builtin_plugins": true
  }
}
```

**Note**: Only non-default values need to be included in the config file. The settings shown above are all default values except for `plugin_directories`.

## Use Cases

### Completely Disable Plugins
```python
config.plugins.enable_plugins = False
```

This is useful for:
- Debugging application issues
- Reducing startup time
- Running in minimal/headless mode

### Manual Plugin Management
```python
config.plugins.auto_discover = False
config.plugins.auto_enable = False
```

This allows you to:
- Control exactly which plugins load
- Load plugins programmatically
- Test plugins individually

### External Plugins Only
```python
config.plugins.load_builtin_plugins = False
config.plugins.plugin_directories = ["/path/to/external/plugins"]
```

This is useful when:
- You only want your custom plugins
- Reducing memory footprint
- Production deployments with specific plugin requirements

### Blacklist Specific Plugins
```python
config.plugins.disabled_plugins = [
    "com.tonietoolbox.example_gui_plugin",
    "com.external.problematic_plugin"
]
```

This allows you to:
- Disable problematic plugins without uninstalling
- Temporarily disable plugins for testing
- Maintain control over which plugins can run

## Programmatic Access

```python
from TonieToolbox.core.config import get_config_manager

config = get_config_manager()

# Check if plugins are enabled
if config.plugins.enable_plugins:
    print("Plugins are enabled")

# Get list of disabled plugins
disabled = config.plugins.disabled_plugins
print(f"Disabled plugins: {disabled}")

# Add a plugin to disabled list
disabled.append("com.example.new_plugin")
config.plugins.disabled_plugins = disabled
config.save_config()
```

## Command-Line Configuration

While there are no command-line flags for plugin configuration yet, you can modify settings before running:

```bash
# Edit config file
vim ~/.tonietoolbox/config.json

# Or use Python
python3 -c "
from TonieToolbox.core.config import get_config_manager
config = get_config_manager()
config.plugins.enable_plugins = False
config.save_config()
"

# Then run TonieToolbox
tonietoolbox --gui
```

## See Also

- [Plugin Development Guide](README.md)
- [Configuration Reference](../reference/configuration.md)
