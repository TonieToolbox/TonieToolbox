#!/usr/bin/python3
"""
Integration management commands for TonieToolbox.

This module handles system integration operations including context menu
installation, uninstallation, and configuration management.
"""

import logging
import os
import platform
import subprocess

from ..integrations import handle_integration
from ..config import get_config_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)
from ..utils.logging import get_logger

logger = get_logger(__name__)


class IntegrationCommandProcessor:
    """Handles all system integration operations."""
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize integration command processor (logger parameter kept for compatibility)."""
        pass
    
    def should_handle_integration_commands(self, args) -> bool:
        """Check if any integration commands should be handled."""
        return (getattr(args, 'install_integration', False) or 
                getattr(args, 'uninstall_integration', False) or
                getattr(args, 'config_integration', False))
    
    def process_integration_commands(self, args, dependency_processor) -> int:
        """Process integration commands that should exit immediately."""
        if getattr(args, 'install_integration', False) or getattr(args, 'uninstall_integration', False):
            return self.handle_integration(args, dependency_processor)
            
        if getattr(args, 'config_integration', False):
            return self.handle_config(args)
            
        return 0
    
    def handle_integration(self, args, dependency_processor) -> int:
        """Handle integration installation/uninstallation."""
        # Validate dependencies first
        if not dependency_processor.validate_integration_dependencies(args):
            return 1
            
        logger.debug("Context menu integration requested: install=%s, uninstall=%s",
                         args.install_integration, args.uninstall_integration)
        
        success = handle_integration(args)
        if success:
            if args.install_integration:
                logger.info("Context menu integration installed successfully")
            else:
                logger.info("Context menu integration uninstalled successfully")
            return 0
        else:
            logger.error("Failed to handle context menu integration")
            return 1
    
    def handle_config(self, args) -> int:
        """Handle configuration management."""
        logger.debug("Opening configuration file for editing")
        
        # Get config file path from unified ConfigManager
        config_manager = get_config_manager()
        config_path = config_manager.config_file_path
        
        if not os.path.exists(config_path):
            logger.info(f"Configuration file not found at {config_path}.")
            logger.info("Creating a new configuration file. Using --install-integration will create a new config file.")
            return 0
        
        # Open configuration file with system default editor
        if platform.system() == "Windows":
            os.startfile(config_path)
        elif platform.system() == "Darwin":
            subprocess.call(["open", config_path])
        elif platform.system() == "Linux":
            subprocess.call(["xdg-open", config_path])
        else:
            logger.error(f"Unsupported OS: {platform.system()}")
            return 1
            
        return 0