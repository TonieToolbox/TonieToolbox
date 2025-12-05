# Frequently Asked Questions

Common questions and answers about TonieToolbox usage, features, and troubleshooting.

## General Questions

### What is TonieToolbox?

TonieToolbox is a comprehensive audio toolkit that converts various audio formats (MP3, FLAC, M4A, etc.) to the TAF (Tonie Audio Format) used by Toniebox devices. It provides command-line conversion tools and a GUI-based TAF player with plugin support.

### What audio formats are supported?

**Input formats supported**:
- MP3 (MPEG Audio Layer III)
- FLAC (Free Lossless Audio Codec)
- M4A/AAC (Advanced Audio Coding)
- OGG Vorbis
- WAV (Uncompressed)
- WMA (Windows Media Audio) - limited support

**Output format**:
- TAF (Tonie Audio Format) - optimized for Toniebox playback

### Is TonieToolbox free?

Yes, TonieToolbox is completely free and open-source software licensed under GPL v3. You can use, modify, and distribute it freely according to the license terms.

### Do I need technical knowledge to use TonieToolbox?

No! TonieToolbox offers multiple interfaces:
- **Command Line**: Convert audio files to TAF format (straightforward commands)
- **GUI Mode** (`--gui`): TAF file player with chapter navigation and playlists
- **Desktop Integration**: Right-click context menu integration

!!! note "GUI Conversion Coming Soon"
    Currently, audio conversion is done via command line. A GUI-based conversion interface is planned for a future release.

Choose the method that matches your comfort level.

## Installation Questions

### What are the system requirements?

**Minimum requirements for v1.0.0a1**:
- Python 3.12 or newer (3.14 recommended)
- 100MB available disk space
- Internet connection (for initial installation)
- PyQt6 6.10.0+ (for GUI features)

**Supported platforms**:
- Windows 10/11 (x64)
- Linux (Ubuntu 20.04+, Debian 11+, CentOS 9+)
- macOS 11+ (Big Sur and newer)

### How do I install TonieToolbox?

**Quick installation**:
```bash
pip install tonietoolbox
```

**Alternative methods**:
- **Docker**: `docker pull quentendo64/tonietoolbox`
- **From source**: Download and run `pip install .`
- **pipx** (recommended): `pipx install tonietoolbox`

See our [Installation Guide](../getting-started/installation.md) for detailed instructions.

### Can I use TonieToolbox without installing Python?

Yes! Docker containers provide an isolated environment without needing Python installed on your system:

```bash
docker pull quentendo64/tonietoolbox
docker run -v $(pwd):/data quentendo64/tonietoolbox input.mp3
```

See the [Docker Guide](docker.md) for complete instructions.

### Why do I get "command not found" errors?

This usually means:
1. **TonieToolbox not installed**: Run `pip install tonietoolbox`
2. **PATH not configured**: Add Python scripts directory to PATH
3. **Wrong Python version**: Ensure Python 3.12+ for v1.0.0a1

**Quick fix**:
```bash
python -m TonieToolbox input.mp3  # Use module syntax
```

## Usage Questions

### How do I convert a single audio file?

**GUI method**:
1. Run `tonietoolbox --gui`
2. Click "Select Files" and choose your audio file
3. Click "Convert"

**Command line**:
```bash
tonietoolbox audiobook.mp3
```

The TAF file will be created in the same directory by default.

### How do I convert entire folders?

**Recursive conversion**:
```bash
tonietoolbox ./audiobooks/ --recursive
```

**With custom output directory**:
```bash
tonietoolbox ./audiobooks/ --recursive --output ./converted/
```

### What's the best bitrate for audiobooks vs music?

**Recommended bitrates**:
- **Audiobooks**: 32-64 kbps (speech content)
- **Podcasts**: 64-96 kbps (good quality speech)  
- **Music**: 96-192 kbps (depending on quality needs)
- **High-quality music**: 192+ kbps (near-CD quality)

**Example usage**:
```bash
tonietoolbox audiobook.mp3 --bitrate 64    # Audiobook
tonietoolbox music.flac --bitrate 128      # Music
```

### How do I use metadata for file naming?

Enable metadata-based naming:
```bash
tonietoolbox album/ --use-media-tags --name-template "{artist}/{album}/{track:02d} - {title}"
```

This creates organized folder structures like:
```
Artist Name/
  Album Name/
    01 - Song Title.taf
    02 - Another Song.taf
```

### Can I upload files directly to TeddyCloud?

Yes! Configure TeddyCloud integration:

**One-time setup**:
```bash
tonietoolbox --config-integration
# Enter your TeddyCloud server details
```

