#!/usr/bin/python3
"""
Domain interfaces for TeddyCloud operations.
Defines contracts for infrastructure implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .entities import (
    TeddyCloudConnection, TeddyCloudTag, TeddyCloudFile,
    UploadResult, DirectoryCreationResult, TagRetrievalResult,
    SpecialFolder
)


class TeddyCloudRepository(ABC):
    """Repository interface for TeddyCloud server operations."""
    
    @abstractmethod
    def connect(self, connection: TeddyCloudConnection) -> bool:
        """Establish connection to TeddyCloud server."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection to server is working."""
        pass
    
    @abstractmethod
    def get_tags(self) -> TagRetrievalResult:
        """Retrieve all tags from server."""
        pass
    
    @abstractmethod
    def get_tonies_json(self) -> Dict[str, Any]:
        """Retrieve tonies.json from server."""
        pass
    
    @abstractmethod
    def get_tonies_custom_json(self) -> List[Dict[str, Any]]:
        """Retrieve tonies_custom.json from server.
        
        Returns:
            Array of custom Tonie definitions with metadata and track info
        """
        pass
    
    @abstractmethod
    def get_file_index(self) -> Dict[str, Any]:
        """Retrieve file index from server."""
        pass
    
    @abstractmethod
    def get_file_index_v2(self) -> Dict[str, Any]:
        """Retrieve file index V2 from server (with unix timestamps and improved format)."""
        pass
    
    @abstractmethod
    def get_tag_info(self, uid: str) -> Dict[str, Any]:
        """Get detailed information about a specific tag by UID."""
        pass
    
    @abstractmethod
    def get_boxes(self) -> Dict[str, Any]:
        """Get list of all registered Tonieboxes."""
        pass
    
    @abstractmethod
    def get_setting(self, setting_path: str) -> Any:
        """Get a specific setting value from server."""
        pass
    
    @abstractmethod
    def set_setting(self, setting_path: str, value: Any) -> bool:
        """Set a specific setting value on server."""
        pass
    
    @abstractmethod
    def trigger_tonies_json_update(self) -> bool:
        """Trigger update of tonies.json from remote source."""
        pass
    
    @abstractmethod
    def trigger_tonies_json_reload(self) -> bool:
        """Trigger reload of tonies.json from disk."""
        pass
    
    @abstractmethod
    def assign_unknown_tag(self, uid: str, tonie_model: str) -> bool:
        """Assign an unknown tag to a specific tonie model."""
        pass
    
    @abstractmethod
    def set_tag_source(self, tag_uid: str, source_path: str, 
                      overlay: Optional[str] = None,
                      nocloud: bool = True) -> 'TagSourceAssignment':
        """Set the source path for a specific tag."""
        pass
    
    @abstractmethod
    def get_unassigned_tags(self) -> List['UnassignedTag']:
        """Get all tags that have no source path assigned."""
        pass
    
    @abstractmethod
    def get_file(self, file_path: str, overlay: Optional[str] = None, 
                special: Optional[SpecialFolder] = None) -> Dict[str, Any]:
        """Retrieve a specific file from server."""
        pass
    
    @abstractmethod
    def upload_file(self, local_path: str, destination_path: Optional[str] = None,
                   overlay: Optional[str] = None, 
                   special: Optional[SpecialFolder] = None) -> UploadResult:
        """Upload a file to the server."""
        pass
    
    @abstractmethod
    def create_directory(self, path: str, overlay: Optional[str] = None,
                        special: Optional[SpecialFolder] = None) -> DirectoryCreationResult:
        """Create a directory on the server."""
        pass
    
    @abstractmethod
    def delete_file(self, path: str, overlay: Optional[str] = None,
                   special: Optional[SpecialFolder] = None) -> bool:
        """Delete a file from the server."""
        pass
    
    @abstractmethod
    def delete_directory(self, path: str, overlay: Optional[str] = None,
                        special: Optional[SpecialFolder] = None) -> bool:
        """Delete a directory from the server."""
        pass


class FileSystemService(ABC):
    """Interface for file system operations."""
    
    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        pass
    
    @abstractmethod
    def read_file_content(self, path: str) -> bytes:
        """Read file content as bytes."""
        pass
    
    @abstractmethod
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists, create if needed."""
        pass


class TemplateProcessor(ABC):
    """Interface for processing path templates."""
    
    @abstractmethod
    def apply_template(self, template: str, metadata: Dict[str, Any]) -> str:
        """Apply metadata to path template."""
        pass
    
    @abstractmethod
    def validate_template(self, template: str) -> bool:
        """Validate template syntax."""
        pass


class MetadataExtractor(ABC):
    """Interface for extracting metadata from files."""
    
    @abstractmethod
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        pass
    
    @abstractmethod
    def supports_file_type(self, file_path: str) -> bool:
        """Check if file type is supported."""
        pass