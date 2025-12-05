#!/usr/bin/python3
"""
Streamlined configuration manager for TonieToolbox.

This version eliminates dataclass duplication by working directly with
the settings registry as the single source of truth.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .settings_registry import (
    SETTINGS_REGISTRY, 
    TONIETOOLBOX_HOME,
    build_minimal_config, 
    get_initial_settings,
    get_default_value,
    validate_setting_value
)
from .config_access import LoggingAccess, TeddyCloudAccess, VersionAccess, GuiAccess, ProcessingAccess, PluginAccess


class ConfigManager:
    """
    Configuration manager using settings registry as single source of truth.
    
    Eliminates duplication by working directly with the centralized settings registry.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = config_file or self._get_default_config_file()
        self._config_data: Optional[Dict[str, Any]] = None
        
        # Typed access helpers
        self._logging_access: Optional[LoggingAccess] = None
        self._teddycloud_access: Optional[TeddyCloudAccess] = None
        self._version_access: Optional[VersionAccess] = None
        self._gui_access: Optional[GuiAccess] = None
        self._processing_access: Optional[ProcessingAccess] = None
        self._plugin_access: Optional[PluginAccess] = None
        
        # Load configuration on initialization
        self._load_config()
    
    def _get_default_config_file(self) -> str:
        """Get the default configuration file path."""
        return os.path.join(TONIETOOLBOX_HOME, "config.json")
    
    @property
    def config_file_path(self) -> str:
        """Get the configuration file path."""
        return self.config_file
    
    def _load_config(self) -> None:
        """Load configuration from file or create minimal default."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config from {self.config_file}: {e}")
                self._config_data = build_minimal_config()
        else:
            # No config exists - create and save initial config file
            self.create_default_config()
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load and return raw configuration data.
        
        Returns:
            Configuration dictionary or None if not found
        """
        if self._config_data is None:
            self._load_config()
        return self._config_data
    
    def save_config(self) -> bool:
        """
        Save configuration to file with only initial + non-default values.
        
        Returns:
            True if saved successfully
        """
        try:
            # Ensure config directory exists
            config_dir = os.path.dirname(self.config_file)
            os.makedirs(config_dir, exist_ok=True)
            
            # Build minimal config with only initial + non-default values
            config_to_save = self._build_minimal_config_data()
            
            # Write to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving config to {self.config_file}: {e}")
            return False
    
    def _build_minimal_config_data(self) -> Dict[str, Any]:
        """Build configuration data with only initial settings and non-default values."""
        config = {}
        
        # Start with all initial settings
        for setting_path in get_initial_settings():
            default_value = get_default_value(setting_path)
            self._set_nested_value(config, setting_path, default_value)
        
        # Add any non-default values from current config
        if self._config_data:
            for setting_path, setting_info in SETTINGS_REGISTRY.items():
                if not setting_info.is_initial:  # Skip initial settings (already added)
                    current_value = self._get_current_value_for_path(setting_path)
                    if current_value != setting_info.default_value:
                        self._set_nested_value(config, setting_path, current_value)
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> None:
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
    
    def _get_current_value_for_path(self, setting_path: str) -> Any:
        """Get current value for a setting path."""
        if not self._config_data:
            return get_default_value(setting_path)
        
        parts = setting_path.split('.')
        current = self._config_data
        
        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            return get_default_value(setting_path)
    
    def get_setting(self, setting_path: str) -> Any:
        """
        Get a configuration setting value.
        
        Args:
            setting_path: Dot-notation path to setting
            
        Returns:
            Current setting value or default if not set
        """
        return self._get_current_value_for_path(setting_path)
    
    def set_setting(self, setting_path: str, value: Any) -> bool:
        """
        Set a configuration setting and mark it for persistence.
        
        Args:
            setting_path: Dot-notation path to setting
            value: Value to set
            
        Returns:
            True if setting was valid and set successfully
        """
        if not validate_setting_value(setting_path, value):
            print(f"Error: Invalid value for setting {setting_path}: {value}")
            return False
        
        # Initialize config data if needed
        if self._config_data is None:
            self._config_data = build_minimal_config()
        
        # Update the config data
        self._set_nested_value(self._config_data, setting_path, value)
        
        return True
    
    # Typed property accessors for configuration sections
    @property
    def logging(self) -> LoggingAccess:
        """Get typed logging configuration access."""
        if self._logging_access is None:
            self._logging_access = LoggingAccess(self, "application.logging")
        return self._logging_access
    
    @property
    def teddycloud(self) -> TeddyCloudAccess:
        """Get typed TeddyCloud configuration access."""
        if self._teddycloud_access is None:
            self._teddycloud_access = TeddyCloudAccess(self, "application.teddycloud")
        return self._teddycloud_access
    
    @property
    def version(self) -> VersionAccess:
        """Get typed version configuration access."""
        if self._version_access is None:
            self._version_access = VersionAccess(self, "application.version")
        return self._version_access
    
    @property
    def gui(self) -> GuiAccess:
        """Get typed GUI configuration access."""
        if self._gui_access is None:
            self._gui_access = GuiAccess(self, "gui")
        return self._gui_access
    
    @property
    def processing(self) -> ProcessingAccess:
        """Get typed processing configuration access."""
        if self._processing_access is None:
            self._processing_access = ProcessingAccess(self, "processing")
        return self._processing_access
    
    @property
    def plugins(self) -> PluginAccess:
        """Get typed plugin configuration access."""
        if self._plugin_access is None:
            self._plugin_access = PluginAccess(self, "plugins")
        return self._plugin_access
    
    def reload_config(self) -> None:
        """Reload configuration from file, clearing cached objects."""
        self._config_data = None
        self._logging_access = None
        self._teddycloud_access = None
        self._version_access = None
        self._gui_access = None
        self._processing_access = None
        self._plugin_access = None
        self._load_config()
    
    def create_default_config(self) -> bool:
        """
        Create a default configuration file.
        
        Returns:
            True if created successfully
        """
        self._config_data = build_minimal_config()
        return self.save_config()


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        ConfigManager instance
    """
    global _global_config_manager
    if _global_config_manager is None or config_file:
        _global_config_manager = ConfigManager(config_file)
    return _global_config_manager