**Convert and upload**:
```bash
tonietoolbox audiobook.mp3 --upload
```

See [TeddyCloud Integration](../usage/teddycloud.md) for detailed setup.

## Technical Questions

### What is the TAF format?

TAF (Tonie Audio Format) is a proprietary audio format used by Toniebox devices. It's essentially:
- **Container**: Similar to MP3/OGG containers
- **Audio codec**: Modified Opus codec optimized for speech/music
- **Metadata**: Embedded playback information
- **Compression**: Efficient for the Toniebox's hardware

### Why are my TAF files larger than expected?

Several factors affect TAF file size:
1. **Bitrate setting**: Higher bitrate = larger files
2. **Content type**: Music requires higher bitrates than speech
3. **Source quality**: High-quality sources need more bits
4. **Encoding mode**: CBR creates predictable but potentially larger files

**Optimization tips**:
```bash
# For audiobooks (smaller files, lower bitrate)
tonietoolbox audiobook.mp3 --bitrate 64

# For music (balanced quality/size)  
tonietoolbox music.flac --bitrate 96 --cbr
```

### Can I convert TAF files back to MP3?

No, TAF to MP3 conversion is not supported. This is intentional - TAF files are designed for Toniebox playback only. Keep your original audio files as backups.

### Does TonieToolbox modify my original files?

No! TonieToolbox never modifies your original audio files. It only creates new TAF files as output. Your source files remain completely unchanged.

## GUI Questions

### How do I access the graphical interface?

Launch the GUI with:
```bash
tonietoolbox --gui
```

Or through desktop integration (after setup):
- **Windows**: Start Menu → TonieToolbox
- **Linux**: Applications → TonieToolbox  
- **macOS**: Applications folder

### Can I process multiple files in the GUI?

Yes! The GUI supports:
- **Multiple file selection**: Ctrl+click or Shift+click
- **Folder processing**: Select entire directories
- **Drag and drop**: Drop files/folders into the window
- **Progress tracking**: Real-time conversion progress

### The GUI won't start - what's wrong?

Common issues:
1. **Missing GUI libraries**: Install with `pip install tonietoolbox[gui]`
2. **Display issues**: Try `export DISPLAY=:0` (Linux)
3. **Permission problems**: Run without sudo/admin rights

**Debug GUI startup**:
```bash
tonietoolbox --gui --debug
```

## TeddyCloud Questions

### What is TeddyCloud?

TeddyCloud is an open-source server that replaces the official Tonie cloud service. It allows you to:
- Host your own Tonie content
- Upload custom audio files
- Manage Toniebox devices locally
- Maintain privacy and control

### Do I need TeddyCloud to use TonieToolbox?

No! TonieToolbox works independently:
- **Without TeddyCloud**: Convert files for manual transfer
- **With TeddyCloud**: Direct upload and management
- **Hybrid approach**: Use both methods as needed

### How do I set up TeddyCloud integration?

**Quick setup**:
```bash
tonietoolbox --config-integration
```

Follow the prompts to enter:
- Server URL (e.g., `https://teddycloud.local:8443`)
- Username and password
- SSL verification settings

### My TeddyCloud uploads keep failing

**Common solutions**:
1. **Check server URL**: Ensure correct address and port
2. **Verify credentials**: Test login through web interface
3. **SSL issues**: Try `--no-ssl-verify` for self-signed certificates
4. **Network connectivity**: Test from same network
5. **Server status**: Check TeddyCloud server logs

**Debug upload issues**:
```bash
tonietoolbox file.taf --upload --debug
```

## Performance Questions

### Converting large files is slow - how can I speed it up?

**Optimization strategies**:
1. **Use SSD storage**: Faster disk I/O
2. **Increase memory**: More RAM helps with large files
3. **Parallel processing**: Convert multiple files simultaneously
4. **Lower bitrates**: Reduce processing complexity
5. **Temp directory**: Use fast storage for temp files

**Example optimization**:
```bash
# Use faster temp directory
export TONIETOOLBOX_TEMP=/fast/ssd/temp
tonietoolbox large-audiobook/ --recursive
```

### Can I convert multiple files simultaneously?

**Command line parallel processing**:
```bash
# Process multiple files in background
tonietoolbox file1.mp3 &
tonietoolbox file2.mp3 &
tonietoolbox file3.mp3 &
wait  # Wait for all to complete
```

**GUI automatic parallel processing**:
The GUI automatically processes multiple files in parallel when you select multiple files or folders.

### How much disk space do I need?

