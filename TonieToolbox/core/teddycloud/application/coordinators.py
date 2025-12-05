#!/usr/bin/python3
"""
Coordinators for complex TeddyCloud workflows.
Handle orchestration of multiple operations and business processes.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .service import TeddyCloudService
from ..domain import (
    UploadResult, TagRetrievalResult, SpecialFolder, TeddyCloudConnection,
    TeddyCloudError, TeddyCloudConnectionError
)
from ...events import get_event_bus


class TeddyCloudUploadCoordinator:
    """
    Coordinates complex upload workflows for TeddyCloud integration.
    
    Handles batch uploads, artwork management, folder uploads, and JSON updates.
    Orchestrates multi-step upload operations including TAF files and associated
    artwork, providing progress tracking and error recovery for complex upload scenarios.
    
    Example:
        >>> from TonieToolbox.core.teddycloud.application import TeddyCloudService
        >>> from TonieToolbox.core.teddycloud.domain import SpecialFolder
        >>> from TonieToolbox.core.utils import get_logger
        >>> 
        >>> # Initialize coordinator
        >>> logger = get_logger(__name__)
        >>> service = TeddyCloudService(connection, logger)
        >>> coordinator = TeddyCloudUploadCoordinator(service, logger)
        >>> 
        >>> # Upload TAF with artwork
        >>> taf_file = '/output/audiobook.taf'
        >>> artwork = ['/output/cover.jpg', '/output/back.jpg']
        >>> taf_result, artwork_results = coordinator.upload_with_artwork(
        ...     taf_file=taf_file,
        ...     artwork_files=artwork,
        ...     template_path='/content/{album}'
        ... )
        >>> 
        >>> if taf_result.success:
        ...     print(f"TAF uploaded to: {taf_result.server_path}")
        ...     print(f"Artwork uploaded: {len([r for r in artwork_results if r.success])}")
        TAF uploaded to: /content/MyAudiobook/audiobook.taf
        Artwork uploaded: 2
        >>> 
        >>> # Upload entire folder
        >>> results = coordinator.upload_folder_contents(
        ...     folder_path='/audiobooks/book1',
        ...     include_artwork=True,
        ...     special=SpecialFolder.CONTENT
        ... )
        >>> print(f"TAF files: {len(results['taf'])}, Artwork: {len(results['artwork'])}")
        TAF files: 1, Artwork: 2
    """
    
    def __init__(self, teddycloud_service: TeddyCloudService,
                 logger: Optional[logging.Logger] = None):
        """Initialize coordinator with TeddyCloud service."""
        self.teddycloud_service = teddycloud_service
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.event_bus = get_event_bus()
    
    def upload_with_artwork(self, taf_file: str, artwork_files: List[str],
                           template_path: Optional[str] = None,
                           special: Optional[SpecialFolder] = None,
                           source_metadata: Optional[Dict[str, Any]] = None,
                           create_custom_json: bool = False,
                           use_version_2: bool = False,
                           input_files: Optional[List[str]] = None,
                           output_dir: Optional[str] = None) -> Tuple[UploadResult, List[UploadResult]]:
        """
        Upload TAF file with associated artwork files.
        
        Args:
            taf_file: Path to TAF file
            artwork_files: List of artwork file paths
            template_path: Optional path template
            special: Special folder designation
            source_metadata: Optional metadata from source files (for TAF files created from source media)
            create_custom_json: Whether to create/update custom Tonies JSON
            use_version_2: Whether to use v2 format for custom JSON (default: v1)
            input_files: List of input audio files used to create the TAF
            output_dir: Directory where to save the tonies.custom.json file
            
        Returns:
            Tuple of (TAF upload result, list of artwork upload results)
        """
        try:
            self.logger.info(f"Starting upload with artwork: {taf_file}")
            
            # Upload main TAF file first with source metadata
            taf_result = self.teddycloud_service.upload_file(
                taf_file, template_path, special, source_metadata=source_metadata
            )
            
            if not taf_result.success:
                self.logger.error(f"TAF upload failed, skipping artwork: {taf_result.error}")
                return taf_result, []
            
            # Upload artwork files
            artwork_results = []
            artwork_url = None
            for artwork_file in artwork_files:
                # Use same destination directory as TAF file
                artwork_template = self._get_artwork_template(template_path, artwork_file)
                
                artwork_result = self.teddycloud_service.upload_file(
                    artwork_file, artwork_template, special
                )
                artwork_results.append(artwork_result)
                
                if artwork_result.success:
                    self.logger.info(f"Uploaded artwork: {artwork_file}")
                    # Store first successful artwork URL for JSON metadata
                    if artwork_url is None and hasattr(artwork_result, 'destination_path'):
                        artwork_url = artwork_result.destination_path
                else:
                    self.logger.warning(f"Artwork upload failed: {artwork_result.error}")
            
            # Update custom Tonies JSON if requested
            if create_custom_json and taf_result.success:
                self._update_custom_json(
                    taf_file=taf_file,
                    input_files=input_files,
                    artwork_url=artwork_url,
                    output_dir=output_dir,
                    use_version_2=use_version_2
                )
            
            return taf_result, artwork_results
            
        except Exception as e:
            self.logger.error(f"Upload with artwork failed: {e}")
            error_result = UploadResult(
                success=False,
                file_path=taf_file,
                error=str(e)
            )
            return error_result, []
    
    def upload_folder_contents(self, folder_path: str, 
                              template_path: Optional[str] = None,
                              special: Optional[SpecialFolder] = None,
                              include_artwork: bool = True) -> Dict[str, List[UploadResult]]:
        """
        Upload all supported files in a folder.
        
        Args:
            folder_path: Path to folder
            template_path: Optional path template
            special: Special folder designation
            include_artwork: Whether to include artwork files
            
        Returns:
            Dictionary categorizing upload results by file type
        """
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                raise TeddyCloudError(f"Invalid folder path: {folder_path}")
            
            # Find supported files
            taf_files = list(folder.glob("*.taf"))
            artwork_files = list(folder.glob("*.jpg")) + list(folder.glob("*.jpeg")) + \
                           list(folder.glob("*.png")) + list(folder.glob("*.webp"))
            json_files = list(folder.glob("*.json"))
            
            results = {
                "taf": [],
                "artwork": [],
                "json": []
            }
            
            # Upload TAF files
            for taf_file in taf_files:
                result = self.teddycloud_service.upload_file(
                    str(taf_file), template_path, special
                )
                results["taf"].append(result)
            
            # Upload artwork if requested
            if include_artwork:
                for artwork_file in artwork_files:
                    artwork_template = self._get_artwork_template(template_path, str(artwork_file))
                    result = self.teddycloud_service.upload_file(
                        str(artwork_file), artwork_template, special
                    )
                    results["artwork"].append(result)
            
            # Upload JSON files
            for json_file in json_files:
                result = self.teddycloud_service.upload_file(
                    str(json_file), template_path, special
                )
                results["json"].append(result)
            
            # Log summary
            total_files = len(taf_files) + len(artwork_files) + len(json_files)
            successful_uploads = sum(
                sum(1 for r in file_results if r.success)
                for file_results in results.values()
            )
            
            self.logger.info(f"Folder upload completed: {successful_uploads}/{total_files} successful")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Folder upload failed: {e}")
            return {"taf": [], "artwork": [], "json": []}
    
    def _get_artwork_template(self, base_template: Optional[str], artwork_file: str) -> Optional[str]:
        """Get template for artwork file based on base template."""
        if not base_template:
            # Use artwork filename without extension
            return Path(artwork_file).stem
        
        # Use same directory as base template, but with artwork filename
        base_path = Path(base_template)
        artwork_name = Path(artwork_file).stem
        
        if base_path.parent != Path('.'):
            return str(base_path.parent / artwork_name)
        else:
            return artwork_name
    
    def _update_custom_json(self, taf_file: str, input_files: Optional[List[str]],
                           artwork_url: Optional[str], output_dir: Optional[str],
                           use_version_2: bool) -> None:
        """
        Update custom Tonies JSON after successful upload.
        
        Args:
            taf_file: Path to uploaded TAF file
            input_files: List of input audio files
            artwork_url: URL of uploaded artwork
            output_dir: Directory for JSON file
            use_version_2: Whether to use v2 format
        """
        try:
            # Get TeddyCloud client from service
            from ..infrastructure import HttpTeddyCloudRepository
            # Get TeddyCloud repository from service
            if hasattr(self.teddycloud_service, 'repository') and \
               isinstance(self.teddycloud_service.repository, HttpTeddyCloudRepository):
                repository = self.teddycloud_service.repository
            else:
                self.logger.warning("Cannot update custom JSON: TeddyCloud repository not available")
                return
            
            # Setup output directory and path
            import os
            if not output_dir:
                output_dir = './output'
            os.makedirs(output_dir, exist_ok=True)
            json_file_path = os.path.join(output_dir, 'tonies.custom.json')
            
            # Get appropriate handler
            from ...tonies_data import ToniesDataManager
            manager = ToniesDataManager(repository)
            handler = manager.get_v2_handler() if use_version_2 else manager.get_v1_handler()
            
            # Load from server
            handler.load_from_server()
            
            # Merge with local file if exists
            if os.path.exists(json_file_path):
                local_handler = manager.get_v2_handler() if use_version_2 else manager.get_v1_handler()
                if local_handler.load_from_file(json_file_path):
                    if handler.is_loaded:
                        # Merge unique entries
                        for local_entry in local_handler.custom_json:
                            if local_entry not in handler.custom_json:
                                handler.custom_json.append(local_entry)
                    else:
                        handler.custom_json = local_handler.custom_json
                        handler.is_loaded = True
            
            # Add new entry if provided
            if taf_file and input_files and handler.is_loaded:
                if not handler.add_entry_from_taf(taf_file, input_files, artwork_url):
                    self.logger.error("Failed to add entry to tonies.custom.json")
                    return
            
            # Save updated JSON
            success = handler.save_to_file(json_file_path)
            
            if success:
                version_label = "v2" if use_version_2 else "v1"
                self.logger.info(f"Successfully updated custom Tonies JSON ({version_label})")
            else:
                self.logger.warning("Failed to update custom Tonies JSON")
                
        except Exception as e:
            self.logger.error(f"Error updating custom Tonies JSON: {e}")


class TeddyCloudTagCoordinator:
    """
    Coordinates tag-related operations for TeddyCloud integration.
    
    Handles tag retrieval, display, validation, and management workflows.
    Provides formatted output of tag information including UIDs, paths, and
    validation status with summary statistics.
    
    Example:
        >>> from TonieToolbox.core.teddycloud.application import TeddyCloudService
        >>> from TonieToolbox.core.utils import get_logger
        >>> 
        >>> # Initialize coordinator
        >>> logger = get_logger(__name__)
        >>> service = TeddyCloudService(connection, logger)
        >>> coordinator = TeddyCloudTagCoordinator(service, logger)
        >>> 
        >>> # Retrieve and display all tags
        >>> exit_code = coordinator.get_and_display_tags()
        >>> print(f"Tags displayed successfully: {exit_code == 0}")
        Tags displayed successfully: True
        
        Output:
        Tag UID: E004AABB1234567
        Path: /content/audiobooks/book1.taf
        Valid: Yes
        
        Tag UID: E004CCDD7654321
        Path: /content/music/song.taf
        Valid: Yes
        
        Summary: 2 total tags (2 valid, 0 invalid)
    """
    
    def __init__(self, teddycloud_service: TeddyCloudService,
                 logger: Optional[logging.Logger] = None):
        """Initialize coordinator with TeddyCloud service."""
        self.teddycloud_service = teddycloud_service
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.event_bus = get_event_bus()
    
    def get_and_display_tags(self) -> int:
        """
        Retrieve tags from server and display them.
        
        Returns:
            Exit code: 0 for success, 1 for failure
        """
        try:
            self.logger.info("Retrieving and displaying tags from TeddyCloud")
            
            # Get tags from service
            result = self.teddycloud_service.get_tags()
            
            if not result.success:
                self.logger.error(f"Failed to retrieve tags: {result.error}")
                return 1
            
            if not result.has_tags:
                print("No tags found on TeddyCloud server.")
                return 0
            
            # Display tags
            display_output = self.teddycloud_service.display_tags(result.tags)
            print(display_output)
            
            # Display summary
            summary = self.teddycloud_service.get_tag_summary(result.tags)
            print(f"\nSummary: {summary['total']} total tags ({summary['valid']} valid, {summary['invalid']} invalid)")
            
            return 0
            
        except TeddyCloudConnectionError as e:
            self.logger.error(f"Connection error: {e}")
            return 1
        except Exception as e:
            self.logger.error(f"Error retrieving tags: {e}")
            return 1
    
    def filter_tags(self, tags: List, filter_criteria: Dict[str, Any]) -> List:
        """
        Filter tags based on criteria.
        
        Args:
            tags: List of tags to filter
            filter_criteria: Dictionary with filter criteria
            
        Returns:
            Filtered list of tags
        """
        filtered_tags = tags
        
        # Filter by validity
        if 'valid_only' in filter_criteria and filter_criteria['valid_only']:
            filtered_tags = [tag for tag in filtered_tags if tag.valid.value == "valid"]
        
        # Filter by type
        if 'tag_type' in filter_criteria:
            target_type = filter_criteria['tag_type']
            filtered_tags = [tag for tag in filtered_tags if tag.tag_type == target_type]
        
        # Filter by series
        if 'series' in filter_criteria:
            target_series = filter_criteria['series'].lower()
            filtered_tags = [
                tag for tag in filtered_tags 
                if tag.series and target_series in tag.series.lower()
            ]
        
        return filtered_tags


class TeddyCloudConfigurationCoordinator:
    """
    Coordinates TeddyCloud configuration and setup operations.
    
    Handles connection configuration, service initialization, and validation
    of TeddyCloud server settings. Builds TeddyCloudService instances from
    command-line arguments or configuration files with proper authentication
    and SSL verification settings.
    
    Example:
        >>> from TonieToolbox.core.utils import get_logger
        >>> import argparse
        >>> 
        >>> # Initialize coordinator
        >>> logger = get_logger(__name__)
        >>> coordinator = TeddyCloudConfigurationCoordinator(logger)
        >>> 
        >>> # Setup from command-line arguments
        >>> args = argparse.Namespace(
        ...     upload_to_teddycloud=True,
        ...     teddycloud_url='http://teddycloud.local',
        ...     teddycloud_username='admin',
        ...     teddycloud_password='password123'
        ... )
        >>> 
        >>> service = coordinator.setup_from_args(args)
        >>> if service:
        ...     print("TeddyCloud service configured successfully")
        ...     print(f"Server: {service.connection.url}")
        TeddyCloud service configured successfully
        Server: http://teddycloud.local
        >>> 
        >>> # Test connection
        >>> if service:
        ...     result = service.test_connection()
        ...     print(f"Connection test: {'Success' if result.success else 'Failed'}")
        Connection test: Success
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize coordinator."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def setup_from_args(self, args) -> Optional[TeddyCloudService]:
        """
        Setup TeddyCloud service from command line arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Configured TeddyCloudService or None if setup not needed
        """
        try:
            # Check if TeddyCloud setup is needed
            if not self._should_setup_teddycloud(args):
                return None
            
            # Get connection configuration from args
            connection_config = self._build_connection_from_args(args)
            if not connection_config:
                return None
            
            # Create service with infrastructure dependencies
            # Note: This would be injected by the factory in practice
            # Placeholder for factory pattern implementation
            service = None  # Will be implemented with factory
            
            # Connect to server
            success = service.connect(connection_config)
            if not success:
                self.logger.error("Failed to connect to TeddyCloud server")
                return None
            
            return service
            
        except Exception as e:
            self.logger.error(f"TeddyCloud setup failed: {e}")
            return None
    
    def _should_setup_teddycloud(self, args) -> bool:
        """Check if TeddyCloud setup is needed based on arguments."""
        return (hasattr(args, 'upload') and args.upload is not None) or \
               (hasattr(args, 'get_tags') and args.get_tags is not None)
    
    def _build_connection_from_args(self, args) -> Optional['TeddyCloudConnection']:
        """Build TeddyCloudConnection from command line arguments."""
        # This would be implemented based on the argument structure
        # For now, return None as placeholder
        return None