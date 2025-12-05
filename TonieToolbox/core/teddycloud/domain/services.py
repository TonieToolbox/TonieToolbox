#!/usr/bin/python3
"""
Domain services for TeddyCloud business logic.
Pure business logic with no infrastructure dependencies.
"""
from typing import Dict, Any, List, Optional, Tuple
import logging

from .entities import (
    TeddyCloudConnection, TeddyCloudTag, UploadResult, DirectoryCreationResult,
    SpecialFolder, TeddyCloudValidationError, AuthenticationType
)
from .interfaces import TeddyCloudRepository, TemplateProcessor


class ConnectionValidationService:
    """Domain service for validating TeddyCloud connections."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize service with optional logger."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def validate_connection_config(self, connection: TeddyCloudConnection) -> bool:
        """Validate connection configuration according to business rules."""
        try:
            # URL validation
            if not connection.base_url:
                raise TeddyCloudValidationError("Base URL is required")
            
            if not connection.base_url.startswith(('http://', 'https://')):
                raise TeddyCloudValidationError("Base URL must start with http:// or https://")
            
            # Security validation
            if not connection.is_secure_connection and not connection.ignore_ssl_verify:
                self.logger.warning("Using insecure HTTP connection")
            
            # Authentication validation
            if connection.authentication_type == AuthenticationType.BASIC:
                if not connection.username or not connection.password:
                    raise TeddyCloudValidationError("Basic auth requires username and password")
            
            elif connection.authentication_type == AuthenticationType.CERTIFICATE:
                if not connection.cert_file:
                    raise TeddyCloudValidationError("Certificate auth requires cert file")
            
            # Timeout validation
            if connection.connection_timeout <= 0 or connection.read_timeout <= 0:
                raise TeddyCloudValidationError("Timeouts must be positive")
            
            if connection.max_retries < 0:
                raise TeddyCloudValidationError("Max retries cannot be negative")
            
            return True
            
        except TeddyCloudValidationError:
            raise
        except Exception as e:
            raise TeddyCloudValidationError(f"Connection validation failed: {e}")


class UploadPathResolutionService:
    """Domain service for resolving upload paths with template support."""
    
    def __init__(self, template_processor: TemplateProcessor, 
                 logger: Optional[logging.Logger] = None):
        """Initialize service with template processor and optional logger."""
        self.template_processor = template_processor
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def resolve_upload_path(self, file_path: str, template: Optional[str], 
                          metadata: Dict[str, Any]) -> Optional[str]:
        """Resolve upload path using template and metadata."""
        from pathlib import Path
        path_obj = Path(file_path)
        
        if not template:
            # Use filename with extension as default path
            return path_obj.name
        
        try:
            # Apply template with metadata
            self.logger.debug(f"Resolving path: template='{template}', metadata={metadata}")
            resolved_path = self.template_processor.apply_template(template, metadata)
            
            # If template resolution failed (returned None), use filename as fallback
            if resolved_path is None:
                self.logger.warning(f"Template '{template}' could not be resolved for {file_path}, using filename")
                return path_obj.name
            
            # Normalize path and append filename
            # Template resolves directory structure, we need to add the filename
            resolved_dir = resolved_path.replace('\\', '/').strip('/')
            filename = path_obj.name
            full_path = f"{resolved_dir}/{filename}" if resolved_dir else filename
            
            self.logger.debug(f"Resolved upload path: {file_path} -> {full_path}")
            return full_path
            
        except Exception as e:
            self.logger.error(f"Failed to resolve upload path for {file_path}: {e}")
            # Fallback to filename with extension
            return path_obj.name
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for TeddyCloud compatibility."""
        # Remove leading/trailing slashes
        path = path.strip('/')
        
        # Replace invalid characters
        invalid_chars = '<>:"|?*'
        for char in invalid_chars:
            path = path.replace(char, '_')
        
        # Remove double slashes
        while '//' in path:
            path = path.replace('//', '/')
        
        return path


