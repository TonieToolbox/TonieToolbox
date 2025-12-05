#!/usr/bin/python3
"""
TeddyCloud processors following BaseFileProcessor pattern.
Handles TeddyCloud operations with proper event publishing and error handling.
"""
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .base import BaseTeddyCloudProcessor
from ..application import TeddyCloudService, TeddyCloudUploadCoordinator, TeddyCloudTagCoordinator
from ..infrastructure import get_teddycloud_service, create_teddycloud_connection_from_args
from ..domain import SpecialFolder, TeddyCloudConnectionError


class TeddyCloudUploadProcessor(BaseTeddyCloudProcessor):
    """Processor for uploading files to TeddyCloud servers."""
    
    def __init__(self, logger: logging.Logger, dependencies: Dict[str, str]):
        """Initialize TeddyCloud upload processor."""
        super().__init__(logger, dependencies)
        self.service: Optional[TeddyCloudService] = None
        self.coordinator: Optional[TeddyCloudUploadCoordinator] = None
    
    def process(self, args, teddycloud_client=None) -> int:
        """Process TeddyCloud upload operations."""
        try:
            # Setup TeddyCloud service
            success = self._setup_service(args)
            if not success:
                return 1
            
            # Determine what to upload
            upload_targets = self._determine_upload_targets(args)
            if not upload_targets:
                self.logger.error("No files to upload")
                return 1
            
            # Publish processing started event
            self._publish_processing_started(
                input_path=Path(upload_targets[0]),
                processing_mode="teddycloud_upload",
                upload_count=len(upload_targets)
            )
            
            # Process uploads
            results = []
            uploaded_paths = []
            
            for target in upload_targets:
                result = self._upload_single_file(target, args)
                results.append(result)
                if result.success and result.destination_path:
                    uploaded_paths.append(result.destination_path)
            
            self.logger.info(f"Upload complete: {len(uploaded_paths)} files uploaded successfully")
            self.logger.info(f"Tag assignment requested: assign_to_tag={getattr(args, 'assign_to_tag', None)}, auto_select_tag={getattr(args, 'auto_select_tag', False)}")
            self.logger.info(f"Uploaded paths: {uploaded_paths}")
            

            if uploaded_paths and (args.assign_to_tag or args.auto_select_tag):
                self.logger.info("Starting tag assignment...")
                self._handle_tag_assignment(uploaded_paths, args)
            elif not uploaded_paths:
                self.logger.warning("No uploaded paths available for tag assignment")
            elif not (args.assign_to_tag or args.auto_select_tag):
                self.logger.info("No tag assignment requested")
            
            # Check results
            successful_uploads = sum(1 for r in results if r.success)
            
            if successful_uploads == len(results):
                self.logger.info(f"All {len(results)} files uploaded successfully")
                self._publish_processing_completed(
                    input_path=Path(upload_targets[0]),
                    processed_files=upload_targets
                )
                return 0
            else:
                self.logger.error(f"Only {successful_uploads}/{len(results)} files uploaded successfully")
                return 1
                
        except Exception as e:
            self.logger.error(f"TeddyCloud upload processing failed: {e}")
            if upload_targets:
                self._publish_processing_failed(
                    input_path=Path(upload_targets[0]),
                    error=e
                )
            return 1
    
    def _setup_service(self, args) -> bool:
        """Setup TeddyCloud service from arguments."""
        try:
            # Create connection from args
            connection = create_teddycloud_connection_from_args(args)
            if not connection:
                self.logger.error("Failed to create TeddyCloud connection from arguments")
                return False
            
            # Create service
            self.service = get_teddycloud_service(self.logger)
            
            # Connect to server
            success = self.service.connect(connection)
            if not success:
                self.logger.error("Failed to connect to TeddyCloud server")
                return False
            
            # Create coordinator
            self.coordinator = TeddyCloudUploadCoordinator(self.service, self.logger)
            
            return True
            
        except Exception as e:
            self.logger.error(f"TeddyCloud service setup failed: {e}")
            return False
    
    def _determine_upload_targets(self, args) -> List[str]:
        """Determine which files to upload based on arguments."""
        targets = []
        
        # Check for direct file arguments
        if hasattr(args, 'files') and args.files:
            for file_path in args.files:
                if Path(file_path).exists():
                    targets.append(file_path)
                else:
                    self.logger.warning(f"File not found: {file_path}")
        
        # Check for input argument
        elif hasattr(args, 'input') and args.input:
            if Path(args.input).exists():
                targets.append(args.input)
            else:
                self.logger.warning(f"Input file not found: {args.input}")
        
        return targets
    
    def _upload_single_file(self, file_path: str, args):
        """Upload a single file to TeddyCloud."""
        try:
            # Determine special folder
            special = None
            if hasattr(args, 'special_folder') and args.special_folder:
                special = SpecialFolder(args.special_folder)
            
            # Determine template path
            template_path = getattr(args, 'path', None)
            
            # Check if artwork should be included
            include_artwork = getattr(args, 'include_artwork', False)
            
            # Check if custom JSON should be created
            create_custom_json = getattr(args, 'create_custom_json', False)
            use_version_2 = getattr(args, 'version_2', False)
            
            # Get input files if available (for JSON metadata)
            input_files = getattr(args, 'input_filename', [])
            if input_files and not isinstance(input_files, list):
                input_files = [input_files]
            
            # Determine output directory for JSON
            output_dir = getattr(args, 'output', None)
            
            if include_artwork:
                # Find artwork files in same directory
                artwork_files = self._find_artwork_files(file_path)
                if artwork_files:
                    taf_result, artwork_results = self.coordinator.upload_with_artwork(
                        file_path, artwork_files, template_path, special,
                        create_custom_json=create_custom_json,
                        use_version_2=use_version_2,
                        input_files=input_files,
                        output_dir=output_dir
                    )
                    return taf_result
            
            # Regular upload
            result = self.service.upload_file(file_path, template_path, special)
            
            if result.success:
                self.logger.info(f"Successfully uploaded: {file_path}")
                
                # Update custom JSON even for regular uploads if requested
                if create_custom_json:
                    self._update_custom_json_after_upload(
                        result, file_path, input_files, output_dir, use_version_2
                    )
            else:
                self.logger.error(f"Upload failed for {file_path}: {result.error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error uploading {file_path}: {e}")
            from ..domain import UploadResult
            return UploadResult(
                success=False,
                file_path=file_path,
                error=str(e)
            )
    
    def _find_artwork_files(self, taf_file: str) -> List[str]:
        """Find artwork files in the same directory as TAF file."""
        try:
            taf_path = Path(taf_file)
            directory = taf_path.parent
            base_name = taf_path.stem
            
            artwork_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            artwork_files = []
            
            for ext in artwork_extensions:
                artwork_file = directory / f"{base_name}{ext}"
                if artwork_file.exists():
                    artwork_files.append(str(artwork_file))
            
            return artwork_files
            
        except Exception as e:
            self.logger.error(f"Error finding artwork files: {e}")
            return []
    
    def _handle_tag_assignment(self, uploaded_paths: List[str], args):
        """Handle tag assignment for uploaded files with summary table."""
        
        if getattr(args, 'auto_select_tag', False):
            # Auto-assign each file to next available tag
            self.logger.info("Auto-assigning files to available unassigned tags...")
            # Create tag coordinator if not already created
            if not hasattr(self, 'tag_coordinator') or not self.tag_coordinator:
                from ..application import TeddyCloudTagCoordinator
                self.tag_coordinator = TeddyCloudTagCoordinator(self.service, self.logger)
            
            assignments = []
            for file_path in uploaded_paths:
                result = self.tag_coordinator.auto_assign_to_available_tag(file_path)
                if result:
                    assignments.append(result)
            
            # Display summary
            self._display_assignment_summary_simple(assignments)
        
        elif getattr(args, 'assign_to_tag', None):
            # Parse tag UIDs
            tag_uids = self._parse_and_validate_tag_uids(args.assign_to_tag)
            
            if not tag_uids:
                self.logger.warning("No valid tag UIDs provided for assignment")
                return
            
            # Determine assignment strategy based on file count
            if len(uploaded_paths) == 1 and len(tag_uids) > 1:
                # Single file, multiple tags: assign file to ALL tags
                self.logger.info(f"Assigning single file to {len(tag_uids)} tags...")
                summary = self.service.assign_file_to_multiple_tags(
                    uploaded_paths[0],
                    tag_uids
                )
            else:
                # Multiple files: sequential assignment
                self.logger.info("Assigning files to tags sequentially...")
                summary = self.service.assign_sources_to_tags_sequential(
                    uploaded_paths,
                    tag_uids
                )
            
            # Display formatted summary table
            self.logger.info(summary.get_summary_table())
    
    def _parse_and_validate_tag_uids(self, tag_string: str) -> List[str]:
        """Parse and validate comma-separated tag UIDs."""
        tag_uids = [uid.strip() for uid in tag_string.split(',')]
        normalized = []
        
        for uid in tag_uids:
            # Remove colons and whitespace
            clean_uid = uid.replace(':', '').replace(' ', '')
            
            # Validate hex format and length (16 hex characters)
            if len(clean_uid) == 16 and all(c in '0123456789abcdefABCDEF' for c in clean_uid):
                # Format with colons for consistency: E0:04:03:50:1E:E9:18:F2
                formatted = ':'.join(clean_uid[i:i+2] for i in range(0, 16, 2))
                normalized.append(formatted.upper())
            else:
                self.logger.warning(
                    f"Invalid tag UID format: {uid} (expected 16 hex chars, got {len(clean_uid)})"
                )
        
        return normalized
    
    def _display_assignment_summary_simple(self, assignments: List):
        """Display simple assignment summary for auto-select mode."""
        self.logger.info("\n" + "="*80)
        self.logger.info("TAG ASSIGNMENT SUMMARY (AUTO-SELECT)")
        self.logger.info("="*80)
        
        for idx, assignment in enumerate(assignments, 1):
            if assignment.success:
                self.logger.info(f"File {idx:02d}: {assignment.file_name} -> ✓ Tag {assignment.tag_uid}")
            else:
                self.logger.info(f"File {idx:02d}: {assignment.file_name} -> ✗ {assignment.error}")
        
        successful = sum(1 for a in assignments if a.success)
        self.logger.info("="*80)
        self.logger.info(f"Total: {len(assignments)} files, {successful} successful assignments")
        self.logger.info("="*80 + "\n")
    
    def _handle_custom_json_creation(self, results: List, args):
        """Handle custom JSON creation for uploaded files."""
        # This feature would need integration with custom JSON update logic
        # For now, just log that it's requested
        self.logger.info("Custom JSON creation requested but not yet implemented for this upload path")
    
    def _update_custom_json_after_upload(self, upload_result, taf_file: str,
                                        input_files: Optional[List[str]],
                                        output_dir: Optional[str],
                                        use_version_2: bool) -> None:
        """Update custom Tonies JSON after successful upload without artwork."""
        try:
            from ...tonies_data import ToniesDataManager
            from ..infrastructure import HttpTeddyCloudRepository
            import os
            
            # Get TeddyCloud repository from service
            if hasattr(self.service, 'repository') and \
               isinstance(self.service.repository, HttpTeddyCloudRepository):
                repository = self.service.repository
            else:
                self.logger.warning("Cannot update custom JSON: TeddyCloud repository not available")
                return
            
            # Setup output directory and path
            if not output_dir:
                output_dir = './output'
            os.makedirs(output_dir, exist_ok=True)
            json_file_path = os.path.join(output_dir, 'tonies.custom.json')
            
            # Get appropriate handler
            manager = ToniesDataManager(repository)
            handler = manager.get_v2_handler() if use_version_2 else manager.get_v1_handler()
            
            # Load from server
            handler.load_from_server()
            
            # Merge with local file if exists
            if os.path.exists(json_file_path):
                local_handler = manager.get_v2_handler() if use_version_2 else manager.get_v1_handler()
                if local_handler.load_from_file(json_file_path):
                    if handler.is_loaded:
                        # Merge unique entries (simplified - handler-specific logic could be added)
                        for local_entry in local_handler.custom_json:
                            if local_entry not in handler.custom_json:
                                handler.custom_json.append(local_entry)
                    else:
                        handler.custom_json = local_handler.custom_json
                        handler.is_loaded = True
            
            # Add new entry if provided
            if taf_file and input_files and handler.is_loaded:
                if not handler.add_entry_from_taf(taf_file, input_files, None):
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
    
    def _handle_tag_assignment(self, uploaded_paths: List[str], args):
        """Handle tag assignment for uploaded files with summary table."""
        
        if args.auto_select_tag:
            # Auto-assign each file to next available tag
            self.logger.info("Auto-assigning files to available unassigned tags...")
            assignments = []
            for file_path in uploaded_paths:
                result = self.service.auto_assign_to_available_tag(file_path)
                if result:
                    assignments.append(result)
            
            # Display summary
            self._display_assignment_summary_simple(assignments)
        
        elif args.assign_to_tag:
            # Parse tag UIDs
            tag_uids = self._parse_and_validate_tag_uids(args.assign_to_tag)
            
            if not tag_uids:
                self.logger.warning("No valid tag UIDs provided for assignment")
                return
            
            # Determine assignment strategy based on file count and recursive flag
            if len(uploaded_paths) == 1 and len(tag_uids) > 1:
                # Single file, multiple tags: assign file to ALL tags
                self.logger.info(f"Assigning single file to {len(tag_uids)} tags...")
                summary = self.service.assign_file_to_multiple_tags(
                    uploaded_paths[0],
                    tag_uids
                )
            else:
                # Multiple files or recursive mode: sequential assignment
                self.logger.info("Assigning files to tags sequentially...")
                summary = self.service.assign_sources_to_tags_sequential(
                    uploaded_paths,
                    tag_uids
                )
            
            # Display formatted summary table
            self.logger.info(summary.get_summary_table())
    
    def _parse_and_validate_tag_uids(self, tag_string: str) -> List[str]:
        """Parse and validate comma-separated tag UIDs."""
        tag_uids = [uid.strip() for uid in tag_string.split(',')]
        normalized = []
        
        for uid in tag_uids:
            # Remove colons and whitespace
            clean_uid = uid.replace(':', '').replace(' ', '')
            
            # Validate hex format and length (16 hex characters)
            if len(clean_uid) == 16 and all(c in '0123456789abcdefABCDEF' for c in clean_uid):
                # Format with colons for consistency: E0:04:03:50:1E:E9:18:F2
                formatted = ':'.join(clean_uid[i:i+2] for i in range(0, 16, 2))
                normalized.append(formatted.upper())
            else:
                self.logger.warning(
                    f"Invalid tag UID format: {uid} (expected 16 hex chars, got {len(clean_uid)})"
                )
        
        return normalized
    
    def _display_assignment_summary_simple(self, assignments: List):
        """Display simple assignment summary for auto-select mode."""
        self.logger.info("\n" + "="*80)
        self.logger.info("TAG ASSIGNMENT SUMMARY (AUTO-SELECT)")
        self.logger.info("="*80)
        
        for idx, assignment in enumerate(assignments, 1):
            if assignment.success:
                self.logger.info(f"File {idx:02d}: {assignment.file_name} -> ✓ Tag {assignment.tag_uid}")
            else:
                self.logger.info(f"File {idx:02d}: {assignment.file_name} -> ✗ {assignment.error}")
        
        successful = sum(1 for a in assignments if a.success)
        self.logger.info("="*80)
        self.logger.info(f"Total: {len(assignments)} files, {successful} successful assignments")
        self.logger.info("="*80 + "\n")


