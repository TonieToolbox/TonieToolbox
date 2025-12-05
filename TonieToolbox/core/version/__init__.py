#!/usr/bin/python3
"""
Version management module for TonieToolbox.

This module provides comprehensive version checking, update management,
and configuration handling with proper error handling and security.
"""
from typing import Optional, Tuple
from ..config import get_config_manager
from .version_checker import VersionChecker, VersionCheckError, NetworkError, CacheError


def get_version_checker() -> VersionChecker:
    """
    Get a configured version checker instance.
        
    Returns:
        Configured VersionChecker instance
    """
    config_manager = get_config_manager()
    return VersionChecker(config_manager)


def get_pypi_version(force_refresh: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Get the latest version from PyPI.
    
    Args:
        force_refresh: If True, bypass cache and fetch directly from PyPI
        
    Returns:
        Tuple of (latest_version, error_message)
    """
    checker = get_version_checker()
    return checker.get_latest_version(force_refresh)


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings according to PEP 440.
    
    Args:
        v1: First version string
        v2: Second version string
        
    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    checker = get_version_checker()
    return checker.compare_versions(v1, v2)


def check_for_updates(quiet: bool = False, force_refresh: bool = False) -> Tuple[bool, Optional[str], str, bool]:
    """
    Check if the current version is the latest available.
    
    Args:
        quiet: If True, suppress interactive prompts
        force_refresh: If True, bypass cache and check PyPI directly
        
    Returns:
        Tuple of (is_latest, latest_version, message, update_confirmed)
    """
    checker = get_version_checker()
    return checker.check_for_updates(quiet, force_refresh)


def clear_version_cache() -> bool:
    """
    Clear the version cache file.
        
    Returns:
        True if cache was cleared, False otherwise
    """
    checker = get_version_checker()
    return checker.clear_cache()

def install_update() -> bool:
    """
    Install the latest update.
        
    Returns:
        True if update was installed successfully, False otherwise
    """
    checker = get_version_checker()
    return checker.install_update()

__all__ = [
    'VersionChecker', 
    'VersionCheckError',
    'NetworkError',
    'CacheError',
    'get_version_checker',
    'get_pypi_version',
    'compare_versions', 
    'check_for_updates',
    'clear_version_cache',
    'install_update'
]