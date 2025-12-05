#!/usr/bin/python3
"""
Typed configuration access for TonieToolbox.

This module provides type-safe access to configuration settings
using the settings registry as the single source of truth.
"""

from typing import Optional, Any, TypeVar, Generic, TYPE_CHECKING
from .settings_registry import get_default_value, get_setting_info, validate_setting_value

if TYPE_CHECKING:
    from .manager import ConfigManager

T = TypeVar('T')


class TypedConfigAccess(Generic[T]):
    """Type-safe configuration access helper."""
    
    def __init__(self, manager: 'ConfigManager', base_path: str):
        """
        Initialize typed access helper.
        
        Args:
            manager: ConfigManager instance
            base_path: Base configuration path (e.g., "application.logging")
        """
        self._manager = manager
        self._base_path = base_path
    
    def get(self, key: str, default: Optional[T] = None) -> T:
        """
        Get a configuration value with type safety.
        
        Args:
            key: Setting key (relative to base_path)
            default: Default value if not set
            
        Returns:
            Configuration value with proper typing
        """
        full_path = f"{self._base_path}.{key}"
        value = self._manager.get_setting(full_path)
        
        if value is None and default is not None:
            return default
        return value
    
    def set(self, key: str, value: T) -> bool:
        """
        Set a configuration value with validation.
        
        Args:
            key: Setting key (relative to base_path)  
            value: Value to set
            
        Returns:
            True if successful
        """
        full_path = f"{self._base_path}.{key}"
        return self._manager.set_setting(full_path, value)


class LoggingAccess(TypedConfigAccess[Any]):
    """Typed access for logging configuration."""
    
    @property
    def level(self) -> str:
        return self.get("level", "INFO")
    
    @level.setter
    def level(self, value: str) -> None:
        self.set("level", value)
    
    @property
    def log_to_file(self) -> bool:
        return self.get("log_to_file", False)
    
    @log_to_file.setter
    def log_to_file(self, value: bool) -> None:
        self.set("log_to_file", value)
    
    @property
    def log_file_path(self) -> Optional[str]:
        return self.get("log_file_path")
    
    @log_file_path.setter
    def log_file_path(self, value: Optional[str]) -> None:
        self.set("log_file_path", value)


class TeddyCloudAccess(TypedConfigAccess[Any]):
    """Typed access for TeddyCloud configuration."""
    
    @property
    def url(self) -> Optional[str]:
        return self.get("url")
    
    @url.setter
    def url(self, value: Optional[str]) -> None:
        self.set("url", value)
    
    @property
    def ignore_ssl_verify(self) -> bool:
        return self.get("ignore_ssl_verify", False)
    
    @ignore_ssl_verify.setter
    def ignore_ssl_verify(self, value: bool) -> None:
        self.set("ignore_ssl_verify", value)
    
    @property
    def username(self) -> Optional[str]:
        return self.get("username")
    
    @username.setter
    def username(self, value: Optional[str]) -> None:
        self.set("username", value)
    
    @property
    def password(self) -> Optional[str]:
        return self.get("password")
    
    @password.setter
    def password(self, value: Optional[str]) -> None:
        self.set("password", value)
    
    @property
    def client_cert(self) -> Optional[str]:
        """Get client certificate path."""
        return self.get("certificate_path")
    
    @client_cert.setter
    def client_cert(self, value: Optional[str]) -> None:
        """Set client certificate path."""
        self.set("certificate_path", value)
    
    @property
    def client_key(self) -> Optional[str]:
        """Get client private key path."""
        return self.get("private_key_path")
    
    @client_key.setter
    def client_key(self, value: Optional[str]) -> None:
        """Set client private key path."""
        self.set("private_key_path", value)


