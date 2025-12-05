# API Reference

Complete programming interface reference for TonieToolbox, including Python API, command-line interface, and extension development.

## Python API

### Core Classes

#### `TonieConverter`

Main conversion class for programmatic access.

```python
from TonieToolbox import TonieConverter

class TonieConverter:
    def __init__(self, config=None):
        """Initialize converter with optional configuration."""
        pass
        
    def convert_file(self, input_path, output_path=None, **options):
        """Convert single audio file to TAF format."""
        pass
        
    def convert_directory(self, input_dir, output_dir=None, recursive=True, **options):
        """Convert all audio files in directory.""" 
        pass
        
    def get_supported_formats(self):
        """Return list of supported input audio formats."""
        return ['mp3', 'flac', 'm4a', 'ogg', 'wav', 'aac']
```

**Usage Example**:
```python
from TonieToolbox import TonieConverter

# Initialize converter
converter = TonieConverter()

# Simple conversion
result = converter.convert_file('audiobook.mp3', 'output.taf')

# Advanced conversion with options
result = converter.convert_file(
    input_path='music.flac',
    output_path='music.taf', 
    bitrate=128,
    use_cbr=True,
    normalize=True
)

# Batch conversion
results = converter.convert_directory(
    input_dir='./audiobooks/',
    output_dir='./taf_files/',
    recursive=True,
    bitrate=64
)
```

#### `TAFAnalyzer`

Analyze and validate TAF files.

```python
from TonieToolbox.analysis import TAFAnalyzer

class TAFAnalyzer:
    def __init__(self):
        """Initialize TAF analyzer."""
        pass
        
    def analyze_file(self, taf_path):
        """Analyze TAF file and return metadata."""
        pass
        
    def validate_file(self, taf_path):
        """Validate TAF file structure and integrity."""
        pass
        
    def extract_metadata(self, taf_path):
        """Extract embedded metadata from TAF file."""
        pass
```

**Usage Example**:
```python
from TonieToolbox.analysis import TAFAnalyzer

analyzer = TAFAnalyzer()

# Analyze TAF file
info = analyzer.analyze_file('audiobook.taf')
print(f"Duration: {info['duration']}")
print(f"Bitrate: {info['bitrate']}")
print(f"File size: {info['file_size']}")

# Validate file integrity
is_valid = analyzer.validate_file('audiobook.taf')
if not is_valid:
    print("TAF file is corrupted or invalid")

# Extract metadata
metadata = analyzer.extract_metadata('audiobook.taf')
for key, value in metadata.items():
    print(f"{key}: {value}")
```

### Configuration Management

#### `ConfigManager`

Handle configuration files and settings.

```python
from TonieToolbox.config import ConfigManager

class ConfigManager:
    def __init__(self, config_path=None):
        """Initialize with optional custom config path."""
        pass
        
    def get_setting(self, section, key, default=None):
        """Get configuration value."""
        pass
        
    def set_setting(self, section, key, value):
        """Set configuration value."""
        pass
        
    def load_profile(self, profile_name):
        """Load conversion profile."""
        pass
        
    def save_config(self):
        """Save configuration to disk."""
        pass
```

**Usage Example**:
```python
from TonieToolbox.config import ConfigManager

config = ConfigManager()

# Get settings
bitrate = config.get_setting('Audio', 'default_bitrate', 128)
output_dir = config.get_setting('General', 'output_dir', './output')

# Modify settings
config.set_setting('Audio', 'default_bitrate', 128)
config.set_setting('TeddyCloud', 'server_url', 'https://myserver.local')

# Save changes
config.save_config()

# Load profile
audiobook_config = config.load_profile('audiobook')
```

### TeddyCloud Integration

#### `TeddyCloudClient`

Upload and manage content on TeddyCloud servers.

```python
from TonieToolbox.integrations import TeddyCloudClient

class TeddyCloudClient:
    def __init__(self, server_url, username=None, password=None):
        """Initialize TeddyCloud client."""
        pass
        
    def upload_file(self, taf_path, target_path=None):
        """Upload TAF file to TeddyCloud."""
        pass
        
    def list_content(self):
        """List existing content on server."""
        pass
        
    def delete_content(self, content_id):
        """Delete content from server."""
        pass
        
    def get_server_info(self):
        """Get server information and status."""
        pass
```

