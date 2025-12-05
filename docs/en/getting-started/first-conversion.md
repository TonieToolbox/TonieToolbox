# Your First Conversion

This guide walks you through converting your very first audio file with TonieToolbox using the command line.

## What You'll Need

Before starting, make sure you have:

- ✅ **TonieToolbox installed** ([Installation Guide](installation.md))
- ✅ **An audio file** to convert (MP3, FLAC, WAV, etc.)
- ✅ **A few minutes** of your time

!!! info "GUI Conversion Status"
    The GUI currently functions as a TAF player. Audio file conversion is done via command line. GUI-based conversion will be added in a future release.

## Command Line Conversion

### Step 1: Open Terminal

=== "Windows"
    Press `Win + R`, type `cmd`, and press Enter

=== "macOS"
    Press `Cmd + Space`, type "Terminal", and press Enter

=== "Linux"
    Press `Ctrl + Alt + T` or find Terminal in your applications

### Step 2: Navigate to Your File

```bash
# Change to the directory containing your audio file
cd /path/to/your/audio/files

# On Windows, it might look like:
# cd C:\Users\YourName\Music

# List files to verify you're in the right place
ls    # Linux/macOS
dir   # Windows
```

### Step 3: Run the Conversion

```bash
tonietoolbox your-audio-file.mp3
```

Replace `your-audio-file.mp3` with your actual file name.

### Step 4: Check the Result

```bash
# List files in the output directory
ls output/      # Linux/macOS
dir output\     # Windows
```

You should see your new `.taf` file!

## Understanding the Output

After conversion, you'll see output similar to this:

```
🎵 TonieToolbox v1.0.0a1
📁 Processing: my-song.mp3
🔄 Converting audio format...
📦 Creating TAF file...
✅ Success: output/my-song.taf (4.2 MB)
⏱️  Conversion completed in 12.3 seconds
```

This tells you:
- ✅ **Success status** - the conversion worked
- 📁 **Output location** - where your file was saved  
- 💾 **File size** - how large the TAF file is
- ⏱️ **Time taken** - how long the process took

## Verify Your Conversion

Check that your TAF file was created correctly:

```bash
tonietoolbox --info output/my-song.taf
```

This displays details about your converted file:
- Duration and file size
- Audio codec information
- Tonie header details

## What Went Wrong? Common Issues

### "Command not found"

If you see `tonietoolbox: command not found`:

```bash
# Try this instead:
python -m TonieToolbox your-audio-file.mp3

# Or check if TonieToolbox is installed:
pip list | grep tonietoolbox
```

### "File not found"

If TonieToolbox can't find your file:
- **Check the file name** for typos
- **Use quotes** if the file name has spaces: `tonietoolbox "my song.mp3"`
- **Verify the path** with `ls` (Linux/macOS) or `dir` (Windows)

### "No such file or directory"

If you see path errors:
- **Navigate to the correct directory** first with `cd`
- **Use full file paths**: `tonietoolbox /full/path/to/file.mp3`
- **Check file permissions** - make sure you can read the file

### GUI Won't Start

If `tonietoolbox --gui` doesn't work:
- **Install PyQt6**: See the [Installation Guide](installation.md) for your system
- **Try command line** instead as a backup method
- **Check Python version**: TonieToolbox v1.0+ needs Python 3.12+

## Success! What's Next?

Congratulations on your first conversion! 🎉

Now you can explore more advanced features:

### Try Different Options

```bash
# Higher quality audio
tonietoolbox input.mp3 --bitrate 128

# Custom output name  
tonietoolbox input.mp3 "My Custom Name.taf"

# See all available options
tonietoolbox --help
```

### Convert Multiple Files

```bash
# Convert all files in a folder
tonietoolbox /path/to/folder/

# Process folders recursively
tonietoolbox --recursive /path/to/music/collection/
```

### Upload to TeddyCloud

If you have a TeddyCloud server:

```bash
tonietoolbox input.mp3 --upload https://your-teddycloud.local
```

## Next Steps

Now that you've mastered the basics:

- 🎨 **[Explore GUI Features](gui-guide.md)** - Learn about the full graphical interface
- 📚 **[Basic Usage Guide](../usage/basic-usage.md)** - Discover all command-line options
- 🏷️ **[Media Tags](../usage/media-tags.md)** - Use metadata for smarter naming
- ☁️ **[TeddyCloud Setup](../usage/teddycloud.md)** - Connect to your TeddyCloud server
- 📖 **[Real-World Examples](../examples/use-cases.md)** - See how others use TonieToolbox

## Getting Help

If you run into problems:

- 📖 **[Troubleshooting Guide](../examples/troubleshooting.md)** - Common solutions
- 💬 **[Community Discussions](https://github.com/TonieToolbox/TonieToolbox/discussions)** - Ask questions
- 🐛 **[Report Issues](https://github.com/TonieToolbox/TonieToolbox/issues)** - Bug reports

Welcome to the TonieToolbox community! 🎵📦