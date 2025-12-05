# Configuration Reference

Complete reference for TonieToolbox configuration system based on the settings registry.

## Configuration File Structure

TonieToolbox uses a centralized JSON configuration file with hierarchical settings organized into logical sections.

### Configuration Location

**Default path**:
- **All platforms**: `~/.tonietoolbox/config.json`

!!! note "Path Resolution"
    The `~` expands to the user's home directory:
    
    - Linux/macOS: `/home/username/.tonietoolbox/config.json`
    - Windows: `C:\Users\username\.tonietoolbox\config.json`

### Configuration Format

TonieToolbox v1.0+ uses JSON format (config version 2.0):

```json
{
  "metadata": {
    "description": "TonieToolbox centralized configuration",
    "config_version": "2.0"
  },
  "application": {
    "logging": {
      "level": "INFO",
      "log_to_file": false
    },
    "teddycloud": {
      "url": null,
      "ignore_ssl_verify": false,
      "username": null,
      "password": null,
      "certificate_path": null,
      "private_key_path": null
    },
    "version": {
      "check_for_updates": true,
      "notify_if_not_latest": true,
      "pre_releases": false,
      "auto_update": false
    }
  }
}
```

## Configuration Sections

### Metadata Section

Core configuration metadata (always present).

#### `metadata.description`
Human-readable configuration description.

**Type**: String  
**Default**: `"TonieToolbox centralized configuration"`

#### `metadata.config_version`
Configuration format version.

**Type**: String  
**Default**: `"2.0"`

### Application Logging

Logging behavior and output configuration.

#### `application.logging.level`
Logging verbosity level.

**Type**: String  
**Default**: `"INFO"`  
**Options**: `"TRACE"`, `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`

**Example:**
```json
{
  "application": {
    "logging": {
      "level": "DEBUG"
    }
  }
}
```

#### `application.logging.log_to_file`
Enable file logging.

**Type**: Boolean  
**Default**: `false`

#### `application.logging.log_file_path`
Custom log file directory path.

**Type**: String  
**Default**: `~/.tonietoolbox/`

#### `application.logging.max_log_size`
Maximum log file size before rotation.

**Type**: Integer (bytes)  
**Default**: `10485760` (10MB)

#### `application.logging.backup_count`
Number of backup log files to keep.

**Type**: Integer  
**Default**: `5`

#### `application.logging.console_format`
Console log message format.

**Type**: String  
**Default**: `"%(levelname)-8s %(name)s: %(message)s"`

#### `application.logging.file_format`
File log message format.

**Type**: String  
**Default**: `"%(asctime)s %(levelname)-8s %(name)s: %(message)s"`

### TeddyCloud Integration

TeddyCloud server connection settings.

#### `application.teddycloud.url`
TeddyCloud server URL.

**Type**: String  
**Default**: `null`

**Example:**
```json
{
  "application": {
    "teddycloud": {
      "url": "https://teddycloud.example.com"
    }
  }
}
```

#### `application.teddycloud.ignore_ssl_verify`
Ignore SSL certificate verification.

**Type**: Boolean  
**Default**: `false`

**Security Warning**: Only use with trusted servers.

#### `application.teddycloud.username`
Basic authentication username.

**Type**: String  
**Default**: `null`

#### `application.teddycloud.password`
Basic authentication password.

**Type**: String  
**Default**: `null`

#### `application.teddycloud.certificate_path`
Client certificate file path for cert-based auth.

**Type**: String  
**Default**: `null`

#### `application.teddycloud.private_key_path`
Client private key file path for cert-based auth.

**Type**: String  
**Default**: `null`

#### `application.teddycloud.connection_timeout`
Connection timeout in seconds.

**Type**: Integer  
**Default**: `10`

#### `application.teddycloud.read_timeout`
Read timeout in seconds.

**Type**: Integer  
**Default**: `300`

#### `application.teddycloud.chunk_size`
Upload chunk size in bytes.

**Type**: Integer  
**Default**: `1048576` (1MB)

#### `application.teddycloud.max_retries`
Maximum retry attempts for failed operations.

**Type**: Integer  
**Default**: `3`

#### `application.teddycloud.retry_delay`
Delay between retry attempts in seconds.

**Type**: Integer  
**Default**: `5`

### Version Management

Update checking and notification settings.

#### `application.version.check_for_updates`
Check for updates automatically on startup.

