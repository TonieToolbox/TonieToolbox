# Quick Start Guide

Get up and running with TonieToolbox in just a few minutes! This guide will walk you through your first audio conversion.

## Choose Your Method

TonieToolbox offers two main interfaces:

=== "⌨️ Command Line (Conversion)"
    
    Perfect for converting audio files to TAF format:
    
    ```bash
    # Convert a single file
    tonietoolbox input.mp3
    
    # Convert with custom output name
    tonietoolbox input.mp3 my_tonie.taf
    
    # Convert entire folder
    tonietoolbox /path/to/audio/folder/
    ```
    
    [:octicons-arrow-right-24: Learn more about CLI options](../usage/basic-usage.md)

=== "🎨 GUI Mode (TAF Player)"
    
    The graphical interface is a TAF file player with plugin support:
    
    1. **Launch the GUI**:
       ```bash
       tonietoolbox --gui
       ```
    
    2. **Load TAF files**: Drag and drop TAF files to play them
    3. **Navigate chapters**: Jump to specific parts of your audiobooks
    4. **Manage playlists**: Queue multiple TAF files
    
    !!! note "GUI Conversion Coming Soon"
        Audio conversion via GUI is planned for a future release. Currently, use the command line for conversion.
    
    [:octicons-arrow-right-24: Learn more about GUI player](gui-guide.md)

## Your First Conversion

Let's convert your first audio file step by step:

### Step 1: Prepare Your Audio File

Make sure you have an audio file ready. TonieToolbox supports:

- **MP3** files
- **FLAC** files  
- **WAV** files
- **OGG** files
- **M4A/AAC** files
- And many more formats supported by FFmpeg!

### Step 2: Convert the File

#### Using Command Line

1. **Navigate to your audio file's directory**:
   ```bash
   cd /path/to/your/audio/files
   ```

2. **Run the conversion**:
   ```bash
   tonietoolbox your-audio-file.mp3
   ```

3. **Check the output**:
   ```bash
   ls output/
   # You should see: your-audio-file.taf
   ```

### Step 3: Play the Result (Optional)

You can play your converted TAF file in the GUI player:

```bash
# Launch GUI and load your TAF file
tonietoolbox --gui
# Then drag and drop the TAF file to play it
```

Or analyze the file details:

```bash
# Analyze the created TAF file
tonietoolbox --info output/your-audio-file.taf
```

This will display information about the converted file including:
- File size and duration
- Audio codec details
- Tonie header information

## Common First-Time Scenarios

### Converting an Audiobook

If you have multiple chapter files that should be combined:

```bash
# Put all chapter files in a folder
tonietoolbox audiobook-chapters/ audiobook.taf
```

### Converting with Better Quality

For higher quality audio (larger file size):

```bash
tonietoolbox input.mp3 --bitrate 128
```

### Converting Multiple Albums

Process an entire music collection:

```bash
tonietoolbox --recursive /path/to/music/collection/
```

## What Happens During Conversion?

Understanding the conversion process:

1. **Input Analysis**: TonieToolbox examines your audio file
2. **Format Conversion**: Audio is converted to Opus format if needed
3. **TAF Creation**: The Tonie Audio Format file is created with proper headers
4. **Verification**: The output file is validated
5. **Output**: Your TAF file is saved to the output directory

## Quick Tips for Success

!!! tip "Pro Tips"
    
    - **Use descriptive names**: `tonietoolbox input.mp3 "My Favorite Songs.taf"`
    - **Check file sizes**: Tonie boxes have storage limits
    - **Use appropriate bitrates**: 64-96 kbps is usually sufficient for spoken content
    - **Organize your files**: Use folders to keep your conversions organized

!!! warning "Common Mistakes"
    
    - Don't use extremely high bitrates (>256 kbps) unless necessary
    - Ensure your input files aren't corrupted
    - Check that you have enough disk space for the output

## Next Steps

Now that you've completed your first conversion:

- 🎨 **[Explore GUI Features](gui-guide.md)** - Learn about the full graphical interface
- 📚 **[Advanced Usage](../usage/basic-usage.md)** - Discover more conversion options
- ☁️ **[TeddyCloud Integration](../usage/teddycloud.md)** - Upload directly to your TeddyCloud server
- 🏷️ **[Media Tags](../usage/media-tags.md)** - Use metadata for smarter file organization

## Need Help?

If something didn't work as expected:

- 📖 Check the [Troubleshooting Guide](../examples/troubleshooting.md)
- 💬 Ask in [GitHub Discussions](https://github.com/TonieToolbox/TonieToolbox/discussions)
- 🐛 Report bugs in [GitHub Issues](https://github.com/TonieToolbox/TonieToolbox/issues)

Congratulations on your first TonieToolbox conversion! 🎉