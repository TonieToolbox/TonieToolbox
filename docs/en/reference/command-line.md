# Command Line Reference

Complete reference for all TonieToolbox command-line options and arguments based on the actual argument parser implementation.

## Synopsis

```bash
tonietoolbox [OPTIONS] [SOURCE] [TARGET]
```

## Positional Arguments

### SOURCE
Input file or directory for conversion (optional if using special commands):

- **Single file**: `input.mp3`
- **Directory**: `audio-folder/` (converts all audio files in directory)
- **Playlist file**: `playlist.lst` (text file with audio file paths, one per line)

### TARGET
Output file name (optional):

- If not specified, uses source name with `.taf` extension
- Saved in the output directory (default: `./output/`)
- Can include path: `/path/to/output.taf`

## General Options

### `-h, --help`
Show help message and exit.

### `-v, --version`
Display TonieToolbox version and exit.

**Example:**
```bash
tonietoolbox --version
```

## Processing Options

### `-f, --ffmpeg PATH`
Specify custom location of ffmpeg executable.

**Default**: Auto-detected from system PATH

**Example:**
```bash
tonietoolbox input.mp3 --ffmpeg /usr/local/bin/ffmpeg
```

### `-b, --bitrate BITRATE`
Set encoding bitrate in kbps for Opus & MP3 conversion.

**Default**: 128 kbps  
**Range**: 32-512 kbps recommended

**Examples:**
```bash
# High quality music
tonietoolbox music.mp3 --bitrate 192

# Audiobook (lower bitrate)
tonietoolbox audiobook.mp3 --bitrate 64
```

### `--cbr`
Encode in CBR (constant bitrate) mode instead of VBR.

**Default**: VBR (variable bitrate)

**When to use**: For predictable file sizes or compatibility with older players.

**Example:**
```bash
tonietoolbox input.mp3 --bitrate 128 --cbr
```

### `-A, --auto-download`
Automatically download ffmpeg if not found on the system.

**Example:**
```bash
tonietoolbox input.mp3 --auto-download
```

### `-M, --no-mono-conversion`
Do not convert mono audio to stereo.

**Default**: Mono audio is converted to stereo

**Example:**
```bash
tonietoolbox mono-file.mp3 --no-mono-conversion
```

## File Operations

### `-i, --info`
Check and display information about a TAF file.

**Example:**
```bash
tonietoolbox --info existing.taf
```

**Output includes:**
- File size and duration
- Audio codec details
- Tonie header information
- Bitstream serial / timestamp

### `-p, --play`
Play TAF file using TonieToolbox GUI Player with auto-play enabled.

**Example:**
```bash
tonietoolbox --play audiobook.taf
```

### `-g, --gui`
Launch the TonieToolbox GUI (TAF player interface).

**Example:**
```bash
tonietoolbox --gui
```

### `-s, --split`
Split TAF file into individual Opus audio tracks.

**Example:**
```bash
tonietoolbox --split audiobook.taf
```

**Output**: Separate Opus files for each chapter/track

### `-e, --extract`
Extract the entire OGG/Opus stream from a TAF file.

Extracts the complete audio content (without Tonie headers) as a single OGG file that can be played with standard audio players.

**Example:**
```bash
tonietoolbox --extract audiobook.taf
```

**Output**: `audiobook.ogg` - Complete OGG/Opus audio file

**Use cases:**
- Create backup of audio content
- Play TAF files on non-Tonie devices
- Analyze audio quality with standard tools
- Convert to other formats using ffmpeg

### `-c, --compare FILE2`
Compare two TAF files for debugging and verification.

Compares TAF headers, chapter information, and audio properties between two files. Useful for verifying conversions or debugging issues.

**Example:**
```bash
tonietoolbox file1.taf --compare file2.taf
```

**Comparison includes:**
- SHA1 hash of audio content
- Valid flag and timestamp
- Number of chapters and chapter details
- Opus stream properties (sample rate, channels)
- Audio analysis (duration, bitrate, page count)
- Alignment validation

### `-D, --detailed-compare [FILE2]`
Show detailed OGG page differences when comparing TAF files.

