#!/usr/bin/env python3
"""
Exception hierarchy for plugin system.

Provides structured error handling with specific exception types
for different failure modes in the plugin system.
"""


class PluginError(Exception):
    """Base exception for all plugin-related errors."""
    pass


# Loading & Discovery Errors
class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found."""
    pass


class PluginManifestError(PluginError):
    """Raised when a plugin manifest is invalid or missing."""
    pass


# Initialization & Lifecycle Errors
class PluginInitializationError(PluginError):
    """Raised when plugin initialization fails."""
    pass


class PluginEnableError(PluginError):
    """Raised when plugin cannot be enabled."""
    pass


class PluginDisableError(PluginError):
    """Raised when plugin cannot be disabled."""
    pass


# Dependency Errors
class PluginDependencyError(PluginError):
    """Base exception for dependency-related errors."""
    pass


class DependencyNotFoundError(PluginDependencyError):
    """Raised when a required dependency is not found."""
    pass


class DependencyVersionError(PluginDependencyError):
    """Raised when dependency version is incompatible."""
    pass


class CircularDependencyError(PluginDependencyError):
    """Raised when circular dependencies are detected."""
    pass


# Installation Errors
class PluginInstallationError(PluginError):
    """Raised when plugin installation fails."""
    pass


class PluginDownloadError(PluginInstallationError):
    """Raised when plugin download fails."""
    pass


class PluginChecksumError(PluginInstallationError):
    """Raised when checksum verification fails."""
    pass


class PluginRepositoryError(PluginError):
    """Raised when repository operations fail."""
    pass


# Configuration Errors
class PluginConfigurationError(PluginError):
    """Raised when plugin configuration is invalid."""
    pass


class ConfigSchemaValidationError(PluginConfigurationError):
    """Raised when config doesn't match schema."""
    pass


# Security & Trust Errors
class PluginSecurityError(PluginError):
    """Raised when security checks fail."""
    pass


class PluginTrustError(PluginSecurityError):
    """Raised when plugin trust verification fails."""
    pass


class PluginPermissionError(PluginSecurityError):
    """Raised when plugin lacks required permissions."""
    pass


# Registry Errors
class PluginRegistryError(PluginError):
    """Raised when registry operations fail."""
    pass


class PluginAlreadyRegisteredError(PluginRegistryError):
    """Raised when attempting to register an already registered plugin."""
    pass


# Version Errors
class PluginVersionError(PluginError):
    """Raised when version operations fail."""
    pass


class IncompatibleVersionError(PluginVersionError):
    """Raised when plugin version is incompatible with TonieToolbox."""
    pass
