#!/usr/bin/python3
"""
Main application class for TonieToolbox.

This module contains the main TonieToolboxApp class that orchestrates
all operations after the refactoring from the monolithic main function.
"""

import sys
import logging
from typing import List, Optional
from pathlib import Path

from .. import __version__
from .parser import ArgumentParserFactory
from .utils.logging import setup_logging_from_args, get_logger
from .command_coordinator import CommandCoordinator
from .config import get_config_manager
from .processing.main_service import MainProcessingService
from .teddycloud import (
    TeddyCloudService, TeddyCloudTagCoordinator,
    TeddyCloudDirectUploadProcessor, create_teddycloud_connection_from_args,
    get_teddycloud_service, get_teddycloud_provider
)
from .processing.application import CustomJsonProcessor
from .utils.input import InputProcessor
from .application_coordinator import ApplicationCoordinator, GUIFactory
from .plugins.manager import PluginManager
from .plugins.base import PluginContext


class TonieToolboxApp:
    """Main application orchestrator for TonieToolbox."""
    
    def __init__(self):
        """Initialize the application with all necessary components."""
        self.logger: Optional[logging.Logger] = None
        self.config_manager = get_config_manager()
        self.arg_parser = ArgumentParserFactory.create_parser(self.config_manager)
        self.command_coordinator: Optional[CommandCoordinator] = None
        self.coordinator: Optional[ApplicationCoordinator] = None
        self.teddycloud_service: Optional[TeddyCloudService] = None
        self.plugin_manager: Optional[PluginManager] = None
        
    def run(self, args: Optional[List[str]] = None) -> int:
        """
        Main entry point with comprehensive error handling.
        
        Args:
            args: Command line arguments. If None, uses sys.argv
            
        Returns:
            Exit code: 0 for success, non-zero for errors
        """
        try:
            return self._execute(args)
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Operation cancelled by user")
            return 130  # Standard exit code for SIGINT
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}")
            else:
                print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def _should_setup_teddycloud(self, args) -> bool:
        """Check if TeddyCloud setup is needed."""
        return (hasattr(args, 'upload') and args.upload is not None) or \
               (hasattr(args, 'get_tags') and args.get_tags is not None) or \
               (hasattr(args, 'create_custom_json') and args.create_custom_json)
    
    def _execute(self, args: Optional[List[str]]) -> int:
        """Internal execution method with the main application logic."""
        # Parse arguments
        parsed_args = self.arg_parser.parse_args(args)
        
        # Setup logging configuration
        setup_logging_from_args(parsed_args)
        
        # Use module-level logger
        self.logger = get_logger(__name__)
        
        # Log startup information
        self.logger.debug(f"Starting TonieToolbox v{__version__} with log level: {logging.getLevelName(self.logger.getEffectiveLevel())}")
        self.logger.debug(f"Command-line arguments: {vars(parsed_args)}")
        
        # Initialize plugin system early if enabled
        if self.config_manager.plugins.enable_plugins:
            try:
                self.plugin_manager = PluginManager(
                    config_manager=self.config_manager,
                    app_version=__version__
                )
                
                # Discover plugins if auto-discovery is enabled
                if self.config_manager.plugins.auto_discover:
                    self.plugin_manager.discover_and_load_plugins()
                    self.logger.debug(f"Loaded {len(self.plugin_manager.get_loaded_plugins())} plugins")
                else:
                    self.logger.debug("Plugin auto-discovery disabled")
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize plugin system: {e}")
        else:
            self.logger.info("Plugin system disabled in configuration")
        
        # Initialize TeddyCloud service provider for unified access (CLI, GUI, Plugins)
        try:
            teddycloud_provider = get_teddycloud_provider()
            teddycloud_provider.initialize(self.config_manager, self.logger)
            
            # Register TeddyCloud service for plugin access
            if self.plugin_manager and teddycloud_provider.get_service():
                PluginContext._shared_services['teddycloud'] = teddycloud_provider.get_service()
                self.logger.debug("TeddyCloud service registered for plugin access")
        except Exception as e:
            self.logger.warning(f"Failed to initialize TeddyCloud service provider: {e}")
        
        # Initialize command coordinator
        self.command_coordinator = CommandCoordinator(self.logger)
        
        # Handle early exit commands (clear cache, integration install/uninstall, config)
        if self.command_coordinator.should_handle_early_exit_commands(parsed_args):
            return self.command_coordinator.process_early_exit_commands(parsed_args)
        
        # Process version check
        self.command_coordinator.process_version_check(parsed_args)
        
        # Setup dependencies (FFmpeg)
        dependencies = self.command_coordinator.setup_dependencies(parsed_args)
        
        # Normalize input paths
        if parsed_args.input_filename:
            parsed_args.input_filename = InputProcessor.normalize_input_path(parsed_args.input_filename)
        
        # Setup TeddyCloud service if needed
        if self._should_setup_teddycloud(parsed_args):
            # Get service from provider (already initialized)
            teddycloud_provider = get_teddycloud_provider()
            
            # If provider has auto-connected from config, use that service
            if teddycloud_provider.is_connected():
                self.teddycloud_service = teddycloud_provider.get_service()
            else:
                # Connect using command-line arguments
                connection = create_teddycloud_connection_from_args(parsed_args)
                if connection:
                    self.teddycloud_service = teddycloud_provider.get_service()
                    if self.teddycloud_service:
                        try:
                            success = self.teddycloud_service.connect(connection)
                            if not success:
                                self.logger.error("Failed to connect to TeddyCloud server")
                                self.teddycloud_service = None
                        except Exception as e:
                            self.logger.error("TeddyCloud connection failed: %s", str(e))
                            self.teddycloud_service = None
            
            # Handle get-tags command
            if parsed_args.get_tags is not None:
                if self.teddycloud_service:
                    coordinator = TeddyCloudTagCoordinator(self.teddycloud_service, self.logger)
                    return coordinator.get_and_display_tags()
                else:
                    self.logger.error("TeddyCloud service not available for tag retrieval")
                    return 1
        
        # Handle direct upload of existing files
        if self.teddycloud_service:
            direct_upload_processor = TeddyCloudDirectUploadProcessor(self.logger, {})
            if direct_upload_processor.should_handle_direct_upload(parsed_args):
                return direct_upload_processor.process(parsed_args)
        
        # Handle custom JSON creation (fetch-only mode)
        if parsed_args.create_custom_json and not parsed_args.input_filename:
            return self._handle_custom_json_fetch_only(parsed_args)
        
        # Setup application coordinator with file processor and GUI factory
        self.coordinator = ApplicationCoordinator(self.logger)
        
        # Setup processing service
        processing_service = MainProcessingService(dependencies, self.logger)
        self.coordinator.set_processing_service(processing_service)
        
        # Setup GUI factory with plugin manager
        gui_factory = GUIFactory()
        if self.plugin_manager:
            gui_factory.set_plugin_manager(self.plugin_manager)
        self.coordinator.set_gui_factory(gui_factory)
        
        # Execute using coordinator
        exit_code = self.coordinator.execute(parsed_args)
        
        return exit_code
    
    def _handle_custom_json_fetch_only(self, parsed_args) -> int:
        """Handle --create-custom-json without file processing (fetch-only mode)."""
        try:
            # Use case 4: Just fetch tonies.custom.json from server
            custom_json_processor = CustomJsonProcessor(
                logger=self.logger,
                teddycloud_service=self.teddycloud_service
            )
            
            # Determine output path (current directory if not specified)
            output_path = parsed_args.output_filename or './tonies.custom.json'
            
            # Fetch JSON from server
            result = custom_json_processor.fetch_tonies_json(
                output_path=output_path,
                use_v2_format=parsed_args.version_2
            )
            
            return 0 if result.get('success') else 1
            
        except Exception as e:
            self.logger.error(f"Custom JSON fetch failed: {e}")
            return 1
    
    def _handle_custom_json_with_files(self, parsed_args) -> int:
        """Handle --create-custom-json with file processing."""
        try:
            custom_json_processor = CustomJsonProcessor(
                logger=self.logger,
                teddycloud_service=self.teddycloud_service
            )
            
            # Determine output directory based on processing mode
            if parsed_args.recursive and parsed_args.input_filename:
                # Recursive mode: output goes to <input_dir>/converted
                input_path = Path(parsed_args.input_filename)
                if parsed_args.output_filename:
                    # User specified output directory
                    output_dir = Path(parsed_args.output_filename)
                else:
                    # Default: input_dir/converted
                    if input_path.is_dir():
                        output_dir = input_path / 'converted'
                    else:
                        output_dir = input_path.parent / 'converted'
            elif parsed_args.output_filename:
                # User specified output
                output_path_obj = Path(parsed_args.output_filename)
                if output_path_obj.is_dir():
                    output_dir = output_path_obj
                else:
                    # Output is a file path, use its parent directory
                    output_dir = output_path_obj.parent
            else:
                # No output specified, use current directory
                output_dir = Path('./')
            
            # Ensure directory exists
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Fetch JSON from server (or create empty if not available)
            result = custom_json_processor.fetch_tonies_json(
                output_path=str(output_dir / 'tonies.custom.json'),
                use_v2_format=parsed_args.version_2
            )
            
            return 0 if result.get('success') else 1
            
        except Exception as e:
            self.logger.error(f"Custom JSON processing with files failed: {e}")
            return 1