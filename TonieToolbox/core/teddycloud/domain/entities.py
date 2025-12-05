#!/usr/bin/python3
"""
Domain entities for TeddyCloud operations.
Pure business logic with no external dependencies.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path
from enum import Enum


class AuthenticationType(Enum):
    """Authentication methods supported by TeddyCloud."""
    NONE = "none"
    BASIC = "basic"
    CERTIFICATE = "certificate"


class SpecialFolder(Enum):
    """Special folder types in TeddyCloud."""
    LIBRARY = "library"
    SYSTEM = "system"


class TagValidationStatus(Enum):
    """Tag validation status."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TeddyCloudConnection:
    """Represents a connection configuration to a TeddyCloud server."""
    
    base_url: str
    authentication_type: AuthenticationType
    username: Optional[str] = None
    password: Optional[str] = None
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    ignore_ssl_verify: bool = False
    connection_timeout: int = 30
    read_timeout: int = 300
    max_retries: int = 3
    retry_delay: int = 1
    
    def __post_init__(self):
        """Validate connection configuration."""
        if not self.base_url:
            raise ValueError("Base URL is required")
            
        if self.authentication_type == AuthenticationType.BASIC:
            if not self.username or not self.password:
                raise ValueError("Username and password required for basic authentication")
                
        elif self.authentication_type == AuthenticationType.CERTIFICATE:
            if not self.cert_file:
                raise ValueError("Certificate file required for certificate authentication")
    
    @property
    def is_secure_connection(self) -> bool:
        """Check if connection uses HTTPS."""
        return self.base_url.startswith('https://')
    
    @property
    def requires_authentication(self) -> bool:
        """Check if connection requires authentication."""
        return self.authentication_type != AuthenticationType.NONE


@dataclass(frozen=True)
class TeddyCloudTag:
    """Represents a tag in TeddyCloud."""
    
    uid: str
    tag_type: str
    valid: TagValidationStatus
    series: Optional[str] = None
    episode: Optional[str] = None
    source: Optional[str] = None
    tracks: Optional[List[str]] = None
    track_seconds: Optional[List[int]] = None
    tonie_info: Optional[Dict[str, Any]] = None
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name for the tag."""
        if self.series and self.episode:
            return f"{self.series} - {self.episode}"
        elif self.series:
            return self.series
        elif self.episode:
            return self.episode
        return f"Tag {self.uid}"
    
    @property
    def total_duration_seconds(self) -> Optional[int]:
        """Get total duration in seconds."""
        if self.track_seconds and len(self.track_seconds) > 1:
            return self.track_seconds[-1]
        return None
    
    @property
    def track_count(self) -> int:
        """Get number of tracks."""
        if self.track_seconds:
            return len(self.track_seconds) - 1  # Last element is total duration
        elif self.tracks:
            return len(self.tracks)
        return 0


@dataclass(frozen=True)
class TeddyCloudFile:
    """Represents a file in TeddyCloud."""
    
    path: str
    name: str
    size: Optional[int] = None
    modified: Optional[str] = None
    content_type: Optional[str] = None
    
    @property
    def is_taf_file(self) -> bool:
        """Check if file is a TAF file."""
        return self.name.lower().endswith('.taf')
    
    @property
    def is_artwork_file(self) -> bool:
        """Check if file is an artwork file."""
        ext = self.name.lower()
        return ext.endswith(('.jpg', '.jpeg', '.png', '.webp'))
    
    @property
    def is_json_file(self) -> bool:
        """Check if file is a JSON file."""
        return self.name.lower().endswith('.json')


@dataclass(frozen=True)
class UploadResult:
    """Result of a file upload operation."""
    
    success: bool
    file_path: str
    destination_path: Optional[str] = None
    message: Optional[str] = None
    server_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if upload was successful."""
        return self.success and self.error is None


@dataclass(frozen=True)
class DirectoryCreationResult:
    """Result of directory creation operation."""
    
    success: bool
    path: str
    message: Optional[str] = None
    already_existed: bool = False
    error: Optional[str] = None


@dataclass(frozen=True)
class TagRetrievalResult:
    """Result of tag retrieval operation."""
    
    success: bool
    tags: List[TeddyCloudTag]
    total_count: int = 0
    message: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def has_tags(self) -> bool:
        """Check if any tags were retrieved."""
        return len(self.tags) > 0


