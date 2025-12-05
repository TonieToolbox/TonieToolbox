#!/usr/bin/python3
"""
Argument Parser Factory for TonieToolbox.

This factory creates argument parsers while maintaining Clean Architecture
by keeping the config manager dependencies in the application layer.
"""

from typing import Dict, Any, Optional
import logging

from .argument_parser import TonieToolboxArgumentParser
from ..config import ConfigManager


class ArgumentParserFactory:
    """Factory for creating argument parsers with proper dependency injection."""
    
    @staticmethod
    def create_parser(config_manager: Optional[ConfigManager] = None) -> TonieToolboxArgumentParser:
        """
        Create an argument parser with configuration defaults injected.
        
        Args:
            config_manager: Optional config manager to extract defaults from.
                           If None, system defaults will be used.
        
        Returns:
            Configured TonieToolboxArgumentParser instance
        """
        default_values = ArgumentParserFactory._extract_cli_defaults(config_manager)
        return TonieToolboxArgumentParser(default_values)
    
    @staticmethod
    def _extract_cli_defaults(config_manager: Optional[ConfigManager]) -> Dict[str, Any]:
        """
        Extract CLI default values from config manager.
        
        Args:
            config_manager: Config manager instance or None
            
        Returns:
            Dictionary of default values for CLI arguments
        """
        if not config_manager:
            # Fallback defaults when no config manager available (match config defaults)
            return {
                'default_bitrate': 128,
                'connection_timeout': 10,
                'read_timeout': 300,
                'max_retries': 3,
                'retry_delay': 5,
            }
        
        try:
            return {
                'default_bitrate': config_manager.get_setting('processing.audio.default_bitrate'),
                'connection_timeout': config_manager.get_setting('application.teddycloud.connection_timeout'),
                'read_timeout': config_manager.get_setting('application.teddycloud.read_timeout'),
                'max_retries': config_manager.get_setting('application.teddycloud.max_retries'),
                'retry_delay': config_manager.get_setting('application.teddycloud.retry_delay'),
            }
        except Exception as e:
            # Log error and fall back to system defaults
            from ..utils.logging import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Failed to extract config defaults, using system defaults: {e}")
            return ArgumentParserFactory._extract_cli_defaults(None)