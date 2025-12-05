# TeddyCloud Service Integration Guide for Plugin Developers

## Overview

The TeddyCloud service is now available to all plugins through the centralized service provider pattern. This allows plugins to interact with TeddyCloud servers for uploading files, retrieving tags, and managing content.

## Quick Start

### Accessing the Service

```python
from TonieToolbox.core.plugins import BasePlugin, PluginContext

class MyPlugin(BasePlugin):
    def initialize(self, context: PluginContext) -> bool:
        # Get TeddyCloud service
        self.tc_service = context.get_service('teddycloud')
        
        if not self.tc_service:
            context.log_warning("TeddyCloud service not available")
            return True  # Still OK, just limited functionality
        
        # Check if connected
        if self.tc_service.is_connected:
            context.log_info("Connected to TeddyCloud server")
        
        return True
```

## Available Service Methods

### Connection Status

```python
# Check if service is connected to TeddyCloud server
if service.is_connected:
    # Server is available
    pass
```

### Tag Operations

#### Get All Tags

```python
result = service.get_tags()

if result.success:
    print(f"Retrieved {result.total_count} tags")
    
    for tag in result.tags:
        print(f"UID: {tag.uid}")
        print(f"Series: {tag.series}")
        print(f"Episode: {tag.episode}")
        print(f"Tracks: {len(tag.tracks)}")
else:
    print(f"Error: {result.error}")
```

**TagRetrievalResult** attributes:
- `success: bool` - Whether operation succeeded
- `tags: List[TeddyCloudTag]` - List of retrieved tags
- `total_count: int` - Total number of tags
- `message: str` - Success message
- `error: str` - Error message if failed

**TeddyCloudTag** attributes:
- `uid: str` - Unique tag identifier
- `tag_type: str` - Tag type (e.g., "tag", "system")
- `valid: TagValidationStatus` - VALID, INVALID, UNKNOWN
- `series: str` - Series name
- `episode: str` - Episode name  
- `source: str` - File source path
- `tracks: List[str]` - Track names
- `track_seconds: List[int]` - Track durations
- `tonie_info: dict` - Additional metadata

#### Display Tags

```python
tags = result.tags
formatted = service.display_tags(tags)
print(formatted)  # Pretty-printed tag information
```

#### Get Tag Summary

```python
summary = service.get_tag_summary(tags)
print(f"Total tags: {summary['total']}")
print(f"Valid tags: {summary['valid']}")
print(f"Invalid tags: {summary['invalid']}")
```

### File Index Operations

#### Get File Index V2 (Recommended)

```python
# Get file index with improved V2 format (unix timestamps, shorter property names)
file_index = service.get_file_index_v2()

if file_index and 'files' in file_index:
    for file_entry in file_index['files']:
        name = file_entry['name']
        timestamp = file_entry['date']  # Unix timestamp
        is_dir = file_entry['isDir']  # Boolean
        hide = file_entry['hide']  # Boolean
        
        # Convert timestamp to datetime
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        
        print(f"{'[DIR]' if is_dir else '[FILE]'} {name} - {dt}")
        
        # Access tonie info if available
        if 'tonieInfo' in file_entry:
            tonie_info = file_entry['tonieInfo']
            print(f"  Series: {tonie_info.get('series')}")
            print(f"  Episode: {tonie_info.get('episode')}")
            print(f"  Tracks: {len(tonie_info.get('tracks', []))}")
```

**File Index V2 Format:**
```python
{
    "files": [
        {
            "name": "F218E91E",
            "date": 1746525784,  # Unix timestamp (numeric)
            "size": 4096,
            "isDir": true,       # Shortened from isDirectory
            "hide": false,       # Boolean flag instead of desc
            "tonieInfo": {
                "tracks": ["Track 1", "Track 2"],
                "model": "10000119",
                "series": "Disney",
                "episode": "Aladdin",
                "picture": "/cache/...",
                "language": "de-de"
            }
        }
    ]
}
```

#### Get File Index V1 (Legacy)

```python
# Get file index with legacy V1 format (string dates)
file_index = service.get_file_index()

if file_index and 'files' in file_index:
    for file_entry in file_index['files']:
        name = file_entry['name']
        date_str = file_entry['date']  # String: " 2025-05-06,  10:03:04"
        is_directory = file_entry['isDirectory']  # Boolean
        desc = file_entry['desc']  # String (usually empty)
        
        print(f"{'[DIR]' if is_directory else '[FILE]'} {name} - {date_str}")
```

**Differences V1 vs V2:**

| Property | V1 Format | V2 Format |
|----------|-----------|-----------|
| **date** | `" 2025-05-06,  10:03:04"` (string) | `1746525784` (unix timestamp) |
| **isDirectory** | `isDirectory: true` | `isDir: true` (shorter) |
| **desc** | `desc: ""` (empty string) | `hide: false` (boolean) |

**Recommendation:** Use `get_file_index_v2()` for new implementations as it provides:
- ✅ Easier date parsing and comparison
- ✅ Better performance with numeric timestamps
- ✅ Cleaner property names
- ✅ More semantic hide flag

### Tag Operations

#### Get Tag Information by UID

