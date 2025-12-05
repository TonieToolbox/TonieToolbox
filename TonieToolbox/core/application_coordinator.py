#!/usr/bin/python3
"""
Application coordinator for TonieToolbox.

This module provides clean separation between GUI and file processing concerns
by coordinating which mode of operation should be used without tight coupling.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

from .processing.main_service import MainProcessingService
from .utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)

if TYPE_CHECKING:
    pass  # No more tkinter GUI dependencies


class ApplicationCoordinator:
    """
    Coordinates between GUI and file processing modes without tight coupling.
    
    This coordinator serves as the main entry point for the application, determining
    whether to launch GUI mode or execute file processing operations based on command-line
    arguments. It maintains separation of concerns by delegating to specialized services.
    
    Example:
        >>> from TonieToolbox.core.utils import get_logger
        >>> from TonieToolbox.core.processing.main_service import MainProcessingService
        >>> 
        >>> # Initialize coordinator
        >>> logger = get_logger(__name__)
        >>> coordinator = ApplicationCoordinator(logger)
        >>> 
        >>> # Set up processing service
        >>> dependencies = {'ffmpeg': '/usr/bin/ffmpeg'}
        >>> processing_service = MainProcessingService(dependencies, logger)
        >>> coordinator.set_processing_service(processing_service)
        >>> 
        >>> # Execute with command-line args
        >>> import argparse
        >>> args = argparse.Namespace(gui=False, input_filename='audio.mp3', output='output.taf')
        >>> exit_code = coordinator.execute(args)
        >>> print(f"Processing completed with exit code: {exit_code}")
        Processing completed with exit code: 0
    """
    
    def __init__(self, _logger: logging.Logger = None):
        """Initialize coordinator (logger parameter kept for compatibility)."""
        self.gui_factory: Optional['GUIFactory'] = None
        self.processing_service: Optional[MainProcessingService] = None
    
    def set_gui_factory(self, gui_factory: 'GUIFactory') -> None:
        """Set the GUI factory for launching GUI mode."""
        self.gui_factory = gui_factory
    
    def set_processing_service(self, processing_service: MainProcessingService) -> None:
        """Set the processing service for file operations."""
        self.processing_service = processing_service
    
    def execute(self, args) -> int:
        """
        Execute the main application logic.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code: 0 for success, non-zero for errors
        """
        # Handle GUI mode (both --gui and --play flags)
        if args.gui or args.play:
            return self._launch_gui_mode(args)
        
        # Handle file processing mode
        if not self.processing_service:
            logger.error("Processing service not configured")
            return 1
            
        return self.processing_service.process_files(args)
    
    def _launch_gui_mode(self, args) -> int:
        """Launch GUI mode if factory is available."""
        if not self.gui_factory:
            logger.error("GUI mode requested but GUI factory not available")
            return 1
        
        logger.info("Launching TonieToolbox GUI")
        
        try:
            # Extract input path (file or directory) if provided
            input_path = None
            auto_play = getattr(args, 'play', False)
            
            if (hasattr(args, 'input_filename') and args.input_filename and 
                os.path.exists(args.input_filename)):
                input_path = Path(args.input_filename)
            
            return self.gui_factory.create_and_run_gui(input_path, logger, auto_play)
            
        except Exception as e:
            logger.error("Failed to launch GUI: %s", e)
            return 1


class GUIFactory:
    """Factory for creating and managing GUI applications."""
    
    def __init__(self):
        """Initialize GUI factory."""
        self.plugin_manager = None
    
    def set_plugin_manager(self, plugin_manager) -> None:
        """Set the plugin manager for GUI integration."""
        self.plugin_manager = plugin_manager
    
    def create_and_run_gui(self, input_path: Optional[Path] = None, 
                          logger: Optional[logging.Logger] = None,
                          auto_play: bool = False) -> int:
        """
        Create and run the GUI application.
        
        Args:
            input_path: Optional TAF file or directory to pre-load
            logger: Optional logger instance
            auto_play: Whether to auto-play the content
            
        Returns:
            Exit code from GUI application
        """
        # Use centralized GUI dependency management
        try:
            from .dependencies.gui import get_gui_dependency_manager
            
            gui_manager = get_gui_dependency_manager()
            gui_type, gui_info = gui_manager.get_best_gui_option()
            
            if gui_type == 'pyqt6':
                if logger:
                    logger.info(f"Launching PyQt6 GUI interface (version: {gui_info.version})")
                from .gui import qt_gui_player
                return qt_gui_player(input_path, auto_play=auto_play, plugin_manager=self.plugin_manager)                
            else:
                if logger:
                    logger.error(f"No GUI interface available: {gui_info.error}")
                    logger.info("To install PyQt6, run: pip install PyQt6>=6.10.0")
                return 1
                
        except Exception as e:
            if logger:
                logger.error(f"Error initializing GUI: {e}")
            return 1
    