class VersionAccess(TypedConfigAccess[Any]):
    """Typed access for version configuration."""
    
    @property
    def check_for_updates(self) -> bool:
        return self.get("check_for_updates", True)
    
    @check_for_updates.setter
    def check_for_updates(self, value: bool) -> None:
        self.set("check_for_updates", value)
    
    @property
    def notify_if_not_latest(self) -> bool:
        return self.get("notify_if_not_latest", True)
    
    @notify_if_not_latest.setter
    def notify_if_not_latest(self, value: bool) -> None:
        self.set("notify_if_not_latest", value)


class GuiAccess(TypedConfigAccess[Any]):
    """Typed access for GUI configuration."""
    
    @property
    def language(self) -> str:
        return self.get("language", "en_US")
    
    @language.setter
    def language(self, value: str) -> None:
        self.set("language", value)
    
    @property
    def auto_detect_language(self) -> bool:
        return self.get("auto_detect_language", True)
    
    @auto_detect_language.setter
    def auto_detect_language(self, value: bool) -> None:
        self.set("auto_detect_language", value)
    
    @property
    def theme(self) -> str:
        return self.get("theme.default_theme", "default")
    
    @theme.setter
    def theme(self, value: str) -> None:
        self.set("theme.default_theme", value)
    
    @property
    def enable_gui(self) -> bool:
        return self.get("enable_gui", True)
    
    @enable_gui.setter
    def enable_gui(self, value: bool) -> None:
        self.set("enable_gui", value)
    
    @property
    def default_theme(self) -> str:
        return self.get("theme.default_theme", "default")
    
    @default_theme.setter
    def default_theme(self, value: str) -> None:
        self.set("theme.default_theme", value)


class ProcessingAccess(TypedConfigAccess[Any]):
    """Typed access for processing configuration."""
    
    @property
    def default_bitrate(self) -> int:
        return self.get("audio.default_bitrate", 128)
    
    @default_bitrate.setter
    def default_bitrate(self, value: int) -> None:
        self.set("audio.default_bitrate", value)
    
    @property
    def default_output_dir(self) -> str:
        return self.get("file_handling.default_output_dir", "./output")
    
    @default_output_dir.setter
    def default_output_dir(self, value: str) -> None:
        self.set("file_handling.default_output_dir", value)