Performs an in-depth comparison including:
- All standard comparison data from `--compare`
- Extracted OGG stream analysis via FFprobe
- **Byte-level content comparison** using SHA256 hashes
- Opus comments and encoder settings
- Full codec details

**Usage 1: With --compare flag**
```bash
tonietoolbox file1.taf --compare file2.taf --detailed-compare
```

**Usage 2: Shorthand syntax**
```bash
tonietoolbox file1.taf --detailed-compare file2.taf
```

**Detailed comparison output includes:**

🔍 **Extracted OGG Analysis:**
- Stream duration and codec
- Bitrate and sample rate  
- Channel configuration

🔬 **OGG Content Comparison:**
- File sizes (in bytes and MB)
- **Full SHA256 hash** for both files
- Content match indicator (IDENTICAL or DIFFERENT)

**Example output:**
```
🔬 OGG Content Comparison
  ⚠ │   File Size      │ 45,637,632 bytes (43.52 MB)  │ 47,951,872 bytes (45.73 MB)
  ⚠ │   SHA256 Hash    │ ec462f67cb3fef2313d4ee98...  │ 8e4e100925ecebce85920d5e...
  ⚠ │   Content Match  │ ⚠ DIFFERENT                  │ ⚠ DIFFERENT
```

**Use cases:**
- Verify bit-perfect audio content
- Debug encoding issues
- Compare different encoder settings
- Validate file integrity after transfer

### `-r, --recursive`
Process folders recursively, combining all audio files in each folder into a single TAF file per folder.

**Default Behavior (Combine Mode):**
```bash
# Combines all files in each folder into one TAF per folder
tonietoolbox --recursive music-collection/

# Example structure:
# music-collection/
#   Artist1/Album1/*.mp3  → output/Album1.taf
#   Artist2/Album2/*.flac → output/Album2.taf
```

**With --files-to-taf (Individual Mode):**
```bash
# Process each file individually
tonietoolbox --recursive --files-to-taf music-collection/

# Example structure:
# music-collection/
#   Artist1/Album1/track1.mp3  → output/track1.taf
#   Artist1/Album1/track2.mp3  → output/track2.taf
```

**With Templates:**
Recursive mode supports `--name-template` and `--output-to-template` using metadata from the first audio file in each folder:

```bash
tonietoolbox --recursive \
  --use-media-tags \
  --name-template "{albumartist} - {album}" \
  --output-to-template "Music/{genre}/{albumartist}" \
  music-collection/
```

### `--max-depth N`
Limit recursive processing to N levels of subdirectories (requires `--recursive`).

**Examples:**
```bash
# Process only top-level folders
tonietoolbox --recursive --max-depth 1 music/

# Process up to 2 levels deep
tonietoolbox --recursive --max-depth 2 music/
```

**Default**: Unlimited depth (processes all subdirectories)

### `-w, --workers N`
Use N parallel workers for recursive folder processing (requires `--recursive`).

**Performance Benefits:**
- Speeds up batch conversions by processing multiple folders simultaneously
- Typical speedup: ~4x with 4 workers on multi-core systems
- Most effective when processing many small to medium-sized folders

**Examples:**
```bash
# Use 4 parallel workers (good for quad-core CPUs)
tonietoolbox --recursive --workers 4 music-collection/

# Use 8 parallel workers (for high-end systems)
tonietoolbox --recursive --workers 8 large-library/

# Process folders sequentially (default)
tonietoolbox --recursive --workers 1 music/
```

**Performance Tips:**
- Start with `--workers` equal to CPU cores
- Each worker uses ~200-500MB RAM plus FFmpeg overhead
- Monitor system resources when using high worker counts
- Serial mode (`--workers 1`) uses less memory but takes longer

**Default**: `1` (sequential processing)

### `--files-to-taf`
Convert each audio file in a directory to individual `.taf` files (one TAF per audio file).

When used **without** `--recursive`:
```bash
tonietoolbox --files-to-taf audio-folder/
```

**Output**: `file1.taf`, `file2.taf`, etc.

When used **with** `--recursive`, switches recursive mode to process individual files instead of combining per folder (see `--recursive` above).

### `--convert-to-separate-mp3`
Convert TAF file chapters to individual MP3 files.

