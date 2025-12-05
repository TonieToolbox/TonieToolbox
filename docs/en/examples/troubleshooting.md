# Troubleshooting Guide

This guide helps you diagnose and resolve common issues with TonieToolbox v1.0.0a1.

## Installation Issues

### "tonietoolbox: command not found"

**Symptoms**: The system doesn't recognize the `tonietoolbox` command.

**Solutions**:

1. **Check if TonieToolbox is installed**:
   ```bash
   pip list | grep tonietoolbox
   ```

2. **Install using pipx (recommended)**:
   ```bash
   pipx install tonietoolbox
   ```

3. **Or install with pip**:
   ```bash
   pip install tonietoolbox
   # or
   pip install --user tonietoolbox
   ```

4. **Alternative execution methods**:
   ```bash
   python -m TonieToolbox input.mp3
   # or direct script
   python path/to/tonietoolbox.py input.mp3
   ```

5. **Check Python PATH**:
   ```bash
   python -m site --user-base
   # Add the Scripts/bin directory to your PATH
   ```

### GUI Won't Start

**Symptoms**: `tonietoolbox --gui` fails or shows PyQt6 errors.

**Solutions**:

1. **Install PyQt6** (required for GUI):
   ```bash
   pip install "tonietoolbox[gui]"
   # or
   pip install PyQt6>=6.10.0
   ```

2. **Check PyQt6 installation**:
   ```bash
   python -c "from PyQt6 import QtWidgets; print('PyQt6 works')"
   ```

3. **System-specific issues**:

=== "Windows"
    
    **Install Visual C++ Redistributables**:
    - Download from [Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)
    - Required for PyQt6 to work
    
    **Try different Python version**:
    ```bash
    # Python 3.12 is well-tested
    py -3.12 -m pip install "tonietoolbox[gui]"
    ```

