# Media Tags Usage Guide

Learn how to use audio metadata (tags) to create intelligent file naming and organization with TonieToolbox.

## What are Media Tags?

Media tags are metadata embedded in audio files that contain information about:

- **Artist** and **Album Artist**
- **Album** and **Track Title**  
- **Genre** and **Year/Date**
- **Track Number** and **Disc Number**
- **Duration** and **Bitrate**
- **Cover Artwork** (embedded images)

TonieToolbox can read these tags and use them for smart file naming and organization.

## Viewing Available Tags

Before creating templates, see what tags are available in your files:

```bash
# Show all available media tags
tonietoolbox --show-media-tags input.mp3

# Example output:
# Available tags in 'input.mp3':
# - title: My Favorite Song
# - artist: Great Artist  
# - albumartist: Great Artist
# - album: Awesome Album
# - date: 2023
# - genre: Pop
# - tracknumber: 5
# - discnumber: 1
```

## Basic Media Tag Usage

### Enable Media Tag Processing

```bash
# Use default naming template
tonietoolbox input.mp3 --use-media-tags

# This creates: "My Favorite Song - Great Artist.taf"
```

### Custom Naming Templates

Create your own naming patterns:

```bash
# Artist - Title format
tonietoolbox input.mp3 --use-media-tags --name-template "{artist} - {title}"

# Album format  
tonietoolbox input.mp3 --use-media-tags --name-template "{album}"

# Detailed format with year
tonietoolbox input.mp3 --use-media-tags --name-template "{year} - {albumartist} - {album} - {title}"
```

## Template Syntax

### Basic Placeholders

Use curly braces `{}` to insert tag values:

| Tag | Description | Example |
|-----|-------------|---------|
| `{title}` | Track title | "My Favorite Song" |
| `{artist}` | Track artist | "Great Artist" |
| `{albumartist}` | Album artist | "Great Artist" |
| `{album}` | Album name | "Awesome Album" |
| `{date}` or `{year}` | Release year | "2023" |
| `{genre}` | Music genre | "Pop" |
| `{tracknumber}` | Track number | "05" |
| `{discnumber}` | Disc number | "1" |

### Default Values

Provide fallback values for missing tags:

```bash
# Use "Unknown" if title is missing
tonietoolbox input.mp3 --use-media-tags --name-template "{title:-Unknown}"

# Multiple fallbacks
tonietoolbox input.mp3 --use-media-tags --name-template "{albumartist:-{artist:-Unknown Artist}}"
```

### Formatting Options

Format numbers with padding:

```bash
# Zero-padded track numbers
tonietoolbox input.mp3 --use-media-tags --name-template "{tracknumber:02d} - {title}"
# Results in: "05 - My Favorite Song"

# Date formatting
tonietoolbox input.mp3 --use-media-tags --name-template "({date}) {album}"
```

## Directory Organization

### Output Path Templates

Create organized directory structures:

```bash
# Organize by artist and album
tonietoolbox input.mp3 \
  --use-media-tags \
  --output-to-template "{albumartist}/{album}"

# Results in: output/Great Artist/Awesome Album/filename.taf
```

### Complex Directory Structures

When using `--recursive`, TonieToolbox combines all audio files in each folder into a single TAF file. The first file's metadata is used for template placeholders:

```bash
# Music library organization (one TAF per album folder)
tonietoolbox --recursive music-collection/ \
  --use-media-tags \
  --output-to-template "Music/{genre}/{albumartist}/{year} - {album}"

# Example:
# music-collection/Artist/Album/*.mp3 → Music/Rock/Artist/2023 - Album/Album.taf

# Audiobook organization (one TAF per audiobook folder)
tonietoolbox --recursive audiobooks/ \
  --use-media-tags \
  --name-template "{album}" \
  --output-to-template "Audiobooks/{albumartist}/{album}"

# Example:
# audiobooks/Author/BookTitle/*.mp3 → Audiobooks/Author/BookTitle/BookTitle.taf
```

**Note**: To process each file individually instead of combining, add `--files-to-taf`:
```bash
tonietoolbox --recursive --files-to-taf --use-media-tags music/
```

## Batch Processing with Tags

### Processing Music Collections

```bash
# Process entire music library (one TAF per album)
tonietoolbox --recursive \
  --use-media-tags \
  --name-template "{albumartist} - {album}" \
  --output-to-template "Music/{genre}/{albumartist}/{year} - {album}" \
  --bitrate 128 \
  music-library/
```

### Audiobook Processing

```bash
# Organize audiobooks by author and series (one TAF per book)
tonietoolbox --recursive \
  --use-media-tags \
  --name-template "{album} - {title}" \
  --output-to-template "Audiobooks/{albumartist}/{album}" \
  --bitrate 96 \
  audiobook-collection/
```

## Advanced Tag Usage

### Conditional Templates

Use tags conditionally:

```bash
# Include year only if available
tonietoolbox input.mp3 --use-media-tags \
  --name-template "{albumartist} - {album}{date: ({date})}"

# Results in either:
# "Great Artist - Awesome Album (2023)"  # if date available
# "Great Artist - Awesome Album"         # if date missing
```