**Example:**
```bash
tonietoolbox --convert-to-separate-mp3 audiobook.taf
```

**Output**: Separate MP3 files for each chapter

### `--convert-to-single-mp3`
Convert entire TAF file to a single MP3 file.

**Example:**
```bash
tonietoolbox --convert-to-single-mp3 audiobook.taf
```

## Output Control

### `-O, --output-to-source`
Save output files in the source directory instead of the default output directory.

**Default**: Files saved to `./output/`

**Example:**
```bash
tonietoolbox input.mp3 --output-to-source
# Saves: input.taf in same directory as input.mp3
```

### `-fc, --force-creation`
Force creation of TAF file even if it already exists (overwrite).

**Default**: Skip existing files

**Example:**
```bash
tonietoolbox input.mp3 --force-creation
```

## Tonie-Specific Options

### `-t, --timestamp TIMESTAMP`
Set custom timestamp / bitstream serial.

**Accepts:**
- UNIX timestamp: `1745078762`
- Hexadecimal: `0x6803C9EA`

**Example:**
```bash
tonietoolbox input.mp3 --timestamp 1745078762
```

### `-a, --append-tonie-tag TAG`
Append 8-character hex tag to filename.

**Format**: Must be exactly 8 hexadecimal characters

**Example:**
```bash
tonietoolbox input.mp3 --append-tonie-tag 12345678
# Output: input_12345678.taf
```

### `-n, --no-tonie-header`
Do not write Tonie header to TAF file.

**Example:**
```bash
tonietoolbox input.mp3 --no-tonie-header
```

### `-k, --keep-temp`
Keep temporary Opus files in temp folder (for debugging/testing).

**Default**: Temporary files are deleted after conversion

**Example:**
```bash
tonietoolbox input.mp3 --keep-temp
```

### `-u, --use-legacy-tags`
Use legacy hardcoded tags instead of dynamic TonieToolbox tags.

**Example:**
```bash
tonietoolbox input.mp3 --use-legacy-tags
```

## Analysis & Debugging

### `-c, --compare FILE2`
Compare input TAF file with another `.taf` file for debugging purposes.

**Example:**
```bash
tonietoolbox original.taf --compare converted.taf
```

### `-D, --detailed-compare`
Show detailed OGG page differences when comparing files (use with `--compare`).

**Example:**
```bash
tonietoolbox file1.taf --compare file2.taf --detailed-compare
```

## System Integration

### `-C, --config-integration`
Open interactive wizard to configure context menu integration.

**Example:**
```bash
tonietoolbox --config-integration
```

### `-I, --install-integration`
Install system integration (context menu entries, file associations).

**Platform support:**
- Windows: Right-click context menu
- Linux: Nautilus/Dolphin context menu
- macOS: Finder services

**Example:**
```bash
tonietoolbox --install-integration
```

### `-U, --uninstall-integration`
Remove system integration (context menu entries).

**Example:**
```bash
tonietoolbox --uninstall-integration
```

## TeddyCloud Options

### `--upload URL`
Upload TAF file to TeddyCloud instance.

**Supported file types**: `.taf`, `.jpg`, `.jpeg`, `.png`

**Example:**
```bash
tonietoolbox audiobook.taf --upload https://teddycloud.example.com
```

### `--include-artwork`
Upload cover artwork image alongside the TAF file when using `--upload`.

**Requires**: Image file with same base name (e.g., `audiobook.jpg` for `audiobook.taf`)

**Example:**
```bash
tonietoolbox audiobook.taf --upload https://server.com --include-artwork
```

### `--assign-to-tag TAG_UID[,TAG_UID,...]`
Assign uploaded file(s) to specific Tonie tag UID(s).

**Requires**: `--upload` option

**Behavior**:
- **Single file + multiple tags**: Assigns the file to ALL specified tags
- **Multiple files (--recursive)**: Assigns files sequentially to tags (file[0]→tag[0], file[1]→tag[1], etc.)

**Tag UID Format**: 16 hex characters with or without colons (e.g., `E0:04:03:50:1E:E9:18:F2` or `E00403501EE918F2`)

**Examples:**