**Usage Example**:
```python
from TonieToolbox.integrations import TeddyCloudClient

# Connect to TeddyCloud server
client = TeddyCloudClient(
    server_url='https://teddycloud.local:8443',
    username='admin',
    password='secret'
)

# Upload TAF file
result = client.upload_file('audiobook.taf', 'My Audiobook')
if result['success']:
    print(f"Uploaded successfully: {result['content_id']}")

# List existing content  
content_list = client.list_content()
for item in content_list:
    print(f"ID: {item['id']}, Name: {item['name']}")

# Get server status
info = client.get_server_info()
print(f"Server version: {info['version']}")
print(f"Available space: {info['free_space']}")
```

### Event System

#### `EventBus`

Subscribe to conversion events for progress monitoring.

```python
from TonieToolbox.events import EventBus, ConversionEvents

class EventBus:
    def __init__(self):
        """Initialize event bus."""
        pass
        
    def subscribe(self, event_type, callback):
        """Subscribe to specific event type."""
        pass
        
    def unsubscribe(self, event_type, callback):
        """Unsubscribe from event type."""
        pass
        
    def emit(self, event_type, data):
        """Emit event to subscribers."""
        pass
```

**Usage Example**:
```python
from TonieToolbox import TonieConverter
from TonieToolbox.events import EventBus, ConversionEvents

def on_progress(data):
    print(f"Progress: {data['percentage']}% - {data['current_file']}")

def on_complete(data):
    print(f"Conversion complete: {data['output_path']}")

def on_error(data):
    print(f"Error: {data['error_message']}")

# Set up event handlers
event_bus = EventBus()
event_bus.subscribe(ConversionEvents.PROGRESS, on_progress)
event_bus.subscribe(ConversionEvents.COMPLETE, on_complete)  
event_bus.subscribe(ConversionEvents.ERROR, on_error)

# Run conversion with events
converter = TonieConverter()
converter.convert_directory('./audiobooks/', event_bus=event_bus)
```

### Utility Functions

#### Audio Processing

```python
from TonieToolbox.utils import audio

def get_audio_info(file_path):
    """Get audio file information."""
    return {
        'duration': float,      # Duration in seconds
        'bitrate': int,         # Bitrate in kbps  
        'sample_rate': int,     # Sample rate in Hz
        'channels': int,        # Number of audio channels
        'format': str          # Audio format/codec
    }

def normalize_audio(input_path, output_path, target_lufs=-16):
    """Normalize audio to target LUFS level."""
    pass

def convert_to_mono(input_path, output_path):
    """Convert stereo audio to mono."""
    pass

def apply_fade(input_path, output_path, fade_in=0, fade_out=0):
    """Apply fade in/out effects."""
    pass
```

#### File Management

```python
from TonieToolbox.utils import files

def find_audio_files(directory, recursive=True):
    """Find all audio files in directory."""
    return ['file1.mp3', 'file2.flac', ...]

def sanitize_filename(filename):
    """Clean filename of invalid characters."""
    return "clean_filename"

def get_safe_output_path(input_path, output_dir):
    """Generate safe output path avoiding conflicts.""" 
    return "/path/to/output/file.taf"

def ensure_directory_exists(directory_path):
    """Create directory if it doesn't exist."""
    pass
```

#### Metadata Processing

```python
from TonieToolbox.utils import metadata

def extract_media_tags(file_path):
    """Extract metadata tags from audio file."""
    return {
        'title': str,
        'artist': str, 
        'album': str,
        'track': int,
        'year': int,
        'genre': str
    }

def apply_filename_template(template, metadata):
    """Apply filename template with metadata."""
    return "formatted_filename"

def clean_metadata(metadata):
    """Clean and sanitize metadata values.""" 
    return cleaned_metadata
```

## Command-Line Interface

### Core Commands

#### Basic Conversion

```bash
# Convert single file
tonietoolbox input.mp3

# Convert with specific output
tonietoolbox input.mp3 --output output.taf

# Convert directory
tonietoolbox ./audiobooks/ --recursive

# Batch convert with options
tonietoolbox *.mp3 --bitrate 128 --cbr --normalize
```

#### Advanced Processing

```bash
# Use metadata for naming
tonietoolbox album/ --use-media-tags --name-template "{artist}/{album}/{track:02d} - {title}"

# Process with custom settings
tonietoolbox input.flac --bitrate 192 --sample-rate 44100 --fade-out 2.0

# Upload to TeddyCloud
tonietoolbox audiobook.taf --upload https://teddycloud.local --username admin
```

#### Analysis and Validation

```bash  
# Analyze TAF file
tonietoolbox --analyze output.taf

# Validate file integrity
tonietoolbox --validate output.taf

# Compare files
tonietoolbox --compare original.mp3 converted.taf
```

### Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Operation completed successfully |
| `1` | General Error | Unspecified error occurred |
| `2` | Invalid Arguments | Command-line arguments invalid |
| `3` | File Not Found | Input file/directory not found |
| `4` | Permission Error | Insufficient file permissions |
| `5` | Conversion Error | Audio conversion failed |
| `6` | Network Error | TeddyCloud upload failed |
| `7` | Validation Error | TAF file validation failed |

### JSON Output Mode

Enable structured output for automation:

```bash
tonietoolbox --json input.mp3
```

**Output Format**:
```json
{
    "status": "success",
    "input_files": ["input.mp3"],
    "output_files": ["output.taf"], 
    "conversion_time": 15.3,
    "file_sizes": {
        "input.mp3": 5242880,
        "output.taf": 4194304
    },
    "audio_info": {
        "duration": 180.5,
        "original_bitrate": 320,
        "output_bitrate": 96
    }
}
```

### Scripting Integration

#### Bash Integration

```bash
#!/bin/bash

# Convert and check result
if tonietoolbox audiobook.mp3 --quiet; then
    echo "Conversion successful"
    # Upload to server
    tonietoolbox audiobook.taf --upload https://teddycloud.local
else
    echo "Conversion failed" >&2
    exit 1
fi

# Process multiple files with error handling
for file in *.mp3; do
    echo "Converting $file..."
    if ! tonietoolbox "$file" --output "${file%.mp3}.taf"; then
        echo "Failed to convert $file" >&2
        failed_files+=("$file")
    fi
done

if [ ${#failed_files[@]} -gt 0 ]; then
    echo "Failed files: ${failed_files[*]}" >&2
fi
```

#### Python Integration

```python
#!/usr/bin/env python3

import subprocess
import json
import sys

def convert_with_tonietoolbox(input_file, **options):
    """Convert file using TonieToolbox CLI."""
    cmd = ['tonietoolbox', '--json', input_file]
    
    # Add options to command
    for key, value in options.items():
        if value is True:
            cmd.append(f'--{key.replace("_", "-")}')
        elif value is not None:
            cmd.extend([f'--{key.replace("_", "-")}', str(value)])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        error_data = json.loads(e.stdout) if e.stdout else {'error': e.stderr}
        raise RuntimeError(f"Conversion failed: {error_data}")

# Usage example
try:
    result = convert_with_tonietoolbox(
        'audiobook.mp3',
        bitrate=64,
        use_media_tags=True,
        name_template='{album}/{track:02d} - {title}'
    )
    print(f"Converted successfully: {result['output_files'][0]}")
except RuntimeError as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
```

## Extension Development

### Plugin Architecture

Create custom processors and integrations.

#### Custom Audio Processor

```python
from TonieToolbox.core.processing import AudioProcessor

class CustomProcessor(AudioProcessor):
    """Custom audio processing plugin."""
    
    def __init__(self):
        super().__init__()
        self.name = "Custom Processor"
        self.version = "1.0.0"
    
    def process(self, input_path, output_path, **options):
        """Implement custom processing logic."""
        # Your custom processing here
        return {
            'success': True,
            'output_path': output_path,
            'processing_time': 10.5
        }
    
    def get_supported_formats(self):
        """Return supported input formats."""
        return ['mp3', 'flac', 'custom_format']
```

#### Custom Integration

```python
from TonieToolbox.integrations.base import BaseIntegration

class CustomCloudService(BaseIntegration):
    """Custom cloud service integration."""
    
    def __init__(self, api_key=None):
        super().__init__()
        self.api_key = api_key
        self.name = "Custom Cloud"
    
    def upload_file(self, file_path, metadata=None):
        """Upload file to custom service."""
        # Implement upload logic
        return {
            'success': True,
            'url': 'https://custom-service.com/file/123',
            'file_id': '123'
        }
    
    def validate_connection(self):
        """Test service connectivity.""" 
        # Implement connection test
        return True
```

### Plugin Registration

```python
from TonieToolbox.core.plugins import register_plugin

# Register custom processor
register_plugin('processor', CustomProcessor)

# Register custom integration  
register_plugin('integration', CustomCloudService)

# Use in configuration
config = {
    'processor': 'CustomProcessor',
    'integrations': {
        'custom_cloud': {
            'api_key': 'your-api-key'
        }
    }
}
```

### GUI Extensions

#### Custom GUI Components

```python
from TonieToolbox.core.gui.components.base import QtBaseComponent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton

class CustomSettingsPanel(QtBaseComponent):
    """Custom settings panel for GUI."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Create UI components."""
        layout = QVBoxLayout()
        
        # Add custom controls
        layout.addWidget(QLabel("Custom Settings"))
        
        self.custom_option = QLineEdit()
        layout.addWidget(self.custom_option)
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        layout.addWidget(apply_button)
        
        self.setLayout(layout)
    
    def apply_settings(self):
        """Apply custom settings."""
        # Implement settings logic
        pass
```

