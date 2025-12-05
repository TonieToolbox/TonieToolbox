# GUI User Guide

TonieToolbox features a modern PyQt6-based graphical interface that functions as a TAF file player with integrated plugin support. This guide covers all GUI features and workflows.

## Launching the GUI

Start the GUI with a simple command:

```bash
tonietoolbox --gui
```

The interface will open in a new window, ready to play and manage your TAF audio files.

## Interface Overview

The TonieToolbox GUI is designed as a **TAF Player** with a tabbed interface:

### Main Window Components

1. **Tab Bar**: Switch between different application views
   - **Player Tab** (Default): TAF file playback interface
   - **Plugin Tabs**: Additional tabs provided by installed plugins

2. **Menu Bar**: Access application features
   - **File**: Open files, recent files, exit
   - **Playback**: Control playback (play/pause, stop, next, previous)
   - **View**: Theme switching, language selection
   - **Tools**: Access plugin manager and other utilities
   - **Help**: About dialog, documentation

3. **Status Bar**: Real-time information
   - Current file status
   - Track information
   - Playback position

## Player Tab Interface

The main Player tab is divided into three panels:

### Left Panel: Playlist
- **Playlist Widget**: Shows all loaded TAF files
  - Double-click to play a file
  - Right-click for context menu (remove, clear all)
  - Drag-and-drop support for adding files
- **Playlist Controls**: 
  - Add Files button
  - Add Folder button (recursive folder scanning)
  - Clear Playlist button
  - Remove Selected button
- **Playlist Info**: 
  - Total tracks count
  - Total duration
  - Current track indicator

### Middle Panel: Chapter Navigation
- **Chapter List**: Displays chapters within the current TAF file
  - Shows chapter number, timestamp, and duration
  - Click to jump to specific chapter
  - Visual indicator for current chapter
- **Auto-scroll**: Automatically scrolls to current chapter during playback

### Right Panel: Player Controls
- **File Information Display**:
  - Current filename
  - Track duration
  - File size
  - Audio format details
  
- **Playback Controls**:
  - Play/Pause button (spacebar shortcut)
  - Stop button
  - Previous track button
  - Next track button
  - Volume slider with mute toggle
  
- **Progress Bar**:
  - Visual playback position
  - Click to seek to position
  - Time display (current / total)
  - Chapter markers overlay

## Basic Workflows

### Playing TAF Files

#### Method 1: Drag and Drop
1. **Drag TAF files** from your file manager into the playlist area
2. **Double-click** a file in the playlist to start playback
3. Use **playback controls** to manage playback

#### Method 2: Add Files Button
1. Click **"Add Files"** in the playlist controls
2. **Select one or more TAF files** in the file dialog
3. Files are added to the playlist
4. **Double-click** to play

#### Method 3: Add Folder
1. Click **"Add Folder"** in the playlist controls
2. **Select a folder** containing TAF files
3. **Recursive scanning** finds all TAF files in subdirectories
4. All found files are added to the playlist

### Navigating Chapters

TAF files can contain multiple chapters:

1. **View chapters** in the middle panel
2. **Click a chapter** to jump to that position
3. **Current chapter** is highlighted during playback
4. **Auto-scroll** keeps current chapter visible

### Managing Playlists

- **Add more files**: Use Add Files/Folder anytime
- **Remove files**: Right-click → Remove, or use Remove Selected button
- **Clear playlist**: Click Clear Playlist to remove all files
- **Reorder**: Drag files within the playlist (if supported)
- **Recent files**: Access via File menu → Recent Files

## Plugin System

TonieToolbox v1.0 introduces a powerful plugin system:

### Accessing Plugins

1. **Menu**: Tools → Plugin Manager
2. **Plugin tabs**: Installed plugins may add their own tabs
3. **Menu items**: Plugins can add custom menu entries

### Plugin Manager

The Plugin Manager allows you to:

- **Discover Plugins**: Browse official and community plugins
- **Install Plugins**: One-click installation from repository
- **Manage Installed**: Enable/disable/uninstall plugins
- **Configure**: Access plugin settings
- **Trust Levels**: See plugin trust badges (Official, Verified, Community)

### Example Plugins

**Tonies Loader** (Official):
- Loads Tonie metadata from tonies.json
- Provides Tonie information lookup

**Tonies Viewer** (Official):
- Visual browser for Tonies
- Shows Tonie images and details
- Adds "Tonies" tab to interface

## Advanced Features

### Keyboard Shortcuts

Master these shortcuts for efficient usage:

| Shortcut | Action |
|----------|--------|
| `Space` | Play / Pause |
| `Ctrl+O` | Open file(s) |
| `Ctrl+D` | Open folder |
| `Ctrl+Q` | Quit application |
| `Delete` | Remove selected from playlist |
| `Right Arrow` | Seek forward 5 seconds |
| `Left Arrow` | Seek backward 5 seconds |
| `Up Arrow` | Increase volume |
| `Down Arrow` | Decrease volume |
| `M` | Mute / Unmute |
| `N` | Next track |
| `P` | Previous track |

### Theme Switching

TonieToolbox supports multiple themes:

1. **Menu**: View → Theme
2. **Choose theme**:
   - Default Light
   - Default Dark
   - System (follows OS preference)
3. **Theme applies immediately** without restart

### Language Selection

Switch interface language:

1. **Menu**: View → Language
2. **Select language**:
   - English (en_US)
   - German (de_DE)
3. **Interface updates immediately**

### Configuration

Settings are managed through the central configuration file:

- **Theme preference**: Saved in config.json
- **Language preference**: Saved in config.json
- **Plugin settings**: Per-plugin configuration storage

## Playback Features

### Supported Formats

