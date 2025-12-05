# Installation Guide

TonieToolbox can be installed in several ways depending on your preference and system setup.

## Prerequisites

Before installing TonieToolbox, ensure you have:

- **Python 3.12 or higher** (3.14 recommended)
- **FFmpeg** (optional - can be auto-downloaded)

!!! tip "Auto-Download FFmpeg"
    TonieToolbox can automatically download FFmpeg if it's not found in your system PATH. Simply run:
    ```bash
    tonietoolbox --auto-download
    ```

## Installation Methods

### pipx (Recommended)

The recommended way to install TonieToolbox is using [pipx](https://pipx.pypa.io/), which installs the application in an isolated environment:

```bash
# Install pipx if you don't have it
pip install pipx
pipx ensurepath

# Install TonieToolbox
pipx install tonietoolbox
```

!!! success "Why pipx?"
    - ✅ Isolated environment - no conflicts with other Python packages
    - ✅ Global access - `tonietoolbox` command available everywhere
    - ✅ Easy updates - `pipx upgrade tonietoolbox`
    - ✅ Clean uninstalls - `pipx uninstall tonietoolbox`

### PyPI

Alternatively, install using pip:

```bash
pip install tonietoolbox
```

This will install TonieToolbox and its dependencies, making the `tonietoolbox` command available in your terminal.

!!! note "Virtual Environment"
    When using pip, it's recommended to use a virtual environment to avoid conflicts:
    
    ```bash
    python -m venv tonietoolbox-env
    source tonietoolbox-env/bin/activate  # On Windows: tonietoolbox-env\Scripts\activate
    pip install tonietoolbox
    ```

### Docker

TonieToolbox is available as a Docker image with all dependencies pre-installed:

```bash
# From Docker Hub
docker pull quentendo64/tonietoolbox:latest

# From GitHub Container Registry
docker pull ghcr.io/quentendo64/tonietoolbox:latest
```

### From Source

For development or to use the latest features:

```bash
# Clone the repository
git clone https://github.com/TonieToolbox/TonieToolbox.git
cd TonieToolbox

# Install in development mode
pip install -e .
```

## System-Specific Instructions

### Windows

1. **Install Python** from [python.org](https://python.org/downloads)
   - ⚠️ **Important**: Check "Add Python to PATH" during installation

2. **Install TonieToolbox**:
   ```cmd
   # Recommended: Using pipx
   pip install pipx
   pipx install tonietoolbox
   
   # Alternative: Using pip
   pip install tonietoolbox
   ```

3. **Install FFmpeg** (Optional):
   ```cmd
   # Option 1: Let TonieToolbox download it automatically
   tonietoolbox --auto-download
   
   # Option 2: Install manually
   # Download from https://ffmpeg.org/download.html
   # Extract to C:\ffmpeg and add C:\ffmpeg\bin to PATH
   
   # Option 3: Using Chocolatey
   choco install ffmpeg
   
   # Option 4: Using winget
   winget install FFmpeg
   ```

### macOS

1. **Install Python** (if not already installed):
   ```bash
   # Using Homebrew (recommended)
   brew install python
   
   # Or download from python.org
   ```

2. **Install TonieToolbox**:
   ```bash
   # Recommended: Using pipx
   pip3 install pipx
   pipx install tonietoolbox
   
   # Alternative: Using pip
   pip3 install tonietoolbox
   ```

3. **Install FFmpeg** (Optional):
   ```bash
   # Option 1: Let TonieToolbox download it automatically
   tonietoolbox --auto-download
   
   # Option 2: Using Homebrew
   brew install ffmpeg
   
   # Option 3: Using MacPorts
   sudo port install ffmpeg
   ```

### Linux

#### Ubuntu/Debian
```bash
# Install Python
sudo apt update
sudo apt install python3 python3-pip

# Install TonieToolbox (Recommended: pipx)
pip3 install pipx
pipx install tonietoolbox

# Or using pip
pip3 install tonietoolbox

# Install FFmpeg (Optional)
sudo apt install ffmpeg
# Or let TonieToolbox download it: tonietoolbox --auto-download
```

#### Fedora
```bash
# Install Python
sudo dnf install python3 python3-pip

# Install TonieToolbox (Recommended: pipx)
pip3 install pipx
pipx install tonietoolbox

# Or using pip
pip3 install tonietoolbox

# Install FFmpeg (Optional)
sudo dnf install ffmpeg
# Or let TonieToolbox download it: tonietoolbox --auto-download
```

#### Arch Linux
```bash
# Install Python
sudo pacman -S python python-pip

# Install TonieToolbox (Recommended: pipx)
pip install pipx
pipx install tonietoolbox

# Or using pip
pip install tonietoolbox

# Install FFmpeg (Optional)
sudo pacman -S ffmpeg
# Or let TonieToolbox download it: tonietoolbox --auto-download
```

## Verification

After installation, verify that TonieToolbox is working correctly:

```bash
# Check version
tonietoolbox --version

# Launch GUI
tonietoolbox --gui

# Get help
tonietoolbox --help

# Test with auto-download
tonietoolbox --auto-download
```

## Dependency Management

### Automatic Download

TonieToolbox can automatically download missing dependencies:

```bash
tonietoolbox --auto-download
```

### Manual Installation

If you prefer to install dependencies manually:

#### FFmpeg

=== "Windows"
    1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
    2. Extract to a folder (e.g., `C:\ffmpeg`)
    3. Add `C:\ffmpeg\bin` to your system PATH

=== "macOS"
    ```bash
    # Using Homebrew
    brew install ffmpeg
    
    # Using MacPorts
    sudo port install ffmpeg
    ```

=== "Linux"
    ```bash
    # Ubuntu/Debian
    sudo apt install ffmpeg
    
    # Fedora
    sudo dnf install ffmpeg
    
    # Arch Linux
    sudo pacman -S ffmpeg
    ```



## Troubleshooting

### Common Issues

#### "tonietoolbox: command not found"

- Make sure Python's scripts directory is in your PATH
- Try using: `python -m TonieToolbox` instead
- Reinstall with: `pip install --user tonietoolbox`

#### GUI won't start

- Make sure PyQt6 is installed (it should be installed automatically with TonieToolbox)
- Try reinstalling: `pipx reinstall tonietoolbox` or `pip install --force-reinstall tonietoolbox`
- Check if there are any missing dependencies: `pip install PyQt6>=6.10.0`

#### Permission errors on Linux/macOS

```bash
# Install to user directory instead
pip install --user tonietoolbox

# Or use a virtual environment (recommended)
python -m venv ~/tonietoolbox-env
source ~/tonietoolbox-env/bin/activate
pip install tonietoolbox
```

### Getting Help

If you encounter issues during installation:

1. Check our [Troubleshooting Guide](../examples/troubleshooting.md)
2. Search [existing issues](https://github.com/TonieToolbox/TonieToolbox/issues)
3. Create a new issue with your system details and error messages

## Next Steps

Once TonieToolbox is installed:

- 📚 Follow the [Quick Start Guide](quickstart.md) to convert your first audio file
- 🎨 Try the [GUI Guide](gui-guide.md) for the easiest experience
- 📖 Read about [Basic Usage](../usage/basic-usage.md) for more detailed instructions