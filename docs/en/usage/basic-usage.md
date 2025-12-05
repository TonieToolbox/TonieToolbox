# Basic Usage

This guide covers all the fundamental ways to use TonieToolbox for converting audio files to Tonie-compatible TAF format.

## Command Structure

The basic TonieToolbox command follows this pattern:

```bash
tonietoolbox [OPTIONS] SOURCE [TARGET]
```

- **SOURCE**: Input file, directory, or playlist file (.lst)
- **TARGET**: Output file name (optional)
- **OPTIONS**: Various flags to control behavior

## Simple Conversions

### Single File Conversion

Convert one audio file to TAF format:

```bash
# Basic conversion (creates output/input.taf)
tonietoolbox input.mp3

# Custom output name
tonietoolbox input.mp3 my-tonie.taf

# Specify full paths
tonietoolbox /path/to/input.mp3 /path/to/output.taf
```

### Multiple Files in a Directory

Convert all audio files in a directory:

```bash
# Convert all files in a directory
tonietoolbox audio-folder/

# This creates: output/audio-folder.taf
```

### Playlist Files (.lst)

Create a text file with audio file paths for custom ordering:

```text
# Contents of playlist.lst
/path/to/track1.mp3
/path/to/track2.flac
/path/to/track3.wav
"C:\Path With Spaces\track4.mp3"
```

Then convert:

```bash
tonietoolbox playlist.lst my-album.taf
```

## Recursive Processing

Process entire directory structures with two modes:

### Combine Mode (Default)

Combines all audio files in each folder into a single TAF file per folder:

```bash
# Process all subdirectories, one TAF per folder
tonietoolbox --recursive /path/to/music/

# Example structure:
# music/
#   Artist1/Album1/*.mp3  → output/Album1.taf (combined)
#   Artist2/Album2/*.flac → output/Album2.taf (combined)
```

### Individual Mode (--files-to-taf)

Process each audio file individually:

```bash
# Convert every file to its own TAF
tonietoolbox --recursive --files-to-taf /path/to/music/

# Example structure:
# music/
#   Artist1/Album1/track1.mp3 → output/track1.taf
#   Artist1/Album1/track2.mp3 → output/track2.taf
```

### Depth Control

Limit how deep the recursion goes:

```bash
# Only process immediate subdirectories
tonietoolbox --recursive --max-depth 1 /path/to/music/

# Process up to 2 levels deep
tonietoolbox --recursive --max-depth 2 /path/to/music/
```

### Parallel Processing

Significantly speed up recursive processing by processing multiple folders simultaneously:

```bash
# Use 4 parallel workers (recommended for most systems)
tonietoolbox --recursive --workers 4 /path/to/music/

# Use 8 workers for faster processing (high-end systems)
tonietoolbox --recursive --workers 8 /path/to/music/

# Combine with other options
tonietoolbox --recursive --workers 4 --max-depth 2 /path/to/music/
```

!!! tip "Performance Recommendations"
    - **Default**: 1 worker (sequential processing)
    - **Recommended**: 4 workers for most systems
    - **High-end systems**: 6-8 workers
    - **Example**: Processing 10 folders @ 30s each:
        - Sequential: ~300 seconds (5 minutes)
        - 4 workers: ~75 seconds (1.25 minutes) - **4x faster!**
    
!!! warning "Resource Usage"
    Each worker runs FFmpeg simultaneously, which consumes CPU and RAM. Adjust the worker count based on your system's capabilities.

### Advanced Options

```bash
# Save TAF files in source directories instead of output/
tonietoolbox --recursive --output-to-source /path/to/music/

# Force creation even if TAF files already exist
tonietoolbox --recursive --force-creation /path/to/music/
```

## Quality and Encoding Options

### Bitrate Control

```bash
# Set custom bitrate (default: 128 kbps)
tonietoolbox input.mp3 --bitrate 192

# Use constant bitrate (CBR) instead of variable (VBR)
tonietoolbox input.mp3 --bitrate 96 --cbr

# Higher quality for music
tonietoolbox music.flac --bitrate 192
```

### Audio Processing

```bash
# Disable mono to stereo conversion
tonietoolbox input.mp3 --no-mono-conversion

# Keep temporary files for debugging
tonietoolbox input.mp3 --keep-temp
```

## File Analysis and Debugging

### Analyze TAF Files

```bash
# Display detailed information about a TAF file
tonietoolbox --info my-tonie.taf

# Split TAF file back into individual opus tracks
tonietoolbox --split my-tonie.taf

# Extract complete OGG audio stream
tonietoolbox --extract my-tonie.taf
# Creates: my-tonie.ogg (playable with any audio player)
```

### Compare and Verify TAF Files

```bash
# Basic comparison of two TAF files
tonietoolbox file1.taf --compare file2.taf

# Detailed comparison with byte-level content verification
tonietoolbox file1.taf --detailed-compare file2.taf

# Shorthand for detailed comparison
tonietoolbox file1.taf -D file2.taf
```

**Comparison features:**
- ✅ TAF headers and metadata
- ✅ Chapter information and timing
- ✅ Audio properties (bitrate, duration, channels)
- ✅ Content integrity (SHA256 hash verification)

**Detailed mode adds:**
- 🔍 Full OGG stream analysis
- 🔬 Byte-level content comparison
- 📊 Encoder settings and comments