class PluginAccess(TypedConfigAccess[Any]):
    """Typed access for plugin configuration."""
    
    @property
    def enable_plugins(self) -> bool:
        """Global toggle to enable/disable entire plugin system."""
        return self.get("enable_plugins", True)
    
    @enable_plugins.setter
    def enable_plugins(self, value: bool) -> None:
        self.set("enable_plugins", value)
    
    @property
    def auto_discover(self) -> bool:
        """Automatically discover plugins on startup."""
        return self.get("auto_discover", True)
    
    @auto_discover.setter
    def auto_discover(self, value: bool) -> None:
        self.set("auto_discover", value)
    
    @property
    def auto_enable(self) -> bool:
        """Automatically enable discovered plugins."""
        return self.get("auto_enable", True)
    
    @auto_enable.setter
    def auto_enable(self, value: bool) -> None:
        self.set("auto_enable", value)
    
    @property
    def plugin_directories(self) -> list:
        """Additional plugin directories to scan."""
        return self.get("plugin_directories", [])
    
    @plugin_directories.setter
    def plugin_directories(self, value: list) -> None:
        self.set("plugin_directories", value)
    
    @property
    def disabled_plugins(self) -> list:
        """List of plugin IDs to keep disabled."""
        return self.get("disabled_plugins", [])
    
    @disabled_plugins.setter
    def disabled_plugins(self, value: list) -> None:
        self.set("disabled_plugins", value)
    
    @property
    def load_builtin_plugins(self) -> bool:
        """Load built-in plugins from TonieToolbox/core/plugins/builtin."""
        return self.get("load_builtin_plugins", True)
    
    @load_builtin_plugins.setter
    def load_builtin_plugins(self, value: bool) -> None:
        self.set("load_builtin_plugins", value)    
    @property
    def repository_urls(self) -> list:
        """Plugin repository URLs to search for community plugins."""
        return self.get("repository_urls", ["https://raw.githubusercontent.com/TonieToolbox/tonietoolbox_plugins/main/"])
    
    @repository_urls.setter
    def repository_urls(self, value: list) -> None:
        self.set("repository_urls", value)
    
    @property
    def auto_update_check(self) -> bool:
        """Automatically check for plugin updates on startup."""
        return self.get("auto_update_check", True)
    
    @auto_update_check.setter
    def auto_update_check(self, value: bool) -> None:
        self.set("auto_update_check", value)
    
    @property
    def verified_authors(self) -> list:
        """List of verified plugin authors for trust system."""
        return self.get("verified_authors", [])
    
    @verified_authors.setter
    def verified_authors(self, value: list) -> None:
        self.set("verified_authors", value)
    
    def get_plugin_config(self, plugin_id: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier (e.g., "com.tonietoolbox.tonies_loader")
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
            
        Example:
            >>> config.plugins.get_plugin_config("com.tonietoolbox.tonies_loader", "cache_ttl", 86400)
            86400
        """
        # Convert plugin_id to safe key: com.tonietoolbox.tonies_loader -> com_tonietoolbox_tonies_loader
        safe_id = plugin_id.replace('.', '_')
        config_key = f"config.{safe_id}.{key}"
        return self.get(config_key, default)
    
    def set_plugin_config(self, plugin_id: str, key: str, value: Any) -> None:
        """
        Set a configuration value for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            key: Configuration key
            value: Configuration value
            
        Example:
            >>> config.plugins.set_plugin_config("com.tonietoolbox.tonies_loader", "cache_ttl", 3600)
        """
        safe_id = plugin_id.replace('.', '_')
        config_key = f"config.{safe_id}.{key}"
        self.set(config_key, value)
    
    def get_all_plugin_config(self, plugin_id: str) -> dict:
        """
        Get all configuration for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Dictionary of all plugin configuration
            
        Example:
            >>> config.plugins.get_all_plugin_config("com.tonietoolbox.tonies_loader")
            {'cache_ttl': 86400, 'auto_update': True}
        """
        safe_id = plugin_id.replace('.', '_')
        config_key = f"config.{safe_id}"
        return self.get(config_key, {})
    
    def set_all_plugin_config(self, plugin_id: str, config_dict: dict) -> None:
        """
        Set all configuration for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            config_dict: Dictionary of configuration values
            
        Example:
            >>> config.plugins.set_all_plugin_config("com.tonietoolbox.tonies_loader", {
            ...     "cache_ttl": 3600,
            ...     "auto_update": False
            ... })
        """
        safe_id = plugin_id.replace('.', '_')
        config_key = f"config.{safe_id}"
        self.set(config_key, config_dict)
    
    @property
    def update_check_interval(self) -> int:
        """Interval in seconds between update checks."""
        return self.get("update_check_interval", 86400)
    
    @update_check_interval.setter
    def update_check_interval(self, value: int) -> None:
        self.set("update_check_interval", value)
    
    @property
    def install_location(self) -> str:
        """Base directory for community plugin installations."""
        return self.get("install_location", "")
    
    @install_location.setter
    def install_location(self, value: str) -> None:
        self.set("install_location", value)
    
    @property
    def allow_unverified(self) -> bool:
        """Allow installation of unverified plugins."""
        return self.get("allow_unverified", False)
    
    @allow_unverified.setter
    def allow_unverified(self, value: bool) -> None:
        self.set("allow_unverified", value)
    
    @property
    def max_parallel_downloads(self) -> int:
        """Maximum number of parallel plugin downloads."""
        return self.get("max_parallel_downloads", 3)
    
    @max_parallel_downloads.setter
    def max_parallel_downloads(self, value: int) -> None:
        self.set("max_parallel_downloads", value)
    
    @property
    def verify_checksums(self) -> bool:
        """Verify SHA512 checksums when installing plugins."""
        return self.get("verify_checksums", True)
    
    @verify_checksums.setter
    def verify_checksums(self, value: bool) -> None:
        self.set("verify_checksums", value)