The player supports:

- **TAF files** (.taf): Primary format
- **Audio detection**: Automatically detects Opus-encoded TAF files
- **Chapter support**: Recognizes chapter markers in TAF files

### Playback Controls

- **Continuous playback**: Automatically plays next track when current ends

### Volume Control

- **Volume slider**: 0-100% range
- **Mute toggle**: Quick mute/unmute

## Troubleshooting GUI Issues

### GUI Won't Start

If `tonietoolbox --gui` doesn't work:### GUI Won't Start

If `tonietoolbox --gui` doesn't work:

=== "Check PyQt6 Installation"
    
    ```bash
    # Verify PyQt6 is installed
    python3.14 -c "from PyQt6 import QtWidgets; print('PyQt6 OK')"
    
    # Reinstall if needed
    pip install --force-reinstall PyQt6>=6.10.0
    ```

=== "Check Dependencies"
    
    ```bash
    # Verify all GUI dependencies
    pip install --upgrade tonietoolbox
    ```

=== "Use Module Syntax"
    
    ```bash
    # Alternative launch method
    python3.14 -m TonieToolbox --gui
    ```

### Audio Playback Issues

**No sound during playback:**

1. **Check system volume**: Ensure OS volume is not muted
2. **Check player volume**: Verify volume slider is not at 0%
3. **Check file format**: Ensure TAF file is valid
4. **Check audio output**: Verify correct audio device selected in OS

**Choppy or stuttering playback:**

1. **Close resource-heavy applications**
2. **Use local storage** instead of network drives
3. **Check file integrity**: Verify TAF file is not corrupted
4. **Update system audio drivers**

### File Loading Problems

**Can't open TAF files:**

- **Check file extension**: Must be .taf
- **Verify file format**: Use `tonietoolbox --info file.taf` to validate
- **Check file permissions**: Ensure read access to the file
- **Try different location**: Copy file to local drive

**Drag and drop not working:**

- **Restart application**: Sometimes Qt drag-drop needs reset
- **Use Add Files button**: Alternative method
- **Check file associations**: Ensure .taf files aren't locked by another application

## Tips for Effective Use

### Organizing Your TAF Library

1. **Create folders** by content type:
   ```
   ~/TAF Files/
   ├── Audiobooks/
   ├── Music/
   ├── Stories/
   └── Podcasts/
   ```

2. **Use consistent naming**: 
   - Audiobooks: `{series} - {book} - Chapter {chapter}.taf`
   - Music: `{artist} - {album} - {track} {title}.taf`
   - Podcasts: `{podcast} - {date} - {title}.taf`

3. **Maintain metadata**: Keep chapter information embedded

### Keyboard Workflow

Power users can work primarily with keyboard:

1. `Ctrl+O` → Select files
2. `Enter` → Play first file
3. `Space` → Control playback
4. `N` → Next track
5. `Arrows` → Seek/volume
6. `M` → Quick mute

### Plugin Recommendations

**Essential Plugins:**

- **Tonies Loader**: Adds Tonie metadata integration
- **Tonies Viewer**: Visual browser for Tonies library
- **Plugin Manager**: Already built-in for managing plugins

**Finding More Plugins:**

1. Open Tools → Plugin Manager
2. Browse "Discover" tab
3. Check trust badges (🏆 Official, ✓ Verified, 👥 Community)
4. Read descriptions and reviews
5. One-click install

### Performance Optimization

For smooth playback:

- **Use SSD storage** for TAF files when possible
- **Keep playlists under 1000 files** for best performance
- **Close unused plugins** to free resources
- **Update to latest version** for performance improvements

## Interface Customization

### Adjusting Layout

The three-panel layout can be adjusted:

1. **Hover over panel dividers** until cursor changes
2. **Drag to resize** panels to your preference
3. **Layout persists** between sessions

### Window Management

- **Full screen**: Maximize window for more space
- **Multi-monitor**: Drag window to preferred screen

## Command Line Integration

You can also control the GUI from command line:

```bash
# Launch GUI with specific file
tonietoolbox --gui /path/to/file.taf

# Launch with multiple files
tonietoolbox --gui *.taf

# Launch with folder
tonietoolbox --gui /path/to/taf/folder/
```

## Data and Configuration

### Configuration Files

All settings are stored in the central configuration file:
- **All platforms**: `~/.tonietoolbox/config.json`

This JSON file contains:
- Application settings (processing, logging, paths)
- GUI settings (theme, language)
- TeddyCloud connection settings
- Plugin configuration (namespaced per plugin)

See [Configuration Reference](../reference/configuration.md) for complete documentation.

### Plugin Data

Each plugin stores its data in separate directories:
- **Plugin cache**: `~/.tonietoolbox/cache/{plugin_name}/`
- **Plugin data**: `~/.tonietoolbox/data/{plugin_name}/` (if used)
- **Installed plugins**: `~/.tonietoolbox/plugins/{author}/{plugin_name}/`

### Keyboard Navigation

- **Tab**: Navigate between controls
- **Shift+Tab**: Navigate backwards
- **Enter/Space**: Activate buttons
- **Arrow keys**: Navigate lists and adjust sliders

## Next Steps

Now that you're familiar with the GUI:

- 🎵 **[Convert Audio Files](first-conversion.md)** - Use CLI to create TAF files
- 🔌 **[Explore Plugins](../plugins/README.md)** - Extend functionality
- ⌨️ **[Learn Command Line](../usage/basic-usage.md)** - Discover automation
- ☁️ **[Set Up TeddyCloud](../usage/teddycloud.md)** - Server integration

The TonieToolbox GUI provides a modern, plugin-extensible interface for managing and playing your TAF audio files! 🎵