class TeddyCloudTagProcessor(BaseTeddyCloudProcessor):
    """Processor for retrieving and managing TeddyCloud tags."""
    
    def __init__(self, logger: logging.Logger, dependencies: Dict[str, str]):
        """Initialize TeddyCloud tag processor."""
        super().__init__(logger, dependencies)
        self.service: Optional[TeddyCloudService] = None
        self.coordinator: Optional[TeddyCloudTagCoordinator] = None
    
    def process(self, args, teddycloud_client=None) -> int:
        """Process TeddyCloud tag operations."""
        try:
            # Setup TeddyCloud service
            success = self._setup_service(args)
            if not success:
                return 1
            
            # Publish processing started event
            self._publish_processing_started(
                input_path=Path("teddycloud_tags"),
                processing_mode="teddycloud_tags"
            )
            
            # Get and display tags
            exit_code = self.coordinator.get_and_display_tags()
            
            if exit_code == 0:
                self._publish_processing_completed(
                    input_path=Path("teddycloud_tags")
                )
            else:
                self._publish_processing_failed(
                    input_path=Path("teddycloud_tags"),
                    error=Exception("Failed to retrieve tags")
                )
            
            return exit_code
            
        except Exception as e:
            self.logger.error(f"TeddyCloud tag processing failed: {e}")
            self._publish_processing_failed(
                input_path=Path("teddycloud_tags"),
                error=e
            )
            return 1
    
    def _setup_service(self, args) -> bool:
        """Setup TeddyCloud service from arguments."""
        try:
            # Create connection from args
            connection = create_teddycloud_connection_from_args(args)
            if not connection:
                self.logger.error("Failed to create TeddyCloud connection from arguments")
                return False
            
            # Create service
            self.service = get_teddycloud_service(self.logger)
            
            # Connect to server
            success = self.service.connect(connection)
            if not success:
                self.logger.error("Failed to connect to TeddyCloud server")
                return False
            
            # Create coordinator
            self.coordinator = TeddyCloudTagCoordinator(self.service, self.logger)
            
            return True
            
        except Exception as e:
            self.logger.error(f"TeddyCloud service setup failed: {e}")
            return False