```bash
# Assign one file to multiple tags (file will be on ALL tags)
tonietoolbox audiobook.taf --upload https://server.com \
  --assign-to-tag E0:04:03:50:1E:E9:18:F2,E00403501EE918F3

# Sequential assignment: file01→tag1, file02→tag2, file03→tag3
tonietoolbox --recursive *.taf --upload https://server.com \
  --assign-to-tag TAG1,TAG2,TAG3

# Single file to single tag
tonietoolbox file.taf --upload https://server.com \
  --assign-to-tag E0:04:03:50:1E:E9:18:F2
```

**Summary Display**: Shows assignment results with checkmarks (✓) for success, X marks for failures, and warnings (⚠) for unassigned files.

### `--auto-select-tag`
Automatically assign uploaded file(s) to the first available unassigned tag(s).

**Requires**: `--upload` option

**Behavior**:
- Queries TeddyCloud server for tags without assigned source files
- Assigns each uploaded file to the next available unassigned tag
- With `--recursive`: finds unassigned tags for each file automatically

**Examples:**
```bash
# Auto-assign single file to first available tag
tonietoolbox audiobook.taf --upload https://server.com --auto-select-tag

# Auto-assign multiple files to available tags
tonietoolbox --recursive *.taf --upload https://server.com --auto-select-tag
```

### `--get-tags [URL]`
Get available Tonie tags from TeddyCloud instance.

**Example:**
```bash
tonietoolbox --get-tags https://teddycloud.example.com
```

### `--ignore-ssl-verify`
Ignore SSL certificate verification (useful for self-signed certificates).

**Security Warning**: Only use with trusted servers

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --ignore-ssl-verify
```

### `--special-folder FOLDER`
Special folder to upload to on TeddyCloud server.

**Supported values**: `library` (default)

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --special-folder library
```

### `--path PATH`
Path where to write the file on TeddyCloud server.

**Supports templates**: Use media tag variables like `/{albumartist}/{album}`

**Example:**
```bash
tonietoolbox audiobook.taf --upload https://server.com --path "/audiobooks/{album}"
```

### Connection Settings

#### `--connection-timeout SECONDS`
Connection timeout in seconds.

**Default**: 10 seconds

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --connection-timeout 30
```

#### `--read-timeout SECONDS`
Read timeout in seconds.

**Default**: 300 seconds (5 minutes)

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --read-timeout 600
```

#### `--max-retries RETRIES`
Maximum number of retry attempts for failed uploads.

**Default**: 3 retries

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --max-retries 5
```

#### `--retry-delay SECONDS`
Delay between retry attempts in seconds.

**Default**: 5 seconds

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --retry-delay 10
```

### JSON Options

#### `--create-custom-json`
Fetch and update custom Tonies JSON data from TeddyCloud.

**Example:**
```bash
tonietoolbox --upload https://server.com --create-custom-json
```

#### `--version-2`
Use version 2 of the Tonies JSON format.

**Default**: Version 1

**Example:**
```bash
tonietoolbox --upload https://server.com --create-custom-json --version-2
```

### Authentication

#### `--username USERNAME`
Username for basic authentication.

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --username admin
```

#### `--password PASSWORD`
Password for basic authentication.

**Security Warning**: Password visible in process list; prefer configuration file

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --username admin --password secret
```