```python
# Get detailed information about a specific tag
tag_uid = "E0:04:03:50:1E:E9:18:F2"
tag_info = service.get_tag_info(tag_uid)

if tag_info:
    print(f"Tag UID: {tag_uid}")
    if 'tonieInfo' in tag_info:
        tonie = tag_info['tonieInfo']
        print(f"Series: {tonie.get('series')}")
        print(f"Episode: {tonie.get('episode')}")
        print(f"Model: {tonie.get('model')}")
        print(f"Tracks: {len(tonie.get('tracks', []))}")
```

#### Assign Unknown Tag to Model

```python
# Map an unrecognized NFC tag to a known tonie model
# This enables the tag to work with your Toniebox
tag_uid = "AA:BB:CC:DD:EE:FF:GG:HH"
tonie_model = "10000119"  # Disney Aladdin

if service.assign_unknown_tag(tag_uid, tonie_model):
    print(f"Tag {tag_uid} assigned to model {tonie_model}")
```

**What does assign_unknown_tag do?**

When you place a new or custom NFC tag on your Toniebox, TeddyCloud may not recognize it. The `assign_unknown_tag()` method allows you to:
- Manually map the tag's UID to a known tonie model ID
- Enable custom/blank tags to play specific content
- Associate third-party NFC tags with tonie audio files
- Recover from lost tag-to-content mappings

**Use cases:**
- 🏷️ Programming blank NFC tags as custom tonies
- 🔄 Replacing damaged/lost official tonie tags
- 🎨 Creating custom tonie collections
- 🛠️ Testing and development with generic NFC tags

### Box Management

#### Get Registered Tonieboxes

```python
# Get list of all registered Tonieboxes
boxes = service.get_boxes()

if boxes and 'boxes' in boxes:
    for box in boxes['boxes']:
        print(f"Box: {box['boxName']}")
        print(f"  ID: {box['ID']}")
        print(f"  Model: {box['boxModel']}")
        print(f"  Common Name: {box['commonName']}")
```

### Server Configuration

#### Get Setting Value

```python
# Get a specific server setting
http_port = service.get_setting("core.server.http_port")
print(f"HTTP Port: {http_port}")

# Other common settings:
# - core.server.https_web_port
# - core.server.https_api_port
# - core.allowNewBox
# - core.tonies_json_auto_update
```

#### Set Setting Value

```python
# Update a server setting
if service.set_setting("core.server.http_port", "8080"):
    print("Setting updated successfully")
else:
    print("Failed to update setting")

# Note: Some settings may require server restart to take effect
```

### Database Management

#### Update Tonies Database

```python
# Trigger download of latest tonies.json from official source
if service.trigger_tonies_json_update():
    print("Tonies database update triggered")
    print("This will download the latest tonie information")
```

#### Reload Tonies Database

```python
# Reload tonies.json from disk (without downloading)
if service.trigger_tonies_json_reload():
    print("Tonies database reloaded from disk")
```

**Difference between update and reload:**
- **`trigger_tonies_json_update()`**: Downloads latest database from internet
- **`trigger_tonies_json_reload()`**: Reloads existing database file from disk

### Upload Operations

#### Upload Single File

```python
result = service.upload_file(
    file_path="/path/to/file.taf",
    template_path="/{albumartist}/{album}",  # Optional path template
    special=SpecialFolder.LIBRARY,            # Optional special folder
    include_artwork=True                      # Optional artwork upload
)

if result.success:
    print(f"Uploaded: {result.file_path}")
    print(f"Destination: {result.destination_path}")
else:
    print(f"Upload failed: {result.error}")
```

**UploadResult** attributes:
- `success: bool` - Whether upload succeeded
- `file_path: str` - Local file path
- `destination_path: str` - Server destination path
- `message: str` - Success message
- `error: str` - Error message if failed
- `server_response: dict` - Server response data

#### Upload Multiple Files

```python
file_paths = ["/path/to/file1.taf", "/path/to/file2.taf"]

results = service.upload_multiple_files(
    file_paths=file_paths,
    template_path="/{albumartist}/{album}",
    special=SpecialFolder.LIBRARY
)

for result in results:
    if result.success:
        print(f"✅ {result.file_path}")
    else:
        print(f"❌ {result.file_path}: {result.error}")
```

### Server Information

```python
info = service.get_server_info()

print(f"Connected: {info['connected']}")
print(f"Server URL: {info['base_url']}")
print(f"Secure: {info['secure']}")
print(f"Auth Type: {info['authentication']}")
```

## Event System Integration

Subscribe to TeddyCloud events to react to operations:

### Available Events

```python
from TonieToolbox.core.teddycloud.events import (
    TeddyCloudConnectionEstablishedEvent,
    TeddyCloudConnectionFailedEvent,
    TeddyCloudUploadStartedEvent,
    TeddyCloudUploadCompletedEvent,
    TeddyCloudUploadFailedEvent,
    TeddyCloudTagsRetrievedEvent,
    TeddyCloudBatchUploadStartedEvent,
    TeddyCloudBatchUploadCompletedEvent
)
```

### Subscribe to Events