**Space requirements**:
- **Temporary space**: 2x the size of your largest input file
- **Output space**: Varies by bitrate and duration
- **Working space**: Additional 10-20% for processing overhead

**Example calculation**:
- 1-hour audiobook at 64 kbps = ~29MB TAF file
- 1-hour music at 128 kbps = ~58MB TAF file
- Processing requires ~2x input file size temporarily

## Error Messages

### "FFmpeg not found" errors

TonieToolbox requires FFmpeg for audio processing:

**Install FFmpeg**:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/)
- **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian)
- **macOS**: `brew install ffmpeg`

**Alternative**: Use Docker version (FFmpeg included)

### "Permission denied" errors

**Common causes**:
1. **File permissions**: Input files not readable
2. **Directory permissions**: Can't write to output directory  
3. **Admin rights**: Running with wrong privileges

**Solutions**:
```bash
# Fix file permissions
chmod 644 input.mp3
chmod 755 output-directory/

# Don't run as root/admin (usually not needed)
```

### "Unsupported format" errors

**Check file format**:
```bash
tonietoolbox --info input.file
```

**Convert to supported format first**:
```bash
ffmpeg -i unsupported.format supported.mp3
tonietoolbox supported.mp3
```

### Memory or disk space errors

**Check available space**:
```bash
df -h
```

**Use external temp directory**:
```bash
tonietoolbox --temp-dir /path/to/large/drive input.mp3
```

## Integration Questions

### How do I set up right-click conversion?

**Automatic setup**:
```bash
tonietoolbox --install-integration
```

This creates context menu entries in:
- **Windows**: Explorer right-click menu
- **Linux**: KDE/GNOME file manager integration
- **macOS**: Finder integration (coming soon)

### Can I customize the context menu options?

Yes! Configure integration settings:
```bash
tonietoolbox --config-integration
```

Customize:
- Menu text and icons
- Default conversion settings
- Multiple conversion profiles
- TeddyCloud upload options

### Integration not working after installation

**Windows troubleshooting**:
1. **Restart Explorer**: Kill and restart explorer.exe
2. **Check registry**: Verify entries in `regedit`
3. **Reinstall**: `tonietoolbox --uninstall-integration` then reinstall

**Linux troubleshooting**:
1. **Update cache**: Run `kbuildsycoca5` (KDE) or restart Nautilus (GNOME)
2. **Check files**: Verify service files exist
3. **Permissions**: Ensure scripts are executable

## Advanced Questions

### Can I create custom conversion profiles?

Not yet. Configuration profiles are planned for a future release. For now, use shell aliases or scripts:

```bash
# Create shell aliases (add to .bashrc or .zshrc)
alias tonie-audiobook='tonietoolbox --bitrate 64'
alias tonie-music='tonietoolbox --bitrate 128 --cbr --use-media-tags'

# Use aliases
tonie-audiobook input.mp3
tonie-music input.mp3
```

### How do I batch process with different settings?

**Custom scripting**:
```bash
#!/bin/bash
# Process different types with different settings
tonietoolbox audiobooks/ --bitrate 64 --recursive
tonietoolbox podcasts/ --bitrate 96 --recursive  
tonietoolbox music/ --bitrate 128 --recursive
```

### Can I integrate with automation tools?

Yes! TonieToolbox supports automation:

**Cron jobs** (scheduled conversion):
```bash
# Convert new files daily at 2 AM
0 2 * * * /usr/local/bin/tonietoolbox /watch/directory/ --recursive --upload
```

**File watchers** (automatic processing):
```bash
# Watch directory and convert new files
inotifywait -m -r -e create /watch/dir/ | while read dir action file; do
    if [[ "$file" == *.mp3 ]]; then
        tonietoolbox "$dir$file" --upload
    fi
done
```

### How do I contribute to TonieToolbox development?

We welcome contributions! Check out our [GitHub repository](https://github.com/TonieToolbox/TonieToolbox):
- Fork and create pull requests
- Report bugs and request features
- Improve documentation
- Help others in discussions
- Review and test changes

## Still Need Help?

Can't find the answer you're looking for?

- 📖 **[Documentation](../index.md)** - Browse full documentation
- 🔧 **[Troubleshooting](../examples/troubleshooting.md)** - Detailed problem-solving
- 🐛 **[GitHub Issues](https://github.com/TonieToolbox/TonieToolbox/issues)** - Report bugs or request features
- 💬 **[Discussions](https://github.com/TonieToolbox/TonieToolbox/discussions)** - Community support
- 📧 **Email**: [Support contact information]

---

*This FAQ is regularly updated based on common user questions. Last updated: January 2025*