class TeddyCloudDirectUploadProcessor(BaseTeddyCloudProcessor):
    """Processor for direct upload of existing files to TeddyCloud."""
    
    def __init__(self, logger: logging.Logger, dependencies: Dict[str, str]):
        """Initialize direct upload processor."""
        super().__init__(logger, dependencies)
        self.service: Optional[TeddyCloudService] = None
        self.coordinator: Optional[TeddyCloudUploadCoordinator] = None
    
    def should_handle_direct_upload(self, args) -> bool:
        """Check if this processor should handle direct upload."""
        # Check if upload is specified (even without URL - will use config)
        if not hasattr(args, 'upload') or args.upload is None:
            return False
        
        # Check if input files are specified
        if hasattr(args, 'files') and args.files:
            # Check if any files are uploadable formats
            uploadable_extensions = {'.taf', '.jpg', '.jpeg', '.png', '.webp', '.json'}
            for file_path in args.files:
                ext = Path(file_path).suffix.lower()
                if ext in uploadable_extensions and Path(file_path).exists():
                    return True
        
        return False
    
    def process(self, args, teddycloud_client=None) -> int:
        """Process direct upload of existing files."""
        try:
            # Setup TeddyCloud service
            success = self._setup_service(args)
            if not success:
                return 1
            
            # Get files to upload
            upload_files = self._get_upload_files(args)
            if not upload_files:
                self.logger.error("No valid files found for upload")
                return 1
            
            # Publish processing started event
            self._publish_processing_started(
                input_path=Path(upload_files[0]),
                processing_mode="teddycloud_direct_upload",
                file_count=len(upload_files)
            )
            
            # Upload files
            results = []
            uploaded_paths = []
            for file_path in upload_files:
                result = self._upload_file(file_path, args)
                results.append(result)
                if result.success and result.destination_path:
                    uploaded_paths.append(result.destination_path)
            
            # Handle tag assignment if requested
            if uploaded_paths and (getattr(args, 'assign_to_tag', None) or getattr(args, 'auto_select_tag', False)):
                self._handle_tag_assignment(uploaded_paths, args)
            
            # Handle custom JSON creation if requested
            if getattr(args, 'create_custom_json', False):
                self._handle_custom_json_creation(results, args)
            
            # Check results
            successful_uploads = sum(1 for r in results if r.success)
            
            if successful_uploads == len(results):
                self.logger.info(f"All {len(results)} files uploaded successfully")
                self._publish_processing_completed(
                    input_path=Path(upload_files[0]),
                    processed_files=upload_files
                )
                return 0
            else:
                self.logger.error(f"Only {successful_uploads}/{len(results)} files uploaded successfully")
                return 1
                
        except Exception as e:
            self.logger.error(f"Direct upload processing failed: {e}")
            if upload_files:
                self._publish_processing_failed(
                    input_path=Path(upload_files[0]),
                    error=e
                )
            return 1
    
    def _setup_service(self, args) -> bool:
        """Setup TeddyCloud service from arguments."""
        try:
            # Create connection from args
            connection = create_teddycloud_connection_from_args(args)
            if not connection:
                self.logger.error("Failed to create TeddyCloud connection from arguments")
                return False
            
            # Create service
            self.service = get_teddycloud_service(self.logger)
            
            # Connect to server
            success = self.service.connect(connection)
            if not success:
                self.logger.error("Failed to connect to TeddyCloud server")
                return False
            
            # Create coordinator
            self.coordinator = TeddyCloudUploadCoordinator(self.service, self.logger)
            
            return True
            
        except Exception as e:
            self.logger.error(f"TeddyCloud service setup failed: {e}")
            return False
    
    def _get_upload_files(self, args) -> List[str]:
        """Get list of files to upload."""
        upload_files = []
        
        if hasattr(args, 'files') and args.files:
            uploadable_extensions = {'.taf', '.jpg', '.jpeg', '.png', '.webp', '.json'}
            
            for file_path in args.files:
                path = Path(file_path)
                if path.exists() and path.suffix.lower() in uploadable_extensions:
                    upload_files.append(file_path)
                else:
                    self.logger.warning(f"Skipping unsupported or missing file: {file_path}")
        
        return upload_files
    
    def _upload_file(self, file_path: str, args):
        """Upload a single file with optional artwork."""
        try:
            # Determine special folder
            special = None
            if hasattr(args, 'special_folder') and args.special_folder:
                special = SpecialFolder(args.special_folder)
            
            # Determine template path
            template_path = getattr(args, 'path', None)
            
            # Get source metadata if available (from recursive processing)
            source_metadata_map = getattr(args, 'source_metadata_map', None)
            
            # Check if artwork should be included
            include_artwork = getattr(args, 'include_artwork', False)
            
            # Check if this is a TAF file and artwork is requested
            if include_artwork and Path(file_path).suffix.lower() == '.taf':
                # Find artwork files in same directory
                artwork_files = self._find_artwork_files(file_path)
                if artwork_files:
                    # Get source metadata for this file if available
                    file_metadata = source_metadata_map.get(file_path) if source_metadata_map else None
                    
                    if file_metadata:
                        self.logger.debug(f"Using source metadata for {file_path}: {file_metadata}")
                    
                    # Upload TAF with artwork
                    taf_result, artwork_results = self.coordinator.upload_with_artwork(
                        file_path, artwork_files, template_path, special, file_metadata
                    )
                    
                    if taf_result.success:
                        self.logger.info(f"Successfully uploaded: {file_path}")
                        successful_artwork = sum(1 for r in artwork_results if r.success)
                        self.logger.info(f"  Uploaded {successful_artwork}/{len(artwork_results)} artwork files")
                    else:
                        self.logger.error(f"Upload failed for {file_path}: {taf_result.error}")
                    
                    return taf_result
            
            # Regular upload (no artwork or non-TAF file)
            # Pass source metadata if available
            file_metadata = source_metadata_map.get(file_path) if source_metadata_map else None
            
            if file_metadata:
                self.logger.info(f"Using source metadata for {Path(file_path).name}: artist={file_metadata.get('artist')}, album={file_metadata.get('album')}")
            else:
                if source_metadata_map:
                    self.logger.warning(f"No source metadata found for {file_path}")
                    self.logger.debug(f"Available metadata keys: {list(source_metadata_map.keys())}")
            
            result = self.service.upload_file(
                file_path=file_path,
                template_path=template_path,
                special=special,
                source_metadata=file_metadata
            )
            
            if result.success:
                self.logger.info(f"Successfully uploaded: {file_path}")
            else:
                self.logger.error(f"Upload failed for {file_path}: {result.error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error uploading {file_path}: {e}")
            from ..domain import UploadResult
            return UploadResult(
                success=False,
                file_path=file_path,
                error=str(e)
            )
    
    def _find_artwork_files(self, taf_file: str) -> List[str]:
        """Find artwork files in the same directory as TAF file."""
        try:
            taf_path = Path(taf_file)
            directory = taf_path.parent
            base_name = taf_path.stem
            
            artwork_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            artwork_files = []
            
            for ext in artwork_extensions:
                artwork_file = directory / f"{base_name}{ext}"
                if artwork_file.exists():
                    artwork_files.append(str(artwork_file))
            
            return artwork_files
            
        except Exception as e:
            self.logger.error(f"Error finding artwork files: {e}")
            return []
    
    def _handle_tag_assignment(self, uploaded_paths: List[str], args):
        """Handle tag assignment for uploaded files."""
        if args.auto_select_tag:
            self.logger.info("Auto-assigning files to available unassigned tags...")
            assignments = []
            for file_path in uploaded_paths:
                # Add lib:// prefix for TeddyCloud source path format
                source_path = f"lib://{file_path}" if not file_path.startswith("lib://") else file_path
                result = self.service.auto_assign_to_available_tag(source_path)
                if result:
                    assignments.append(result)
            
            self._display_assignment_summary_simple(assignments)
            
        elif getattr(args, 'assign_to_tag', None):
            tag_uids = self._parse_and_validate_tag_uids(args.assign_to_tag)
            if not tag_uids:
                return
            
            self.logger.info(f"Assigning {len(uploaded_paths)} files to {len(tag_uids)} tags sequentially...")
            assignments = []
            
            for idx, file_path in enumerate(uploaded_paths):
                if idx >= len(tag_uids):
                    self.logger.warning(f"More files ({len(uploaded_paths)}) than tags ({len(tag_uids)}). Remaining files not assigned.")
                    break
                
                tag_uid = tag_uids[idx]
                # Add lib:// prefix for TeddyCloud source path format
                source_path = f"lib://{file_path}" if not file_path.startswith("lib://") else file_path
                result = self.service.assign_source_to_tag(tag_uid, source_path)
                if result:
                    assignments.append({
                        'tag_uid': tag_uid,
                        'file_path': file_path,
                        'success': True
                    })
                else:
                    assignments.append({
                        'tag_uid': tag_uid,
                        'file_path': file_path,
                        'success': False
                    })
            
            self._display_assignment_summary_simple(assignments)
    
    def _parse_and_validate_tag_uids(self, tag_input: str) -> List[str]:
        """Parse and validate tag UIDs from input."""
        tag_uids = [uid.strip() for uid in tag_input.split(',') if uid.strip()]
        
        valid_uids = []
        for uid in tag_uids:
            if ':' in uid and len(uid.replace(':', '')) == 16:
                valid_uids.append(uid)
            else:
                self.logger.warning(f"Invalid tag UID format: {uid}")
        
        return valid_uids
    
    def _display_assignment_summary_simple(self, assignments: List[dict]):
        """Display assignment summary in simple format."""
        if not assignments:
            self.logger.info("No tag assignments were made.")
            return
        
        self.logger.info("\n=== Tag Assignment Summary ===")
        for assignment in assignments:
            tag_uid = assignment.get('tag_uid', 'N/A')
            file_path = assignment.get('file_path', 'N/A')
            success = assignment.get('success', False)
            status = "✓" if success else "✗"
            
            self.logger.info(f"{status} Tag {tag_uid} → {Path(file_path).name}")
        
        successful = sum(1 for a in assignments if a.get('success', False))
        self.logger.info(f"\nTotal: {successful}/{len(assignments)} successful assignments")
    
    def _handle_custom_json_creation(self, results: List, args):
        """Handle custom JSON creation for uploaded files."""
        try:
            from ...processing.application import CustomJsonProcessor
            
            # Filter successful TAF uploads
            taf_results = [r for r in results if r.success and r.file_path.endswith('.taf')]
            
            if not taf_results:
                self.logger.info("No TAF files were uploaded, skipping custom JSON creation")
                return
            
            # Determine output directory
            if hasattr(args, 'recursive') and args.recursive and hasattr(args, 'input_filename') and args.input_filename:
                # Recursive mode: output goes to <input_dir>/converted
                input_path = Path(args.input_filename)
                if hasattr(args, 'output_filename') and args.output_filename:
                    # User specified output directory
                    output_dir = Path(args.output_filename)
                else:
                    # Default: input_dir/converted
                    if input_path.is_dir():
                        output_dir = input_path / 'converted'
                    else:
                        output_dir = input_path.parent / 'converted'
            elif hasattr(args, 'output_filename') and args.output_filename:
                # User specified output
                output_path_obj = Path(args.output_filename)
                if output_path_obj.is_dir():
                    output_dir = output_path_obj
                else:
                    # Output is a file path, use its parent directory
                    output_dir = output_path_obj.parent
            else:
                # No output specified, use directory of first TAF file
                output_dir = Path(taf_results[0].file_path).parent
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get source metadata map if available
            source_metadata_map = getattr(args, 'source_metadata_map', {})
            
            # Build input files map and artwork URLs
            input_files_map = {}
            artwork_urls = {}
            
            for result in taf_results:
                taf_path = result.file_path
                
                # Try to find source audio files
                if source_metadata_map and taf_path in source_metadata_map:
                    metadata = source_metadata_map[taf_path]
                    source_files = metadata.get('source_files', [])
                    if source_files:
                        input_files_map[taf_path] = source_files
                    
                # Find artwork files
                artwork_files = self._find_artwork_files(taf_path)
                if artwork_files:
                    # Use first artwork file as URL
                    artwork_urls[taf_path] = str(artwork_files[0])
            
            # If no source files found in metadata, use TAF files themselves as input
            for result in taf_results:
                if result.file_path not in input_files_map:
                    input_files_map[result.file_path] = [result.file_path]
            
            # Create custom JSON processor
            processor = CustomJsonProcessor(
                logger=self.logger,
                teddycloud_service=self.service if hasattr(self, 'service') else None,
                use_v2_format=getattr(args, 'version_2', False)
            )
            
            # Process and create JSON
            taf_files = [r.file_path for r in taf_results]
            json_result = processor.process_and_create_json(
                taf_files=taf_files,
                input_files_map=input_files_map,
                artwork_urls=artwork_urls,
                output_dir=str(output_dir),
                use_v2_format=getattr(args, 'version_2', False)
            )
            
            if json_result.get('success'):
                self.logger.info(f"✓ Custom JSON created with {json_result.get('entries_added', 0)} new entries")
            else:
                self.logger.error(f"Failed to create custom JSON: {json_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Error handling custom JSON creation: {e}", exc_info=True)
