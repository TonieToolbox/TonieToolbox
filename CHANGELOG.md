# Changelog
All notable changes to TonieToolbox will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0a1] - 2025-12-05

### Added
#### Tag Assignment Feature
- Assign uploaded files to Tonie tags on TeddyCloud
  - `--assign-to-tag TAG_UID[,TAG_UID,...]` - Assign files to specific tags
  - **Single file + multiple tags**: Assigns one file to ALL specified tags
  - **Recursive mode**: Sequential assignment (file[0]→tag[0], file[1]→tag[1], etc.)
  - `--auto-select-tag` - Automatically find and assign to available unassigned tags
  - Tag UID validation (16 hex characters with or without colons)
  - Overlay auto-detection from TeddyCloud server's registered Tonieboxes
  - **Summary table display** with assignment results:
    - Success indicators (✓), failure markers (✗), warnings (⚠)
    - Statistics showing successful/failed/unassigned files
    - Professional formatted output with file details
  - Event-driven architecture with tag assignment events for plugin integration
  - Examples:
    - `tonietoolbox file.taf --upload https://server.com --assign-to-tag E0:04:03:50:1E:E9:18:F2`
    - `tonietoolbox --recursive *.taf --upload https://server.com --assign-to-tag TAG1,TAG2,TAG3`
    - `tonietoolbox file.taf --upload https://server.com --auto-select-tag`

#### Parallel Processing
- **`--workers` (`-w`) argument** - Parallel processing for recursive operations
  - Process multiple folders simultaneously during `--recursive` operations
  - Significantly improves performance for large directory trees
  - Default is 1 (sequential), recommended 4-8 for optimal throughput
  - Example: `tonietoolbox /audiobooks --recursive --workers 4`
  - Uses platform-agnostic parallel execution that works in both CLI and GUI
  - Automatic resource management and progress tracking across all workers
  - **Beautiful Summary Table** at completion showing:
    - Total folders processed with success/failure/cancellation breakdown
    - Total input/output sizes (MB) with compression ratio percentage
    - Processing time, worker count, average time per folder
    - Throughput metric (folders/minute) for performance analysis
    - Professional Unicode box-drawing table format

- **Unified Parallel Execution Architecture**
  - New `ParallelExecutor` abstraction supporting both CLI and GUI contexts
  - `ThreadPoolParallelExecutor` for CLI batch processing
  - `QtParallelExecutor` for GUI with proper Qt signal/slot integration
  - Factory pattern for automatic executor selection based on context
  - Full dependency injection support for testability

- **Configuration Setting** - `processing.processing_modes.max_parallel_workers`
  - Configure default maximum parallel workers (default: 4)
  - Applies to recursive processing workflows

#### TAF Analysis Features
- **`--extract` (`-e`) argument** - Extract complete OGG/Opus stream from TAF files
  - Creates playable `.ogg` files from TAF content
  - Useful for backup, conversion, or playing on non-Tonie devices
  - Example: `tonietoolbox file.taf --extract` creates `file.ogg`
  
- **`--compare` (`-c`) argument** - Compare two TAF files for verification
  - Compares TAF headers, chapters, and audio properties
  - Shows SHA1 hash, validity, timestamps, and alignment
  - Displays side-by-side comparison table
  - Example: `tonietoolbox file1.taf --compare file2.taf`
  
- **`--detailed-compare` (`-D`) argument** - In-depth TAF file comparison
  - All features from `--compare` plus:
  - Extracts and analyzes OGG streams with FFprobe
  - **Byte-level content verification using SHA256 hashing**
  - Full codec details and Opus comments
  - File size comparison with detailed breakdown
  - Supports shorthand syntax: `tonietoolbox file1.taf -D file2.taf`
  - Example output includes full SHA256 hashes for integrity verification

### Changed
- OGG content comparison now displays in main comparison table (not summary)
- Full SHA256 hashes shown instead of truncated versions for better verification

