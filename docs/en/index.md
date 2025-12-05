# Welcome to TonieToolbox

!!! warning "Documentation Work in Progress"
    This documentation is being updated for TonieToolbox v1.0.0a1. Some sections may contain outdated information or be incomplete. We're actively working on updating all pages to reflect the new architecture and features.

**TonieToolbox** is a powerful, user-friendly toolkit for converting various audio formats into Tonie-compatible TAF format and seamlessly integrating with TeddyCloud servers.

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Get up and running in minutes with our step-by-step guides

    [:octicons-arrow-right-24: Installation Guide](getting-started/installation.md)
    
    [:octicons-arrow-right-24: First Conversion](getting-started/first-conversion.md)

-   :material-monitor:{ .lg .middle } **GUI Interface**

    ---

    New in v1.0.0a1! Modern PyQt6 TAF player with plugin support

    [:octicons-arrow-right-24: GUI Guide](getting-started/gui-guide.md)

-   :material-console:{ .lg .middle } **Command Line**

    ---

    Powerful automation capabilities for advanced users

    [:octicons-arrow-right-24: Command Reference](reference/command-line.md)

-   :material-cloud-upload:{ .lg .middle } **TeddyCloud**

    ---

    Seamless integration with TeddyCloud servers

    [:octicons-arrow-right-24: TeddyCloud Setup](usage/teddycloud.md)

</div>

## Merry Christmas 🎄🎉

<img src="assets/tonietoolbox_christmas.png" alt="TonieToolbox Christmas" width="150"/>

As a special holiday gift to myself, I am proud to announce the alpha release of **TonieToolbox v1.0.0a1**! This is a complete rewrite of the TonieToolbox.


## What's New in v1.0.0a1 ✨

The first alpha release of the 1.0 series brings a complete architectural overhaul:

!!! tip "New Features"

    - **🏗️ Clean Architecture** - Complete codebase refactoring with event-driven design
    - **🔌 Plugin System** - Extensible plugin marketplace with official and community plugins
    - **🎨 Modern GUI** - New PyQt6 interface with TAF player, playlist management, and themes
    - **🖥️ Enhanced Desktop Integration** - Improved context menu support across platforms
    - **⚡ Better Performance** - Async operations, background processing, improved threading

## Key Features

- **🔄 Audio Conversion** - Convert MP3, FLAC, WAV, OGG, and more to TAF format
- **📁 Batch Processing** - Handle entire music libraries recursively
- **🎨 Modern GUI** - PyQt6 interface with TAF player and plugin support
- **☁️ TeddyCloud Integration** - Direct upload with artwork support
- **🏷️ Smart Tagging** - Use audio metadata for intelligent file naming
- **🖥️ Desktop Integration** - Right-click context menus across platforms
- **🔍 Analysis Tools** - Validate, split, and compare TAF files
- **🔌 Plugin Marketplace** - Extend functionality with community plugins
- **🐳 Docker Support** - Cross-platform containerized execution

## Common Use Cases

=== "📚 Audiobooks"

    Convert and organize entire audiobook series with proper metadata and artwork.
    
    ```bash
    tonietoolbox --recursive --use-media-tags --name-template "{series} - {title}" audiobooks/
    ```

=== "🎵 Music Libraries"

    Process music collections with intelligent organization by artist and album.
    
    ```bash
    tonietoolbox --recursive --output-to-template "{artist}/{album}" music/
    ```

=== "🎭 Children's Content"

    Create custom Tonie content for kids with artwork and proper naming.
    
    ```bash
    tonietoolbox stories/ --upload https://teddycloud.local --include-artwork
    ```

## Quick Links

<div class="grid cards" markdown>

-   [📖 Complete User Guide](usage/basic-usage.md)
-   [🔧 Installation Instructions](getting-started/installation.md)  
-   [💡 Examples & Use Cases](examples/use-cases.md)
-   [❓ Troubleshooting Guide](examples/troubleshooting.md)
-   [📋 Changelog](https://github.com/TonieToolbox/TonieToolbox/blob/main/CHANGELOG.md)

</div>

## Community & Support

- **🐛 [Report Issues](https://github.com/TonieToolbox/TonieToolbox/issues)** - Bug reports and feature requests
- **💬 [Join Discussions](https://github.com/TonieToolbox/TonieToolbox/discussions)** - Community Q&A and ideas
- **🔄 [Source Code](https://github.com/TonieToolbox/TonieToolbox)** - GitHub repository

!!! warning "Legal Notice"

    This project is independent and not affiliated with tonies GmbH. tonies®, toniebox®, and related trademarks belong to [tonies GmbH](https://tonies.com). Use responsibly with legally owned content only.