class DirectoryManagementService:
    """Domain service for managing directory operations."""
    
    def __init__(self, repository: TeddyCloudRepository,
                 logger: Optional[logging.Logger] = None):
        """Initialize service with repository and optional logger."""
        self.repository = repository
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def ensure_directory_path_exists(self, path: str, 
                                   special: Optional[SpecialFolder] = None) -> bool:
        """Ensure all directories in path exist, creating them if needed."""
        if not path:
            return True
        
        # Split path into components and create recursively
        path_components = path.split('/')
        current_path = ""
        
        for component in path_components:
            if current_path:
                current_path += f"/{component}"
            else:
                current_path = component
            
            if not current_path:  # Skip empty components
                continue
            
            # Always create directory - TeddyCloud returns success if it already exists
            result = self.repository.create_directory(current_path, special=special)
            
            if result.success or result.already_existed:
                self.logger.debug(f"Created/confirmed directory: {current_path}")
            else:
                self.logger.error(f"Failed to create directory {current_path}: {result.error}")
                return False
        
        return True


class TagDisplayService:
    """Domain service for formatting tag information for display."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize service with optional logger."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def format_tags_for_display(self, tags: List[TeddyCloudTag]) -> str:
        """Format tags for console display."""
        if not tags:
            return "No tags found."
        
        output_lines = ["\nAvailable Tags from TeddyCloud:", "-" * 60]
        
        # Sort tags by type and UID for consistent display
        sorted_tags = sorted(tags, key=lambda x: (x.tag_type, x.uid))
        
        for tag in sorted_tags:
            # Basic tag info
            valid_symbol = "✓" if tag.valid.value == "valid" else "✗"
            output_lines.append(f"UID: {tag.uid} ({tag.tag_type}) - Valid: {valid_symbol}")
            
            # Series and episode info
            if tag.series:
                output_lines.append(f"Series: {tag.series}")
            if tag.episode:
                output_lines.append(f"Episode: {tag.episode}")
            if tag.source:
                output_lines.append(f"Source: {tag.source}")
            
            # Track information
            if tag.tracks:
                output_lines.append("Tracks:")
                for i, track in enumerate(tag.tracks, 1):
                    output_lines.append(f"  {i}. {track}")
            
            # Duration information
            if tag.total_duration_seconds and tag.track_count > 0:
                minutes = tag.total_duration_seconds // 60
                seconds = tag.total_duration_seconds % 60
                output_lines.append(f"Duration: {minutes}:{seconds:02d} ({tag.track_count} tracks)")
            
            output_lines.append("-" * 60)
        
        return "\n".join(output_lines)
    
    def get_tag_summary(self, tags: List[TeddyCloudTag]) -> Dict[str, Any]:
        """Get summary statistics for tags."""
        if not tags:
            return {"total": 0, "valid": 0, "invalid": 0, "types": {}}
        
        total = len(tags)
        valid = sum(1 for tag in tags if tag.valid.value == "valid")
        invalid = total - valid
        
        # Count by type
        type_counts = {}
        for tag in tags:
            type_counts[tag.tag_type] = type_counts.get(tag.tag_type, 0) + 1
        
        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "types": type_counts
        }


class UploadValidationService:
    """Domain service for validating upload operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize service with optional logger."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def validate_upload_request(self, file_path: str, destination_path: Optional[str],
                              special: Optional[SpecialFolder]) -> bool:
        """Validate upload request according to business rules."""
        # File path validation
        if not file_path:
            raise TeddyCloudValidationError("File path is required")
        
        # Check if it's a supported file type
        supported_extensions = {'.taf', '.jpg', '.jpeg', '.png', '.webp', '.json'}
        from pathlib import Path
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in supported_extensions:
            raise TeddyCloudValidationError(f"Unsupported file type: {file_ext}")
        
        # Special folder validation
        if special and special not in SpecialFolder:
            raise TeddyCloudValidationError(f"Invalid special folder: {special}")
        
        # Destination path validation
        if destination_path:
            # Check for invalid characters
            invalid_chars = '<>:"|?*'
            if any(char in destination_path for char in invalid_chars):
                raise TeddyCloudValidationError(f"Destination path contains invalid characters")
        
        return True
    
    def validate_upload_result(self, result: UploadResult) -> bool:
        """Validate upload result for business logic compliance."""
        if not result.success and not result.error:
            self.logger.warning("Upload marked as failed but no error provided")
        
        if result.success and result.error:
            self.logger.warning("Upload marked as successful but error is present")
        
        return result.success and not result.error