## Output Control

### Directory Management

```bash
# Save in source directory instead of output/
tonietoolbox input.mp3 --output-to-source

# Force creation even if file exists
tonietoolbox input.mp3 --force-creation

# Custom output directory (set via configuration)
tonietoolbox input.mp3  # Uses configured output directory
```

### File Naming

```bash
# Append hex tag to filename
tonietoolbox input.mp3 --append-tonie-tag 7F8A6B2E
# Creates: output/input-7F8A6B2E.taf

# Create without Tonie header (advanced)
tonietoolbox input.mp3 --no-tonie-header
```

## Dependency Management

### Automatic Downloads

```bash
# Download FFmpeg and opus-tools if missing
tonietoolbox input.mp3 --auto-download

# Specify custom tool locations
tonietoolbox input.mp3 --ffmpeg /path/to/ffmpeg --opusenc /path/to/opusenc
```

## Timestamps and Headers

### Custom Timestamps

```bash
# UNIX timestamp
tonietoolbox input.mp3 --timestamp 1745078762

# Hexadecimal bitstream time
tonietoolbox input.mp3 --timestamp 0x6803C9EA

# Extract timestamp from reference TAF file
tonietoolbox input.mp3 --timestamp reference.taf
```

## Logging and Debug Options

### Logging Levels

```bash
# Enable debug logging
tonietoolbox input.mp3 --debug

# Very verbose trace logging
tonietoolbox input.mp3 --trace

# Quiet mode (warnings and errors only)
tonietoolbox input.mp3 --quiet

# Silent mode (errors only)
tonietoolbox input.mp3 --silent

# Save logs to timestamped file
tonietoolbox input.mp3 --log-file
```

## Supported Input Formats

TonieToolbox supports any audio format that FFmpeg can handle:

### Common Formats
- **MP3** - Most common format
- **FLAC** - Lossless compression
- **WAV** - Uncompressed audio
- **OGG** - Open source format
- **M4A/AAC** - Apple/iTunes format
- **WMA** - Windows Media Audio

### Less Common Formats
- **AIFF** - Audio Interchange File Format
- **AU** - Sun/NeXT audio format
- **AMR** - Adaptive Multi-Rate codec
- **APE** - Monkey's Audio lossless
- **And many more...**

## Output Information

Understanding TonieToolbox output:

```bash
tonietoolbox input.mp3
```

```text
🎵 TonieToolbox v1.0.0a1
📁 Processing: input.mp3
🔄 Converting to opus format...
📦 Creating TAF file with Tonie headers...
✅ Success: output/input.taf
   📊 Size: 5.1 MB | Duration: 5:23 | Bitrate: 128 kbps
⏱️  Completed in 12.3 seconds
```

This shows:
- **Input file** being processed
- **Conversion steps** performed
- **Output location** and file details
- **Performance metrics**

## Common Patterns

### Audiobook Processing

```bash
# Convert chapter files in order
tonietoolbox chapter-*.mp3 audiobook.taf

# Or use a playlist for custom ordering
tonietoolbox audiobook-chapters.lst "My Audiobook.taf"
```

### Music Album Processing

```bash
# Convert entire album folder
tonietoolbox "Album Name/" "Artist - Album.taf"

# Process with higher quality
tonietoolbox "Album Name/" --bitrate 128 "Artist - Album.taf"
```

### Bulk Processing

```bash
# Process multiple album directories
tonietoolbox --recursive --output-to-source music-collection/

# With custom quality settings
tonietoolbox --recursive --bitrate 128 --cbr music-collection/
```

## Error Handling

TonieToolbox provides clear error messages:

```bash
# Missing file
tonietoolbox nonexistent.mp3
# Error: File 'nonexistent.mp3' not found

# Invalid format
tonietoolbox document.txt
# Error: Unsupported audio format for 'document.txt'

# Permission issues
tonietoolbox /protected/file.mp3
# Error: Permission denied reading '/protected/file.mp3'
```

## Performance Tips

### Optimize Conversion Speed

- **Use SSD storage** for input and output directories
- **Close unnecessary applications** during batch processing
- **Use appropriate bitrates** - higher bitrates take longer to encode
- **Process smaller batches** for better responsiveness

### Manage Disk Space

- **Monitor output directory** size during batch operations
- **Use lower bitrates** for spoken content to save space
- **Clean up temporary files** if using `--keep-temp`

## Integration with Other Tools

### Shell Scripts

```bash
#!/bin/bash
# Convert all MP3 files in current directory
for file in *.mp3; do
    tonietoolbox "$file" --bitrate 128
done
```

### Batch Files (Windows)

```batch
@echo off
REM Convert all files in Music folder
tonietoolbox --recursive "C:\Music" --bitrate 96
```

## Next Steps

Now that you understand basic usage:

- 🏷️ **[Learn Media Tags](media-tags.md)** - Use metadata for smart naming
- ☁️ **[Set Up TeddyCloud](teddycloud.md)** - Upload files automatically
- 🖥️ **[Desktop Integration](desktop-integration.md)** - Right-click conversion
- 🐳 **[Docker Usage](../docker.md)** - Containerized processing
- 📚 **[See Examples](../examples/use-cases.md)** - Real-world scenarios