### Tag Cleaning and Normalization

```bash
# Remove special characters (handled automatically)
tonietoolbox "track with / slash.mp3" --use-media-tags
# Creates safe filename: "track with - slash.taf"
```

## TeddyCloud Integration with Tags

### Smart Upload Paths

```bash
# Upload with tag-based organization
tonietoolbox audiobook.mp3 \
  --use-media-tags \
  --upload https://teddycloud.local \
  --path "/{genre}/{albumartist}" \
  --include-artwork
```

### Custom JSON with Metadata

```bash
# Create TeddyCloud entries with rich metadata
tonietoolbox album/ \
  --use-media-tags \
  --upload https://teddycloud.local \
  --create-custom-json \
  --version-2
```

## Supported Tag Formats

TonieToolbox reads tags from various formats:

### ID3 Tags (MP3)
- **ID3v1**: Basic tag support
- **ID3v2.3/2.4**: Full tag support including artwork

### Vorbis Comments (FLAC, OGG)
- **FLAC**: Native Vorbis comment support
- **OGG Vorbis**: Full metadata support

### Other Formats
- **MP4/M4A**: iTunes-style tags
- **WAV**: Various tag formats
- **APE**: APEv2 tags

## Tag Quality Guidelines

### Best Practices for Source Files

1. **Consistent Formatting**:
   ```
   Artist: "The Beatles"
   Album Artist: "The Beatles" 
   Album: "Abbey Road"
   Title: "Come Together"
   Date: "1969"
   ```

2. **Avoid Special Characters**:
   - Use standard punctuation
   - Avoid filesystem-reserved characters (`/`, `\`, `?`, etc.)
   - TonieToolbox automatically sanitizes filenames

3. **Complete Information**:
   - Include all relevant tags
   - Use consistent artist names across albums
   - Add release years for better organization

### Fixing Poor Tags

Use audio tagging software to improve metadata:

- **MusicBrainz Picard**: Automatic tag lookup and correction
- **Mp3tag**: Windows tag editor
- **Kid3**: Cross-platform tag editor
- **Beets**: Command-line music library management

## Common Template Examples

### Music Collections

```bash
# Classic album format
--name-template "{albumartist} - {album}"

# Track listing format  
--name-template "{albumartist} - {album} - {tracknumber:02d} - {title}"

# Compilation format
--name-template "{album} - {artist} - {title}"

# Year-focused format
--name-template "({date}) {albumartist} - {album}"
```

### Audiobooks

```bash
# Series format
--name-template "{albumartist} - {album} - Book {discnumber}"

# Chapter format
--name-template "{album} - Chapter {tracknumber:02d} - {title}"

# Simple format
--name-template "{albumartist} - {album}"
```

### Podcasts

```bash
# Episode format
--name-template "{album} - Episode {tracknumber} - {title}"

# Date format (if date is episode date)
--name-template "{album} - {date} - {title}"

# Simple format
--name-template "{album} - {title}"
```

## Troubleshooting Tag Issues

### Missing Tags

```bash
# Check what tags are available
tonietoolbox --show-media-tags problematic-file.mp3

# Use fallback values
tonietoolbox problematic-file.mp3 --use-media-tags \
  --name-template "{title:-{filename}}"
```

### Character Encoding Issues

```bash
# TonieToolbox handles encoding automatically
# But you can debug with:
tonietoolbox --debug --show-media-tags file-with-special-chars.mp3
```

### Inconsistent Tags

```bash
# Use albumartist for consistency
tonietoolbox *.mp3 --use-media-tags \
  --name-template "{albumartist:-{artist}} - {album}"
```

## Integration Examples

### Shell Scripts with Tags

```bash
#!/bin/bash
# Organize music by decade

for file in *.mp3; do
    year=$(tonietoolbox --show-media-tags "$file" | grep "date:" | cut -d: -f2 | xargs)
    decade=$((${year:-0} / 10 * 10))
    
    tonietoolbox "$file" --use-media-tags \
      --output-to-template "Music/${decade}s/{albumartist}/{album}"
done
```

### Automated Organization

```python
#!/usr/bin/env python3
import subprocess
import os

def organize_by_genre(music_dir):
    """Organize music by genre using TonieToolbox tags."""
    for root, dirs, files in os.walk(music_dir):
        for file in files:
            if file.endswith('.mp3'):
                filepath = os.path.join(root, file)
                
                cmd = [
                    'tonietoolbox', filepath,
                    '--use-media-tags',
                    '--output-to-template', '{genre}/{albumartist}/{album}',
                    '--name-template', '{albumartist} - {album}'
                ]
                
                subprocess.run(cmd)

organize_by_genre('/path/to/music')
```

Media tags provide powerful ways to organize and name your audio content intelligently. By leveraging the metadata already in your files, TonieToolbox can create consistent, organized collections that are easy to navigate and maintain.

## Next Steps

- ☁️ **[TeddyCloud Integration](teddycloud.md)** - Upload with tag-based paths  
- 📚 **[Real-World Examples](../examples/use-cases.md)** - See tag usage in practice
- 🛠️ **[Configuration Guide](../reference/configuration.md)** - Save tag templates as defaults