=== "macOS"
    
    **Install using official Python**:
    - Download from [python.org](https://python.org)
    - System Python may have compatibility issues
    
    **Check Rosetta on Apple Silicon**:
    ```bash
    # For M1/M2 Macs, ensure Rosetta is installed
    softwareupdate --install-rosetta
    ```

=== "Linux"
    
    **Ubuntu/Debian** - Install Qt dependencies:
    ```bash
    sudo apt update
    sudo apt install libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0
    ```
    
    **Fedora**:
    ```bash
    sudo dnf install qt6-qtbase-gui
    ```
    
    **Arch Linux**:
    ```bash
    sudo pacman -S qt6-base
    ```

### FFmpeg Auto-Download Issues

**Symptoms**: `--auto-download` fails to download FFmpeg.

**Solutions**:

1. **Check network connectivity**:
   ```bash
   curl -I https://github.com
   ```

2. **Manual FFmpeg installation**:

=== "Windows"
    
    **Using winget**:
    ```powershell
    winget install ffmpeg
    ```
    
    **Manual download**:
    1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
    2. Extract to `C:\ffmpeg`
    3. Add `C:\ffmpeg\bin` to system PATH

=== "macOS"
    
    ```bash
    # Using Homebrew (recommended)
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

3. **Specify custom FFmpeg path**:
   ```bash
   tonietoolbox input.mp3 --ffmpeg /path/to/ffmpeg
   ```

### Permission Errors

**Symptoms**: "Permission denied" errors during installation or execution.

**Solutions**:

1. **Use pipx (recommended)**:
   ```bash
   pipx install tonietoolbox
   ```

2. **Use user installation**:
   ```bash
   pip install --user tonietoolbox
   ```

3. **Virtual environment** (for development):
   ```bash
   python -m venv tonietoolbox-env
   source tonietoolbox-env/bin/activate  # Linux/macOS
   # tonietoolbox-env\Scripts\activate   # Windows
   pip install tonietoolbox
   ```

4. **Fix directory permissions**:
   ```bash
   ls -la ~/.local/bin/  # Linux/macOS
   # Ensure the directory is writable
   ```

## Conversion Issues

### "FFmpeg not found"

**Symptoms**: FFmpeg dependency error during conversion.

**Quick Fix**:
```bash
tonietoolbox input.mp3 --auto-download
```

**Verify FFmpeg**:
```bash
ffmpeg -version
```

### Audio Conversion Failures

**Symptoms**: Conversion starts but fails with audio processing errors.

**Debugging Steps**:

1. **Enable debug logging**:
   ```bash
   tonietoolbox input.mp3 --debug --log-file
   ```

   Logs saved to: `~/.tonietoolbox/tonietoolbox_YYYYMMDD_HHMMSS.log`

2. **Check input file**:
   ```bash
   # Test file with FFmpeg directly
   ffmpeg -i input.mp3 -t 10 test-output.wav
   ```

3. **Try different settings**:
   ```bash
   # Lower bitrate
   tonietoolbox input.mp3 --bitrate 64
   
   # Use CBR encoding
   tonietoolbox input.mp3 --cbr
   
   # Keep temporary files for inspection
   tonietoolbox input.mp3 --keep-temp
   ```

**Common Causes**:
- **Corrupted input file**: Try different audio files
- **Unsupported format**: Check FFmpeg supports the format
- **Insufficient disk space**: Check available storage
- **File permissions**: Ensure read/write access to input/output directories

### Large File Issues

**Symptoms**: Conversion fails or is extremely slow with large files (>500MB).

**Solutions**:

1. **Check available disk space**:
   ```bash
   df -h .  # Linux/macOS
   # Windows: Check drive properties
   ```

2. **Use lower bitrates**:
   ```bash
   tonietoolbox large-audiobook.mp3 --bitrate 64
   ```

3. **Split large files**:
   ```bash
   # Use ffmpeg to split into chapters
   ffmpeg -i large-file.mp3 -f segment -segment_time 3600 -c copy chapter_%03d.mp3
   ```

4. **Monitor resource usage**:
   ```bash
   # Linux/macOS
   top -p $(pgrep -f tonietoolbox)
   
   # Windows: Task Manager
   ```

## File Format Issues

### Unsupported Input Format

**Symptoms**: "Unsupported audio format" or conversion errors.

**Solutions**:

1. **Check supported formats**:
   - MP3 (recommended)
   - FLAC
   - WAV
   - M4A/AAC
   - OGG Vorbis
   - WMA (limited support)

2. **Convert format first**:
   ```bash
   # Convert to MP3
   ffmpeg -i input.unknown output.mp3
   tonietoolbox output.mp3
   ```

3. **Verify file integrity**:
   ```bash
   ffmpeg -v error -i input.mp3 -f null -
   ```

### Corrupted TAF Files

**Symptoms**: Generated TAF files don't play or show errors.

**Debugging**:

1. **Analyze the TAF file**:
   ```bash
   tonietoolbox --info output.taf
   ```

2. **Compare with reference file**:
   ```bash
   tonietoolbox working.taf --compare suspicious.taf --detailed-compare
   ```

3. **Regenerate with debugging**:
   ```bash
   tonietoolbox input.mp3 --force-creation --debug --log-file
   ```

## GUI Player Issues

### TAF File Won't Play

**Symptoms**: GUI launches but TAF files don't play or show errors.

**Solutions**:

1. **Verify TAF file**:
   ```bash
   tonietoolbox --info file.taf
   ```

2. **Check audio backend**:
   - Ensure system audio is working
   - Try different audio output device
   - Check system volume settings

3. **Launch with debugging**:
   ```bash
   tonietoolbox --gui --debug --log-file
   ```

4. **Test with command-line player**:
   ```bash
   tonietoolbox --play file.taf
   ```

### Plugin Issues

**Symptoms**: Plugins won't load or cause crashes.

**Solutions**:

1. **Check plugin status**:
   - Open GUI → Plugin Manager tab
   - Check enabled/disabled status
   - Look for error messages

2. **Disable problematic plugins**:
   ```json
   # Edit ~/.tonietoolbox/config.json
   {
     "plugins": {
       "disabled_plugins": ["com.example.problematic"]
     }
   }
   ```

3. **Clear plugin cache**:
   ```bash
   rm -rf ~/.tonietoolbox/cache/plugins/
   ```

4. **Reinstall plugins**:
   - Remove plugin directory
   - Restart TonieToolbox
   - Reinstall via Plugin Manager

### GUI Performance Issues

**Symptoms**: Slow or unresponsive GUI.

**Solutions**:

1. **Reduce playlist size**:
   - Large playlists (>100 files) may slow down GUI
   - Split into smaller playlists

2. **Disable resource-intensive plugins**:
   - Check Plugin Manager for active plugins
   - Disable unnecessary visualization or analysis plugins

3. **Clear cache**:
   ```bash
   rm -rf ~/.tonietoolbox/cache/
   ```

## TeddyCloud Integration Issues

### Connection Problems

**Symptoms**: Upload fails with connection errors.

**Debugging**:

1. **Test basic connectivity**:
   ```bash
   curl -I https://your-teddycloud.server.com
   ```

2. **Check TeddyCloud status**:
   - Verify TeddyCloud is running
   - Check server logs
   - Ensure network connectivity

3. **Debug upload**:
   ```bash
   tonietoolbox file.taf \
     --upload https://teddycloud.server.com \
     --debug --log-file
   ```

4. **Increase timeouts**:
   ```bash
   tonietoolbox file.taf \
     --upload https://server.com \
     --connection-timeout 30 \
     --read-timeout 600
   ```

### SSL Certificate Issues

**Symptoms**: SSL verification errors.

**Solutions**:

1. **For self-signed certificates**:
   ```bash
   tonietoolbox file.taf \
     --upload https://teddycloud.local \
     --ignore-ssl-verify
   ```

   !!! warning "Security Warning"
       Only use `--ignore-ssl-verify` with trusted servers you control.

2. **Install certificate**:
   - Add self-signed cert to system trust store
   - Or use certificate-based authentication

3. **Use HTTP for local testing**:
   ```bash
   tonietoolbox file.taf --upload http://192.168.1.100
   ```

### Authentication Failures

**Symptoms**: 401 Unauthorized or 403 Forbidden errors.

**Solutions**:

1. **Basic authentication**:
   ```bash
   tonietoolbox file.taf \
     --upload https://server.com \
     --username admin --password your-password
   ```

2. **Certificate authentication**:
   ```bash
   tonietoolbox file.taf \
     --upload https://server.com \
     --client-cert cert.pem \
     --client-key key.pem
   ```

3. **Configuration file** (recommended):
   ```json
   {
     "application": {
       "teddycloud": {
         "url": "https://teddycloud.example.com",
         "username": "admin",
         "password": "secret",
         "ignore_ssl_verify": false
       }
     }
   }
   ```

4. **Verify TeddyCloud settings**:
   - Check user permissions
   - Verify authentication is enabled
   - Check TeddyCloud logs

### Upload Failures

**Symptoms**: Upload starts but fails partway through.

**Solutions**:

1. **Increase retry settings**:
   ```bash
   tonietoolbox file.taf \
     --upload https://server.com \
     --max-retries 5 \
     --retry-delay 10
   ```

2. **Check file size limits**:
   - TeddyCloud may have upload size limits
   - Check server configuration
   - Monitor server logs during upload

3. **Use smaller chunks**:
   - Not configurable via CLI
   - Edit config.json: `application.teddycloud.chunk_size`

## Performance Issues

### Slow Conversion

**Symptoms**: Conversions take much longer than expected.

**Solutions**:

1. **Use faster storage**:
   - Move files to SSD
   - Avoid network drives for temp files

2. **Close other applications**:
   - Free up CPU and memory
   - Stop background processes

3. **Optimize encoding settings**:
   ```bash
   # Use CBR (faster than VBR)
   tonietoolbox input.mp3 --cbr
   
   # Lower bitrate
   tonietoolbox input.mp3 --bitrate 64
   ```

4. **Disable unnecessary features**:
   ```bash
   # Skip update checks
   tonietoolbox input.mp3 --skip-update-check
   
   # Disable analysis cache
   tonietoolbox input.mp3 --debug  # Check logs for cache hits
   ```

### High Memory Usage

**Symptoms**: System becomes unresponsive, out of memory errors.

**Solutions**:

1. **Process files individually**:
   ```bash
   # Instead of: tonietoolbox folder/
   for file in folder/*.mp3; do
       tonietoolbox "$file"
   done
   ```

2. **Disable parallel processing**:
   ```json
   {
     "processing": {
       "processing_modes": {
         "parallel_processing": false
       }
     }
   }
   ```

3. **Increase system resources**:
   - Close other applications
   - Add RAM if consistently hitting limits
   - Use swap/page file

## Configuration Issues

### Config File Corruption

**Symptoms**: TonieToolbox fails to start or shows config errors.

**Solutions**:

1. **Validate config file**:
   ```bash
   python -m json.tool ~/.tonietoolbox/config.json
   ```

2. **Reset to defaults**:
   ```bash
   # Backup current config
   cp ~/.tonietoolbox/config.json ~/.tonietoolbox/config.backup.json
   
   # Delete corrupted config
   rm ~/.tonietoolbox/config.json
   
   # TonieToolbox will create new default config on next run
   tonietoolbox --version
   ```

3. **Manual repair**:
   - Open `~/.tonietoolbox/config.json` in editor
   - Fix JSON syntax errors
   - Validate with JSON linter

### Settings Not Persisting

**Symptoms**: Configuration changes don't save or revert.

**Solutions**:

1. **Check file permissions**:
   ```bash
   ls -la ~/.tonietoolbox/config.json
   # Should be writable by user
   ```

2. **Verify config location**:
   ```bash
   # Linux/macOS
   echo ~/.tonietoolbox/config.json
   ```
   
   ```powershell
   # Windows
   echo %USERPROFILE%\.tonietoolbox\config.json
   ```

3. **Check for multiple configs**:
   - Ensure only one config file exists
   - CLI arguments override config file

## Getting More Help

### Enable Comprehensive Logging

For any issue, enable detailed logging:

```bash
tonietoolbox input.mp3 --trace --log-file
```

Log location: `~/.tonietoolbox/tonietoolbox_YYYYMMDD_HHMMSS.log`

### Collect System Information

When reporting issues, gather:

```bash
# TonieToolbox version
tonietoolbox --version

# Python version
python --version

# FFmpeg version
ffmpeg -version

# Operating system
uname -a  # Linux/macOS
# Windows: Settings → System → About
```

### Where to Get Help

1. **Documentation**: [https://tonietoolbox.github.io/TonieToolbox/](https://tonietoolbox.github.io/TonieToolbox/)
2. **GitHub Issues**: [https://github.com/TonieToolbox/TonieToolbox/issues](https://github.com/TonieToolbox/TonieToolbox/issues)
3. **GitHub Discussions**: [https://github.com/TonieToolbox/TonieToolbox/discussions](https://github.com/TonieToolbox/TonieToolbox/discussions)
4. **Search existing issues**: Many common problems already have solutions

### Creating Good Bug Reports

Include these details:

- **TonieToolbox version**: `tonietoolbox --version`
- **Operating system**: Windows 11, macOS 14, Ubuntu 22.04, etc.
- **Python version**: `python --version`
- **Installation method**: pip, pipx, development install
- **Complete command**: The exact command that failed
- **Full error message**: Complete error text, not just "it doesn't work"
- **Input file details**: Format, size, duration
- **Log files**: Attach logs from `--trace --log-file`
- **Steps to reproduce**: Detailed steps to recreate the issue

### Debug Command Patterns

```bash
# Basic debugging
tonietoolbox input.mp3 --debug

# Full debugging with logs
tonietoolbox input.mp3 --trace --log-file --keep-temp

# Test with minimal options
tonietoolbox input.mp3 --bitrate 96

# Test dependencies
tonietoolbox input.mp3 --auto-download

# Test without network
tonietoolbox input.mp3 --skip-update-check

# GUI debugging
tonietoolbox --gui --debug --log-file

# Test specific file
tonietoolbox --info suspicious.taf
```

## Known Issues (v1.0.0a1)

!!! info "Alpha Release Limitations"
    TonieToolbox v1.0.0a1 is an alpha release. Known issues:
    
    - **GUI translation incomplete**: Some UI elements may show English only
    - **Plugin stability**: Community plugins may have compatibility issues
    - **CLI integration tests**: 15 tests failing (documented in CHANGELOG)
    - **Theme switching**: Requires restart in some cases
    - **Large playlist performance**: GUI may slow with >100 files
    
    These are being addressed in upcoming releases. Check [CHANGELOG.md](https://github.com/TonieToolbox/TonieToolbox/blob/main/CHANGELOG.md) for updates.

## Common Error Messages

### "No such file or directory: 'ffmpeg'"

**Cause**: FFmpeg not installed or not in PATH

**Solution**: 
```bash
tonietoolbox input.mp3 --auto-download
```

### "PyQt6 is not installed"

**Cause**: GUI dependencies not installed

**Solution**:
```bash
pip install "tonietoolbox[gui]"
```

### "Permission denied: ~/.tonietoolbox/config.json"

**Cause**: Config file not writable

**Solution**:
```bash
chmod 644 ~/.tonietoolbox/config.json
```

### "Connection refused" or "Connection timeout"

**Cause**: TeddyCloud server unreachable

**Solution**:
- Verify server is running
- Check network connectivity
- Increase timeout: `--connection-timeout 30`

### "Invalid TAF file format"

**Cause**: Corrupted or incomplete TAF file

**Solution**:
```bash
# Verify file
tonietoolbox --info file.taf

# Regenerate
tonietoolbox original.mp3 --force-creation
```

Remember: Most issues can be resolved with:
1. **Update dependencies**: `pip install --upgrade tonietoolbox`
2. **Enable debugging**: `--debug --log-file`
3. **Check logs**: `~/.tonietoolbox/tonietoolbox_*.log`
4. **Verify FFmpeg**: `ffmpeg -version`
5. **Reset config**: Delete `~/.tonietoolbox/config.json`
