#!/usr/bin/env python3
"""
Input specification value object.

This module defines the InputSpecification value object that describes
what inputs are expected for a processing operation.
"""

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Set, Union
import os
import glob

from ..exceptions import ValidationError


class InputType(Enum):
    """Type of input for processing operations."""
    
    FILE = auto()           # Single file
    DIRECTORY = auto()      # Directory path
    PATTERN = auto()        # File pattern (e.g., *.mp3)
    FILE_LIST = auto()      # List of files


class ContentType(Enum):
    """Expected content type of input."""
    
    AUDIO = auto()          # Audio files (mp3, ogg, wav, etc.)
    TAF = auto()            # TAF files
    PLAYLIST = auto()       # Playlist files (.lst)
    ANY = auto()            # Any file type


@dataclass(frozen=True)
class InputSpecification:
    """Value object describing input requirements for processing."""
    
    input_path: str
    input_type: InputType
    content_type: ContentType
    recursive: bool = False
    required_extensions: Optional[Set[str]] = None
    min_files: int = 1
    max_files: Optional[int] = None
    
    def __post_init__(self):
        """Validate input specification."""
        if self.min_files < 0:
            raise ValidationError("min_files", "Must be non-negative", self.min_files)
        
        if self.max_files is not None and self.max_files < self.min_files:
            raise ValidationError("max_files", "Must be >= min_files", self.max_files)
        
        if self.input_type == InputType.DIRECTORY and not self.recursive:
            # For directories, we typically need recursive processing
            object.__setattr__(self, 'recursive', True)
    
    @classmethod
    def from_path(cls, input_path: str, content_type: ContentType = ContentType.AUDIO, 
                  recursive: bool = False) -> 'InputSpecification':
        """Create input specification from path analysis."""
        # Determine input type from path
        if os.path.isfile(input_path):
            input_type = InputType.FILE
        elif os.path.isdir(input_path):
            input_type = InputType.DIRECTORY
        elif '*' in input_path or '?' in input_path:
            input_type = InputType.PATTERN
        else:
            # Assume it's a file path that might not exist yet
            input_type = InputType.FILE
        
        return cls(
            input_path=input_path,
            input_type=input_type,
            content_type=content_type,
            recursive=recursive
        )
    
    @classmethod
    def for_single_file(cls, file_path: str, content_type: ContentType = ContentType.AUDIO) -> 'InputSpecification':
        """Create specification for single file processing."""
        return cls(
            input_path=file_path,
            input_type=InputType.FILE,
            content_type=content_type,
            recursive=False,
            min_files=1,
            max_files=1
        )
    
    @classmethod
    def for_multiple_files(cls, pattern: str, content_type: ContentType = ContentType.AUDIO,
                          min_files: int = 1, max_files: Optional[int] = None) -> 'InputSpecification':
        """Create specification for multiple file processing."""
        return cls(
            input_path=pattern,
            input_type=InputType.PATTERN,
            content_type=content_type,
            recursive=False,
            min_files=min_files,
            max_files=max_files
        )
    
    @classmethod
    def for_recursive_directory(cls, directory: str, content_type: ContentType = ContentType.AUDIO) -> 'InputSpecification':
        """Create specification for recursive directory processing."""
        return cls(
            input_path=directory,
            input_type=InputType.DIRECTORY,
            content_type=content_type,
            recursive=True,
            min_files=1
        )
    
    def resolve_files(self) -> List[Path]:
        """Resolve input specification to actual file paths."""
        files = []
        
        if self.input_type == InputType.FILE:
            if os.path.isfile(self.input_path):
                files.append(Path(self.input_path))
        
        elif self.input_type == InputType.DIRECTORY:
            if os.path.isdir(self.input_path):
                files.extend(self._find_files_in_directory())
        
        elif self.input_type == InputType.PATTERN:
            files.extend(Path(p) for p in glob.glob(self.input_path, recursive=self.recursive))
        
        # Filter by extensions if specified
        if self.required_extensions:
            files = [f for f in files if f.suffix.lower() in self.required_extensions]
        
        return sorted(files)
    
    def _find_files_in_directory(self) -> List[Path]:
        """Find files in directory based on content type."""
        directory = Path(self.input_path)
        files = []
        
        if self.content_type == ContentType.AUDIO:
            audio_extensions = {'.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.opus'}
            pattern = "**/*" if self.recursive else "*"
            for ext in audio_extensions:
                files.extend(directory.glob(f"{pattern}{ext}"))
        
        elif self.content_type == ContentType.TAF:
            pattern = "**/*.taf" if self.recursive else "*.taf"
            files.extend(directory.glob(pattern))
        
        elif self.content_type == ContentType.PLAYLIST:
            pattern = "**/*.lst" if self.recursive else "*.lst"
            files.extend(directory.glob(pattern))
        
        elif self.content_type == ContentType.ANY:
            pattern = "**/*" if self.recursive else "*"
            files.extend(f for f in directory.glob(pattern) if f.is_file())
        
        return files
    
    def validate_requirements(self) -> List[ValidationError]:
        """Validate that input meets requirements."""
        errors = []
        
        try:
            files = self.resolve_files()
            file_count = len(files)
            
            if file_count < self.min_files:
                errors.append(ValidationError(
                    "file_count", 
                    f"Found {file_count} files, requires at least {self.min_files}",
                    file_count
                ))
            
            if self.max_files is not None and file_count > self.max_files:
                errors.append(ValidationError(
                    "file_count",
                    f"Found {file_count} files, maximum allowed is {self.max_files}",
                    file_count
                ))
            
            # Check if input path exists
            if not os.path.exists(self.input_path):
                # For patterns, check if parent directory exists
                if self.input_type == InputType.PATTERN:
                    parent_dir = os.path.dirname(self.input_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        errors.append(ValidationError(
                            "input_path",
                            f"Parent directory does not exist: {parent_dir}",
                            parent_dir
                        ))
                else:
                    errors.append(ValidationError(
                        "input_path",
                        f"Input path does not exist: {self.input_path}",
                        self.input_path
                    ))
        
        except Exception as e:
            errors.append(ValidationError(
                "input_path",
                f"Error accessing input path: {str(e)}",
                self.input_path
            ))
        
        return errors
    
    @property
    def description(self) -> str:
        """Get human-readable description of input specification."""
        type_desc = {
            InputType.FILE: "single file",
            InputType.DIRECTORY: "directory",
            InputType.PATTERN: "file pattern",
            InputType.FILE_LIST: "file list"
        }
        
        content_desc = {
            ContentType.AUDIO: "audio files",
            ContentType.TAF: "TAF files", 
            ContentType.PLAYLIST: "playlist files",
            ContentType.ANY: "any files"
        }
        
        desc = f"{type_desc.get(self.input_type, 'unknown')} containing {content_desc.get(self.content_type, 'unknown')}"
        
        if self.recursive:
            desc += " (recursive)"
        
        if self.min_files > 1 or self.max_files is not None:
            if self.max_files:
                desc += f" ({self.min_files}-{self.max_files} files)"
            else:
                desc += f" (min {self.min_files} files)"
        
        return desc