### Fixed
- **Dependency Injection for WorkflowCoordinator** - Fixed initialization error
  - Corrected parameter names in `ProcessingApplicationService` (file_repo → file_repository)
  - Added missing `event_bus` parameter to service initialization chain
  - Removed obsolete upload_service and validation_service from coordinator constructor
  - Ensures parallel processing (`--workers`) initializes correctly in production

- **RecursiveProcessingAdapter Refactoring** - Enabled parallel folder processing
  - Refactored `_process_folders_to_taf` to delegate to `WorkflowCoordinator` via `ProcessingOperation`
  - Removed manual sequential folder loop in favor of coordinator-managed parallel/sequential routing
  - Added `parallel_workers` custom option propagation from CLI request to operation options
  - Fixed `OutputSpecification` creation to use `for_multiple_taf()` factory method
  - Result: `--workers N` now correctly processes N folders simultaneously

- **Logging Output Buffering** - Fixed delayed log output in terminal
  - Implemented `FlushingStreamHandler` that flushes after every log message
  - Ensures immediate visibility of all log output, especially during parallel processing
  - Fixes issue where detailed comparison tables required pressing Enter to appear
  - Particularly important for long-running operations with multiple workers

### Known Issues (Alpha Release)
- **`--max-depth` argument**: Recursive depth limiting not fully implemented, will process all subdirectories regardless of specified depth (tracked for beta release)
- **Custom JSON creation**: Some edge cases in TeddyCloud custom JSON generation need refinement (30 failing tests related to custom JSON workflows)
- **Plugin Manager GUI**: Minor UI state synchronization issues in checkbox states and dependency management
- **TAF Analysis Service**: File comparison edge cases need additional testing coverage
These issues do not affect core functionality (file conversion, upload, basic analysis) and will be addressed in upcoming releases.

- ** Probably more to come... **: This is an alpha release, so please report any issues you encounter! 

### Added
#### Core Architecture
- Complete codebase refactoring following Clean Architecture principles
- Event-driven architecture with centralized event bus for decoupled communication
- Modular plugin system for extensibility with hot-loading support
- Dependency injection pattern throughout the application
- Coordinator pattern for complex workflow orchestration

#### GUI Features
- New PyQt6-based GUI interface (`--gui` flag)
- TAF file player with playback controls (play/pause, seek, volume)
- Playlist management with drag-and-drop support
- Chapter navigation and display
- Audio file conversion tools integrated into GUI
- Theme system with dark/light mode support
- Multi-language support (i18n) with German and English translations
- Plugin manager GUI for installing and managing plugins

#### Plugin System
- Plugin marketplace with official and community plugins
- Plugin discovery and installation from remote repositories
- Plugin trust system (official, verified, community)
- Builtin plugins: Tonies Loader, Tonies Viewer, Plugin Manager
- Plugin SDK with comprehensive API for developers
- Centralized plugin data management (cache, downloads, configuration)

#### Audio Processing
- Enhanced audio conversion pipeline with better error handling
- Support for MP3, FLAC, WAV, OGG, M4A, and more formats
- **Batch processing with recursive directory scanning**
  - `--recursive` flag combines files per folder into one TAF per folder (default behavior)
  - `--recursive --files-to-taf` processes each file individually
  - `--max-depth N` controls recursion depth (unlimited by default)
  - Preserves directory structure in output
  - Template-based naming with `--name-template` and `--output-to-template`
- Progress tracking with event-based updates
- Smart metadata extraction and tagging
- Chapter detection and splitting capabilities

#### Desktop Integration
- Cross-platform desktop integration (Windows, Linux, macOS)
- Context menu support for TAF files
- Shell completion for bash, zsh, and fish
- System tray integration (coming soon)

#### Configuration & Settings
- Centralized configuration management via ConfigManager
- User-specific and system-wide configuration files
- Configuration validation with schema support
- Migration system for config version upgrades

#### TeddyCloud Integration
- Async upload support with aiohttp
- Client certificate authentication
- Basic authentication support
- Artwork upload alongside audio files
- Connection pooling and retry logic

