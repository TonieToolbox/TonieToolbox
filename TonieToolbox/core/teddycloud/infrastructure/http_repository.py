#!/usr/bin/python3
"""
HTTP repository implementation for TeddyCloud API operations.
Handles all external HTTP communication with proper error handling.
"""
import json
import ssl
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..domain import (
    TeddyCloudConnection, TeddyCloudTag, TeddyCloudFile,
    UploadResult, DirectoryCreationResult, TagRetrievalResult,
    SpecialFolder, TagValidationStatus, AuthenticationType,
    TeddyCloudRepository, TeddyCloudConnectionError, TeddyCloudAuthenticationError,
    TeddyCloudUploadError, TeddyCloudError
)


class HttpTeddyCloudRepository(TeddyCloudRepository):
    """HTTP implementation of TeddyCloud repository."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize HTTP repository."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        self.session: Optional[requests.Session] = None
        self.base_url: Optional[str] = None
        self.connection: Optional[TeddyCloudConnection] = None
    
    def connect(self, connection: TeddyCloudConnection) -> bool:
        """Establish connection to TeddyCloud server."""
        try:
            self.connection = connection
            self.base_url = connection.base_url.rstrip('/')
            
            # Create session with proper configuration
            self.session = self._create_session(connection)
            
            self.logger.info(f"HTTP repository connected to: {self.base_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            raise TeddyCloudConnectionError(f"Failed to connect: {e}")
    
    def test_connection(self) -> bool:
        """Test if connection to server is working."""
        try:
            if not self.session or not self.base_url:
                return False
            
            # Try to get file index as connection test
            response = self._make_request('GET', '/api/fileIndex')
            return response.status_code == 200
            
        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}")
            return False
    
    def get_tags(self) -> TagRetrievalResult:
        """Retrieve all tags from server."""
        try:
            response = self._make_request('GET', '/api/getTagIndex')
            response.raise_for_status()
            
            data = response.json()
            
            # Parse tags from response
            tags = []
            if isinstance(data, dict) and 'tags' in data:
                for tag_data in data['tags']:
                    tag = self._parse_tag_data(tag_data)
                    if tag:
                        tags.append(tag)
            
            return TagRetrievalResult(
                success=True,
                tags=tags,
                total_count=len(tags),
                message=f"Retrieved {len(tags)} tags"
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to retrieve tags: {e}"
            self.logger.error(error_msg)
            return TagRetrievalResult(
                success=False,
                tags=[],
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error retrieving tags: {e}"
            self.logger.error(error_msg)
            return TagRetrievalResult(
                success=False,
                tags=[],
                error=error_msg
            )
    
    def get_tonies_json(self) -> Dict[str, Any]:
        """Retrieve tonies.json from server."""
        try:
            response = self._make_request('GET', '/api/toniesJson')
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get tonies.json: {e}")
            return {}
    
    def get_tonies_custom_json(self) -> List[Dict[str, Any]]:
        """Retrieve tonies_custom.json from server.
        
        Returns:
            Array of custom Tonie definitions with metadata and track info
        """
        try:
            response = self._make_request('GET', '/api/toniesCustomJson')
            response.raise_for_status()
            
            # Response is a base64-encoded data URL
            # Format: data:application/octet-stream;base64,<base64_data>
            response_text = response.text.strip()
            
            if response_text.startswith('data:'):
                # Extract base64 part after the comma
                import base64
                _, base64_data = response_text.split(',', 1)
                decoded_json = base64.b64decode(base64_data).decode('utf-8')
                return json.loads(decoded_json)
            else:
                # Fallback: try to parse as regular JSON
                return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get tonies_custom.json: {e}")
            return []
    
    def get_file_index(self) -> Dict[str, Any]:
        """Retrieve file index from server."""
        try:
            response = self._make_request('GET', '/api/fileIndex')
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get file index: {e}")
            return {}
    
    def get_file_index_v2(self) -> Dict[str, Any]:
        """Retrieve file index V2 from server (with unix timestamps and improved format)."""
        try:
            response = self._make_request('GET', '/api/fileIndexV2')
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get file index v2: {e}")
            return {}
    
    def get_tag_info(self, uid: str, overlay: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a specific tag by UID.
        
        Args:
            uid: Tag UID (normalized format without colons)
            overlay: Optional overlay ID to query (defaults to current overlay if not specified)
        """
        try:
            # API uses 'ruid' parameter (not 'uid')
            params = {'ruid': uid}
            if overlay:
                params['overlay'] = overlay
            
            response = self._make_request('GET', '/api/getTagInfo', params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get tag info for {uid}: {e}")
            return {}
    
    def get_boxes(self) -> Dict[str, Any]:
        """Get list of all registered Tonieboxes."""
        try:
            response = self._make_request('GET', '/api/getBoxes')
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get boxes: {e}")
            return {}
    
    def get_index(self, overlay: Optional[str] = None, show_internal: bool = False, 
                 no_level: bool = False) -> Dict[str, Any]:
        """Get configuration index with all settings.
        
        Args:
            overlay: Optional overlay name to get settings for
            show_internal: Whether to include internal settings
            no_level: Whether to ignore user level restrictions
            
        Returns:
            Dictionary containing settings configuration
        """
        try:
            params = {}
            if overlay:
                params['overlay'] = overlay
            if show_internal:
                params['internal'] = 'true'
            if no_level:
                params['nolevel'] = 'true'
            
            response = self._make_request('GET', '/api/getIndex', params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get index: {e}")
            return {}
    
    def get_toniebox_json(self) -> List[Dict[str, Any]]:
        """Get list of registered Tonieboxes in toniebox.json format.
        
        Returns:
            Array of Toniebox definitions with id, name, img_src, and crop info
        """
        try:
            response = self._make_request('GET', '/api/tonieboxJson')
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get toniebox.json: {e}")
            return []
    
    def get_toniebox_custom_json(self) -> List[Dict[str, Any]]:
        """Get custom Toniebox definitions.
        
        Note: This endpoint may not exist in all TeddyCloud versions.
        Consider using get_boxes() instead for Toniebox information.
        
        Returns:
            Array of custom Toniebox definitions
        """
        try:
            response = self._make_request('GET', '/api/tonieboxCustomJson')
            response.raise_for_status()
            
            # Response might be a base64-encoded data URL
            response_text = response.text.strip()
            
            if response_text.startswith('data:'):
                # Extract base64 part after the comma
                import base64
                _, base64_data = response_text.split(',', 1)
                decoded_json = base64.b64decode(base64_data).decode('utf-8')
                return json.loads(decoded_json)
            else:
                # Fallback: try to parse as regular JSON
                return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get toniebox custom json: {e}")
            return []
    
    def get_setting(self, setting_path: str) -> Any:
        """Get a specific setting value from server."""
        try:
            endpoint = f'/api/settings/get/{setting_path}'
            response = self._make_request('GET', endpoint)
            response.raise_for_status()
            # Settings endpoint returns raw value, not JSON
            return response.text
            
        except Exception as e:
            self.logger.error(f"Failed to get setting {setting_path}: {e}")
            return None
    
    def set_setting(self, setting_path: str, value: Any) -> bool:
        """Set a specific setting value on server."""
        try:
            endpoint = f'/api/settings/set/{setting_path}'
            data = {'value': str(value)}
            response = self._make_request('POST', endpoint, data=data)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set setting {setting_path}: {e}")
            return False
    
    def reset_setting(self, setting_path: str, overlay: Optional[str] = None) -> bool:
        """Reset a setting to its default value.
        
        Args:
            setting_path: Path to the setting to reset
            overlay: Optional overlay name
            
        Returns:
            True if setting was reset successfully
        """
        try:
            endpoint = f'/api/settings/reset/{setting_path}'
            params = {}
            if overlay:
                params['overlay'] = overlay
            
            response = self._make_request('POST', endpoint, params=params)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset setting {setting_path}: {e}")
            return False
    
    def trigger_tonies_json_update(self) -> bool:
        """Trigger update of tonies.json from remote source."""
        try:
            response = self._make_request('GET', '/api/toniesJsonUpdate')
            response.raise_for_status()
            self.logger.info("Triggered tonies.json update")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger tonies.json update: {e}")
            return False
    
    def trigger_tonies_json_reload(self) -> bool:
        """Trigger reload of tonies.json from disk."""
        try:
            response = self._make_request('GET', '/api/toniesJsonReload')
            response.raise_for_status()
            self.logger.info("Triggered tonies.json reload")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to trigger tonies.json reload: {e}")
            return False
    
    def assign_unknown_tag(self, uid: str, tonie_model: str) -> bool:
        """Assign an unknown tag to a specific tonie model."""
        try:
            data = {'uid': uid, 'model': tonie_model}
            response = self._make_request('POST', '/api/assignUnknown', data=data)
            response.raise_for_status()
            self.logger.info(f"Assigned tag {uid} to model {tonie_model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to assign tag {uid}: {e}")
            return False
    
    def set_tag_source(self, tag_uid: str, source_path: str, 
                      overlay: Optional[str] = None,
                      nocloud: bool = True):
        """
        Set the source path for a specific tag.
        
        Args:
            tag_uid: Tag UID (with or without colons, e.g., E0:04:03:50:1E:E9:18:F2)
            source_path: Source path (e.g., "lib:///path/to/file.taf")
            overlay: Overlay ID (Toniebox MAC address). If None, auto-selects first available box.
            nocloud: Prevent cloud sync (default: True)
            
        Returns:
            TagSourceAssignment with result
        """
        from ..domain import TagSourceAssignment
        from ..events import TeddyCloudTagAssignmentStartedEvent, TeddyCloudTagAssignmentCompletedEvent, TeddyCloudTagAssignmentFailedEvent
        from ...events import get_event_bus
        from pathlib import Path
        
        # Publish started event
        event_bus = get_event_bus()
        event_bus.publish(TeddyCloudTagAssignmentStartedEvent(
            source='HttpTeddyCloudRepository',
            tag_uid=tag_uid,
            source_path=source_path
        ))
        
        # Normalize UID - remove colons, convert to lowercase, and REVERSE byte order
        # Example: E0:04:03:50:0E:EA:97:2D → e00403500eea972d → 2d97ea0e500304e0
        uid_no_colons = tag_uid.replace(':', '').lower()
        
        # Reverse byte order: split into 2-char chunks, reverse, rejoin
        uid_bytes = [uid_no_colons[i:i+2] for i in range(0, len(uid_no_colons), 2)]
        normalized_uid = ''.join(reversed(uid_bytes))
        
        self.logger.debug(f"UID transformation: {tag_uid} → {uid_no_colons} → {normalized_uid} (reversed)")
        
        # Auto-detect overlay if not provided
        if overlay is None:
            boxes = self.get_boxes()
            if boxes and isinstance(boxes, dict) and 'boxes' in boxes:
                box_list = boxes['boxes']
                if box_list and len(box_list) > 0:
                    # Use first available Toniebox MAC address
                    overlay = box_list[0].get('ID', '').replace(':', '')
                    self.logger.debug(f"Auto-selected overlay from first Toniebox: {overlay}")
                else:
                    error_msg = "No Tonieboxes found on server for overlay auto-detection"
                    event_bus.publish(TeddyCloudTagAssignmentFailedEvent(
                        source='HttpTeddyCloudRepository',
                        tag_uid=tag_uid,
                        source_path=source_path,
                        error=error_msg
                    ))
                    return TagSourceAssignment(
                        tag_uid=tag_uid,
                        source_path=source_path,
                        file_name=Path(source_path).name,
                        overlay=None,
                        success=False,
                        error=error_msg
                    )
        
        # Build endpoint with overlay
        endpoint = f'/content/json/set/{normalized_uid}'
        if overlay:
            endpoint += f'?overlay={overlay}'
        
        # Prepare payload - TeddyCloud expects URL-encoded plain text body, not form data
        # Example from browser: source=lib%3A%2F%2FOtfried%20Preu%C3%9Fler%2F...
        from urllib.parse import urlencode
        payload = urlencode({'source': source_path})
        
        # Set Content-Type to text/plain as browser does
        headers = {
            'Content-Type': 'text/plain'
        }
        
        try:
            response = self._make_request('POST', endpoint, data=payload, headers=headers)
            response.raise_for_status()
            
            self.logger.debug(f"Assignment response status: {response.status_code}")
            self.logger.debug(f"Assignment response body: {response.text}")
            
            self.logger.info(f"Set source for tag {tag_uid}: {source_path}")
            
            # Verify the assignment by checking tag info WITH the same overlay
            import time
            time.sleep(0.5)  # Brief delay to ensure server has processed the assignment
            
            self.logger.debug(f"Verifying assignment for tag (original UID: {tag_uid}) with overlay {overlay}")
            # get_tag_info also expects reversed UID format
            tag_info = self.get_tag_info(normalized_uid, overlay=overlay)
            self.logger.debug(f"Verification response for {normalized_uid}: {tag_info}")
            if tag_info and 'tagInfo' in tag_info:
                actual_source = tag_info['tagInfo'].get('source', '')
                if actual_source == source_path:
                    self.logger.info(f"✓ Verified tag assignment: {tag_uid} → {source_path}")
                else:
                    error_msg = f"Tag assignment verification failed: expected '{source_path}', got '{actual_source}'"
                    self.logger.error(error_msg)
                    
                    event_bus.publish(TeddyCloudTagAssignmentFailedEvent(
                        source='HttpTeddyCloudRepository',
                        tag_uid=tag_uid,
                        source_path=source_path,
                        error=error_msg
                    ))
                    
                    return TagSourceAssignment(
                        tag_uid=tag_uid,
                        source_path=source_path,
                        file_name=Path(source_path).name,
                        overlay=overlay,
                        success=False,
                        error=error_msg
                    )
            else:
                self.logger.warning(f"Could not verify tag assignment for {tag_uid} - tag info not available")
            
            # Publish completed event
            event_bus.publish(TeddyCloudTagAssignmentCompletedEvent(
                source='HttpTeddyCloudRepository',
                tag_uid=tag_uid,
                source_path=source_path,
                overlay=overlay
            ))
            
            return TagSourceAssignment(
                tag_uid=tag_uid,
                source_path=source_path,
                file_name=Path(source_path).name,
                overlay=overlay,
                success=True
            )
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Failed to set source for tag {tag_uid}: {error_msg}")
            
            # Publish failed event
            event_bus.publish(TeddyCloudTagAssignmentFailedEvent(
                source='HttpTeddyCloudRepository',
                tag_uid=tag_uid,
                source_path=source_path,
                error=error_msg
            ))
            
            return TagSourceAssignment(
                tag_uid=tag_uid,
                source_path=source_path,
                file_name=Path(source_path).name,
                overlay=overlay,
                success=False,
                error=error_msg
            )
    
    def get_unassigned_tags(self) -> List:
        """Get all tags that have no source path assigned."""
        from ..domain import UnassignedTag, TagValidationStatus
        
        try:
            tags_result = self.get_tags()
            unassigned = []
            
            for tag in tags_result.tags:
                # Check if tag has no source or empty source
                if not tag.source or tag.source.strip() == '':
                    # Get tag info to extract overlay if available
                    tag_info = self.get_tag_info(tag.uid)
                    overlay = tag_info.get('overlay') if tag_info else None
                    
                    unassigned.append(UnassignedTag(
                        uid=tag.uid,
                        overlay=overlay,
                        valid=tag.valid == TagValidationStatus.VALID
                    ))
            
            return unassigned
            
        except Exception as e:
            self.logger.error(f"Failed to get unassigned tags: {e}")
            return []
    
    def get_file(self, file_path: str, overlay: Optional[str] = None,
                special: Optional[SpecialFolder] = None) -> Dict[str, Any]:
        """Retrieve a specific file from server."""
        try:
            params = {'path': file_path}
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            response = self._make_request('GET', '/api/getFile', params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get file {file_path}: {e}")
            return {}
    
    def upload_file(self, local_path: str, destination_path: Optional[str] = None,
                   overlay: Optional[str] = None,
                   special: Optional[SpecialFolder] = None) -> UploadResult:
        """Upload a file to the server."""
        try:
            import os
            from pathlib import Path
            
            # Extract filename and directory from destination_path
            if destination_path:
                # destination_path is the full path like "artist/album/file.taf"
                # We need to extract: directory="artist/album" and filename="file.taf"
                dest_pathobj = Path(destination_path)
                directory = str(dest_pathobj.parent) if dest_pathobj.parent != Path('.') else ''
                filename = dest_pathobj.name
            else:
                directory = ''
                filename = os.path.basename(local_path)
            
            # Prepare upload data
            params = {}
            if directory:
                params['path'] = directory  # Just the directory, not the full path
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            # Open and upload file
            with open(local_path, 'rb') as file_obj:
                # Use filename as form field name (matching browser behavior)
                files = {filename: (filename, file_obj, 'application/x-tonie-audio-file')}
                
                response = self._make_request(
                    'POST', '/api/fileUpload',
                    params=params,
                    files=files
                )
                response.raise_for_status()
                
                # Parse response - TeddyCloud may return empty body or plain text on success
                result_data = {}
                if response.content:
                    try:
                        result_data = response.json()
                    except ValueError:
                        # Response is not JSON (e.g., plain text "OK"), treat as success
                        result_data = {'message': response.text.strip()}
                
                return UploadResult(
                    success=True,
                    file_path=local_path,
                    destination_path=destination_path,
                    message="Upload successful",
                    server_response=result_data
                )
                
        except FileNotFoundError:
            error_msg = f"Local file not found: {local_path}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Upload failed: {e}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected upload error: {e}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
    
    def create_directory(self, path: str, overlay: Optional[str] = None,
                        special: Optional[SpecialFolder] = None) -> DirectoryCreationResult:
        """Create a directory on the server."""
        try:
            params = {}
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            # Path must be sent in request body as plain text
            headers = {'Content-Type': 'text/plain'}
            response = self._make_request('POST', '/api/dirCreate', params=params, data=path, headers=headers)
            
            # Handle different response cases
            if response.status_code == 200:
                return DirectoryCreationResult(
                    success=True,
                    path=path,
                    message="Directory created successfully"
                )
            elif response.status_code == 500:
                # Check if directory already exists
                # TeddyCloud returns "Generic error code [1]" when directory exists
                response_text = response.text.lower()
                if "already exists" in response_text or "file exists" in response_text or "generic error code [1]" in response_text:
                    return DirectoryCreationResult(
                        success=True,
                        path=path,
                        message="Directory already exists",
                        already_existed=True
                    )
            
            # If we get here, something went wrong
            response.raise_for_status()
            
            return DirectoryCreationResult(
                success=False,
                path=path,
                error=f"Unexpected response: {response.status_code}"
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to create directory {path}: {e}"
            self.logger.error(error_msg)
            return DirectoryCreationResult(
                success=False,
                path=path,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected error creating directory {path}: {e}"
            self.logger.error(error_msg)
            return DirectoryCreationResult(
                success=False,
                path=path,
                error=error_msg
            )
    
    def delete_file(self, path: str, overlay: Optional[str] = None,
                   special: Optional[SpecialFolder] = None) -> bool:
        """Delete a file from the server."""
        try:
            params = {'path': path}
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            response = self._make_request('POST', '/api/fileDelete', params=params)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {path}: {e}")
            return False
    
    def delete_directory(self, path: str, overlay: Optional[str] = None,
                        special: Optional[SpecialFolder] = None) -> bool:
        """Delete a directory from the server."""
        try:
            params = {'path': path}
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            response = self._make_request('POST', '/api/dirDelete', params=params)
            response.raise_for_status()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete directory {path}: {e}")
            return False
    
    def move_file(self, source_path: str, target_path: str, 
                 overlay: Optional[str] = None,
                 special: Optional[SpecialFolder] = None) -> bool:
        """Move or rename a file on the server.
        
        Args:
            source_path: Source file path
            target_path: Destination file path
            overlay: Optional overlay name
            special: Optional special folder
            
        Returns:
            True if file was moved successfully
        """
        try:
            data = {
                'source': source_path,
                'target': target_path
            }
            
            params = {}
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            response = self._make_request('POST', '/api/fileMove', 
                                         params=params, data=data)
            response.raise_for_status()
            self.logger.info(f"Moved file from {source_path} to {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to move file from {source_path} to {target_path}: {e}")
            return False
    
    def upload_taf_file(self, local_path: str, name: Optional[str] = None,
                       destination_path: str = '/', overlay: Optional[str] = None,
                       special: Optional[SpecialFolder] = None) -> UploadResult:
        """Upload a TAF file to the server with validation.
        
        Args:
            local_path: Path to local TAF file
            name: Optional custom filename (defaults to original filename)
            destination_path: Destination directory on server
            overlay: Optional overlay name
            special: Optional special folder
            
        Returns:
            UploadResult with success status and details
        """
        try:
            import os
            
            # Use original filename if not specified
            if not name:
                name = os.path.basename(local_path)
            
            # Ensure .taf extension
            if not name.endswith('.taf'):
                name += '.taf'
            
            # Prepare parameters
            params = {
                'name': name,
                'path': destination_path
            }
            if overlay:
                params['overlay'] = overlay
            if special:
                params['special'] = special.value
            
            # Open and upload file
            with open(local_path, 'rb') as file_obj:
                files = {'file': file_obj}
                
                response = self._make_request(
                    'POST', '/api/tafUpload',
                    params=params,
                    files=files
                )
                
                # Check response
                if response.status_code == 200:
                    return UploadResult(
                        success=True,
                        file_path=local_path,
                        destination_path=destination_path,
                        message="TAF file uploaded and validated successfully",
                        server_response={'name': name, 'path': destination_path}
                    )
                elif response.status_code == 500:
                    error_msg = response.text or "TAF validation failed"
                    return UploadResult(
                        success=False,
                        file_path=local_path,
                        error=f"TAF upload failed: {error_msg}"
                    )
                else:
                    response.raise_for_status()
                    return UploadResult(
                        success=False,
                        file_path=local_path,
                        error=f"Unexpected response: {response.status_code}"
                    )
                    
        except FileNotFoundError:
            error_msg = f"Local TAF file not found: {local_path}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"TAF upload failed: {e}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Unexpected TAF upload error: {e}"
            self.logger.error(error_msg)
            return UploadResult(
                success=False,
                file_path=local_path,
                error=error_msg
            )
    
    def get_content_json(self, ruid: str, overlay: Optional[str] = None) -> Dict[str, Any]:
        """Get content.json for a specific RUID.
        
        Args:
            ruid: Reverse UID (16 hex characters)
            overlay: Optional overlay name
            
        Returns:
            Content JSON data
        """
        try:
            # Validate RUID format (16 hex characters)
            if len(ruid) != 16 or not all(c in '0123456789abcdefABCDEF' for c in ruid):
                self.logger.error(f"Invalid RUID format: {ruid}")
                return {}
            
            endpoint = f'/api/content/json/get/{ruid.lower()}'
            params = {}
            if overlay:
                params['overlay'] = overlay
            
            response = self._make_request('GET', endpoint, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get content JSON for {ruid}: {e}")
            return {}
    
    def set_content_json(self, ruid: str, 
                        source: Optional[str] = None,
                        tonie_model: Optional[str] = None,
                        live: Optional[bool] = None,
                        nocloud: Optional[bool] = None,
                        hide: Optional[bool] = None,
                        claimed: Optional[bool] = None,
                        overlay: Optional[str] = None) -> bool:
        """Update content.json settings for a specific RUID.
        
        Args:
            ruid: Reverse UID (16 hex characters)
            source: Optional source path
            tonie_model: Optional tonie model identifier
            live: Optional live streaming flag
            nocloud: Optional no cloud flag
            hide: Optional hide flag
            claimed: Optional claimed flag
            overlay: Optional overlay name
            
        Returns:
            True if content JSON was updated successfully
        """
        try:
            # Validate RUID format
            if len(ruid) != 16 or not all(c in '0123456789abcdefABCDEF' for c in ruid):
                self.logger.error(f"Invalid RUID format: {ruid}")
                return False
            
            endpoint = f'/api/content/json/set/{ruid.lower()}'
            
            # Build data with only provided parameters
            data = {}
            if source is not None:
                data['source'] = source
            if tonie_model is not None:
                data['tonie_model'] = tonie_model
            if live is not None:
                data['live'] = 'true' if live else 'false'
            if nocloud is not None:
                data['nocloud'] = 'true' if nocloud else 'false'
            if hide is not None:
                data['hide'] = 'true' if hide else 'false'
            if claimed is not None:
                data['claimed'] = 'true' if claimed else 'false'
            
            params = {}
            if overlay:
                params['overlay'] = overlay
            
            response = self._make_request('POST', endpoint, params=params, data=data)
            response.raise_for_status()
            self.logger.info(f"Updated content JSON for {ruid}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set content JSON for {ruid}: {e}")
            return False
    
    def _create_session(self, connection: TeddyCloudConnection) -> requests.Session:
        """Create configured requests session."""
        session = requests.Session()
                
        # Configure SSL
        if connection.ignore_ssl_verify:
            session.verify = False
            # Disable SSL warnings
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Configure authentication
        if connection.authentication_type == AuthenticationType.BASIC:
            session.auth = (connection.username, connection.password)
        elif connection.authentication_type == AuthenticationType.CERTIFICATE:
            session.cert = (connection.cert_file, connection.key_file)
        
        # Configure timeouts and retries
        retry_strategy = Retry(
            total=connection.max_retries,
            backoff_factor=connection.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default timeout
        session.timeout = (connection.connection_timeout, connection.read_timeout)
        
        return session
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling."""
        if not self.session or not self.base_url:
            raise TeddyCloudConnectionError("Not connected to server")
        
        url = urljoin(self.base_url, endpoint)
        
        try:
            self.logger.debug(f"Making {method} request to: {url}")
            response = self.session.request(method, url, **kwargs)
            # Ensure proper UTF-8 encoding for responses
            response.encoding = 'utf-8'
            self.logger.debug(f"Response status: {response.status_code}")
            return response
            
        except requests.exceptions.ConnectionError as e:
            raise TeddyCloudConnectionError(f"Connection failed: {e}")
        except requests.exceptions.Timeout as e:
            raise TeddyCloudConnectionError(f"Request timeout: {e}")
        except requests.exceptions.RequestException as e:
            raise TeddyCloudError(f"Request failed: {e}")
    
    def _parse_tag_data(self, tag_data: Dict[str, Any]) -> Optional[TeddyCloudTag]:
        """Parse tag data from server response."""
        try:
            uid = tag_data.get('uid', '')
            tag_type = tag_data.get('type', 'Unknown')
            
            # Parse validation status
            valid_value = tag_data.get('valid', False)
            if isinstance(valid_value, bool):
                valid = TagValidationStatus.VALID if valid_value else TagValidationStatus.INVALID
            else:
                valid = TagValidationStatus.UNKNOWN
            
            # Extract tonie info
            tonie_info = tag_data.get('tonieInfo', {})
            series = tonie_info.get('series')
            episode = tonie_info.get('episode')
            tracks = tonie_info.get('tracks', [])
            
            return TeddyCloudTag(
                uid=uid,
                tag_type=tag_type,
                valid=valid,
                series=series,
                episode=episode,
                source=tag_data.get('source'),
                tracks=tracks,
                track_seconds=tag_data.get('trackSeconds', []),
                tonie_info=tonie_info
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to parse tag data: {e}")
            return None