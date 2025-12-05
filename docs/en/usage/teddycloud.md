# TeddyCloud Integration

TonieToolbox seamlessly integrates with TeddyCloud servers, allowing you to upload converted TAF files directly to your self-hosted Tonie cloud alternative.

## What is TeddyCloud?

[TeddyCloud](https://github.com/toniebox-reverse-engineering/teddycloud) is an open-source, self-hosted alternative to the official Tonie cloud service. It allows you to:

- Host your own Tonie content
- Upload custom audio files
- Manage Tonie configurations
- Maintain privacy and control over your data

## Basic Upload

### Simple Upload

Upload a TAF file to your TeddyCloud server:

```bash
tonietoolbox my-file.taf --upload https://teddycloud.example.com
```

### Convert and Upload

Convert audio files and upload directly:

```bash
tonietoolbox input.mp3 --upload https://teddycloud.example.com
```

### Upload with Artwork

Automatically include cover artwork:

```bash
tonietoolbox input.mp3 --upload https://teddycloud.example.com --include-artwork
```

## Server Configuration

### Basic Connection

```bash
# Standard HTTP connection
tonietoolbox file.taf --upload http://teddycloud.local

# HTTPS with valid certificate
tonietoolbox file.taf --upload https://teddycloud.example.com

# HTTPS with self-signed certificate
tonietoolbox file.taf --upload https://teddycloud.local --ignore-ssl-verify
```

### Authentication

TonieToolbox supports multiple authentication methods:

#### Basic Authentication

```bash
tonietoolbox file.taf \
  --upload https://teddycloud.example.com \
  --username admin \
  --password secret123
```

#### Certificate-Based Authentication

```bash
tonietoolbox file.taf \
  --upload https://teddycloud.example.com \
  --client-cert /path/to/certificate.crt \
  --client-key /path/to/private.key
```

## Advanced Upload Options

### Custom Paths

Organize files on your TeddyCloud server:

```bash
# Upload to specific directory
tonietoolbox audiobook.taf \
  --upload https://teddycloud.example.com \
  --path "/audiobooks/children"

# Use media tag templates in paths
tonietoolbox album.taf \
  --upload https://teddycloud.example.com \
  --path "/{albumartist}/{album}" \
  --use-media-tags
```

### Special Folders

Upload to TeddyCloud's special directories:

```bash
# Upload to library folder
tonietoolbox content.taf \
  --upload https://teddycloud.example.com \
  --special-folder library
```

### Connection Tuning

Adjust connection parameters for reliability:

```bash
tonietoolbox large-file.taf \
  --upload https://teddycloud.example.com \
  --connection-timeout 30 \
  --read-timeout 600 \
  --max-retries 5 \
  --retry-delay 10
```

## Artwork Management

### Automatic Artwork Detection

TonieToolbox can find and upload cover artwork automatically:

```bash
tonietoolbox audiobook/ \
  --upload https://teddycloud.example.com \
  --include-artwork
```

This will look for:
- `cover.jpg`, `cover.png`
- `folder.jpg`, `folder.png` 
- `artwork.jpg`, `artwork.png`
- Embedded artwork in audio files

### Artwork Requirements

For best results with TeddyCloud:
- **Format**: JPEG or PNG
- **Size**: 400x400 pixels recommended
- **File size**: Under 1MB
- **Location**: Same directory as audio files or embedded

## Custom Tonies JSON

Update TeddyCloud's custom Tonies database:

### Basic JSON Creation

```bash
tonietoolbox audiobook.taf \
  --upload https://teddycloud.example.com \
  --create-custom-json
```

### JSON Format Versions

```bash
# Use version 1 format (default)
tonietoolbox content.taf \
  --upload https://teddycloud.example.com \
  --create-custom-json

# Use version 2 format (enhanced metadata)
tonietoolbox content.taf \
  --upload https://teddycloud.example.com \
  --create-custom-json \
  --version-2
```

## Batch Operations

### Recursive Upload

Process and upload entire directories:

```bash
tonietoolbox --recursive music-collection/ \
  --upload https://teddycloud.example.com \
  --include-artwork \
  --use-media-tags \
  --path "/{albumartist}/{album}"
```

### Upload Existing TAF Files

Upload previously converted files:

```bash
# Upload all TAF files in output directory
for file in output/*.taf; do
    tonietoolbox "$file" --upload https://teddycloud.example.com --include-artwork
done
```

## Server Information

### Get Available Tags

Retrieve tags supported by your TeddyCloud server:

```bash
tonietoolbox --get-tags https://teddycloud.example.com
```

This shows available Tonie UIDs and associated information including series, episode, source path, and validation status.

### Assign Files to Tags

Automatically link uploaded files to specific Tonie tags on your TeddyCloud server.

#### Single File to Multiple Tags

Assign one file to multiple tags (all tags will play the same file):

```bash
tonietoolbox audiobook.taf --upload https://server.com \
  --assign-to-tag E0:04:03:50:1E:E9:18:F2,E00403501EE918F3,E00403501EE91234
```

This assigns `audiobook.taf` to **all three tags**.

#### Sequential Tag Assignment (Recursive Mode)

When uploading multiple files with `--recursive`, files are assigned sequentially to tags:

```bash
tonietoolbox --recursive /audiobooks/*.taf --upload https://server.com \
  --assign-to-tag TAG1,TAG2,TAG3,TAG4
```

Result:
- `book01.taf` → TAG1
- `book02.taf` → TAG2  
- `book03.taf` → TAG3
- `book04.taf` → TAG4

#### Auto-Select Available Tags

Let TonieToolbox automatically find unassigned tags:

```bash
# Single file - finds first available unassigned tag
tonietoolbox audiobook.taf --upload https://server.com --auto-select-tag

# Multiple files - finds available tags for each file
tonietoolbox --recursive *.taf --upload https://server.com --auto-select-tag
```

**Summary Display**: After assignment, you'll see a formatted table showing:
- ✓ Successfully assigned files
- ✗ Failed assignments with error messages
- ⚠ Unassigned files (when more files than tags)
- Statistics (total files, successful/failed assignments)

### Server Compatibility

TonieToolbox works with:
- **TeddyCloud** v0.4.0 and later
- **TeddyCloudStarter** setups
- Custom TeddyCloud deployments

## Configuration Files

### Persistent Settings

Save upload settings for repeated use:

```bash
# Configure integration settings
tonietoolbox --config-integration
```

This allows you to set:
- Default TeddyCloud server URL
- Authentication credentials
- Upload preferences
- Path templates

### Environment Variables

Set common options via environment:

```bash
export TEDDYCLOUD_URL="https://teddycloud.example.com"
export TEDDYCLOUD_USERNAME="admin"
export TEDDYCLOUD_PASSWORD="secret123"

# Now upload without specifying server details
tonietoolbox file.taf --upload
```

## Error Handling

### Common Upload Issues

#### Connection Problems

```bash
# Error: Connection refused
tonietoolbox file.taf --upload https://teddycloud.local
# Solution: Check server is running and URL is correct

# Error: SSL certificate verify failed
tonietoolbox file.taf --upload https://teddycloud.local
# Solution: Use --ignore-ssl-verify for self-signed certificates
```

#### Authentication Issues

```bash
# Error: 401 Unauthorized
tonietoolbox file.taf --upload https://teddycloud.example.com
# Solution: Provide --username and --password, or certificate auth
```

#### Path Problems

```bash
# Error: 404 Path not found
tonietoolbox file.taf --upload https://server.com --path "/nonexistent"
# Solution: Create path on server first, or use existing paths
```

### Debug Upload Issues

Enable detailed logging for troubleshooting:

```bash
tonietoolbox file.taf \
  --upload https://teddycloud.example.com \
  --debug \
  --log-file
```

## Integration with TeddyCloudStarter

[TeddyCloudStarter](https://github.com/Quentendo64/TeddyCloudStarter) provides easy TeddyCloud deployment with TonieToolbox integration:

### Automated Setup

TeddyCloudStarter automatically:
- Configures proper directory mounts
- Sets up authentication
- Enables artwork uploads
- Provides default paths

### Enhanced Features

With TeddyCloudStarter, you get:
- **Automatic `/custom_img` mounting** for artwork
- **Pre-configured authentication**
- **Optimized network settings**
- **Backup and restore capabilities**

## Security Considerations

### Network Security

- **Use HTTPS** when possible for encrypted uploads
- **Validate certificates** - only use `--ignore-ssl-verify` for trusted self-signed certs
- **Secure credentials** - avoid passwords in command history
- **Use certificate auth** for production deployments

### File Security

- **Scan uploaded content** for malware before processing
- **Limit upload paths** to prevent directory traversal
- **Monitor disk usage** to prevent storage exhaustion
- **Regular backups** of TeddyCloud data

## Performance Optimization

### Upload Speed

- **Use wired connections** when possible
- **Upload during off-peak hours** for better bandwidth
- **Batch similar files** for efficient processing
- **Monitor server resources** during large uploads

### Server Load

- **Limit concurrent uploads** to avoid overwhelming the server
- **Use appropriate timeouts** for large files
- **Monitor server logs** for performance issues
- **Scale TeddyCloud resources** if needed

## Next Steps

Now that you understand TeddyCloud integration:

- 🏷️ **[Media Tags](media-tags.md)** - Use metadata for organized uploads
- 🖥️ **[Desktop Integration](desktop-integration.md)** - Right-click upload functionality
- 📚 **[Examples](../examples/use-cases.md)** - Real-world TeddyCloud scenarios
- 🔧 **[Configuration](../reference/configuration.md)** - Advanced settings