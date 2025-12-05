#!/usr/bin/python3
"""
Adapter implementations for file system and template processing.
Provides infrastructure implementations for domain interfaces.
"""
import os
import re
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from ..domain import FileSystemService, TemplateProcessor, MetadataExtractor


class StandardFileSystemService(FileSystemService):
    """Standard file system service implementation."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize file system service."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        try:
            return Path(path).exists() and Path(path).is_file()
        except Exception as e:
            self.logger.error(f"Error checking file existence: {e}")
            return False
    
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            return Path(path).stat().st_size
        except Exception as e:
            self.logger.error(f"Error getting file size: {e}")
            return 0
    
    def read_file_content(self, path: str) -> bytes:
        """Read file content as bytes."""
        try:
            with open(path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file content: {e}")
            raise IOError(f"Failed to read file: {e}")
    
    def ensure_directory_exists(self, path: str) -> None:
        """Ensure directory exists, create if needed."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Error creating directory: {e}")
            raise IOError(f"Failed to create directory: {e}")


class StandardTemplateProcessor(TemplateProcessor):
    """Standard template processor implementation using the existing utility."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize template processor."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def apply_template(self, template: str, metadata: Dict[str, Any]) -> str:
        """Apply metadata to path template."""
        try:
            # Use existing utility function
            from ...utils import apply_template_to_path
            return apply_template_to_path(template, metadata)
            
        except Exception as e:
            self.logger.error(f"Template processing failed: {e}")
            # Return template as-is if processing fails
            return template
    
    def validate_template(self, template: str) -> bool:
        """Validate template syntax."""
        try:
            # Check for balanced braces
            open_braces = template.count('{')
            close_braces = template.count('}')
            
            if open_braces != close_braces:
                return False
            
            # Check for valid template variable pattern
            # Look for {variable_name} patterns
            pattern = r'\{[a-zA-Z_][a-zA-Z0-9_]*\}'
            variables = re.findall(r'\{[^}]+\}', template)
            
            for var in variables:
                if not re.match(r'^\{[a-zA-Z_][a-zA-Z0-9_]*\}$', var):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Template validation failed: {e}")
            return False


class MediaTagMetadataExtractor(MetadataExtractor):
    """Metadata extractor using existing media tag functionality."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize metadata extractor."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        
        # Supported file extensions
        self.supported_extensions = {
            '.mp3', '.flac', '.ogg', '.m4a', '.wav', '.opus',
            '.taf'  # TAF files might have embedded metadata
        }
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        try:
            # Use existing media tag service
            from ...media.tags import get_media_tag_service
            service = get_media_tag_service()
            
            tags = service.get_file_tags(file_path)
            
            if tags:
                # Convert MediaTag to dictionary
                return {
                    'title': tags.title or '',
                    'artist': tags.artist or '',
                    'album': tags.album or '', 
                    'albumartist': tags.album_artist or '',
                    'date': tags.date or '',
                    'genre': tags.genre or '',
                    'track': tags.track_number or '',
                    'disc': tags.disc_number or '',
                    'duration': tags.duration_seconds or 0
                }
            else:
                # Return basic file information
                file_path_obj = Path(file_path)
                return {
                    'filename': file_path_obj.stem,
                    'extension': file_path_obj.suffix,
                    'directory': file_path_obj.parent.name
                }
                
        except Exception as e:
            self.logger.error(f"Metadata extraction failed for {file_path}: {e}")
            # Return minimal metadata on failure
            file_path_obj = Path(file_path)
            return {
                'filename': file_path_obj.stem,
                'extension': file_path_obj.suffix,
                'directory': file_path_obj.parent.name
            }
    
    def supports_file_type(self, file_path: str) -> bool:
        """Check if file type is supported."""
        try:
            extension = Path(file_path).suffix.lower()
            return extension in self.supported_extensions
        except Exception:
            return False


class SimpleMetadataExtractor(MetadataExtractor):
    """Simple metadata extractor that only uses file path information."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize simple metadata extractor."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic metadata from file path."""
        try:
            file_path_obj = Path(file_path)
            
            return {
                'filename': file_path_obj.stem,
                'extension': file_path_obj.suffix,
                'directory': file_path_obj.parent.name,
                'full_directory': str(file_path_obj.parent),
                'basename': file_path_obj.name
            }
            
        except Exception as e:
            self.logger.error(f"Simple metadata extraction failed for {file_path}: {e}")
            return {
                'filename': 'unknown',
                'extension': '',
                'directory': '',
                'full_directory': '',
                'basename': 'unknown'
            }
    
    def supports_file_type(self, file_path: str) -> bool:
        """All file types are supported for basic metadata extraction."""
        return True