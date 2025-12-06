#!/usr/bin/python3
"""
Direct integration wrapper using the new modular system.
"""
import argparse
import os
import sys
from .manager import install_integration, uninstall_integration
from .base import UploadConfiguration
from ..config import get_config_manager
from ..utils import get_logger

logger = get_logger(__name__)


def handle_integration(args: argparse.Namespace) -> bool:
    """
    Handle integration install/uninstall using the modular system directly.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        True if operation was successful, False otherwise
        
    Raises:
        OSError: If output directory cannot be created
        PermissionError: If insufficient permissions for integration
        ValueError: If upload configuration is invalid
    """
    # Get executable path from args or let integration auto-detect
    # Do NOT set exe_path here - let the integration's _find_executable() handle it
    exe_path = getattr(args, 'exe_path', None)
    
    # Set up output directory
    output_dir = os.path.join(os.path.expanduser("~"), ".tonietoolbox")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create upload configuration from unified config system
    config_manager = get_config_manager()
    raw_config = config_manager.load_config() or {}
    upload_data = raw_config.get('upload', {})
    
    # Ensure all required keys exist with defaults
    upload_data.setdefault('url', [])
    upload_data.setdefault('ignore_ssl_verify', False)
    upload_data.setdefault('username', '')
    upload_data.setdefault('password', '')
    upload_data.setdefault('client_cert_path', '')
    upload_data.setdefault('client_cert_key_path', '')
    
    upload_config = UploadConfiguration(upload_data)
    
    # Determine log level
    log_level = getattr(args, 'loglevel', 'INFO').upper()
    log_to_file = getattr(args, 'log_to_file', False)
    
    # Use the new modular system directly
    if args.install_integration:
        success = install_integration(
            exe_path=exe_path,
            output_dir=output_dir,
            upload_config=upload_config,
            log_level=log_level,
            log_to_file=log_to_file
        )
        if success:
            logger.info("Integration installed successfully.")
            return True
        else:
            logger.error("Integration installation failed.")
            return False
    
    elif args.uninstall_integration:
        success = uninstall_integration(
            exe_path=exe_path,
            output_dir=output_dir,
            upload_config=upload_config,
            log_level=log_level,
            log_to_file=log_to_file
        )
        if success:
            logger.info("Integration uninstalled successfully.")
            return True
        else:
            logger.error("Integration uninstallation failed.")
            return False
    
    return False