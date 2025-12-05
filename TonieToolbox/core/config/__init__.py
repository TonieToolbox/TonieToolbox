#!/usr/bin/python3
"""
Streamlined configuration management for TonieToolbox.

This package provides a single source of truth for all configuration
through the settings registry and streamlined manager.
"""

from .manager import ConfigManager, get_config_manager
from .settings_registry import (
    SETTINGS_REGISTRY,
    TONIETOOLBOX_HOME,
    ConfigSetting,
    ConfigSection,
    get_initial_settings,
    get_default_value,
    get_setting_info,
    build_minimal_config,
    validate_setting_value
)
from .config_access import (
    LoggingAccess,
    TeddyCloudAccess,
    VersionAccess,
    GuiAccess,
    ProcessingAccess
)

__all__ = [
    # Core Configuration Manager
    'ConfigManager',
    'get_config_manager',
    
    # Settings Registry (Domain Layer)
    'SETTINGS_REGISTRY',
    'TONIETOOLBOX_HOME',
    'ConfigSetting',
    'ConfigSection',
    'get_initial_settings',
    'get_default_value',
    'get_setting_info',
    'build_minimal_config',
    'validate_setting_value',
    
    # Typed Access Helpers (Interface Layer)
    'LoggingAccess',
    'TeddyCloudAccess',
    'VersionAccess',
    'GuiAccess',
    'ProcessingAccess'
]