```python
def initialize(self, context: PluginContext) -> bool:
    # Subscribe to upload completion
    context.event_bus.subscribe(
        TeddyCloudUploadCompletedEvent,
        self._on_upload_completed
    )
    
    # Subscribe to tag retrieval
    context.event_bus.subscribe(
        TeddyCloudTagsRetrievedEvent,
        self._on_tags_retrieved
    )
    
    return True

def _on_upload_completed(self, event: TeddyCloudUploadCompletedEvent):
    """Handle upload completion."""
    context.log_info(f"Upload completed: {event.file_path}")
    # React to upload - update UI, refresh data, etc.

def _on_tags_retrieved(self, event: TeddyCloudTagsRetrievedEvent):
    """Handle tags retrieval."""
    if event.successful:
        context.log_info(f"Retrieved {event.tag_count} tags")
```

### Event Attributes

#### TeddyCloudConnectionEstablishedEvent
- `source: str` - Event source
- `server_url: str` - TeddyCloud server URL
- `authentication_type: str` - Authentication type used
- `secure_connection: bool` - Whether using HTTPS

#### TeddyCloudUploadCompletedEvent
- `source: str` - Event source
- `file_path: Path` - Local file path
- `destination_path: str` - Server destination
- `upload_result: dict` - Server response

#### TeddyCloudTagsRetrievedEvent
- `source: str` - Event source
- `tag_count: int` - Number of tags retrieved
- `successful: bool` - Whether retrieval succeeded
- `server_url: str` - TeddyCloud server URL
- `error: str` - Error message if failed

## Complete Example Plugin

See `plugin_teddycloud_example/` for a complete working example that demonstrates:

- Service access and initialization
- Connection status checking
- Tag retrieval and display
- Event subscription
- Error handling

## Best Practices

### 1. Check Service Availability

Always check if the service is available before using it:

```python
self.tc_service = context.get_service('teddycloud')

if not self.tc_service:
    # Service not available - handle gracefully
    context.log_warning("TeddyCloud service unavailable")
    return True  # Can still initialize with limited features
```

### 2. Check Connection Status

Before performing operations, verify the connection:

```python
if not self.tc_service.is_connected:
    context.log_error("Not connected to TeddyCloud server")
    return
```

### 3. Handle Errors Gracefully

Always handle potential errors:

```python
try:
    result = self.tc_service.get_tags()
    if not result.success:
        context.log_error(f"Failed to get tags: {result.error}")
except Exception as e:
    context.log_error(f"Error getting tags: {e}", exc_info=True)
```

### 4. Clean Up Event Subscriptions

Unsubscribe from events in the cleanup method:

```python
def cleanup(self) -> None:
    if self._context:
        try:
            self._context.event_bus.unsubscribe(
                TeddyCloudUploadCompletedEvent,
                self._on_upload_completed
            )
        except Exception as e:
            self._context.log_error(f"Error unsubscribing: {e}")
    
    super().cleanup()
```

### 5. Use Context Logging

Use context logging methods for consistent log formatting:

```python
context.log_info("Information message")
context.log_warning("Warning message")
context.log_error("Error message", exc_info=True)
context.log_debug("Debug message")
```

## Configuration

TeddyCloud connection is configured in `~/.tonietoolbox/config.json`:

```json
{
  "application": {
    "teddycloud": {
      "url": "https://teddycloud.example.com",
      "ignore_ssl_verify": false,
      "username": null,
      "password": null,
      "certificate_path": "/path/to/client.crt",
      "private_key_path": "/path/to/client.key"
    }
  }
}
```

If configured, the service will auto-connect on initialization.

## Testing Your Plugin

Use the test script to verify your plugin can access the service:

```bash
python3 test_teddycloud_plugin_access.py
```

## Troubleshooting

### Service is None

**Problem:** `context.get_service('teddycloud')` returns `None`

**Solutions:**
- Check if plugins are enabled in configuration
- Verify TeddyCloud service provider is initialized in app
- Check application logs for initialization errors

### Service Not Connected

**Problem:** `service.is_connected` is `False`

**Solutions:**
- Check TeddyCloud configuration in `config.json`
- Verify TeddyCloud server is accessible
- Check authentication credentials
- Review connection logs

### Import Errors

**Problem:** Cannot import TeddyCloud events or classes

**Solution:**
```python
# Correct import paths
from TonieToolbox.core.plugins import BasePlugin, PluginContext
from TonieToolbox.core.teddycloud.events import TeddyCloudUploadCompletedEvent
from TonieToolbox.core.teddycloud.domain import SpecialFolder
```

## API Reference

For complete API documentation, see:
- `TonieToolbox/core/teddycloud/application/service.py` - TeddyCloudService class
- `TonieToolbox/core/teddycloud/domain/entities.py` - Domain entities
- `TonieToolbox/core/teddycloud/events.py` - Event definitions

## Support

- Example Plugin: `plugin_teddycloud_example/`
- Test Script: `test_teddycloud_plugin_access.py`
- Documentation: `TEDDYCLOUD_MODULE_ANALYSIS.md`
- Issues: https://github.com/TonieToolbox/TonieToolbox/issues
