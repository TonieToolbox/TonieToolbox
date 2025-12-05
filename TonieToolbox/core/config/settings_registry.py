#!/usr/bin/python3
"""
Central settings registry for TonieToolbox configuration system.

This module defines all possible configuration options with their defaults and metadata,
providing a single source of truth for the entire application configuration.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Set, Optional
from enum import Enum

# Application paths
TONIETOOLBOX_HOME = os.path.join(os.path.expanduser("~"), ".tonietoolbox")


class ConfigSection(Enum):
    """Configuration sections for organizing settings."""
    METADATA = "metadata"
    APPLICATION_LOGGING = "application.logging"
    APPLICATION_TEDDYCLOUD = "application.teddycloud"
    APPLICATION_VERSION = "application.version"
    PROCESSING_AUDIO = "processing.audio"
    PROCESSING_FILE_HANDLING = "processing.file_handling"
    PROCESSING_MODES = "processing.processing_modes"
    GUI_THEME = "gui.theme"
    GUI_WINDOW = "gui.window"
    GUI_BEHAVIOR = "gui.behavior"
    GUI_GENERAL = "gui"
    PLUGINS = "plugins"
    DEPENDENCIES_NETWORK = "dependencies.network"
    DEPENDENCIES_CACHE = "dependencies.cache"
    DEPENDENCIES_GENERAL = "dependencies"
    MEDIA_TAGS = "media.tags"


@dataclass
class ConfigSetting:
    """Metadata for a configuration setting."""
    key: str                          # Setting key (e.g., "level", "url")
    default_value: Any               # Default value
    section: ConfigSection           # Which section it belongs to
    is_initial: bool = False         # Always appears in minimal config
    description: str = ""            # Human-readable description
    data_type: type = str           # Expected data type
    validation_fn: Optional[callable] = None  # Optional validation function


# Central registry - single source of truth for all settings
SETTINGS_REGISTRY: Dict[str, ConfigSetting] = {
    
    # ===== METADATA SECTION (always in config) =====
    "metadata.description": ConfigSetting(
        key="description", 
        default_value="TonieToolbox centralized configuration", 
        section=ConfigSection.METADATA,
        is_initial=True, 
        description="Configuration description", 
        data_type=str
    ),
    "metadata.config_version": ConfigSetting(
        key="config_version", 
        default_value="2.0", 
        section=ConfigSection.METADATA,
        is_initial=True, 
        description="Configuration format version", 
        data_type=str
    ),
    
    # ===== APPLICATION LOGGING (initial settings) =====
    "application.logging.level": ConfigSetting(
        key="level", 
        default_value="INFO", 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=True,
        description="Logging level", 
        data_type=str
    ),
    "application.logging.log_to_file": ConfigSetting(
        key="log_to_file", 
        default_value=False, 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=True,
        description="Enable file logging", 
        data_type=bool
    ),
    
    # ===== APPLICATION LOGGING (dynamic settings) =====
    "application.logging.log_file_path": ConfigSetting(
        key="log_file_path", 
        default_value=TONIETOOLBOX_HOME, 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=False,
        description="Custom log file path", 
        data_type=str
    
    ),
    "application.logging.max_log_size": ConfigSetting(
        key="max_log_size", 
        default_value=10 * 1024 * 1024,  # 10MB
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=False,
        description="Maximum log file size in bytes", 
        data_type=int
    ),
    "application.logging.backup_count": ConfigSetting(
        key="backup_count", 
        default_value=5, 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=False,
        description="Number of backup log files", 
        data_type=int
    
    ),
    "application.logging.console_format": ConfigSetting(
        key="console_format", 
        default_value="%(levelname)-8s %(name)s: %(message)s", 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=False,
        description="Console log format", 
        data_type=str
    
    ),
    "application.logging.file_format": ConfigSetting(
        key="file_format", 
        default_value="%(asctime)s %(levelname)-8s %(name)s: %(message)s", 
        section=ConfigSection.APPLICATION_LOGGING,
        is_initial=False,
        description="File log format", 
        data_type=str
    
    ),
    
    # ===== APPLICATION TEDDYCLOUD (initial settings) =====
    "application.teddycloud.url": ConfigSetting(
        key="url", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="TeddyCloud server URL", 
        data_type=str
    
    ),
    "application.teddycloud.ignore_ssl_verify": ConfigSetting(
        key="ignore_ssl_verify", 
        default_value=False, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="Ignore SSL certificate verification", 
        data_type=bool
    
    ),
    "application.teddycloud.username": ConfigSetting(
        key="username", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="TeddyCloud username", 
        data_type=str
    
    ),
    "application.teddycloud.password": ConfigSetting(
        key="password", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="TeddyCloud password", 
        data_type=str
    
    ),
    
    # ===== APPLICATION TEDDYCLOUD (dynamic settings) =====
    "application.teddycloud.connection_timeout": ConfigSetting(
        key="connection_timeout", 
        default_value=10, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=False,
        description="Connection timeout in seconds", 
        data_type=int
    
    ),
    "application.teddycloud.read_timeout": ConfigSetting(
        key="read_timeout", 
        default_value=300, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=False,
        description="Read timeout in seconds", 
        data_type=int
    
    ),
    "application.teddycloud.chunk_size": ConfigSetting(
        key="chunk_size", 
        default_value=1024 * 1024,  # 1MB
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=False,
        description="Upload chunk size in bytes", 
        data_type=int
    ),
    "application.teddycloud.max_retries": ConfigSetting(
        key="max_retries", 
        default_value=3, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=False,
        description="Maximum retry attempts", 
        data_type=int
    
    ),
    "application.teddycloud.retry_delay": ConfigSetting(
        key="retry_delay", 
        default_value=5, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=False,
        description="Retry delay in seconds", 
        data_type=int
    
    ),
    "application.teddycloud.certificate_path": ConfigSetting(
        key="certificate_path", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="Client certificate path", 
        data_type=str
    
    ),
    "application.teddycloud.private_key_path": ConfigSetting(
        key="private_key_path", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="Client private key path", 
        data_type=str
    
    ),
    "application.teddycloud.username": ConfigSetting(
        key="username", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="Basic Authentication username", 
        data_type=str
    
    ),
    "application.teddycloud.password": ConfigSetting(
        key="password", 
        default_value=None, 
        section=ConfigSection.APPLICATION_TEDDYCLOUD,
        is_initial=True,
        description="Basic Authentication password", 
        data_type=str
    
    ),
    
    # ===== APPLICATION VERSION (initial settings) =====
    "application.version.check_for_updates": ConfigSetting(
        key="check_for_updates", 
        default_value=True, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=True,
        description="Check for updates automatically", 
        data_type=bool
    
    ),
    "application.version.notify_if_not_latest": ConfigSetting(
        key="notify_if_not_latest", 
        default_value=True, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=True,
        description="Notify if not latest version", 
        data_type=bool
    
    ),
    "application.version.pre_releases": ConfigSetting(
        key="pre_releases", 
        default_value=False, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=True,
        description="Include pre-releases in updates", 
        data_type=bool
    
    ),
    "application.version.auto_update": ConfigSetting(
        key="auto_update", 
        default_value=False, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=True,
        description="Enable automatic updates", 
        data_type=bool
    
    ),
    
    # ===== APPLICATION VERSION (dynamic settings) =====
    "application.version.cache_expiry": ConfigSetting(
        key="cache_expiry", 
        default_value=86400,  # 24 hours
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=False,
        description="Version cache expiry in seconds", 
        data_type=int
    ),
    "application.version.timeout": ConfigSetting(
        key="timeout", 
        default_value=10, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=False,
        description="Version check timeout", 
        data_type=int
    
    ),
    "application.version.max_retries": ConfigSetting(
        key="max_retries", 
        default_value=3, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=False,
        description="Version check max retries", 
        data_type=int
    
    ),
    "application.version.retry_delay": ConfigSetting(
        key="retry_delay", 
        default_value=5, 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=False,
        description="Version check retry delay", 
        data_type=int
    
    ),
    "application.version.pypi_url": ConfigSetting(
        key="pypi_url", 
        default_value="https://pypi.org/pypi/TonieToolbox/json", 
        section=ConfigSection.APPLICATION_VERSION,
        is_initial=False,
        description="PyPI URL for version checking", 
        data_type=str
    
    ),
    
    # ===== PROCESSING AUDIO (dynamic settings only) =====
    "processing.audio.default_bitrate": ConfigSetting(
        key="default_bitrate", 
        default_value=128, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Default audio bitrate in kbps", 
        data_type=int
    
    ),
    "processing.audio.default_sample_rate": ConfigSetting(
        key="default_sample_rate", 
        default_value=48000, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Default sample rate in Hz", 
        data_type=int
    
    ),
    "processing.audio.default_channels": ConfigSetting(
        key="default_channels", 
        default_value=2, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Default number of channels", 
        data_type=int
    
    ),
    "processing.audio.use_cbr": ConfigSetting(
        key="use_cbr", 
        default_value=False, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Use constant bitrate encoding", 
        data_type=bool
    
    ),
    "processing.audio.opus_complexity": ConfigSetting(
        key="opus_complexity", 
        default_value=10, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Opus encoding complexity", 
        data_type=int
    
    ),
    "processing.audio.opus_application": ConfigSetting(
        key="opus_application", 
        default_value="audio", 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Opus application type", 
        data_type=str
    
    ),
    "processing.audio.auto_mono_conversion": ConfigSetting(
        key="auto_mono_conversion", 
        default_value=True, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Automatically convert mono to stereo", 
        data_type=bool
    
    ),
    "processing.audio.normalize_audio": ConfigSetting(
        key="normalize_audio", 
        default_value=False, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Normalize audio levels", 
        data_type=bool
    
    ),
    "processing.audio.remove_silence": ConfigSetting(
        key="remove_silence", 
        default_value=False, 
        section=ConfigSection.PROCESSING_AUDIO,
        is_initial=False,
        description="Remove silence from audio", 
        data_type=bool
    
    ),
    
    # ===== PROCESSING FILE HANDLING (dynamic settings only) =====
    "processing.file_handling.default_output_dir": ConfigSetting(
        key="default_output_dir", 
        default_value="./output", 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Default output directory", 
        data_type=str
    
    ),
    "processing.file_handling.output_to_source": ConfigSetting(
        key="output_to_source", 
        default_value=False, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Output to source directory", 
        data_type=bool
    
    ),
    "processing.file_handling.force_creation": ConfigSetting(
        key="force_creation", 
        default_value=False, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Force file creation/overwrite", 
        data_type=bool
    
    ),
    "processing.file_handling.use_media_tags": ConfigSetting(
        key="use_media_tags", 
        default_value=False, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Use media tags for naming", 
        data_type=bool
    
    ),
    "processing.file_handling.name_template": ConfigSetting(
        key="name_template", 
        default_value="{artist} - {title}", 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Filename template", 
        data_type=str
    
    ),
    "processing.file_handling.append_tonie_tag": ConfigSetting(
        key="append_tonie_tag", 
        default_value=None, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Tag to append to filenames", 
        data_type=str
    
    ),
    "processing.file_handling.keep_temp_files": ConfigSetting(
        key="keep_temp_files", 
        default_value=False, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Keep temporary files", 
        data_type=bool
    
    ),
    "processing.file_handling.temp_dir": ConfigSetting(
        key="temp_dir", 
        default_value=None, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Custom temporary directory", 
        data_type=str
    
    ),
    "processing.file_handling.auto_cleanup": ConfigSetting(
        key="auto_cleanup", 
        default_value=True, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Auto-cleanup temporary files", 
        data_type=bool
    
    ),
    "processing.file_handling.validate_outputs": ConfigSetting(
        key="validate_outputs", 
        default_value=True, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Validate output files", 
        data_type=bool
    
    ),
    "processing.file_handling.check_existing_files": ConfigSetting(
        key="check_existing_files", 
        default_value=True, 
        section=ConfigSection.PROCESSING_FILE_HANDLING,
        is_initial=False,
        description="Check for existing files", 
        data_type=bool
    
    ),
    
    # ===== PROCESSING MODES (dynamic settings only) =====
    "processing.processing_modes.recursive_depth_limit": ConfigSetting(
        key="recursive_depth_limit", 
        default_value=10, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Maximum recursive directory depth", 
        data_type=int
    
    ),
    "processing.processing_modes.skip_empty_folders": ConfigSetting(
        key="skip_empty_folders", 
        default_value=True, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Skip empty folders during processing", 
        data_type=bool
    
    ),
    "processing.processing_modes.folder_size_limit": ConfigSetting(
        key="folder_size_limit", 
        default_value=1024 * 1024 * 1024,  # 1GB
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Folder size limit in bytes", 
        data_type=int
    ),
    "processing.processing_modes.parallel_processing": ConfigSetting(
        key="parallel_processing", 
        default_value=False, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Enable parallel processing", 
        data_type=bool
    
    ),
    "processing.processing_modes.max_parallel_files": ConfigSetting(
        key="max_parallel_files", 
        default_value=4, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Maximum parallel files", 
        data_type=int
    
    ),
    "processing.processing_modes.max_parallel_workers": ConfigSetting(
        key="max_parallel_workers", 
        default_value=4, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Maximum parallel workers for recursive processing", 
        data_type=int
    
    ),
    "processing.processing_modes.analysis_cache_enabled": ConfigSetting(
        key="analysis_cache_enabled", 
        default_value=True, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Enable analysis caching", 
        data_type=bool
    
    ),
    "processing.processing_modes.detailed_analysis": ConfigSetting(
        key="detailed_analysis", 
        default_value=False, 
        section=ConfigSection.PROCESSING_MODES,
        is_initial=False,
        description="Enable detailed analysis", 
        data_type=bool
    
    ),
    
    # ===== GUI SETTINGS (dynamic settings only) =====
    "gui.enable_gui": ConfigSetting(
        key="enable_gui", 
        default_value=True, 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="Enable GUI mode", 
        data_type=bool
    
    ),
    "gui.language": ConfigSetting(
        key="language", 
        default_value="en_US", 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="GUI language", 
        data_type=str
    
    ),
    "gui.auto_detect_language": ConfigSetting(
        key="auto_detect_language", 
        default_value=True, 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="Auto-detect system language", 
        data_type=bool
    
    ),
    "gui.fallback_language": ConfigSetting(
        key="fallback_language", 
        default_value="en_US", 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="Fallback language", 
        data_type=str
    
    ),
    "gui.debug_mode": ConfigSetting(
        key="debug_mode", 
        default_value=False, 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="GUI debug mode", 
        data_type=bool
    
    ),
    "gui.show_debug_info": ConfigSetting(
        key="show_debug_info", 
        default_value=False, 
        section=ConfigSection.GUI_GENERAL,
        is_initial=False,
        description="Show debug information", 
        data_type=bool
    
    ),
    
    # ===== PLUGIN SETTINGS (dynamic settings only) =====
    "plugins.enable_plugins": ConfigSetting(
        key="enable_plugins",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Enable plugin system (global toggle)",
        data_type=bool
    
    ),
    "plugins.auto_discover": ConfigSetting(
        key="auto_discover",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Automatically discover plugins on startup",
        data_type=bool
    
    ),
    "plugins.auto_enable": ConfigSetting(
        key="auto_enable",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Automatically enable discovered plugins",
        data_type=bool
    
    ),
    "plugins.plugin_directories": ConfigSetting(
        key="plugin_directories",
        default_value=[os.path.join(TONIETOOLBOX_HOME, "plugins")],
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Additional plugin directories to scan",
        data_type=list
    
    ),
    "plugins.disabled_plugins": ConfigSetting(
        key="disabled_plugins",
        default_value=[],
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="List of plugin IDs to keep disabled",
        data_type=list
    
    ),
    "plugins.load_builtin_plugins": ConfigSetting(
        key="load_builtin_plugins",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Load built-in plugins from TonieToolbox/core/plugins/builtin",
        data_type=bool
    
    ),
    "plugins.repository_urls": ConfigSetting(
        key="repository_urls",
        default_value=["https://raw.githubusercontent.com/TonieToolbox/tonietoolbox_plugins/main/"],
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Plugin repository URLs to search for community plugins",
        data_type=list
    
    ),
    "plugins.auto_update_check": ConfigSetting(
        key="auto_update_check",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Automatically check for plugin updates on startup",
        data_type=bool
    
    ),
    "plugins.update_check_interval": ConfigSetting(
        key="update_check_interval",
        default_value=86400,  # 24 hours in seconds
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Interval in seconds between update checks",
        data_type=int
    
    ),
    "plugins.install_location": ConfigSetting(
        key="install_location",
        default_value=os.path.join(TONIETOOLBOX_HOME, "plugins"),
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Base directory for community plugin installations",
        data_type=str
    
    ),
    "plugins.allow_unverified": ConfigSetting(
        key="allow_unverified",
        default_value=False,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Allow installation of unverified plugins",
        data_type=bool
    
    ),
    "plugins.max_parallel_downloads": ConfigSetting(
        key="max_parallel_downloads",
        default_value=3,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Maximum number of parallel plugin downloads",
        data_type=int
    
    ),
    "plugins.verify_checksums": ConfigSetting(
        key="verify_checksums",
        default_value=True,
        section=ConfigSection.PLUGINS,
        is_initial=False,
        description="Verify SHA512 checksums when installing plugins",
        data_type=bool
    
    ),
    
    # ===== GUI THEME (dynamic settings only) =====
    "gui.theme.default_theme": ConfigSetting(
        key="default_theme", 
        default_value="default", 
        section=ConfigSection.GUI_THEME,
        is_initial=False,
        description="Default theme name", 
        data_type=str
    
    ),
    "gui.theme.custom_theme_dir": ConfigSetting(
        key="custom_theme_dir", 
        default_value=None, 
        section=ConfigSection.GUI_THEME,
        is_initial=False,
        description="Custom theme directory", 
        data_type=str
    
    ),
    "gui.theme.default_font_family": ConfigSetting(
        key="default_font_family", 
        default_value="Arial", 
        section=ConfigSection.GUI_THEME,
        is_initial=False,
        description="Default font family", 
        data_type=str
    
    ),
    "gui.theme.default_font_size": ConfigSetting(
        key="default_font_size", 
        default_value=10, 
        section=ConfigSection.GUI_THEME,
        is_initial=False,
        description="Default font size", 
        data_type=int
    
    ),
    
    # ===== GUI WINDOW (dynamic settings only) =====
    "gui.window.default_width": ConfigSetting(
        key="default_width", 
        default_value=1000, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Default window width", 
        data_type=int
    
    ),
    "gui.window.default_height": ConfigSetting(
        key="default_height", 
        default_value=700, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Default window height", 
        data_type=int
    
    ),
    "gui.window.min_width": ConfigSetting(
        key="min_width", 
        default_value=800, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Minimum window width", 
        data_type=int
    
    ),
    "gui.window.min_height": ConfigSetting(
        key="min_height", 
        default_value=600, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Minimum window height", 
        data_type=int
    
    ),
    "gui.window.remember_size": ConfigSetting(
        key="remember_size", 
        default_value=True, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Remember window size", 
        data_type=bool
    
    ),
    "gui.window.remember_position": ConfigSetting(
        key="remember_position", 
        default_value=True, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Remember window position", 
        data_type=bool
    
    ),
    "gui.window.start_maximized": ConfigSetting(
        key="start_maximized", 
        default_value=False, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Start maximized", 
        data_type=bool
    
    ),
    "gui.window.auto_adapt_size": ConfigSetting(
        key="auto_adapt_size", 
        default_value=True, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Auto-adapt window size", 
        data_type=bool
    
    ),
    "gui.window.maximize_on_large_screens": ConfigSetting(
        key="maximize_on_large_screens", 
        default_value=True, 
        section=ConfigSection.GUI_WINDOW,
        is_initial=False,
        description="Maximize on large screens", 
        data_type=bool
    
    ),
    
    # ===== GUI BEHAVIOR (dynamic settings only) =====
    "gui.behavior.auto_play_on_open": ConfigSetting(
        key="auto_play_on_open", 
        default_value=False, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Auto-play files when opened", 
        data_type=bool
    
    ),
    "gui.behavior.remember_last_directory": ConfigSetting(
        key="remember_last_directory", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Remember last directory", 
        data_type=bool
    
    ),
    "gui.behavior.show_file_extensions": ConfigSetting(
        key="show_file_extensions", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Show file extensions", 
        data_type=bool
    
    ),
    "gui.behavior.show_progress_bars": ConfigSetting(
        key="show_progress_bars", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Show progress bars", 
        data_type=bool
    
    ),
    "gui.behavior.show_tooltips": ConfigSetting(
        key="show_tooltips", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Show tooltips", 
        data_type=bool
    
    ),
    "gui.behavior.confirm_destructive_actions": ConfigSetting(
        key="confirm_destructive_actions", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Confirm destructive actions", 
        data_type=bool
    
    ),
    "gui.behavior.auto_loop": ConfigSetting(
        key="auto_loop", 
        default_value=False, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Auto-loop audio playback", 
        data_type=bool
    
    ),
    "gui.behavior.volume_step": ConfigSetting(
        key="volume_step", 
        default_value=10, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Volume change step", 
        data_type=int
    
    ),
    "gui.behavior.seek_step": ConfigSetting(
        key="seek_step", 
        default_value=5, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Seek step in seconds", 
        data_type=int
    
    ),
    "gui.behavior.auto_save_playlist": ConfigSetting(
        key="auto_save_playlist", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Auto-save playlist on exit", 
        data_type=bool
    
    ),
    "gui.behavior.auto_load_last_playlist": ConfigSetting(
        key="auto_load_last_playlist", 
        default_value=True, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Auto-load last playlist on startup", 
        data_type=bool
    
    ),
    "gui.behavior.last_playlist_path": ConfigSetting(
        key="last_playlist_path", 
        default_value=os.path.join(TONIETOOLBOX_HOME, "last_playlist.lst"),
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Path to last playlist file", 
        data_type=str
    
    ),
    "gui.behavior.playlist_file_cache_size": ConfigSetting(
        key="playlist_file_cache_size", 
        default_value=100, 
        section=ConfigSection.GUI_BEHAVIOR,
        is_initial=False,
        description="Maximum playlist file cache size", 
        data_type=int
    
    ),
    
    # ===== DEPENDENCIES (dynamic settings only) =====
    "dependencies.parallel_downloads": ConfigSetting(
        key="parallel_downloads", 
        default_value=True, 
        section=ConfigSection.DEPENDENCIES_GENERAL,
        is_initial=False,
        description="Enable parallel downloads", 
        data_type=bool
    
    ),
    "dependencies.max_concurrent_downloads": ConfigSetting(
        key="max_concurrent_downloads", 
        default_value=3, 
        section=ConfigSection.DEPENDENCIES_GENERAL,
        is_initial=False,
        description="Maximum concurrent downloads", 
        data_type=int
    
    ),
    "dependencies.python_package_auto_install": ConfigSetting(
        key="python_package_auto_install", 
        default_value=True, 
        section=ConfigSection.DEPENDENCIES_GENERAL,
        is_initial=False,
        description="Auto-install Python packages", 
        data_type=bool
    
    ),
    "dependencies.pip_timeout": ConfigSetting(
        key="pip_timeout", 
        default_value=120, 
        section=ConfigSection.DEPENDENCIES_GENERAL,
        is_initial=False,
        description="Pip timeout in seconds", 
        data_type=int
    
    ),
    
    # ===== DEPENDENCIES NETWORK (dynamic settings only) =====
    "dependencies.network.connection_timeout": ConfigSetting(
        key="connection_timeout", 
        default_value=30, 
        section=ConfigSection.DEPENDENCIES_NETWORK,
        is_initial=False,
        description="Network connection timeout", 
        data_type=int
    
    ),
    "dependencies.network.read_timeout": ConfigSetting(
        key="read_timeout", 
        default_value=300, 
        section=ConfigSection.DEPENDENCIES_NETWORK,
        is_initial=False,
        description="Network read timeout", 
        data_type=int
    
    ),
    "dependencies.network.max_retries": ConfigSetting(
        key="max_retries", 
        default_value=3, 
        section=ConfigSection.DEPENDENCIES_NETWORK,
        is_initial=False,
        description="Maximum network retries", 
        data_type=int
    
    ),
    "dependencies.network.retry_backoff": ConfigSetting(
        key="retry_backoff", 
        default_value=2.0, 
        section=ConfigSection.DEPENDENCIES_NETWORK,
        is_initial=False,
        description="Retry backoff factor", 
        data_type=float
    
    ),
    "dependencies.network.user_agent": ConfigSetting(
        key="user_agent", 
        default_value=f"TonieToolbox/1.0", 
        section=ConfigSection.DEPENDENCIES_NETWORK,
        is_initial=False,
        description="HTTP User-Agent string", 
        data_type=str
    
    ),
    
    # ===== DEPENDENCIES CACHE (dynamic settings only) =====
    "dependencies.cache.cache_dir": ConfigSetting(
        key="cache_dir", 
        default_value=os.path.join(TONIETOOLBOX_HOME, "cache"),
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Cache directory path", 
        data_type=str
    ),
    "dependencies.cache.libs_dir": ConfigSetting(
        key="libs_dir", 
        default_value=os.path.join(TONIETOOLBOX_HOME, "libs"),
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Libraries directory path", 
        data_type=str
    ),
    "dependencies.cache.max_cache_size": ConfigSetting(
        key="max_cache_size", 
        default_value=1024 * 1024 * 1024,  # 1GB
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Maximum cache size in bytes", 
        data_type=int
    ),
    "dependencies.cache.cache_expiry_days": ConfigSetting(
        key="cache_expiry_days", 
        default_value=30, 
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Cache expiry in days", 
        data_type=int
    
    ),
    "dependencies.cache.auto_cleanup": ConfigSetting(
        key="auto_cleanup", 
        default_value=True, 
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Auto-cleanup expired cache", 
        data_type=bool
    
    ),
    "dependencies.cache.enabled": ConfigSetting(
        key="enabled", 
        default_value=True, 
        section=ConfigSection.DEPENDENCIES_CACHE,
        is_initial=False,
        description="Enable dependency caching", 
        data_type=bool
    
    ),
    # ===== MEDIA  (dynamic settings only) =====
    "media.tags.additional_tags": ConfigSetting(
        key="additional_tags", 
        default_value=[], 
        section=ConfigSection.MEDIA_TAGS,
        is_initial=False,
        description="Additional media tags to handle (extend the TAG_MAPPINGS)", 
        data_type=list
    ),
}


def get_initial_settings() -> Set[str]:
    """Get all settings that should always appear in config."""
    return {key for key, setting in SETTINGS_REGISTRY.items() if setting.is_initial}


def get_default_value(setting_path: str) -> Any:
    """Get default value for a setting."""
    setting = SETTINGS_REGISTRY.get(setting_path)
    return setting.default_value if setting else None


def get_setting_info(setting_path: str) -> Optional[ConfigSetting]:
    """Get complete setting information."""
    return SETTINGS_REGISTRY.get(setting_path)


def build_minimal_config() -> Dict[str, Any]:
    """Build minimal configuration with only initial settings."""
    config = {}
    
    for setting_path, setting in SETTINGS_REGISTRY.items():
        if setting.is_initial:
            # Build nested dict structure using dot notation
            _set_nested_value(config, setting_path, setting.default_value)
    
    return config


def _set_nested_value(config: Dict[str, Any], path: str, value: Any) -> None:
    """Set a nested configuration value using dot notation path."""
    parts = path.split('.')
    current = config
    
    # Navigate to the parent dict
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Set the final value
    current[parts[-1]] = value


def get_settings_for_section(section: ConfigSection) -> Dict[str, ConfigSetting]:
    """Get all settings for a specific section."""
    return {
        path: setting 
        for path, setting in SETTINGS_REGISTRY.items() 
        if setting.section == section
    }


def validate_setting_value(setting_path: str, value: Any) -> bool:
    """Validate a setting value against its expected type and validation function."""
    setting = SETTINGS_REGISTRY.get(setting_path)
    if not setting:
        return False
    
    # Type check
    if value is not None and not isinstance(value, setting.data_type):
        return False
    
    # Custom validation
    if setting.validation_fn and not setting.validation_fn(value):
        return False
    
    return True