**Type**: Boolean  
**Default**: `true`

#### `application.version.notify_if_not_latest`
Show notification if newer version available.

**Type**: Boolean  
**Default**: `true`

#### `application.version.pre_releases`
Include pre-release versions (alpha, beta, rc).

**Type**: Boolean  
**Default**: `false`

#### `application.version.auto_update`
Enable automatic updates.

**Type**: Boolean  
**Default**: `false`

#### `application.version.cache_expiry`
Version cache expiry in seconds.

**Type**: Integer  
**Default**: `86400` (24 hours)

#### `application.version.timeout`
Version check timeout in seconds.

**Type**: Integer  
**Default**: `10`

#### `application.version.max_retries`
Max retries for version checks.

**Type**: Integer  
**Default**: `3`

#### `application.version.retry_delay`
Retry delay for version checks.

**Type**: Integer  
**Default**: `5`

#### `application.version.pypi_url`
PyPI JSON API endpoint for version checking.

**Type**: String  
**Default**: `"https://pypi.org/pypi/TonieToolbox/json"`

### Audio Processing

Audio encoding and conversion settings.

#### `processing.audio.default_bitrate`
Default audio bitrate in kbps.

**Type**: Integer  
**Default**: `128`

#### `processing.audio.default_sample_rate`
Default sample rate in Hz.

**Type**: Integer  
**Default**: `48000`

#### `processing.audio.default_channels`
Default number of audio channels.

**Type**: Integer  
**Default**: `2` (stereo)

#### `processing.audio.use_cbr`
Use constant bitrate encoding.

**Type**: Boolean  
**Default**: `false`

#### `processing.audio.opus_complexity`
Opus encoding complexity (0-10).

**Type**: Integer  
**Default**: `10`

#### `processing.audio.opus_application`
Opus application type.

**Type**: String  
**Default**: `"audio"`  
**Options**: `"audio"`, `"voip"`, `"lowdelay"`

#### `processing.audio.auto_mono_conversion`
Automatically convert mono to stereo.

**Type**: Boolean  
**Default**: `true`

#### `processing.audio.normalize_audio`
Normalize audio levels.

**Type**: Boolean  
**Default**: `false`

#### `processing.audio.remove_silence`
Remove silence from audio.

**Type**: Boolean  
**Default**: `false`

### File Handling

File processing and output management.

#### `processing.file_handling.default_output_dir`
Default output directory path.

**Type**: String  
**Default**: `"./output"`

#### `processing.file_handling.output_to_source`
Save output files in source directory.

**Type**: Boolean  
**Default**: `false`

#### `processing.file_handling.force_creation`
Overwrite existing files.

**Type**: Boolean  
**Default**: `false`

#### `processing.file_handling.use_media_tags`
Use media tags for file naming.

**Type**: Boolean  
**Default**: `false`

#### `processing.file_handling.name_template`
Filename template for media tag naming.

**Type**: String  
**Default**: `"{artist} - {title}"`

**Available variables**: `{artist}`, `{title}`, `{album}`, `{albumartist}`, `{track}`, `{year}`, `{genre}`

#### `processing.file_handling.append_tonie_tag`
8-character hex tag to append to filenames.

**Type**: String  
**Default**: `null`

#### `processing.file_handling.keep_temp_files`
Keep temporary files after processing.

**Type**: Boolean  
**Default**: `false`

#### `processing.file_handling.temp_dir`
Custom temporary directory.

**Type**: String  
**Default**: `null` (uses system temp)

#### `processing.file_handling.auto_cleanup`
Automatically cleanup temporary files.

**Type**: Boolean  
**Default**: `true`

#### `processing.file_handling.validate_outputs`
Validate output files after creation.

**Type**: Boolean  
**Default**: `true`

#### `processing.file_handling.check_existing_files`
Check for existing files before processing.

**Type**: Boolean  
**Default**: `true`

### Processing Modes

Advanced processing behavior.

#### `processing.processing_modes.recursive_depth_limit`
Maximum recursive directory depth.

**Type**: Integer  
**Default**: `10`

#### `processing.processing_modes.skip_empty_folders`
Skip empty folders during processing.

**Type**: Boolean  
**Default**: `true`

#### `processing.processing_modes.folder_size_limit`
Maximum folder size in bytes.

**Type**: Integer  
**Default**: `1073741824` (1GB)