@dataclass
class TagSourceAssignment:
    """Result of assigning a source path to a tag."""
    tag_uid: str
    source_path: str
    file_name: str  # Original file name for reporting
    overlay: Optional[str]
    success: bool
    error: Optional[str] = None
    previous_source: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation for summary display."""
        if self.success:
            return f"✓ {self.file_name} -> Tag {self.tag_uid}"
        else:
            return f"✗ {self.file_name} -> Tag {self.tag_uid} (Error: {self.error})"


@dataclass
class UnassignedTag:
    """Tag without a source path assigned."""
    uid: str
    overlay: Optional[str] = None
    valid: bool = True


@dataclass
class TagAssignmentSummary:
    """Summary of tag assignment operations."""
    total_files: int
    total_tags_provided: int
    successful_assignments: int
    failed_assignments: int
    unassigned_files: int
    assignments: List[TagSourceAssignment]
    
    def get_summary_table(self) -> str:
        """Generate formatted summary table."""
        lines = []
        lines.append("\n" + "="*80)
        lines.append("TAG ASSIGNMENT SUMMARY")
        lines.append("="*80)
        
        for idx, assignment in enumerate(self.assignments, 1):
            file_num = f"File {idx:02d}"
            if assignment.success:
                lines.append(f"{file_num}: {assignment.file_name}")
                lines.append(f"         -> ✓ Tag {assignment.tag_uid}")
            elif assignment.error and "No tag provided" not in assignment.error:
                lines.append(f"{file_num}: {assignment.file_name}")
                lines.append(f"         -> ✗ Failed: {assignment.error}")
            else:
                lines.append(f"{file_num}: {assignment.file_name}")
                lines.append(f"         -> ⚠  No tag provided (exceeded tag list)")
        
        lines.append("="*80)
        lines.append(f"Total Files:       {self.total_files}")
        lines.append(f"Tags Provided:     {self.total_tags_provided}")
        lines.append(f"Successful:        {self.successful_assignments}")
        lines.append(f"Failed:            {self.failed_assignments}")
        lines.append(f"No Tag Available:  {self.unassigned_files}")
        lines.append("="*80 + "\n")
        
        return "\n".join(lines)


class TeddyCloudError(Exception):
    """Base exception for TeddyCloud operations.
    
    Root exception for all TeddyCloud integration errors including connection,
    authentication, upload, and validation failures.
    
    Example:
        Generic TeddyCloud error::
        
            raise TeddyCloudError("TeddyCloud API version mismatch")
        
        Catching all TeddyCloud errors::
        
            try:
                upload_to_teddycloud(file_path, config)
            except TeddyCloudError as e:
                logger.error(f"TeddyCloud operation failed: {e}")
    """
    pass


class TeddyCloudConnectionError(TeddyCloudError):
    """Exception raised when connection to TeddyCloud fails.
    
    Raised when unable to establish connection to the TeddyCloud server,
    including network errors, timeout, or server unavailability.
    
    Example:
        Connection timeout::
        
            try:
                response = requests.get(server_url, timeout=5)
            except requests.Timeout:
                raise TeddyCloudConnectionError(
                    f"Connection timeout to {server_url}"
                )
        
        Server unreachable::
        
            if not is_server_reachable(config.server_url):
                raise TeddyCloudConnectionError(
                    f"Cannot reach TeddyCloud server at {config.server_url}"
                )
    """
    pass


class TeddyCloudAuthenticationError(TeddyCloudError):
    """Exception raised when authentication fails.
    
    Raised when credentials are invalid, missing, or when the authentication
    token has expired.
    
    Example:
        Invalid credentials::
        
            if response.status_code == 401:
                raise TeddyCloudAuthenticationError(
                    "Invalid username or password"
                )
        
        Missing authentication::
        
            if not config.username or not config.password:
                raise TeddyCloudAuthenticationError(
                    "Username and password required for TeddyCloud access"
                )
    """
    pass


class TeddyCloudUploadError(TeddyCloudError):
    """Exception raised when file upload fails.
    
    Raised when file upload to TeddyCloud fails due to network errors,
    server rejection, file size limits, or invalid file format.
    
    Example:
        Upload failure::
        
            if response.status_code != 200:
                raise TeddyCloudUploadError(
                    f"Upload failed with status {response.status_code}: {response.text}"
                )
        
        File too large::
        
            if file_size > MAX_UPLOAD_SIZE:
                raise TeddyCloudUploadError(
                    f"File size {file_size} exceeds maximum {MAX_UPLOAD_SIZE}"
                )
    """
    pass


class TeddyCloudValidationError(TeddyCloudError):
    """Exception raised when validation fails.
    
    Raised when TeddyCloud rejects data due to validation errors, such as
    invalid TAF format, missing metadata, or unsupported audio parameters.
    
    Example:
        Invalid TAF format::
        
            if not is_valid_taf_file(file_path):
                raise TeddyCloudValidationError(
                    f"File {file_path} is not a valid TAF file"
                )
        
        Missing required metadata::
        
            if not tonie_model:
                raise TeddyCloudValidationError(
                    "Tonie model ID required for upload"
                )
    """
    pass