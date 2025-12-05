#!/usr/bin/python3
"""
Version management commands for TonieToolbox.

This module handles all version-related operations including update checking,
cache management, and version display.
"""

import logging

from ..version import get_version_checker, clear_version_cache
from ..config import get_config_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class VersionCommandProcessor:
    """Handles all version-related commands and operations."""
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize version command processor (logger parameter kept for compatibility)."""
        pass
    
    def should_handle_version_commands(self, args) -> bool:
        """Check if any version-related commands should be handled."""
        return (getattr(args, 'clear_version_cache', False) or 
                getattr(args, 'check_updates_only', False))
    
    def process_version_commands(self, args) -> int:
        """Process version commands that should exit immediately."""
        if getattr(args, 'clear_version_cache', False):
            return self.clear_cache(args)
            
        if getattr(args, 'check_updates_only', False):
            self.check_updates(args)
            return 0
            
        return 0
    
    def clear_cache(self, args) -> int:
        """Clear version cache and exit."""
        logger.debug("Clearing version cache")
        if clear_version_cache():
            logger.info("Version cache cleared successfully")
        else:
            logger.info("No version cache to clear or error clearing cache")
        return 0
    
    def check_updates(self, args) -> None:
        """Check for available updates."""
        logger.debug("Checking for updates")
        
        # Get version config from unified configuration system
        config_manager = get_config_manager()
        version_config = config_manager.version
        
        # Override with command line arguments if provided
        if hasattr(args, 'skip_update_check') and args.skip_update_check:
            version_config.check_for_updates = False
        if hasattr(args, 'force_update_check') and args.force_update_check:
            pass
        if hasattr(args, 'disable_notifications') and args.disable_notifications:
            version_config.notify_if_not_latest = False
        if hasattr(args, 'include_pre_releases') and args.include_pre_releases:
            version_config.pre_releases = True
        
        # Get version checker instance (uses ConfigManager internally)
        version_checker = get_version_checker()
        
        try:
            # Check for updates using new version checker
            is_latest, latest_version, message, update_confirmed = version_checker.check_for_updates()
            
            logger.debug("Update check results: is_latest=%s, latest_version=%s, "
                             "message=%s, update_confirmed=%s", is_latest, latest_version, message, update_confirmed)
            
            # Handle update notification based on configuration
            if not is_latest and version_config.notify_if_not_latest:
                if not (hasattr(args, 'silent') and args.silent) and not (hasattr(args, 'quiet') and args.quiet):
                    from ... import __version__
                    logger.info(f"A newer version {latest_version} is available. "
                                   f"You are running {__version__}.")
                    
        except Exception as e:
            logger.debug(f"Error checking for updates: {e}")
            # Don't let update check failures stop the application
    
    def process_version_check(self, args) -> None:
        """Handle version checking if not skipped."""
        if not args.skip_update_check:
            self.check_updates(args)