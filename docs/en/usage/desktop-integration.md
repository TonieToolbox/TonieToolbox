# Desktop Integration Guide

TonieToolbox integrates seamlessly with your desktop environment, allowing you to convert audio files directly from your file manager with right-click context menus.

## Supported Platforms

TonieToolbox provides desktop integration for:

- **Windows**: Explorer context menus
- **Linux**: KDE Plasma and GNOME integration
- **macOS**: Finder integration (planned)

## Installation

### Automatic Installation

Install desktop integration with a single command:

```bash
tonietoolbox --install-integration
```

This will:
- Detect your desktop environment automatically
- Install appropriate context menu entries
- Configure default settings
- Set up GUI launcher shortcuts

### Manual Configuration

For custom setups or troubleshooting:

```bash
# Configure integration settings first
tonietoolbox --config-integration

# Then install with custom settings
tonietoolbox --install-integration
```

## Windows Integration

### Explorer Context Menu

After installation, right-click on audio files or folders in Windows Explorer to see:

- **"Convert to Tonie Format"** - Quick conversion with default settings
- **"Open in TonieToolbox Player"** - Open TAF files in GUI player
- **"Upload to TeddyCloud"** - Direct upload if configured

### Registry Entries

TonieToolbox creates registry entries at:
```
HKEY_CURRENT_USER\Software\Classes\*\shell\TonieToolbox
HKEY_CURRENT_USER\Software\Classes\Directory\shell\TonieToolbox
```

### Customization

Configure integration behavior:

```bash
tonietoolbox --config-integration
```

Options include:
- Default conversion settings (bitrate, format)
- TeddyCloud server configuration
- GUI vs. command-line preference
- File type associations

## Linux Integration

### KDE Plasma

Integration with Dolphin file manager:

**Service Files Created**:
- `~/.local/share/kservices5/tonietoolbox-convert.desktop`
- `~/.local/share/kservices5/tonietoolbox-gui.desktop`

**Context Menu Actions**:
- Convert selected files
- Open with TonieToolbox GUI
- Upload to TeddyCloud (if configured)

### GNOME

Integration with Nautilus file manager:

**Script Files Created**:
- `~/.local/share/nautilus/scripts/TonieToolbox Convert`
- `~/.local/share/nautilus/scripts/TonieToolbox GUI`

**Usage**:
1. Select audio files in Nautilus
2. Right-click and choose "Scripts"
3. Select desired TonieToolbox action

### Configuration Files

Linux integration settings stored in:
```
~/.config/tonietoolbox/integration.conf
```

## Configuration Options

### Basic Settings

```bash
tonietoolbox --config-integration
```

Interactive configuration wizard covers:

1. **Default Action**: Command-line conversion settings
2. **Quality Settings**: Bitrate, encoding mode
3. **File Organization**: Naming templates, output directories
4. **TeddyCloud Integration**: Server URL, credentials
5. **Artwork Handling**: Include cover art in uploads

### Advanced Configuration

Edit configuration files directly for fine-tuning:

#### Windows Registry
```reg
[HKEY_CURRENT_USER\Software\Classes\*\shell\TonieToolbox]
@="Convert to Tonie Format"
"Icon"="C:\\Path\\To\\TonieToolbox\\icon.ico"

[HKEY_CURRENT_USER\Software\Classes\*\shell\TonieToolbox\command]  
@="\"C:\\Path\\To\\tonietoolbox.exe\" \"%1\" --bitrate 96"
```

#### Linux Service Files
```desktop
[Desktop Entry]
Type=Service
ServiceTypes=KonqPopupMenu/Plugin
MimeType=audio/mpeg;audio/flac;audio/ogg;
Actions=convert;gui;upload;

[Desktop Action convert]
Name=Convert to Tonie Format
Icon=audio-x-generic
Exec=tonietoolbox %F --bitrate 96 --use-media-tags

[Desktop Action gui]
Name=Open with TonieToolbox GUI  
Icon=tonietoolbox
Exec=tonietoolbox --gui %F
```

## Usage Examples

### Single File Conversion

1. **Right-click** on an audio file
2. **Select** "Convert to Tonie Format"
3. **Wait** for conversion to complete
4. **Find** the TAF file in your configured output directory

### Batch Conversion

1. **Select multiple audio files** in your file manager
2. **Right-click** and choose "Convert to Tonie Format"
3. **Monitor progress** (GUI will show if enabled)
4. **Check results** in the output directory

### Folder Processing

1. **Right-click** on a folder containing audio files
2. **Choose** "Convert to Tonie Format"
3. **Confirm** recursive processing (if prompted)
4. **Review** generated TAF files

### TeddyCloud Upload

1. **Configure TeddyCloud settings** first:
   ```bash
   tonietoolbox --config-integration
   ```
2. **Right-click** on converted TAF files
3. **Select** "Upload to TeddyCloud"
4. **Verify** successful upload

## Customization Examples

### Custom Conversion Profiles

Create profiles for different use cases:

```bash
# Music profile (high quality)
tonietoolbox --config-integration --profile music
# Configure: bitrate=192, cbr=true, use-media-tags=true

# Audiobook profile (optimized for speech)  
tonietoolbox --config-integration --profile audiobook
# Configure: bitrate=64, cbr=true, mono-conversion=false

# Podcast profile
tonietoolbox --config-integration --profile podcast
# Configure: bitrate=96, cbr=true, name-template="{album} - {title}"
```

