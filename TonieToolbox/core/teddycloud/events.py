#!/usr/bin/python3
"""
TeddyCloud-specific domain events.
Events for TeddyCloud operations like uploads, tag retrieval, etc.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..events.base_events import DomainEvent


class TeddyCloudUploadStartedEvent(DomainEvent):
    """Event fired when TeddyCloud upload starts."""
    
    def __init__(self, source: str, file_path: Path, destination_path: Optional[str] = None,
                 special_folder: Optional[str] = None, 
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize upload started event."""
        data = {
            'file_path': str(file_path),
            'destination_path': destination_path,
            'special_folder': special_folder,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.upload.started"
    
    @property
    def file_path(self) -> Path:
        """Get source file path."""
        return Path(self.get_data('file_path'))
    
    @property
    def destination_path(self) -> Optional[str]:
        """Get destination path."""
        return self.get_data('destination_path')
    
    @property
    def special_folder(self) -> Optional[str]:
        """Get special folder."""
        return self.get_data('special_folder')


class TeddyCloudUploadCompletedEvent(DomainEvent):
    """Event fired when TeddyCloud upload completes successfully."""
    
    def __init__(self, source: str, file_path: Path, destination_path: Optional[str] = None,
                 upload_result: Optional[Dict[str, Any]] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize upload completed event."""
        data = {
            'file_path': str(file_path),
            'destination_path': destination_path,
            'upload_result': upload_result,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.upload.completed"
    
    @property
    def file_path(self) -> Path:
        """Get source file path."""
        return Path(self.get_data('file_path'))
    
    @property
    def destination_path(self) -> Optional[str]:
        """Get destination path."""
        return self.get_data('destination_path')
    
    @property
    def upload_result(self) -> Optional[Dict[str, Any]]:
        """Get upload result details."""
        return self.get_data('upload_result')


class TeddyCloudUploadFailedEvent(DomainEvent):
    """Event fired when TeddyCloud upload fails."""
    
    def __init__(self, source: str, file_path: Path, error: str,
                 destination_path: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize upload failed event."""
        data = {
            'file_path': str(file_path),
            'error': error,
            'destination_path': destination_path,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.upload.failed"
    
    @property
    def file_path(self) -> Path:
        """Get source file path."""
        return Path(self.get_data('file_path'))
    
    @property
    def error(self) -> str:
        """Get error message."""
        return self.get_data('error', 'Unknown error')
    
    @property
    def destination_path(self) -> Optional[str]:
        """Get destination path."""
        return self.get_data('destination_path')


class TeddyCloudTagsRetrievedEvent(DomainEvent):
    """Event fired when tags are retrieved from TeddyCloud."""
    
    def __init__(self, source: str, tag_count: int, successful: bool,
                 server_url: Optional[str] = None, error: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tags retrieved event."""
        data = {
            'tag_count': tag_count,
            'successful': successful,
            'server_url': server_url,
            'error': error,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tags.retrieved"
    
    @property
    def tag_count(self) -> int:
        """Get number of tags retrieved."""
        return self.get_data('tag_count', 0)
    
    @property
    def successful(self) -> bool:
        """Check if retrieval was successful."""
        return self.get_data('successful', False)
    
    @property
    def server_url(self) -> Optional[str]:
        """Get server URL."""
        return self.get_data('server_url')
    
    @property
    def error(self) -> Optional[str]:
        """Get error message if any."""
        return self.get_data('error')


class TeddyCloudConnectionEstablishedEvent(DomainEvent):
    """Event fired when connection to TeddyCloud is established."""
    
    def __init__(self, source: str, server_url: str, authentication_type: str,
                 secure_connection: bool = False,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize connection established event."""
        data = {
            'server_url': server_url,
            'authentication_type': authentication_type,
            'secure_connection': secure_connection,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.connection.established"
    
    @property
    def server_url(self) -> str:
        """Get server URL."""
        return self.get_data('server_url')
    
    @property
    def authentication_type(self) -> str:
        """Get authentication type."""
        return self.get_data('authentication_type')
    
    @property
    def secure_connection(self) -> bool:
        """Check if connection is secure (HTTPS)."""
        return self.get_data('secure_connection', False)


class TeddyCloudConnectionFailedEvent(DomainEvent):
    """Event fired when connection to TeddyCloud fails."""
    
    def __init__(self, source: str, server_url: str, error: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize connection failed event."""
        data = {
            'server_url': server_url,
            'error': error,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.connection.failed"
    
    @property
    def server_url(self) -> str:
        """Get server URL."""
        return self.get_data('server_url')
    
    @property
    def error(self) -> str:
        """Get error message."""
        return self.get_data('error', 'Unknown connection error')


class TeddyCloudBatchUploadStartedEvent(DomainEvent):
    """Event fired when batch upload starts."""
    
    def __init__(self, source: str, file_count: int, batch_type: str = "files",
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize batch upload started event."""
        data = {
            'file_count': file_count,
            'batch_type': batch_type,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.batch.upload.started"
    
    @property
    def file_count(self) -> int:
        """Get number of files in batch."""
        return self.get_data('file_count', 0)
    
    @property
    def batch_type(self) -> str:
        """Get batch type."""
        return self.get_data('batch_type', 'files')


class TeddyCloudBatchUploadCompletedEvent(DomainEvent):
    """Event fired when batch upload completes."""
    
    def __init__(self, source: str, total_files: int, successful_uploads: int,
                 failed_uploads: int, batch_type: str = "files",
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize batch upload completed event."""
        data = {
            'total_files': total_files,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'batch_type': batch_type,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.batch.upload.completed"
    
    @property
    def total_files(self) -> int:
        """Get total number of files in batch."""
        return self.get_data('total_files', 0)
    
    @property
    def successful_uploads(self) -> int:
        """Get number of successful uploads."""
        return self.get_data('successful_uploads', 0)
    
    @property
    def failed_uploads(self) -> int:
        """Get number of failed uploads."""
        return self.get_data('failed_uploads', 0)
    
    @property
    def batch_type(self) -> str:
        """Get batch type."""
        return self.get_data('batch_type', 'files')
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful_uploads / self.total_files) * 100

class TeddyCloudTagAssignmentStartedEvent(DomainEvent):
    """Event fired when tag assignment starts."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment started event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.started"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')


class TeddyCloudTagAssignmentCompletedEvent(DomainEvent):
    """Event fired when tag assignment completes successfully."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str,
                 overlay: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment completed event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            'overlay': overlay,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.completed"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')
    
    @property
    def overlay(self) -> Optional[str]:
        """Get overlay ID."""
        return self.get_data('overlay')


class TeddyCloudTagAssignmentFailedEvent(DomainEvent):
    """Event fired when tag assignment fails."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str, error: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment failed event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            'error': error,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.failed"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')
    
    @property
    def error(self) -> str:
        """Get error message."""
        return self.get_data('error', 'Unknown error')


class TeddyCloudTagAssignmentStartedEvent(DomainEvent):
    """Event fired when tag assignment starts."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment started event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.started"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')


class TeddyCloudTagAssignmentCompletedEvent(DomainEvent):
    """Event fired when tag assignment completes successfully."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str,
                 overlay: Optional[str] = None,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment completed event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            'overlay': overlay,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.completed"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')
    
    @property
    def overlay(self) -> Optional[str]:
        """Get overlay ID."""
        return self.get_data('overlay')


class TeddyCloudTagAssignmentFailedEvent(DomainEvent):
    """Event fired when tag assignment fails."""
    
    def __init__(self, source: str, tag_uid: str, source_path: str, error: str,
                 event_data: Optional[Dict[str, Any]] = None):
        """Initialize tag assignment failed event."""
        data = {
            'tag_uid': tag_uid,
            'source_path': source_path,
            'error': error,
            **(event_data or {})
        }
        super().__init__(source, data)
    
    @property
    def event_type(self) -> str:
        """Get event type."""
        return "teddycloud.tag.assignment.failed"
    
    @property
    def tag_uid(self) -> str:
        """Get tag UID."""
        return self.get_data('tag_uid', '')
    
    @property
    def source_path(self) -> str:
        """Get source path."""
        return self.get_data('source_path', '')
    
    @property
    def error(self) -> str:
        """Get error message."""
        return self.get_data('error', 'Unknown error')