#### Developer Tools
- Comprehensive test suite (459 passing tests)
- Integration tests for workflows
- Unit tests with high coverage
- Mock-based testing for external dependencies
- Development documentation and architecture decision records

### Changed
- Migrated from monolithic architecture to layered Clean Architecture
- Replaced tkinter GUI with modern PyQt6 interface
- Improved logging system with structured logging and trace level
- Enhanced error handling with domain-specific exceptions
- Updated dependencies: PyQt6>=6.10.0, aiohttp>=3.13.2, aiofiles>=25.1.0
- Modernized CLI argument parsing and validation
- Improved Docker support with multi-architecture builds

### Fixed
- Memory leaks in event subscriptions (now using weak references)
- Thread safety issues in shared resources
- GUI freezing during long-running operations
- File path handling on Windows
- Unicode support in file names and metadata

### Removed
- Legacy tkinter-based GUI (`--play-ui` flag deprecated)
- Support for Python <3.12 (now requires 3.12+)
- Deprecated configuration options from 0.x versions

### Known Issues
- 15 failing tests related to GUI translation edge cases and CLI integration
- Some TODO items in non-critical code paths (documented in code)
- macOS desktop integration requires additional testing

### Migration Notes
- Configuration files will be automatically migrated from 0.x format
- Plugin directory moved to `~/.tonietoolbox/plugins/`
- Cache directory now at `~/.tonietoolbox/cache/`
- Logs directory now at `~/.tonietoolbox/logs/`


