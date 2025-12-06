#!/usr/bin/env python3
"""
Main Processing Application Service.

This service provides the primary entry point for all processing operations,
coordinating between interface adapters and use cases following Clean Architecture principles.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Callable

from ..utils.logging import get_logger
from .domain import (
    ProcessingOperation, ProcessingResult, ProcessingMode, 
    InputSpecification, OutputSpecification, ProcessingOptions
)
from .application.use_cases import (
    ConvertToTafUseCase, FilesToTafUseCase, FileAnalysisUseCase
)
from .application.services.processing_application_service import ProcessingApplicationService
from .infrastructure import (
    FileSystemRepository, FFmpegConverter, TeddyCloudAdapter, TafAnalysisService
)
from .interface import (
    CLIProcessingCoordinator, EnhancedModeDetector,
    SingleFileProcessingAdapter, FilesToTafAdapter, 
    RecursiveProcessingAdapter, FileAnalysisAdapter
)
from ..events import get_event_bus

# Module-level logger
logger = get_logger(__name__)


class MainProcessingService:
    """
    Main processing service that replaces the legacy FileProcessor.
    
    This service coordinates all processing operations using Clean Architecture principles,
    providing a unified interface for CLI, GUI, and other external interfaces.
    """
    
    def __init__(self, dependencies: Dict[str, str], logger: Optional[logging.Logger] = None):
        """
        Initialize main processing service.
        
        Args:
            dependencies: Dictionary containing paths to external dependencies (ffmpeg, etc.)
            logger: Optional logger instance (kept for compatibility, uses module logger)
        """
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        self.dependencies = dependencies
        self.event_bus = get_event_bus()
        
        # Initialize infrastructure layer
        self._setup_infrastructure(logger)
        
        # Initialize application layer
        self._setup_application_layer(logger)
        
        # Initialize interface layer
        self._setup_interface_layer(logger)
        
        logger.info("MainProcessingService initialized")
    
    def _setup_infrastructure(self, logger):
        """Setup infrastructure layer components."""
        try:
            # File system repository
            self.file_repository = FileSystemRepository(logger=logger)
            
            # Media converter (FFmpeg)
            ffmpeg_path = self.dependencies.get('ffmpeg', 'ffmpeg')
            ffprobe_path = self.dependencies.get('ffprobe', 'ffprobe')
            
            self.media_converter = FFmpegConverter(
                ffmpeg_path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                logger=logger
            )
            
            # TAF analysis service
            self.analysis_service = TafAnalysisService(logger=logger)
            
            # TeddyCloud adapter (optional)
            self.upload_service = None  # Will be set up when needed
            
            logger.debug("Infrastructure layer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize infrastructure layer: {str(e)}")
            raise
    
    def _setup_application_layer(self, logger):
        """Setup application layer components."""
        try:
            # Use cases
            self.convert_to_taf_use_case = ConvertToTafUseCase(
                file_repo=self.file_repository,
                media_converter=self.media_converter,
                logger=logger
            )
            
            self.files_to_taf_use_case = FilesToTafUseCase(
                file_repo=self.file_repository,
                media_converter=self.media_converter,
                logger=logger
            )
            
            self.analysis_use_case = FileAnalysisUseCase(
                file_repo=self.file_repository,
                media_converter=self.media_converter,
                analysis_service=self.analysis_service,
                logger=logger
            )
            
            # Application service coordinator
            self.processing_service = ProcessingApplicationService(
                file_repo=self.file_repository,
                media_converter=self.media_converter,
                analysis_service=self.analysis_service,
                event_bus=self.event_bus,
                upload_service=self.upload_service,
                logger=logger
            )
            
            logger.debug("Application layer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize application layer: {str(e)}")
            raise
    
    def _setup_interface_layer(self, logger):
        """Setup interface layer components."""
        try:
            # Mode detector
            self.mode_detector = EnhancedModeDetector(logger=logger)
            
            # Interface adapters
            self.single_file_adapter = SingleFileProcessingAdapter(
                self.processing_service, logger
            )
            self.files_to_taf_adapter = FilesToTafAdapter(
                self.processing_service, logger  
            )
            self.recursive_adapter = RecursiveProcessingAdapter(
                self.processing_service, logger
            )
            self.analysis_adapter = FileAnalysisAdapter(
                self.processing_service, logger
            )
            
            # CLI coordinator
            self.cli_coordinator = CLIProcessingCoordinator(
                self.processing_service, logger
            )
            
            logger.debug("Interface layer initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize interface layer: {str(e)}")
            raise
    
    def process_files(self, args) -> int:
        """
        Main entry point for file processing - replaces legacy FileProcessor.process_files().
        
        Args:
            args: Command-line arguments namespace
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            logger.info("Starting file processing with Clean Architecture")
            
            # Use CLI coordinator to handle the request
            result = self.cli_coordinator.execute_from_args(args)
            
            logger.info(f"File processing completed with exit code: {result}")
            return result
            
        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")
            return 1
    
    def analyze_file(self, file_path: Union[str, Path], detailed: bool = False) -> Dict[str, Any]:
        """
        Analyze a single file and return analysis results.
        
        Args:
            file_path: Path to file to analyze
            detailed: Whether to perform detailed analysis
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            file_path = Path(file_path)
            
            # Create request for analysis
            request = {
                'input_path': str(file_path),
                'analyze_only': True,
                'detailed': detailed,
                'output_format': 'json'
            }
            
            # Execute analysis
            result = self.analysis_adapter.execute(request)
            
            if result == 0:
                # Return analysis results (would need to be extracted from the adapter)
                return {'success': True, 'file_path': str(file_path)}
            else:
                return {'success': False, 'error': 'Analysis failed'}
                
        except Exception as e:
            logger.error(f"File analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def convert_single_file(self, input_path: Union[str, Path], 
                          output_path: Optional[Union[str, Path]] = None,
                          options: Optional[Dict[str, Any]] = None,
                          progress_callback: Optional[Callable] = None) -> bool:
        """
        Convert a single file to TAF format.
        
        Args:
            input_path: Input file path
            output_path: Output file path (optional)
            options: Processing options
            progress_callback: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            options = options or {}
            
            # Create request for single file conversion
            request = {
                'input_path': str(input_path),
                'output_path': str(output_path) if output_path else None,
                **options
            }
            
            # Add progress callback if provided
            if progress_callback:
                self.single_file_adapter.add_progress_callback(progress_callback)
            
            # Execute conversion
            result = self.single_file_adapter.execute(request)
            
            return result == 0
            
        except Exception as e:
            logger.error(f"Single file conversion failed: {str(e)}")
            return False
    
    def convert_multiple_files(self, input_pattern: str,
                             output_directory: Optional[Union[str, Path]] = None,
                             options: Optional[Dict[str, Any]] = None,
                             progress_callback: Optional[Callable] = None) -> bool:
        """
        Convert multiple files matching a pattern.
        
        Args:
            input_pattern: File pattern or directory path
            output_directory: Output directory path
            options: Processing options
            progress_callback: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            options = options or {}
            
            # Create request for multi-file conversion
            request = {
                'input_pattern': input_pattern,
                'output_directory': str(output_directory) if output_directory else None,
                **options
            }
            
            # Add progress callback if provided
            if progress_callback:
                self.files_to_taf_adapter.add_progress_callback(progress_callback)
            
            # Execute conversion
            result = self.files_to_taf_adapter.execute(request)
            
            return result == 0
            
        except Exception as e:
            logger.error(f"Multiple file conversion failed: {str(e)}")
            return False
    
    def process_recursively(self, input_directory: Union[str, Path],
                          output_directory: Optional[Union[str, Path]] = None,
                          options: Optional[Dict[str, Any]] = None,
                          progress_callback: Optional[Callable] = None) -> bool:
        """
        Process files recursively in a directory tree.
        
        Args:
            input_directory: Input directory path
            output_directory: Output directory path
            options: Processing options  
            progress_callback: Optional progress callback
            
        Returns:
            True if successful, False otherwise
        """
        try:
            options = options or {}
            
            # Create request for recursive processing
            request = {
                'input_directory': str(input_directory),
                'output_directory': str(output_directory) if output_directory else None,
                'recursive': True,
                **options
            }
            
            # Add progress callback if provided
            if progress_callback:
                self.recursive_adapter.add_progress_callback(progress_callback)
            
            # Execute recursive processing
            result = self.recursive_adapter.execute(request)
            
            return result == 0
            
        except Exception as e:
            logger.error(f"Recursive processing failed: {str(e)}")
            return False
    
    def setup_teddycloud_integration(self, connection_config: Dict[str, Any]) -> bool:
        """
        Setup TeddyCloud integration for uploads.
        
        Args:
            connection_config: TeddyCloud connection configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from .infrastructure.services.teddycloud_adapter import TeddyCloudConnection
            
            # Create TeddyCloud connection
            connection = TeddyCloudConnection(
                hostname=connection_config.get('hostname', 'localhost'),
                port=connection_config.get('port', 80),
                username=connection_config.get('username'),
                password=connection_config.get('password'),
                use_https=connection_config.get('use_https', False)
            )
            
            # Create TeddyCloud adapter
            self.upload_service = TeddyCloudAdapter(connection, logger)
            
            # Update use cases with upload service
            self.convert_to_taf_use_case.upload_service = self.upload_service
            self.files_to_taf_use_case.upload_service = self.upload_service
            
            logger.info("TeddyCloud integration setup successful")
            return True
            
        except Exception as e:
            logger.error(f"TeddyCloud integration setup failed: {str(e)}")
            return False
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """
        Get supported input and output formats.
        
        Returns:
            Dictionary with 'input' and 'output' format lists
        """
        try:
            return {
                'input': self.media_converter.get_supported_input_formats(),
                'output': self.media_converter.get_supported_output_formats()
            }
        except Exception as e:
            logger.error(f"Failed to get supported formats: {str(e)}")
            return {'input': [], 'output': []}
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """
        Validate that all required dependencies are available.
        
        Returns:
            Dictionary mapping dependency names to availability status
        """
        validation_results = {}
        
        try:
            # Test FFmpeg availability
            validation_results['ffmpeg'] = self.media_converter._verify_ffmpeg_availability()
        except:
            validation_results['ffmpeg'] = False
        
        try:
            # Test file system access
            self.file_repository.create_temp_file("test", ".txt")
            validation_results['filesystem'] = True
        except:
            validation_results['filesystem'] = False
        
        return validation_results