#!/usr/bin/python3
"""
Application service for coordinating TeddyCloud operations.
This layer orchestrates domain services and infrastructure implementations.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from ..domain import (
    TeddyCloudConnection, TeddyCloudTag, UploadResult, TagRetrievalResult,
    SpecialFolder, TeddyCloudRepository,
    ConnectionValidationService, UploadPathResolutionService,
    DirectoryManagementService, TagDisplayService, UploadValidationService,
    TemplateProcessor, MetadataExtractor, FileSystemService,
    TeddyCloudError, TeddyCloudConnectionError
)
from ...events import get_event_bus
from ..events import (
    TeddyCloudConnectionEstablishedEvent, TeddyCloudConnectionFailedEvent,
    TeddyCloudUploadStartedEvent, TeddyCloudUploadCompletedEvent, TeddyCloudUploadFailedEvent,
    TeddyCloudTagsRetrievedEvent
)


class TeddyCloudService:
    """
    Application service for TeddyCloud operations.
    Coordinates domain services and infrastructure implementations.
    """
    
    def __init__(self,
                 repository: TeddyCloudRepository,
                 template_processor: TemplateProcessor,
                 metadata_extractor: MetadataExtractor,
                 file_system_service: FileSystemService,
                 logger: Optional[logging.Logger] = None):
        """Initialize service with injected dependencies."""
        self.repository = repository
        self.template_processor = template_processor
        self.metadata_extractor = metadata_extractor
        self.file_system_service = file_system_service
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.event_bus = get_event_bus()
        
        # Cache directory list for current session
        self._directory_cache: Optional[set] = None
        
        # Initialize domain services
        self.connection_validator = ConnectionValidationService(self.logger)
        self.path_resolver = UploadPathResolutionService(template_processor, self.logger)
        self.directory_manager = DirectoryManagementService(
            repository, self.logger
        )
        self.tag_display = TagDisplayService(self.logger)
        self.upload_validator = UploadValidationService(self.logger)
        
        self._connection: Optional[TeddyCloudConnection] = None
        self._is_connected = False
    
    def connect(self, connection: TeddyCloudConnection) -> bool:
        """
        Establish connection to TeddyCloud server.
        
        Args:
            connection: Connection configuration
            
        Returns:
            True if connection successful
            
        Raises:
            TeddyCloudConnectionError: If connection fails
        """
        try:
            # Validate connection configuration
            self.connection_validator.validate_connection_config(connection)
            
            # Attempt connection
            success = self.repository.connect(connection)
            
            if success:
                self._connection = connection
                self._is_connected = True
                self.logger.info(f"Successfully connected to TeddyCloud: {connection.base_url}")
                
                # Test connection to ensure it's working
                if not self.repository.test_connection():
                    raise TeddyCloudConnectionError("Connection test failed")
                
                # Publish connection established event
                self.event_bus.publish(TeddyCloudConnectionEstablishedEvent(
                    source=self.__class__.__name__,
                    server_url=connection.base_url,
                    authentication_type=connection.authentication_type.value,
                    secure_connection=connection.is_secure_connection
                ))
                
                return True
            else:
                raise TeddyCloudConnectionError("Failed to establish connection")
                
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._is_connected = False
            
            # Publish connection failed event
            if connection:
                self.event_bus.publish(TeddyCloudConnectionFailedEvent(
                    source=self.__class__.__name__,
                    server_url=connection.base_url,
                    error=str(e)
                ))
            
            raise TeddyCloudConnectionError(f"Connection failed: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if service is connected to TeddyCloud."""
        return self._is_connected and self._connection is not None
    
    def get_tags(self) -> TagRetrievalResult:
        """
        Retrieve all tags from TeddyCloud server.
        
        Returns:
            TagRetrievalResult with retrieved tags
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            self.logger.info("Retrieving tags from TeddyCloud server")
            result = self.repository.get_tags()
            
            # Publish tags retrieved event
            self.event_bus.publish(TeddyCloudTagsRetrievedEvent(
                source=self.__class__.__name__,
                tag_count=len(result.tags),
                successful=result.success,
                server_url=self._connection.base_url,
                error=result.error
            ))
            
            if result.success:
                self.logger.info(f"Successfully retrieved {len(result.tags)} tags")
            else:
                self.logger.error(f"Failed to retrieve tags: {result.error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error retrieving tags: {e}")
            return TagRetrievalResult(
                success=False,
                tags=[],
                error=str(e)
            )
    
    def display_tags(self, tags: List[TeddyCloudTag]) -> str:
        """
        Format tags for display.
        
        Args:
            tags: List of tags to display
            
        Returns:
            Formatted string for console output
        """
        return self.tag_display.format_tags_for_display(tags)
    
    def get_tag_summary(self, tags: List[TeddyCloudTag]) -> Dict[str, Any]:
        """
        Get summary statistics for tags.
        
        Args:
            tags: List of tags to summarize
            
        Returns:
            Dictionary with tag statistics
        """
        return self.tag_display.get_tag_summary(tags)
    
    def upload_file(self, file_path: str, template_path: Optional[str] = None,
                   special: Optional[SpecialFolder] = None,
                   include_artwork: bool = False,
                   source_metadata: Optional[Dict[str, Any]] = None) -> UploadResult:
        """
        Upload a file to TeddyCloud server.
        
        Args:
            file_path: Path to local file
            template_path: Optional path template
            special: Special folder designation
            include_artwork: Whether to include artwork
            source_metadata: Optional metadata from source files (for TAF files created from source media)
            
        Returns:
            UploadResult with operation details
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            # Validate file exists
            if not self.file_system_service.file_exists(file_path):
                return UploadResult(
                    success=False,
                    file_path=file_path,
                    error="File does not exist"
                )
            
            # Extract metadata for path resolution
            # Use source metadata if provided, otherwise extract from file
            if source_metadata:
                self.logger.debug(f"Using provided source metadata for {file_path}")
                metadata = source_metadata
            else:
                metadata = {}
                if self.metadata_extractor.supports_file_type(file_path):
                    metadata = self.metadata_extractor.extract_metadata(file_path)
            
            # Resolve destination path
            destination_path = self.path_resolver.resolve_upload_path(
                file_path, template_path, metadata
            )
            
            # Validate upload request
            self.upload_validator.validate_upload_request(
                file_path, destination_path, special
            )
            
            # Ensure directory structure exists
            if destination_path:
                dir_path = str(Path(destination_path).parent)
                if dir_path and dir_path != '.':
                    success = self._ensure_directory_exists_optimized(
                        dir_path, special
                    )
                    if not success:
                        return UploadResult(
                            success=False,
                            file_path=file_path,
                            error="Failed to create directory structure"
                        )
            
            # Publish upload started event
            self.event_bus.publish(TeddyCloudUploadStartedEvent(
                source=self.__class__.__name__,
                file_path=Path(file_path),
                destination_path=destination_path,
                special_folder=special.value if special else None
            ))
            
            # Perform upload
            self.logger.info(f"Uploading file: {file_path} -> {destination_path}")
            result = self.repository.upload_file(file_path, destination_path, special=special)
            
            # Validate result
            self.upload_validator.validate_upload_result(result)
            
            # Publish upload result event
            if result.success:
                self.event_bus.publish(TeddyCloudUploadCompletedEvent(
                    source=self.__class__.__name__,
                    file_path=Path(file_path),
                    destination_path=destination_path,
                    upload_result=result.server_response
                ))
                self.logger.info(f"Successfully uploaded: {file_path}")
            else:
                self.event_bus.publish(TeddyCloudUploadFailedEvent(
                    source=self.__class__.__name__,
                    file_path=Path(file_path),
                    error=result.error or "Unknown upload error",
                    destination_path=destination_path
                ))
                self.logger.error(f"Upload failed: {result.error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            return UploadResult(
                success=False,
                file_path=file_path,
                error=str(e)
            )
    
    def upload_multiple_files(self, file_paths: List[str], 
                             template_path: Optional[str] = None,
                             special: Optional[SpecialFolder] = None,
                             include_artwork: bool = False) -> List[UploadResult]:
        """
        Upload multiple files to TeddyCloud server.
        
        Args:
            file_paths: List of file paths to upload
            template_path: Optional path template
            special: Special folder designation
            include_artwork: Whether to include artwork
            
        Returns:
            List of UploadResult objects
        """
        results = []
        
        for file_path in file_paths:
            result = self.upload_file(file_path, template_path, special, include_artwork)
            results.append(result)
            
            # Log progress
            success_count = sum(1 for r in results if r.success)
            self.logger.info(f"Upload progress: {success_count}/{len(results)} completed")
        
        return results
    
    def get_file_index(self) -> Dict[str, Any]:
        """
        Get file index from TeddyCloud server.
        
        Returns:
            Dictionary with file index data (legacy format with string dates)
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.get_file_index()
        except Exception as e:
            self.logger.error(f"Error getting file index: {e}")
            return {}
    
    def get_file_index_v2(self) -> Dict[str, Any]:
        """
        Get file index V2 from TeddyCloud server.
        
        V2 improvements:
        - Unix timestamps instead of formatted strings
        - Shorter property names (isDir vs isDirectory)
        - Hide flag instead of desc field
        
        Returns:
            Dictionary with file index data (improved V2 format)
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.get_file_index_v2()
        except Exception as e:
            self.logger.error(f"Error getting file index v2: {e}")
            return {}
    
    def get_tag_info(self, uid: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tag by UID.
        
        Args:
            uid: Tag UID (e.g., "E0:04:03:50:1E:E9:18:F2")
            
        Returns:
            Dictionary with tag details
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.get_tag_info(uid)
        except Exception as e:
            self.logger.error(f"Error getting tag info for {uid}: {e}")
            return {}
    
    def get_boxes(self) -> Dict[str, Any]:
        """
        Get list of all registered Tonieboxes.
        
        Returns:
            Dictionary with boxes list containing ID, commonName, boxName, boxModel
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.get_boxes()
        except Exception as e:
            self.logger.error(f"Error getting boxes: {e}")
            return {}
    
    def get_setting(self, setting_path: str) -> Any:
        """
        Get a specific setting value from TeddyCloud server.
        
        Args:
            setting_path: Setting path (e.g., "core.server.http_port")
            
        Returns:
            Setting value as string
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.get_setting(setting_path)
        except Exception as e:
            self.logger.error(f"Error getting setting {setting_path}: {e}")
            return None
    
    def set_setting(self, setting_path: str, value: Any) -> bool:
        """
        Set a specific setting value on TeddyCloud server.
        
        Args:
            setting_path: Setting path (e.g., "core.server.http_port")
            value: Setting value
            
        Returns:
            True if setting was updated successfully
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.set_setting(setting_path, value)
        except Exception as e:
            self.logger.error(f"Error setting {setting_path}: {e}")
            return False
    
    def trigger_tonies_json_update(self) -> bool:
        """
        Trigger update of tonies.json from remote source.
        
        This downloads the latest tonies database from the official source.
        
        Returns:
            True if update was triggered successfully
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.trigger_tonies_json_update()
        except Exception as e:
            self.logger.error(f"Error triggering tonies.json update: {e}")
            return False
    
    def trigger_tonies_json_reload(self) -> bool:
        """
        Trigger reload of tonies.json from disk.
        
        This reloads the tonies database from the local file without downloading.
        
        Returns:
            True if reload was triggered successfully
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.trigger_tonies_json_reload()
        except Exception as e:
            self.logger.error(f"Error triggering tonies.json reload: {e}")
            return False
    
    def assign_unknown_tag(self, uid: str, tonie_model: str) -> bool:
        """
        Assign an unknown tag to a specific tonie model.
        
        This allows you to manually map unrecognized NFC tags to known tonie models,
        enabling them to be used with your Toniebox.
        
        Args:
            uid: Tag UID (e.g., "E0:04:03:50:1E:E9:18:F2")
            tonie_model: Tonie model ID (e.g., "10000119" for Disney Aladdin)
            
        Returns:
            True if tag was assigned successfully
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            return self.repository.assign_unknown_tag(uid, tonie_model)
        except Exception as e:
            self.logger.error(f"Error assigning tag {uid}: {e}")
            return False
    
    def assign_source_to_tag(self, tag_uid: str, source_path: str,
                            overlay: Optional[str] = None,
                            nocloud: bool = True):
        """
        Assign a source file to a specific tag.
        
        Args:
            tag_uid: Tag UID (E0:04:03:50:1E:E9:18:F2 or E00403501EE918F2)
            source_path: Path on server (lib:///path/file.taf)
            overlay: Overlay ID (Toniebox MAC). Auto-detected if None.
            nocloud: Prevent cloud sync
            
        Returns:
            TagSourceAssignment with result
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        return self.repository.set_tag_source(tag_uid, source_path, overlay, nocloud)
    
    def assign_sources_to_tags_sequential(self, file_paths: List[str], 
                                          tag_uids: List[str],
                                          nocloud: bool = True):
        """
        Assign multiple files to tags sequentially (round-robin).
        
        If more files than tags: remaining files won't be assigned.
        If more tags than files: remaining tags won't be used.
        
        Args:
            file_paths: List of uploaded file paths on server
            tag_uids: List of tag UIDs to assign to
            nocloud: Prevent cloud sync
            
        Returns:
            TagAssignmentSummary with complete results
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        from ..domain import TagAssignmentSummary, TagSourceAssignment
        from pathlib import Path
        
        self._ensure_connected()
        
        assignments = []
        successful = 0
        failed = 0
        unassigned = 0
        
        for idx, file_path in enumerate(file_paths):
            if idx < len(tag_uids):
                # Assign to corresponding tag
                tag_uid = tag_uids[idx]
                result = self.assign_source_to_tag(tag_uid, file_path, nocloud=nocloud)
                assignments.append(result)
                
                if result.success:
                    successful += 1
                else:
                    failed += 1
            else:
                # No tag available for this file
                assignments.append(TagSourceAssignment(
                    tag_uid="",
                    source_path=file_path,
                    file_name=Path(file_path).name,
                    overlay=None,
                    success=False,
                    error="No tag provided (exceeded tag list)"
                ))
                unassigned += 1
        
        return TagAssignmentSummary(
            total_files=len(file_paths),
            total_tags_provided=len(tag_uids),
            successful_assignments=successful,
            failed_assignments=failed,
            unassigned_files=unassigned,
            assignments=assignments
        )
    
    def assign_file_to_multiple_tags(self, file_path: str,
                                     tag_uids: List[str],
                                     nocloud: bool = True):
        """
        Assign a single file to multiple tags.
        
        Args:
            file_path: Server file path to assign (lib:///path/file.taf)
            tag_uids: List of tag UIDs to assign the file to
            nocloud: Prevent cloud sync
            
        Returns:
            TagAssignmentSummary with results for each tag
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        from ..domain import TagAssignmentSummary
        
        self._ensure_connected()
        
        assignments = []
        successful = 0
        failed = 0
        
        for tag_uid in tag_uids:
            result = self.assign_source_to_tag(tag_uid, file_path, nocloud=nocloud)
            assignments.append(result)
            
            if result.success:
                successful += 1
            else:
                failed += 1
        
        return TagAssignmentSummary(
            total_files=1,
            total_tags_provided=len(tag_uids),
            successful_assignments=successful,
            failed_assignments=failed,
            unassigned_files=0,
            assignments=assignments
        )
    
    def get_unassigned_tags(self) -> List:
        """
        Get all tags without source assignments.
        
        Returns:
            List of UnassignedTag objects
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        return self.repository.get_unassigned_tags()
    
    def auto_assign_to_available_tag(self, source_path: str,
                                     nocloud: bool = True) -> Optional:
        """
        Automatically assign source to first available unassigned tag.
        
        Args:
            source_path: Server path to assign (lib:///path/file.taf)
            nocloud: Prevent cloud sync
            
        Returns:
            TagSourceAssignment if successful, None if no tags available
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        unassigned = self.get_unassigned_tags()
        if not unassigned:
            self.logger.warning("No unassigned tags available for auto-assignment")
            return None
        
        # Use first valid unassigned tag
        for tag in unassigned:
            if tag.valid:
                return self.assign_source_to_tag(tag.uid, source_path, nocloud=nocloud)
        
        # If no valid tags, use first one anyway
        if unassigned:
            return self.assign_source_to_tag(unassigned[0].uid, source_path, nocloud=nocloud)
        
        return None
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information and status.
        
        Returns:
            Dictionary with server information
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            # Get various server endpoints for info
            file_index = self.repository.get_file_index_v2()  # Use V2 for better performance
            tonies_json = self.repository.get_tonies_json()
            
            return {
                "connected": True,
                "base_url": self._connection.base_url,
                "secure": self._connection.is_secure_connection,
                "authentication": self._connection.authentication_type.value,
                "file_index_available": bool(file_index),
                "tonies_json_available": bool(tonies_json),
            }
            
        except Exception as e:
            self.logger.error(f"Error getting server info: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    def _ensure_connected(self) -> None:
        """Ensure service is connected to TeddyCloud server."""
        if not self.is_connected:
            raise TeddyCloudConnectionError("Not connected to TeddyCloud server")
    
    def get_file_index_v2_with_path(
        self,
        path: Optional[str] = None,
        special: str = "library"
    ) -> Dict[str, Any]:
        """
        Get fileIndexV2 from TeddyCloud API with optional path parameter.
        
        This allows querying subdirectories within special folders.
        
        Args:
            path: Optional subdirectory path (e.g., "Die drei !!!/test")
            special: Special folder type (default: "library")
            
        Returns:
            Dictionary containing file index data
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
        """
        self._ensure_connected()
        
        try:
            params = {"special": special}
            if path:
                params["path"] = path
            
            response = self.repository._make_request(
                'GET',
                '/api/fileIndexV2',
                params=params
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get file index for path '{path}': {e}")
            return {}
    
    def build_directory_tree(
        self,
        path: Optional[str] = None,
        special: str = "library",
        max_depth: int = 10,
        include_files: bool = True,
        include_taf_header: bool = True,
        include_tonie_info: bool = True,
        directories_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Build a complete directory tree recursively from TeddyCloud library.
        
        This method recursively traverses the directory structure and returns
        a nested representation with files and/or directories.
        
        Args:
            path: Starting path (None for root)
            special: Special folder type (default: "library")
            max_depth: Maximum recursion depth (default: 10)
            include_files: Include files in output (default: True)
            include_taf_header: Include TAF header data in file entries (default: True)
            include_tonie_info: Include tonie metadata in file entries (default: True)
            directories_only: Return only directories, no files (default: False)
            
        Returns:
            List of file/directory entries with nested structure
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
            
        Example:
            >>> service.build_directory_tree(directories_only=True)
            [
                {
                    "name": "Die drei !!!",
                    "path": "Die drei !!!",
                    "isDir": True,
                    "children": [
                        {
                            "name": "test",
                            "path": "Die drei !!!/test",
                            "isDir": True
                        }
                    ]
                }
            ]
        """
        self._ensure_connected()
        
        return self._build_tree_recursive(
            path=path,
            special=special,
            depth=0,
            max_depth=max_depth,
            include_files=include_files,
            include_taf_header=include_taf_header,
            include_tonie_info=include_tonie_info,
            directories_only=directories_only
        )
    
    def _build_tree_recursive(
        self,
        path: Optional[str],
        special: str,
        depth: int,
        max_depth: int,
        include_files: bool,
        include_taf_header: bool,
        include_tonie_info: bool,
        directories_only: bool
    ) -> List[Dict[str, Any]]:
        """
        Recursive implementation of directory tree building.
        
        Args:
            path: Current directory path
            special: Special folder type
            depth: Current recursion depth
            max_depth: Maximum recursion depth
            include_files: Include files in output
            include_taf_header: Include TAF header data
            include_tonie_info: Include tonie metadata
            directories_only: Return only directories
            
        Returns:
            List of entries at current level
        """
        if depth >= max_depth:
            self.logger.warning(f"Max depth {max_depth} reached at path: {path}")
            return []
        
        # Get file index for current path
        file_index = self.get_file_index_v2_with_path(path=path, special=special)
        
        if not file_index or 'files' not in file_index:
            return []
        
        files = file_index['files']
        result = []
        
        for item in files:
            name = item.get('name')
            is_dir = item.get('isDir', False)
            
            # Skip navigation entries
            if name in ['.', '..']:
                continue
            
            # Skip files if directories_only mode
            if directories_only and not is_dir:
                continue
            
            # Skip files if not including them
            if not include_files and not is_dir:
                continue
            
            # Build entry
            entry = {
                'name': name,
                'date': item.get('date'),
                'size': item.get('size'),
                'isDir': is_dir,
                'hide': item.get('hide', False)
            }
            
            # Add full path for directories
            if is_dir:
                entry['path'] = f"{path}/{name}" if path else name
            
            # Add optional metadata for files
            if not is_dir:
                if include_taf_header and 'tafHeader' in item:
                    entry['tafHeader'] = item['tafHeader']
                
                if include_tonie_info and 'tonieInfo' in item:
                    entry['tonieInfo'] = item['tonieInfo']
            
            # Recursively process directories
            if is_dir:
                child_path = f"{path}/{name}" if path else name
                
                children = self._build_tree_recursive(
                    path=child_path,
                    special=special,
                    depth=depth + 1,
                    max_depth=max_depth,
                    include_files=include_files,
                    include_taf_header=include_taf_header,
                    include_tonie_info=include_tonie_info,
                    directories_only=directories_only
                )
                
                if children:
                    entry['children'] = children
            
            result.append(entry)
        
        return result
    
    def get_directory_list(
        self,
        path: Optional[str] = None,
        special: str = "library",
        max_depth: int = 10
    ) -> List[str]:
        """
        Get a flat list of all directory paths.
        
        Args:
            path: Starting path (None for root)
            special: Special folder type (default: "library")
            max_depth: Maximum recursion depth (default: 10)
            
        Returns:
            Sorted list of directory paths
            
        Raises:
            TeddyCloudConnectionError: If not connected to server
            
        Example:
            >>> service.get_directory_list()
            [
                "Die drei !!!",
                "Die drei !!!/test",
                "Die drei Fragezeichen",
                "by",
                "by/audioID"
            ]
        """
        tree = self.build_directory_tree(
            path=path,
            special=special,
            max_depth=max_depth,
            directories_only=True
        )
        
        paths = []
        
        def collect_paths(items: List[Dict[str, Any]]):
            for item in items:
                if item.get('isDir') and 'path' in item:
                    paths.append(item['path'])
                    if 'children' in item:
                        collect_paths(item['children'])
        
        collect_paths(tree)
        return sorted(paths)
    
    def _ensure_directory_exists_optimized(self, path: str,
                                          special: Optional[SpecialFolder] = None,
                                          use_cache: bool = False) -> bool:
        """
        Ensure directory path exists using optimized approach.
        
        Args:
            path: Directory path to ensure exists (e.g., "artist/album")
            special: Special folder designation (default: library)
            use_cache: Whether to fetch and use directory cache (slower but creates fewer requests)
            
        Returns:
            True if all directories exist or were created successfully
        """
        if not path or path == '.':
            return True
        
        # Use library as default special folder
        special_str = special.value if special else "library"
        
        # If caching disabled, use simple sequential creation
        if not use_cache:
            return self.directory_manager.ensure_directory_path_exists(path, special)
        
        # Get existing directory structure (cached if available)
        if not self._directory_cache:
            self.logger.debug(f"Fetching directory tree for {special_str}")
            try:
                existing_dirs = set(self.get_directory_list(special=special_str, max_depth=10))  # Reduced depth
                self._directory_cache = existing_dirs
                self.logger.debug(f"Cached {len(existing_dirs)} existing directories")
            except Exception as e:
                self.logger.warning(f"Failed to fetch directory tree, using fallback: {e}")
                # Fall back to old method if directory tree fetch fails
                return self.directory_manager.ensure_directory_path_exists(path, special)
        
        existing_dirs = self._directory_cache
        
        # Split path into components
        path_components = path.split('/')
        current_path = ""
        directories_to_create = []
        
        # Determine which directories need to be created
        for component in path_components:
            if current_path:
                current_path += f"/{component}"
            else:
                current_path = component
            
            if not current_path:  # Skip empty components
                continue
            
            if current_path not in existing_dirs:
                directories_to_create.append(current_path)
        
        # Create missing directories
        if directories_to_create:
            self.logger.info(f"Creating {len(directories_to_create)} missing directories for path: {path}")
            
            for dir_path in directories_to_create:
                self.logger.debug(f"Creating directory: {dir_path}")
                result = self.repository.create_directory(dir_path, special=special)
                
                if result.success or result.already_existed:
                    # Add to cache
                    self._directory_cache.add(dir_path)
                    self.logger.debug(f"Created directory: {dir_path}")
                else:
                    self.logger.error(f"Failed to create directory {dir_path}: {result.error}")
                    return False
        else:
            self.logger.debug(f"All directories in path '{path}' already exist")
        
        return True
    
    def clear_directory_cache(self) -> None:
        """Clear the cached directory structure. Call after external directory changes."""
        self._directory_cache = None
        self.logger.debug("Directory cache cleared")