#### `processing.processing_modes.parallel_processing`
Enable parallel file processing.

**Type**: Boolean  
**Default**: `false`

#### `processing.processing_modes.max_parallel_files`
Maximum number of parallel files.

**Type**: Integer  
**Default**: `4`

#### `processing.processing_modes.max_parallel_workers`
Maximum number of parallel workers for recursive folder processing.

**Type**: Integer  
**Default**: `4`  
**CLI Override**: `--workers N`

**Description**: Controls the number of folders processed simultaneously during recursive operations. Higher values provide better performance on multi-core systems but consume more memory.

**Performance Guidelines**:
- Start with value equal to CPU cores
- Each worker uses ~200-500MB RAM
- Monitor system resources when using high values

#### `processing.processing_modes.analysis_cache_enabled`
Enable file analysis caching.

**Type**: Boolean  
**Default**: `true`

#### `processing.processing_modes.detailed_analysis`
Enable detailed file analysis.

**Type**: Boolean  
**Default**: `false`

### GUI Settings

Graphical interface configuration.

#### `gui.enable_gui`
Enable GUI mode.

**Type**: Boolean  
**Default**: `true`

#### `gui.language`
GUI language code.

**Type**: String  
**Default**: `"en_US"`  
**Options**: `"en_US"`, `"de_DE"`, `"fr_FR"`, `"es_ES"`

#### `gui.auto_detect_language`
Auto-detect system language.

**Type**: Boolean  
**Default**: `true`

#### `gui.fallback_language`
Fallback language if translation unavailable.

**Type**: String  
**Default**: `"en_US"`

#### `gui.debug_mode`
Enable GUI debug mode.

**Type**: Boolean  
**Default**: `false`

#### `gui.show_debug_info`
Show debug information in GUI.

**Type**: Boolean  
**Default**: `false`

### GUI Theme

Theme and appearance settings.

#### `gui.theme.default_theme`
Default theme name.

**Type**: String  
**Default**: `"default"`

#### `gui.theme.custom_theme_dir`
Custom theme directory path.

**Type**: String  
**Default**: `null`

#### `gui.theme.default_font_family`
Default font family.

**Type**: String  
**Default**: `"Arial"`

#### `gui.theme.default_font_size`
Default font size in points.

**Type**: Integer  
**Default**: `10`

### GUI Window

Window size and position settings.

#### `gui.window.default_width`
Default window width in pixels.

**Type**: Integer  
**Default**: `1000`

#### `gui.window.default_height`
Default window height in pixels.

**Type**: Integer  
**Default**: `700`

#### `gui.window.min_width`
Minimum window width in pixels.

**Type**: Integer  
**Default**: `800`

#### `gui.window.min_height`
Minimum window height in pixels.

**Type**: Integer  
**Default**: `600`

#### `gui.window.remember_size`
Remember window size between sessions.

**Type**: Boolean  
**Default**: `true`

#### `gui.window.remember_position`
Remember window position between sessions.

**Type**: Boolean  
**Default**: `true`

#### `gui.window.start_maximized`
Start window maximized.

**Type**: Boolean  
**Default**: `false`

#### `gui.window.auto_adapt_size`
Automatically adapt window size.

**Type**: Boolean  
**Default**: `true`

#### `gui.window.maximize_on_large_screens`
Maximize window on large screens automatically.

**Type**: Boolean  
**Default**: `true`

### GUI Behavior

GUI interaction and playback behavior.

#### `gui.behavior.auto_play_on_open`
Automatically play files when opened.

**Type**: Boolean  
**Default**: `false`

#### `gui.behavior.remember_last_directory`
Remember last used directory.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.show_file_extensions`
Show file extensions in file lists.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.show_progress_bars`
Show progress bars during operations.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.show_tooltips`
Show tooltips on hover.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.confirm_destructive_actions`
Confirm destructive actions (delete, overwrite).

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.auto_loop`
Auto-loop audio playback.

**Type**: Boolean  
**Default**: `false`

#### `gui.behavior.volume_step`
Volume change step percentage.

**Type**: Integer  
**Default**: `10`

#### `gui.behavior.seek_step`
Seek step in seconds.

**Type**: Integer  
**Default**: `5`

#### `gui.behavior.auto_save_playlist`
Auto-save playlist on exit.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.auto_load_last_playlist`
Auto-load last playlist on startup.