### Testing Extensions

#### Unit Tests

```python
import unittest
from TonieToolbox.tests import BaseTestCase

class TestCustomProcessor(BaseTestCase):
    """Test custom audio processor."""
    
    def setUp(self):
        self.processor = CustomProcessor()
    
    def test_processing(self):
        """Test basic processing functionality."""
        result = self.processor.process(
            input_path=self.get_test_file('test.mp3'),
            output_path=self.get_temp_path('output.taf')
        )
        
        self.assertTrue(result['success'])
        self.assertTrue(os.path.exists(result['output_path']))
    
    def test_supported_formats(self):
        """Test supported format detection."""
        formats = self.processor.get_supported_formats()
        self.assertIn('mp3', formats)
```

#### Integration Tests

```python
import unittest
from TonieToolbox.tests import IntegrationTestCase

class TestCustomIntegration(IntegrationTestCase):
    """Test custom cloud integration."""
    
    def setUp(self):
        self.integration = CustomCloudService(api_key='test-key')
    
    def test_file_upload(self):
        """Test file upload functionality."""
        test_file = self.create_test_taf_file()
        
        result = self.integration.upload_file(test_file)
        
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['file_id'])
```

## Error Handling

### Exception Classes

```python
from TonieToolbox.exceptions import (
    TonieToolboxError,
    ConversionError, 
    ValidationError,
    NetworkError,
    ConfigurationError
)

# Base exception
class TonieToolboxError(Exception):
    """Base exception for TonieToolbox errors."""
    pass

# Specific exceptions
class ConversionError(TonieToolboxError):
    """Audio conversion failed."""
    pass

class ValidationError(TonieToolboxError):
    """File validation failed."""
    pass

class NetworkError(TonieToolboxError):
    """Network operation failed."""
    pass
```

### Error Handling Patterns

```python
from TonieToolbox import TonieConverter
from TonieToolbox.exceptions import ConversionError, ValidationError

try:
    converter = TonieConverter()
    result = converter.convert_file('input.mp3')
    
except ConversionError as e:
    print(f"Conversion failed: {e}")
    # Handle conversion-specific errors
    
except ValidationError as e:
    print(f"File validation failed: {e}")
    # Handle validation errors
    
except FileNotFoundError as e:
    print(f"File not found: {e}")
    # Handle missing files
    
except PermissionError as e:
    print(f"Permission denied: {e}")
    # Handle permission issues
    
except Exception as e:
    print(f"Unexpected error: {e}")
    # Handle unexpected errors
```

## Performance Considerations

### Memory Management

```python
# Process large files in chunks
converter = TonieConverter(config={
    'processing': {
        'chunk_size': '1MB',
        'low_memory_mode': True
    }
})

# Use context managers for cleanup
with TonieConverter() as converter:
    result = converter.convert_file('large_file.flac')
# Automatic cleanup happens here
```

### Parallel Processing

```python
import concurrent.futures
from TonieToolbox import TonieConverter

def convert_file_wrapper(args):
    """Wrapper for parallel processing."""
    input_file, options = args
    converter = TonieConverter()
    return converter.convert_file(input_file, **options)

# Process multiple files in parallel  
files_to_convert = [
    ('file1.mp3', {'bitrate': 96}),
    ('file2.flac', {'bitrate': 128}), 
    ('file3.m4a', {'bitrate': 64})
]

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(convert_file_wrapper, files_to_convert))

for result in results:
    print(f"Converted: {result['output_path']}")
```

## Version Compatibility

### API Versioning

```python
from TonieToolbox import __version__, __api_version__

# Check minimum required version
import packaging.version

required_version = "1.0.0"
current_version = __version__

if packaging.version.parse(current_version) < packaging.version.parse(required_version):
    raise RuntimeError(f"TonieToolbox {required_version}+ required, found {current_version}")
```

## Version Management

```python
# Check minimum required version
import packaging.version
from TonieToolbox import __version__

required_version = "1.0.0"
current_version = __version__

if packaging.version.parse(current_version) < packaging.version.parse(required_version):
    raise RuntimeError(f"TonieToolbox {required_version}+ required, found {current_version}")
```

## Next Steps

- 🚀 **[Installation Guide](../getting-started/installation.md)** - Set up development environment
- 📚 **[Examples & Use Cases](../examples/use-cases.md)** - See real-world examples
- 🔧 **[Configuration](configuration.md)** - Configure TonieToolbox settings