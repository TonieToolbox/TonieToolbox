# Docker Usage Guide 🐳

This guide covers how to use TonieToolbox with Docker for containerized audio conversion.

## Quick Start

### Pull the Image

```bash
# Latest stable release
docker pull quentendo64/tonietoolbox:latest

# Specific version
docker pull quentendo64/tonietoolbox:1.0.0

# Pre-release versions
docker pull quentendo64/tonietoolbox:alpha
docker pull quentendo64/tonietoolbox:beta
docker pull quentendo64/tonietoolbox:rc
```

### Basic Usage

Convert a single audio file:

```bash
docker run --rm \
  -v "$(pwd)/input:/tonietoolbox/input" \
  -v "$(pwd)/output:/tonietoolbox/output" \
  quentendo64/tonietoolbox:latest \
  /tonietoolbox/input/audio.mp3 \
  /tonietoolbox/output/audio.taf
```

## Volume Mounts

The container expects three volume mounts:

| Path | Purpose | Required |
|------|---------|----------|
| `/tonietoolbox/input` | Source audio files | Yes |
| `/tonietoolbox/output` | Converted TAF files | Yes |
| `/tonietoolbox/temp` | Temporary processing files | No |

## Multi-Architecture Support

Images are built for:
- **linux/amd64** - x86_64 processors (Intel/AMD)
- **linux/arm64** - ARM 64-bit processors (Raspberry Pi 4+, Apple Silicon)

Docker automatically pulls the correct architecture for your system.

## Available Tags

### Stable Releases
- `latest` - Most recent stable release
- `X.Y.Z` - Specific version (e.g., `1.0.0`)
- `X.Y` - Latest patch version (e.g., `1.0`)
- `X` - Latest minor version (e.g., `1`)

### Pre-releases
- `alpha` - Latest alpha version
- `beta` - Latest beta version
- `rc` - Latest release candidate
- `X.Y.ZaN` - Specific alpha (e.g., `1.0.0a1`)
- `X.Y.ZbN` - Specific beta (e.g., `1.0.0b2`)
- `X.Y.ZrcN` - Specific RC (e.g., `1.0.0rc1`)

### Other Tags
- `sha-<commit>` - Built from specific commit

## Common Use Cases

### Convert Multiple Files

```bash
docker run --rm \
  -v "$(pwd)/input:/tonietoolbox/input" \
  -v "$(pwd)/output:/tonietoolbox/output" \
  quentendo64/tonietoolbox:latest \
  /tonietoolbox/input/*.mp3 \
  -o /tonietoolbox/output
```

### Using with TeddyCloud

```bash
docker run --rm \
  -v "$(pwd)/input:/tonietoolbox/input" \
  -v "$(pwd)/output:/tonietoolbox/output" \
  -e TEDDYCLOUD_URL="http://teddycloud.local" \
  quentendo64/tonietoolbox:latest \
  --upload \
  /tonietoolbox/input/audio.mp3
```

### Interactive Shell

```bash
docker run --rm -it \
  -v "$(pwd)/input:/tonietoolbox/input" \
  -v "$(pwd)/output:/tonietoolbox/output" \
  --entrypoint /bin/bash \
  quentendo64/tonietoolbox:latest
```

### Show Version

```bash
docker run --rm quentendo64/tonietoolbox:latest --version
```

### Show Help

```bash
docker run --rm quentendo64/tonietoolbox:latest --help
```

## Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  tonietoolbox:
    image: quentendo64/tonietoolbox:latest
    volumes:
      - ./input:/tonietoolbox/input
      - ./output:/tonietoolbox/output
      - ./temp:/tonietoolbox/temp
    command: /tonietoolbox/input/audio.mp3 /tonietoolbox/output/audio.taf
```

Run with:

```bash
docker-compose run --rm tonietoolbox
```

## Building Locally

### Build for Current Architecture

```bash
docker build -t tonietoolbox:local .
```

### Build Multi-Architecture

```bash
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t tonietoolbox:local \
  --load \
  .
```

### Build with Version

```bash
docker build \
  --build-arg VERSION=1.0.0 \
  -t tonietoolbox:1.0.0 \
  .
```

## Troubleshooting

### Permission Issues

If you encounter permission errors with output files, ensure the mounted volumes have appropriate permissions:

```bash
chmod -R 777 input/ output/
```

The container runs as root by default to avoid permission issues with volume mounts.

### Missing Dependencies

If FFmpeg or other tools are missing, rebuild the image:

```bash
docker pull quentendo64/tonietoolbox:latest --no-cache
```

### ARM64 Issues

If you're on ARM64 (Raspberry Pi, Apple Silicon) and getting architecture errors:

```bash
# Force ARM64 pull
docker pull --platform linux/arm64 quentendo64/tonietoolbox:latest
```

## Registry Locations

TonieToolbox is published to:

- **Docker Hub**: `docker.io/quentendo64/tonietoolbox`
- **GitHub Container Registry**: `ghcr.io/quentendo64/tonietoolbox`

Both registries have identical images. Use whichever you prefer:

```bash
# Docker Hub (default)
docker pull quentendo64/tonietoolbox:latest

# GitHub Container Registry
docker pull ghcr.io/quentendo64/tonietoolbox:latest
```

## Security

- Images include SBOM (Software Bill of Materials) for vulnerability scanning
- Provenance attestation for supply chain security
- Regular updates with security patches
- Minimal base image (Python slim) reduces attack surface

## Performance Tips

1. **Use local volumes** for better I/O performance
2. **Mount temp directory** to avoid repeated extraction: `-v temp:/tonietoolbox/temp`
3. **Batch operations** by converting multiple files in one run
4. **Use specific versions** to ensure reproducible builds

## Support

For issues or questions:
- GitHub Issues: https://github.com/TonieToolbox/TonieToolbox/issues
- Documentation: https://github.com/TonieToolbox/TonieToolbox