**Type**: Boolean  
**Default**: `true`

#### `gui.behavior.last_playlist_path`
Path to last playlist file.

**Type**: String  
**Default**: `~/.tonietoolbox/last_playlist.lst`

#### `gui.behavior.playlist_file_cache_size`
Maximum playlist file cache size.

**Type**: Integer  
**Default**: `100`

### Plugin System

Plugin management configuration.

#### `plugins.enable_plugins`
Enable plugin system (global toggle).

**Type**: Boolean  
**Default**: `true`

#### `plugins.auto_discover`
Automatically discover plugins on startup.

**Type**: Boolean  
**Default**: `true`

#### `plugins.auto_enable`
Automatically enable discovered plugins.

**Type**: Boolean  
**Default**: `true`

#### `plugins.plugin_directories`
Additional plugin directories to scan.

**Type**: Array of strings  
**Default**: `["~/.tonietoolbox/plugins"]`

**Example:**
```json
{
  "plugins": {
    "plugin_directories": [
      "~/.tonietoolbox/plugins",
      "/opt/tonietoolbox-plugins"
    ]
  }
}
```

#### `plugins.disabled_plugins`
List of plugin IDs to keep disabled.

**Type**: Array of strings  
**Default**: `[]`

**Example:**
```json
{
  "plugins": {
    "disabled_plugins": [
      "com.example.myplugin",
      "com.other.unwanted"
    ]
  }
}
```

#### `plugins.load_builtin_plugins`
Load built-in plugins from TonieToolbox core.

**Type**: Boolean  
**Default**: `true`

#### `plugins.repository_urls`
Plugin repository URLs to search.

**Type**: Array of strings  
**Default**: `["https://raw.githubusercontent.com/TonieToolbox/tonietoolbox_plugins/main/"]`

#### `plugins.auto_update_check`
Check for plugin updates on startup.

**Type**: Boolean  
**Default**: `true`

#### `plugins.update_check_interval`
Interval between update checks in seconds.

**Type**: Integer  
**Default**: `86400` (24 hours)

#### `plugins.install_location`
Base directory for community plugin installations.

**Type**: String  
**Default**: `~/.tonietoolbox/plugins`

#### `plugins.allow_unverified`
Allow installation of unverified plugins.

**Type**: Boolean  
**Default**: `false`

#### `plugins.max_parallel_downloads`
Maximum number of parallel plugin downloads.

**Type**: Integer  
**Default**: `3`

#### `plugins.verify_checksums`
Verify SHA512 checksums when installing plugins.

**Type**: Boolean  
**Default**: `true`

### Dependencies

External dependency management.

#### `dependencies.parallel_downloads`
Enable parallel downloads.

**Type**: Boolean  
**Default**: `true`

#### `dependencies.max_concurrent_downloads`
Maximum concurrent downloads.

**Type**: Integer  
**Default**: `3`

#### `dependencies.python_package_auto_install`
Auto-install missing Python packages.

**Type**: Boolean  
**Default**: `true`

#### `dependencies.pip_timeout`
Pip timeout in seconds.

**Type**: Integer  
**Default**: `120`

### Dependencies Network

Network settings for dependency downloads.

#### `dependencies.network.connection_timeout`
Connection timeout in seconds.

**Type**: Integer  
**Default**: `30`

#### `dependencies.network.read_timeout`
Read timeout in seconds.

**Type**: Integer  
**Default**: `300`

#### `dependencies.network.max_retries`
Maximum network retries.

**Type**: Integer  
**Default**: `3`

#### `dependencies.network.retry_backoff`
Retry backoff multiplier.

**Type**: Float  
**Default**: `2.0`

#### `dependencies.network.user_agent`
HTTP User-Agent string.

**Type**: String  
**Default**: `"TonieToolbox/1.0"`

### Dependencies Cache

Dependency caching settings.

#### `dependencies.cache.cache_dir`
Cache directory path.

**Type**: String  
**Default**: `~/.tonietoolbox/cache`

#### `dependencies.cache.libs_dir`
Libraries directory path.

**Type**: String  
**Default**: `~/.tonietoolbox/libs`

#### `dependencies.cache.max_cache_size`
Maximum cache size in bytes.

**Type**: Integer  
**Default**: `1073741824` (1GB)

#### `dependencies.cache.cache_expiry_days`
Cache expiry in days.

**Type**: Integer  
**Default**: `30`

