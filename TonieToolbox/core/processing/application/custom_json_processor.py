#!/usr/bin/python3
"""
Custom JSON processor for creating and updating tonies.custom.json files.

This processor provides a unified interface for both CLI and GUI to generate
custom Tonie metadata JSON files from processed TAF files.
"""
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from ...utils.logging import get_logger
from ...tonies_data import ToniesDataManager
from ...events import get_event_bus


logger = get_logger(__name__)


class CustomJsonProcessor:
    """
    Processor for creating and updating custom Tonies JSON metadata.
    
    Handles four main use cases:
    1. Fetch-only: Download tonies.custom.json from server
    2. Process + Create: Convert files and generate metadata JSON
    3. Upload + Create: Convert, upload, assign tags, and generate JSON
    4. Batch processing: Handle multiple files with recursive processing
    
    Architecture:
        - Reuses existing ToniesDataManager and format handlers
        - Emits events for progress tracking (GUI integration)
        - Gracefully handles server unavailability
        - Supports both V1 and V2 JSON formats
    
    Example:
        >>> from TonieToolbox.core.teddycloud.service_provider import TeddyCloudServiceProvider
        >>> from TonieToolbox.core.config import get_config_manager
        >>> 
        >>> # Initialize
        >>> config = get_config_manager()
        >>> tc_provider = TeddyCloudServiceProvider(config_manager=config)
        >>> tc_provider.initialize()
        >>> 
        >>> processor = CustomJsonProcessor(
        ...     logger=logger,
        ...     teddycloud_service=tc_provider.get_service()
        ... )
        >>> 
        >>> # Fetch-only mode
        >>> result = processor.fetch_tonies_json(
        ...     output_path='./tonies.custom.json',
        ...     use_v2_format=False
        ... )
        >>> 
        >>> # Process and create mode
        >>> result = processor.process_and_create_json(
        ...     taf_files=['file1.taf', 'file2.taf'],
        ...     input_files_map={'file1.taf': ['track1.mp3'], 'file2.taf': ['track2.mp3']},
        ...     output_dir='./output',
        ...     use_v2_format=False
        ... )
    """
    
    def __init__(
        self,
        logger: Optional[Any] = None,
        teddycloud_service: Optional[Any] = None,
        use_v2_format: bool = False
    ):
        """
        Initialize custom JSON processor.
        
        Args:
            logger: Logger instance
            teddycloud_service: TeddyCloudService instance for server operations
            use_v2_format: Whether to use V2 JSON format (default: V1)
        """
        self.logger = logger or get_logger(__name__)
        self.teddycloud_service = teddycloud_service
        self.use_v2_format = use_v2_format
        self.event_bus = get_event_bus()
        
        # Get TeddyCloud repository if service available
        self.client = None
        if teddycloud_service and hasattr(teddycloud_service, 'repository'):
            self.client = teddycloud_service.repository
        
        self.manager = ToniesDataManager(self.client)
    
    def fetch_tonies_json(
        self,
        output_path: Optional[str] = None,
        use_v2_format: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Fetch tonies.custom.json from TeddyCloud server and save locally.
        
        Use Case: tonietoolbox --create-custom-json
        
        Args:
            output_path: Where to save the JSON file (default: ./tonies.custom.json)
            use_v2_format: Override default format selection
            
        Returns:
            Dict with:
                - success (bool): Whether operation succeeded
                - file_path (str): Path where JSON was saved
                - entry_count (int): Number of entries fetched
                - error (str): Error message if failed
        """
        from ...events.custom_json_events import (
            CustomJsonFetchStartedEvent,
            CustomJsonFetchCompletedEvent,
            CustomJsonFetchFailedEvent
        )
        
        self.event_bus.publish(CustomJsonFetchStartedEvent(source='CustomJsonProcessor'))
        
        try:
            if not self.client:
                error_msg = "TeddyCloud not configured or unreachable. Cannot fetch tonies.custom.json."
                self.logger.error(error_msg)
                self.event_bus.publish(CustomJsonFetchFailedEvent(
                    source='CustomJsonProcessor',
                    error=error_msg
                ))
                return {
                    'success': False,
                    'error': error_msg
                }
            
            format_version = use_v2_format if use_v2_format is not None else self.use_v2_format
            
            # Fetch from server
            self.logger.info(f"Fetching tonies.custom.json from TeddyCloud (format: V{'2' if format_version else '1'})")
            
            custom_json_data = self.client.get_tonies_custom_json()
            
            if not custom_json_data:
                error_msg = "No data returned from server"
                self.logger.warning(error_msg)
                self.event_bus.publish(CustomJsonFetchFailedEvent(
                    source='CustomJsonProcessor',
                    error=error_msg
                ))
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Determine output path
            if not output_path:
                output_path = './tonies.custom.json'
            
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            import json
            with open(output_path_obj, 'w', encoding='utf-8') as f:
                json.dump(custom_json_data, f, ensure_ascii=False, indent=2)
            
            entry_count = len(custom_json_data)
            self.logger.info(f"✓ Saved {entry_count} entries to {output_path_obj}")
            
            self.event_bus.publish(CustomJsonFetchCompletedEvent(
                source='CustomJsonProcessor',
                file_path=str(output_path_obj),
                entry_count=entry_count
            ))
            
            return {
                'success': True,
                'file_path': str(output_path),
                'entry_count': entry_count
            }
            
        except Exception as e:
            error_msg = f"Failed to fetch tonies.custom.json: {e}"
            self.logger.error(error_msg)
            self.event_bus.publish(CustomJsonFetchFailedEvent(
                source='CustomJsonProcessor',
                error=error_msg
            ))
            return {
                'success': False,
                'error': error_msg
            }
    
    def process_and_create_json(
        self,
        taf_files: List[str],
        input_files_map: Dict[str, List[str]],
        artwork_urls: Optional[Dict[str, str]] = None,
        output_dir: Optional[str] = None,
        use_v2_format: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Create/update tonies.custom.json from processed TAF files.
        
        Use Cases:
            - tonietoolbox /path --create-custom-json
            - tonietoolbox --recursive /path --create-custom-json
            - tonietoolbox --recursive /path --upload --assign-to-tag TAG --create-custom-json
        
        Args:
            taf_files: List of TAF file paths that were created
            input_files_map: Mapping of TAF file -> list of source audio files
            artwork_urls: Optional mapping of TAF file -> artwork URL
            output_dir: Where to save tonies.custom.json (default: ./output)
            use_v2_format: Override default format selection
            
        Returns:
            Dict with:
                - success (bool): Whether operation succeeded
                - file_path (str): Path where JSON was saved
                - entries_added (int): Number of new entries added
                - entries_updated (int): Number of existing entries updated
                - total_entries (int): Total entries in final JSON
                - error (str): Error message if failed
        """
        from ...events.custom_json_events import (
            CustomJsonProcessingStartedEvent,
            CustomJsonProcessingCompletedEvent,
            CustomJsonProcessingFailedEvent,
            CustomJsonEntryAddedEvent,
            CustomJsonEntryUpdatedEvent
        )
        
        self.event_bus.publish(CustomJsonProcessingStartedEvent(
            source='CustomJsonProcessor',
            file_count=len(taf_files)
        ))
        
        try:
            if not taf_files:
                self.logger.warning("No TAF files provided for custom JSON generation")
                return {
                    'success': True,
                    'entries_added': 0,
                    'entries_updated': 0,
                    'total_entries': 0
                }
            
            format_version = use_v2_format if use_v2_format is not None else self.use_v2_format
            artwork_urls = artwork_urls or {}
            
            if not output_dir:
                output_dir = './output'
            
            output_dir_obj = Path(output_dir)
            output_dir_obj.mkdir(parents=True, exist_ok=True)
            json_file_path = output_dir_obj / 'tonies.custom.json'
            
            self.logger.info(f"Processing {len(taf_files)} TAF file(s) for custom JSON (format: V{'2' if format_version else '1'})")
            
            # Get appropriate handler ONCE for all files
            handler = self.manager.get_v2_handler() if format_version else self.manager.get_v1_handler()
            
            # Load from server if available (ONCE)
            server_loaded = False
            if self.client:
                server_loaded = handler.load_from_server()
            
            # Only load from local file if server is NOT available
            # (otherwise we'd duplicate entries that are already on the server)
            if not server_loaded and json_file_path.exists():
                handler.load_from_file(str(json_file_path))
            elif not server_loaded:
                # No server and no local file - start fresh
                handler.custom_json = []
                handler.is_loaded = True
            
            # Process each TAF file and add to the SAME handler
            entries_added = 0
            entries_updated = 0
            
            for taf_file in taf_files:
                input_files = input_files_map.get(taf_file, [])
                artwork_url = artwork_urls.get(taf_file)
                
                if not input_files:
                    self.logger.warning(f"No input files found for {taf_file}, skipping")
                    continue
                
                self.logger.debug(f"Adding entry for {taf_file}")
                
                # Add new entry to existing handler
                if handler.is_loaded:
                    if handler.add_entry_from_taf(taf_file, input_files, artwork_url):
                        entries_added += 1
                        
                        self.event_bus.publish(CustomJsonEntryAddedEvent(
                            source='CustomJsonProcessor',
                            taf_file=taf_file,
                            series='',  # Would need to extract from handler
                            episodes=''
                        ))
                    else:
                        self.logger.error(f"Failed to add entry for {taf_file}")
            
            # Save ONCE at the end after processing all files
            if handler.is_loaded:
                handler.save_to_file(str(json_file_path))
            
            # Get final entry count
            import json
            total_entries = 0
            if json_file_path.exists():
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_entries = len(data) if isinstance(data, list) else 0
            
            self.logger.info(f"✓ Custom JSON saved to {json_file_path}")
            self.logger.info(f"  Entries added: {entries_added}, Total entries: {total_entries}")
            
            self.event_bus.publish(CustomJsonProcessingCompletedEvent(
                source='CustomJsonProcessor',
                file_path=str(json_file_path),
                entries_added=entries_added,
                entries_updated=entries_updated,
                total_entries=total_entries
            ))
            
            return {
                'success': True,
                'file_path': str(json_file_path),
                'entries_added': entries_added,
                'entries_updated': entries_updated,
                'total_entries': total_entries
            }
            
        except Exception as e:
            error_msg = f"Failed to create custom JSON: {e}"
            self.logger.error(error_msg, exc_info=True)
            self.event_bus.publish(CustomJsonProcessingFailedEvent(
                source='CustomJsonProcessor',
                error=error_msg
            ))
            return {
                'success': False,
                'error': error_msg
            }