### Multiple TeddyCloud Servers

Configure different upload targets:

```bash
# Home server
tonietoolbox --config-integration --server home
# Configure: url=https://home-teddycloud.local

# Office server
tonietoolbox --config-integration --server office  
# Configure: url=https://office-teddycloud.internal
```

### Custom File Associations

Add support for additional file types:

**Windows Registry**:
```reg
[HKEY_CURRENT_USER\Software\Classes\.m4a\shell\TonieToolbox]
@="Convert M4A to Tonie Format"

[HKEY_CURRENT_USER\Software\Classes\.m4a\shell\TonieToolbox\command]
@="\"C:\\Path\\To\\tonietoolbox.exe\" \"%1\""
```

**Linux MIME Types**:
```desktop
MimeType=audio/mpeg;audio/flac;audio/ogg;audio/mp4;audio/x-m4a;audio/wav;
```

## Troubleshooting

### Integration Not Appearing

**Windows**:
1. **Check registry entries**: Use `regedit` to verify entries exist
2. **Restart Explorer**: Kill and restart explorer.exe process
3. **Check permissions**: Ensure user has registry write access
4. **Reinstall**: `tonietoolbox --uninstall-integration && tonietoolbox --install-integration`

**Linux KDE**:
1. **Verify service files**: Check `~/.local/share/kservices5/`
2. **Update KDE cache**: Run `kbuildsycoca5`
3. **Check MIME types**: Verify audio file associations
4. **Restart Dolphin**: Close and reopen file manager

**Linux GNOME**:
1. **Check script directory**: Verify `~/.local/share/nautilus/scripts/`
2. **File permissions**: Ensure scripts are executable
3. **Restart Nautilus**: `nautilus -q && nautilus &`

### Commands Not Working

1. **Check TonieToolbox installation**:
   ```bash
   which tonietoolbox
   tonietoolbox --version
   ```

2. **Verify configuration**:
   ```bash
   tonietoolbox --config-integration --show
   ```

3. **Test manually**:
   ```bash
   tonietoolbox test-file.mp3 --debug
   ```

### Performance Issues

**Large File Sets**:
- Configure batch processing limits
- Use background processing mode
- Enable progress notifications

**Network Uploads**:
- Check TeddyCloud server connectivity
- Configure appropriate timeouts
- Use retry mechanisms

## Security Considerations

### File Permissions

Integration respects system security:
- **No elevated privileges** required for installation
- **User-space only** registry/file modifications
- **Sandboxed execution** where supported

### Network Security

TeddyCloud integration:
- **HTTPS enforcement** when possible
- **Certificate validation** (can be disabled for self-signed)
- **Credential storage** in user profile only

### Privacy

Desktop integration:
- **No telemetry** or usage tracking
- **Local processing** only
- **Optional cloud uploads** with explicit user action

## Uninstallation

Remove desktop integration:

```bash
# Remove all integration
tonietoolbox --uninstall-integration

# Remove specific components (Windows)
tonietoolbox --uninstall-integration --component registry

# Remove specific components (Linux)  
tonietoolbox --uninstall-integration --component kde
tonietoolbox --uninstall-integration --component gnome
```

**Manual Removal**:

**Windows**:
```cmd
# Remove registry entries
reg delete "HKCU\Software\Classes\*\shell\TonieToolbox" /f
reg delete "HKCU\Software\Classes\Directory\shell\TonieToolbox" /f
```

**Linux**:
```bash
# Remove KDE service files
rm ~/.local/share/kservices5/tonietoolbox-*.desktop

# Remove GNOME scripts
rm ~/.local/share/nautilus/scripts/TonieToolbox*

# Update caches
kbuildsycoca5  # KDE
```

## Advanced Integration

### Custom Actions

Create specialized context menu entries:

```bash
# High-quality music conversion
tonietoolbox --config-integration --action music-hq
# Command: tonietoolbox %F --bitrate 192 --cbr --use-media-tags

# Quick audiobook processing
tonietoolbox --config-integration --action audiobook-quick
# Command: tonietoolbox %F --bitrate 64 --recursive --upload https://teddycloud.local
```

### Workflow Integration

Integrate with existing workflows:

**Photo Management**:
- Add TonieToolbox to photo management software
- Process audio files alongside photo organization
- Batch process vacation recordings

**Media Centers**:
- Integrate with Plex, Jellyfin, etc.
- Auto-convert new audio content
- Organize by media center categories

### API Integration

For developers - programmatic access:

```python
import subprocess

def convert_with_integration(file_path, options=None):
    """Use TonieToolbox integration programmatically."""
    cmd = ['tonietoolbox', file_path]
    if options:
        cmd.extend(options)
    
    return subprocess.run(cmd, capture_output=True, text=True)
```

Desktop integration makes TonieToolbox accessible to all users, regardless of technical expertise. The right-click conversion workflow eliminates the need to remember command-line options and provides immediate access to TonieToolbox's powerful features.

## Next Steps

- 🎨 **[GUI Guide](../getting-started/gui-guide.md)** - Learn about the graphical interface
- 🏷️ **[Media Tags](media-tags.md)** - Use metadata for intelligent naming
- ☁️ **[TeddyCloud Integration](teddycloud.md)** - Set up server uploads
- 🔧 **[Configuration Reference](../reference/configuration.md)** - Advanced settings