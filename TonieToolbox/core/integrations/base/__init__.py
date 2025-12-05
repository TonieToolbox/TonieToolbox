#!/usr/bin/python3
"""
Base Integration Classes and Utilities.

This module provides the foundational classes for platform-specific desktop integrations.
It includes base integration classes, command builders, template managers, and configuration
models. All platform-specific integrations (Windows, macOS, Linux) inherit from these base
classes to ensure consistent behavior across different operating systems.
"""

from .integration import BaseIntegration, UploadConfiguration, CommandBuilder
from .commands import IntegrationCommand, CommandSet, StandardCommandFactory, PlatformCommandAdapter
from .templates import (
    IntegrationTemplate, DesktopEntryTemplate, ServiceMenuTemplate, 
    ThunarActionTemplate, RegistryTemplate, MacOSActionTemplate,
    TemplateManager, get_template_manager
)

__all__ = [
    'BaseIntegration',
    'UploadConfiguration', 
    'CommandBuilder',
    'IntegrationCommand',
    'CommandSet',
    'StandardCommandFactory',
    'PlatformCommandAdapter',
    'IntegrationTemplate',
    'DesktopEntryTemplate',
    'ServiceMenuTemplate',
    'ThunarActionTemplate', 
    'RegistryTemplate',
    'MacOSActionTemplate',
    'TemplateManager',
    'get_template_manager'
]