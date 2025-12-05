#!/usr/bin/env python3
"""
Plugin System for TonieToolbox.

This module provides an extensible plugin architecture allowing developers to add
custom features, GUI components, processors, and integrations without modifying core code.

Plugin Types:
- GUI Plugins: Add custom UI components, dialogs, and menu items
- Processor Plugins: Add custom file processors and converters
- Integration Plugins: Add custom integrations with external services
- Tool Plugins: Add custom tools and utilities

Example Plugin:
    ```python
    from TonieToolbox.core.plugins import BasePlugin, PluginManifest
    
    class MyCustomPlugin(BasePlugin):
        def get_manifest(self) -> PluginManifest:
            return PluginManifest(
                id="my.custom.plugin",
                name="My Custom Plugin",
                version="1.0.0",
                author="Your Name",
                description="Custom functionality for TonieToolbox"
            )
        
        def initialize(self, context):
            # Register components, processors, etc.
            pass
    ```
"""

from .base import (
    BasePlugin,
    PluginContext,
    PluginManifest,
    PluginMetadata,
    PluginDependency,
    PluginDependencies,
    PluginInstallInfo,
    PluginType,
    PluginSource,
    load_manifest_from_json
)
from .manager import PluginManager, get_plugin_manager
from .registry import PluginRegistry
from .loader import PluginLoader
from .repository import PluginRepository
from .dependency_resolver import DependencyResolver
from .installer import PluginInstaller
from .trust import TrustManager, TrustLevel, TrustBadge, get_trust_manager
from .dependency_parser import (
    parse_dependency_string,
    parse_dependencies,
    check_version_compatibility,
    get_dependency_conflicts,
    get_missing_dependencies,
    DependencyParseError
)
from .plugin_config import PluginConfigManager
from .testing import PluginTester, PluginTestReport, TestResult, test_plugin_cli
from .scaffolding import PluginScaffolder, create_plugin_cli
from .exceptions import (
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    PluginManifestError,
    PluginInitializationError,
    PluginDependencyError,
    PluginConfigurationError,
    DependencyNotFoundError,
    DependencyVersionError,
    CircularDependencyError,
    PluginInstallationError,
    PluginChecksumError,
    PluginConfigurationError,
    PluginSecurityError,
    PluginTrustError
)
from .events import (
    PluginLoadedEvent,
    PluginUnloadedEvent,
    PluginErrorEvent,
    PluginEnabledEvent,
    PluginDisabledEvent,
    PluginInstalledEvent,
    PluginReloadedEvent,
    PluginGuiComponentsChangedEvent
)

__all__ = [
    # Base classes
    'BasePlugin',
    'PluginContext',
    'PluginManifest',
    'PluginMetadata',
    'PluginDependency',
    'PluginDependencies',
    'PluginInstallInfo',
    'PluginType',
    'PluginSource',
    'load_manifest_from_json',
    
    # Management
    'PluginManager',
    'get_plugin_manager',
    'PluginRegistry',
    'PluginLoader',
    
    # Repository & Installation
    'PluginRepository',
    'DependencyResolver',
    'PluginInstaller',
    
    # Trust & Security
    'TrustManager',
    'TrustLevel',
    'TrustBadge',
    'get_trust_manager',
    
    # Dependencies
    'parse_dependency_string',
    'parse_dependencies',
    'check_version_compatibility',
    'get_dependency_conflicts',
    'get_missing_dependencies',
    'DependencyParseError',
    
    # Configuration
    'PluginConfigManager',
    'PluginConfigurationError',
    
    # Testing & Development
    'PluginTester',
    'PluginTestReport',
    'TestResult',
    'test_plugin_cli',
    'PluginScaffolder',
    'create_plugin_cli',
    
    # Exceptions
    'PluginError',
    'PluginLoadError',
    'PluginNotFoundError',
    'PluginManifestError',
    'PluginInitializationError',
    'PluginDependencyError',
    'DependencyNotFoundError',
    'DependencyVersionError',
    'CircularDependencyError',
    'PluginInstallationError',
    'PluginChecksumError',
    'PluginConfigurationError',
    'PluginSecurityError',
    'PluginTrustError',
    
    # Events
    'PluginLoadedEvent',
    'PluginUnloadedEvent',
    'PluginErrorEvent',
    'PluginEnabledEvent',
    'PluginDisabledEvent',
    'PluginInstalledEvent',
    'PluginReloadedEvent',
    'PluginGuiComponentsChangedEvent',
]