#### `dependencies.cache.auto_cleanup`
Auto-cleanup expired cache.

**Type**: Boolean  
**Default**: `true`

#### `dependencies.cache.enabled`
Enable dependency caching.

**Type**: Boolean  
**Default**: `true`

### Media Tags

Media metadata handling.

#### `media.tags.additional_tags`
Additional custom media tags to extract.

**Type**: Array of strings  
**Default**: `[]`

**Example:**
```json
{
  "media": {
    "tags": {
      "additional_tags": ["composer", "conductor", "publisher"]
    }
  }
}
```

## Plugin Configuration

Plugins have their own namespaced configuration under the `plugins.config.{plugin_id}` section.

### Plugin Config Structure

```json
{
  "plugins": {
    "config": {
      "com.tonietoolbox.tonies_loader": {
        "auto_update": true,
        "cache_ttl_hours": 24,
        "fallback_enabled": true
      },
      "com.tonietoolbox.tonies_viewer": {
        "image_quality": "high",
        "cache_images": true
      }
    }
  }
}
```

### Plugin Config Access

Plugins access their configuration through the PluginContext:

```python
# Get plugin-specific config value
cache_ttl = context.get_config("cache_ttl_hours", default=24)

# Set plugin-specific config value
context.set_config("auto_update", True)

# Get all plugin config
config = context.get_all_config()
```

**Key features**:
- **Auto-namespaced**: Plugin ID automatically prepended
- **Schema defaults**: Merged with plugin's config schema defaults
- **Auto-saved**: Changes persist to config.json
- **Type-safe**: Validates against plugin's config schema

### Example Plugin Config Schema

In plugin's `manifest.json`:

```json
{
  "config_schema": {
    "auto_update": {
      "type": "boolean",
      "default": true,
      "description": "Automatically update Tonies database"
    },
    "cache_ttl_hours": {
      "type": "integer",
      "default": 24,
      "description": "Cache time-to-live in hours"
    }
  }
}
```

## Configuration Examples

### Audiobook Processing Profile

```json
{
  "processing": {
    "audio": {
      "default_bitrate": 64,
      "use_cbr": true,
      "auto_mono_conversion": false
    },
    "file_handling": {
      "use_media_tags": true,
      "name_template": "{albumartist}/{album}/Chapter {track:02d}"
    }
  }
}
```

### Music Collection Profile

```json
{
  "processing": {
    "audio": {
      "default_bitrate": 192,
      "normalize_audio": true
    },
    "file_handling": {
      "use_media_tags": true,
      "name_template": "{albumartist}/{year} - {album}/{track:02d} - {title}",
      "output_to_source": false
    },
    "processing_modes": {
      "parallel_processing": true,
      "max_parallel_files": 4
    }
  }
}
```

### TeddyCloud Auto-Upload

```json
{
  "application": {
    "teddycloud": {
      "url": "https://teddycloud.local",
      "username": "admin",
      "password": "secret",
      "ignore_ssl_verify": false
    }
  }
}
```

### Debug Mode

```json
{
  "application": {
    "logging": {
      "level": "DEBUG",
      "log_to_file": true
    }
  },
  "gui": {
    "debug_mode": true,
    "show_debug_info": true
  }
}
```

## Configuration Management

### Manual Editing

Edit configuration file directly:

**Linux/macOS**:
```bash
nano ~/.tonietoolbox/config.json
```

**Windows**:
```powershell
notepad %USERPROFILE%\.tonietoolbox\config.json
```

### Validation

TonieToolbox validates configuration on startup:
- Type checking (string, integer, boolean, array)
- Range validation for numeric values
- Path validation for directory/file settings

Invalid settings fall back to defaults with warnings in logs.

### Reset Configuration

Delete config file to reset to defaults:

```bash
rm ~/.tonietoolbox/config.json
```

TonieToolbox will create a new configuration with defaults on next startup.

### Backup Configuration

```bash
# Backup
cp ~/.tonietoolbox/config.json ~/.tonietoolbox/config.backup.json

# Restore
cp ~/.tonietoolbox/config.backup.json ~/.tonietoolbox/config.json
```

## See Also

- [Command Line Reference](command-line.md) - CLI options override config settings
- [Plugin System](../plugins/README.md) - Learn about plugin configuration
- [Basic Usage Guide](../usage/basic-usage.md) - Common usage patterns