## [0.6.5] - 2025-10-25
### Added
- Implemented minimal GUI player using tkinter with --play-ui option
- Added Tools tab to GUI player for audio file conversion
- Added docker multiarchitecture build (amd64, arm64)
- Multi-platform python builds for Windows (x64), Linux (x64, arm64), MacOS (x64, arm64)
### Fixed
- Fixed FFmpeg output path handling for conversion functions
### Changed
- Improved Tools tab to automatically synchronize with Player tab when a file is loaded
- kde integration updated to use --play-ui for GUI player
- Bump protobuf dependency to <=6.33.0 and requests to >=2.32.5
- Updated protobuf generated code to match new dependency version
### Removed
- Support/Automatic testing for Python <=3.12
## [0.6.4] - 2025-10-25
### Added
- Added simple .taf player using --play
- Added initial KDE integration for context menu handling
### Fixed
- Fixed certificate path issue on Windows-Integration for TeddyCloud upload
### Changed
- Adjusted --show-tags to return all available tags (excluding artwork/picture tags)
## [0.6.1] - 2025-05-24
### Fixed
- Fixed --custom-json generation for v1 and v2 formats with correct handling header timestamp and hash
## [0.6.0rc2] - 2025-05-15
### Fixed
- Error when using --install-integration caused by a distracted developer who forgot to comment on something. Silly™ 
## [0.6.0rc1] - 2025-05-15
### Added
### Fixed
- Possible Integration of *WIP Integration for MacOS
### Changed
- README Structure, moved Technical Details to [TECHNICAL.md](TECHNICAL.md) 
### Removed
- Not ready: MacOS Integration
- Not ready: Compare from Windows Integration for .taf
## [0.6.0a5] - 2025-05-15
### Added
- Dynamic Pathing based on meta tags
### Fixed
- Fixes for context menu integration
## [0.6.0a4] - 2025-05-14
### Fixed
- Fixes for context menu integration
## [0.6.0a3] - 2025-05-13
### Fixed
- Fixes for context menu integration
## [0.6.0a2] - 2025-05-12
### Added
- Context menu integration for Windows using --install-integration / --uninstall-integration
- Advanced context menu configuration using --config-integration after installation
## [0.6.0a1] - 2025-05-12
### Added
- *WIP* Context menu integration for Windows
- *WIP* Context menu integration for Linux
- *WIP* Context menu integration for MacOS
### Changed
- Logging to subdirectory `~/.tonietoolbox/logs`
## [0.5.1] - 2025-05-12
### Fixed
- gh-17: Fixed issue with --show-tags not displaying correctly
### Changed
- Adjusted get_input_files() for better handling of file types
## [0.5.0] - 2025-05-11
### Added
- Added new handler for generating v1 tonies.custom.json
### Changed
- Default behaviour of --create-custom-json to create a v1 tonies.custom.json
- Updated README.md with new features and usage examples
### Fixed
- gh-12: --name-template not working as expected
## [0.5.0a2] - 2025-05-08
### Changed
- Updated README.md with new features and usage examples
- Updated HOWTO.md with new features and usage examples
- Updated version handler to check for new releases on GitHub
- Direct Upload to TeddyCloud now only works with .TAF files
## [0.5.0a1] - 2025-05-07
### Added
- Initial release of version 0.5.0a1
- gh-2 - Allow BasicAuth & Client-Cert Authentication for TeddyCloud
- gh-3 - --include-artwork is not working for upload only
- Added Client-Certificate Authentication for TeddyCloud Upload Module
- gh-5 - Change Workflow for --upload in --recursive mode
- gh-6 - Adjust the conversion processing and check for valid existing .TAF
- gh-7 - Prevent duplicates in tonies.custom.json
- gh-10 - Add the correct runtime to tonies.custom.json
### Fixed
- gh-4 - Copying artwork fails if src/dst is mounted as NFS
- gh-9 - --create-custom-json code not reached
## [0.4.2] - 2025-04-21
### Fixed
- Github Docker Push Workflow
## [0.4.1] - 2025-04-21
### Added
- Added docker setup
### Fixed
- Python requirements (mutagen)
## [0.4.0] - 2025-04-21
### Added
- Added `--create-custom-json` for creating tonies.custom.json
- Added `--log-file` file logging for better support options.
- Added more debug & trace logging. More logging, more good.
## [0.3.0] - 2025-04-20
### Added
- Added a Legal Notice
- Added `--upload` Implementation of the TeddyCloud Upload Module
- Added `--include-artwork` option to automatically upload cover artwork alongside Tonie files
## [0.2.3] - 2025-04-20
### Added
- Using media tags for .TAF naming --use-media-tags | --use-media-tags --name-template "{artist} - {album} - {title}"
## [0.2.2] - 2025-04-20
### Added
- dynamic opus header / comments creation
## [0.2.1] - 2025-04-20
### Added
- short versions (aliases) for all the command-line arguments
## [0.2.0] - 2025-04-20
### Added
- Recursive Folder Processing - Using --recursive | --recursive --output-to-source
### Fixed
- dependency manager: Using opusenc after apt install
- .lst encoding problem
## [0.1.8] - 2025-04-20
### Changed
- consolidate all tonietoolbox files to ~/.tonietoolbox
- prioritize libs from tonietoolbox instead of system-wide installed
## [0.1.7] - 2025-04-20
### Added
- version handler try to install updates automatically after user confirmation
### Fixed
- dependency manager checks previous downloaded versions now
### Changed
- version handler need user confirmation when update is available
## [0.1.6] - 2025-04-20
### Fixed
- Version Handler and cache invalidation
- Github Workflow Relesenotes extraction
## [0.1.5] - 2025-04-20
### Added
- Version Handler *WIP
## [0.1.4] - 2025-04-20
### Added
- Auto Github Release based on tags.
## [0.1.3] - 2025-04-20
### Added
- Added HOWTO.md for beginners.
### Changed
- Changed default timestamp behaviour to act like TeddyCloud/Teddybench. (Deduct)
## [0.1.2] - 2025-04-20
### Changed
- Upgrade dependencies: ffmpeg shared to full.
## [0.1.1] - 2025-04-20
### Added
- Added --auto-download argument for dependency_manager.
## [0.1.0] - 2025-04-20
### Added
- Initial release
- Audio file conversion to Tonie format
- Support for FFmpeg and opusenc dependencies
- Command line interface with various options
- Automatic dependency download with --auto-download flag