#### `--client-cert CERT_FILE`
Path to client certificate file for certificate-based authentication.

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --client-cert /path/to/cert.pem
```

#### `--client-key KEY_FILE`
Path to client private key file for certificate-based authentication.

**Example:**
```bash
tonietoolbox file.taf --upload https://server.com --client-cert cert.pem --client-key key.pem
```

## Media Tag Options

### `-m, --use-media-tags`
Use media tags from audio files for naming output files.

**Example:**
```bash
tonietoolbox album/ --use-media-tags
```

### `--name-template TEMPLATE`
Template for naming files using media tags.

**Available variables**: `{albumartist}`, `{album}`, `{title}`, `{artist}`, `{track}`, `{year}`, `{genre}`

**Example:**
```bash
tonietoolbox album/ --name-template "{albumartist} - {album}"
```

### `--output-to-template PATH_TEMPLATE`
Template for output path using media tags.

**Example:**
```bash
tonietoolbox music/ --output-to-template "C:\\Music\\{albumartist}\\{album}"
```

### `--show-media-tags`
Show available media tags from input files (no conversion).

**Example:**
```bash
tonietoolbox album/ --show-media-tags
```

**Output**: Lists all available metadata tags (artist, album, title, etc.)

## Version Check Options

### `-S, --skip-update-check`
Skip checking for TonieToolbox updates.

**Default**: Updates checked on startup

**Example:**
```bash
tonietoolbox input.mp3 --skip-update-check
```

### `-F, --force-update-check`
Force refresh of update information from PyPI.

**Example:**
```bash
tonietoolbox --force-update-check
```

### `--clear-version-cache`
Clear the version check cache and exit.

**Example:**
```bash
tonietoolbox --clear-version-cache
```

### `--check-updates-only`
Only check for updates and exit (no other processing).

**Example:**
```bash
tonietoolbox --check-updates-only
```

### `--disable-notifications`
Disable update notification messages.

**Example:**
```bash
tonietoolbox input.mp3 --disable-notifications
```

### `--include-pre-releases`
Include pre-release versions (alpha, beta, rc) when checking for updates.

**Example:**
```bash
tonietoolbox --check-updates-only --include-pre-releases
```

## Logging Options

### `-d, --debug`
Enable debug logging (detailed diagnostic output).

**Example:**
```bash
tonietoolbox input.mp3 --debug
```

### `-T, --trace`
Enable trace logging (very verbose, includes all internal operations).

**Example:**
```bash
tonietoolbox input.mp3 --trace
```

### `-q, --quiet`
Show only warnings and errors (suppress info messages).

**Example:**
```bash
tonietoolbox input.mp3 --quiet
```

### `-Q, --silent`
Show only errors (suppress warnings and info).

**Example:**
```bash
tonietoolbox input.mp3 --silent
```

### `--log-file`
Save logs to a timestamped file in `~/.tonietoolbox/` folder.

**Example:**
```bash
tonietoolbox input.mp3 --log-file
```

**Output file**: `~/.tonietoolbox/tonietoolbox_YYYYMMDD_HHMMSS.log`

## Usage Examples

### Basic Conversion
```bash
# Convert single file
tonietoolbox audiobook.mp3

# Convert with custom bitrate
tonietoolbox music.flac --bitrate 192

# Convert entire folder
tonietoolbox audiobook-chapters/
```

### TeddyCloud Upload
```bash
# Upload with authentication
tonietoolbox file.taf --upload https://server.com --username admin --password secret

# Upload with SSL verification disabled
tonietoolbox file.taf --upload https://192.168.1.100 --ignore-ssl-verify

# Upload to specific path with artwork
tonietoolbox audiobook.taf --upload https://server.com \
  --path "/audiobooks/{album}" \
  --include-artwork
```

### Media Tag Naming
```bash
# Use album/artist naming
tonietoolbox music-folder/ \
  --use-media-tags \
  --name-template "{albumartist} - {album}"

# Organize by artist and album
tonietoolbox music-library/ \
  --use-media-tags \
  --output-to-template "/Music/{albumartist}/{album}" \
  --recursive
```

### Advanced Processing
```bash
# Convert with custom ffmpeg and debugging
tonietoolbox input.mp3 \
  --ffmpeg /custom/path/ffmpeg \
  --bitrate 128 \
  --cbr \
  --debug \
  --log-file

# Recursive conversion with overwrite
tonietoolbox audiobooks/ \
  --recursive \
  --force-creation \
  --bitrate 64

# Parallel processing with multiple workers
tonietoolbox music-library/ \
  --recursive \
  --workers 4 \
  --use-media-tags \
  --name-template "{albumartist} - {album}"
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Invalid arguments |
| `3` | File not found |
| `4` | Conversion failed |
| `5` | Upload failed |
| `6` | Network error |

## See Also

- [Configuration Reference](configuration.md) - Configuration file options
- [API Reference](api.md) - Python API documentation
- [Basic Usage Guide](../usage/basic-usage.md) - Common usage patterns
