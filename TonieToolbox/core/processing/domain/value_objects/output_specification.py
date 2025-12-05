#!/usr/bin/env python3
"""
Output specification value object.

This module defines the OutputSpecification value object that describes
expected outputs for a processing operation.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, Any, List
import os

from ..exceptions import ValidationError


class OutputFormat(Enum):
    """Output format types."""
    
    TAF = auto()            # Tonie Audio Format
    MP3_SINGLE = auto()     # Single MP3 file
    MP3_SEPARATE = auto()   # Separate MP3 files
    INFO = auto()           # Information display (no file output)
    

class OutputMode(Enum):
    """Output generation modes."""
    
    SINGLE_FILE = auto()    # Generate single output file
    MULTIPLE_FILES = auto() # Generate multiple output files
    IN_PLACE = auto()       # Modify files in place
    CONSOLE_ONLY = auto()   # Output to console only


@dataclass(frozen=True)
class OutputSpecification:
    """Value object describing output requirements for processing."""
    
    output_format: OutputFormat
    output_mode: OutputMode
    output_path: Optional[str] = None
    filename_template: Optional[str] = None
    overwrite_existing: bool = False
    create_directories: bool = True
    preserve_structure: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate output specification."""
        # Validate that file output modes have output paths
        if (self.output_mode != OutputMode.CONSOLE_ONLY and 
            self.output_format != OutputFormat.INFO and 
            not self.output_path):
            raise ValidationError(
                "output_path", 
                "Output path required for file output modes"
            )
        
        # Validate filename template for multiple files
        if (self.output_mode == OutputMode.MULTIPLE_FILES and 
            not self.filename_template):
            object.__setattr__(self, 'filename_template', '{name}.{ext}')
    
    @classmethod
    def for_single_taf(cls, output_path: str, overwrite: bool = False) -> 'OutputSpecification':
        """Create specification for single TAF file output."""
        return cls(
            output_format=OutputFormat.TAF,
            output_mode=OutputMode.SINGLE_FILE,
            output_path=output_path,
            overwrite_existing=overwrite
        )
    
    @classmethod
    def for_multiple_taf(cls, output_dir: str, filename_template: str = '{name}.taf',
                        preserve_structure: bool = False, overwrite: bool = False) -> 'OutputSpecification':
        """Create specification for multiple TAF file output."""
        return cls(
            output_format=OutputFormat.TAF,
            output_mode=OutputMode.MULTIPLE_FILES,
            output_path=output_dir,
            filename_template=filename_template,
            preserve_structure=preserve_structure,
            overwrite_existing=overwrite
        )
    
    @classmethod
    def for_mp3_conversion(cls, output_path: str, separate_files: bool = False,
                          overwrite: bool = False) -> 'OutputSpecification':
        """Create specification for MP3 conversion output."""
        output_format = OutputFormat.MP3_SEPARATE if separate_files else OutputFormat.MP3_SINGLE
        output_mode = OutputMode.MULTIPLE_FILES if separate_files else OutputMode.SINGLE_FILE
        
        return cls(
            output_format=output_format,
            output_mode=output_mode,
            output_path=output_path,
            filename_template='{name}.mp3' if separate_files else None,
            overwrite_existing=overwrite
        )
    
    @classmethod
    def for_info_display(cls) -> 'OutputSpecification':
        """Create specification for information display (no file output)."""
        return cls(
            output_format=OutputFormat.INFO,
            output_mode=OutputMode.CONSOLE_ONLY
        )
    
    def resolve_output_path(self, input_name: str, index: Optional[int] = None) -> Path:
        """Resolve output path for a specific input."""
        if self.output_mode == OutputMode.CONSOLE_ONLY:
            raise ValueError("Cannot resolve file path for console-only output")
        
        if not self.output_path:
            raise ValueError("Output path not specified")
        
        base_path = Path(self.output_path)
        
        if self.output_mode == OutputMode.SINGLE_FILE:
            return base_path
        
        # For multiple files, use filename template
        template = self.filename_template or '{name}.{ext}'
        
        # Extract name without extension
        input_path = Path(input_name)
        name_without_ext = input_path.stem
        
        # Get appropriate extension
        ext = self._get_output_extension()
        
        # Format filename
        filename = template.format(
            name=name_without_ext,
            ext=ext,
            index=index or 0,
            original_name=input_path.name,
            **self.metadata
        )
        
        return base_path / filename
    
    def _get_output_extension(self) -> str:
        """Get file extension for output format."""
        extensions = {
            OutputFormat.TAF: 'taf',
            OutputFormat.MP3_SINGLE: 'mp3',
            OutputFormat.MP3_SEPARATE: 'mp3'
        }
        return extensions.get(self.output_format, 'out')
    
    def validate_output_requirements(self) -> List[ValidationError]:
        """Validate output requirements and constraints."""
        errors = []
        
        if self.output_mode == OutputMode.CONSOLE_ONLY:
            return errors  # No file validation needed
        
        if not self.output_path:
            errors.append(ValidationError(
                "output_path",
                "Output path is required for file output"
            ))
            return errors
        
        output_path = Path(self.output_path)
        
        # For single file mode, check parent directory
        if self.output_mode == OutputMode.SINGLE_FILE:
            parent_dir = output_path.parent
            
            if not parent_dir.exists() and not self.create_directories:
                errors.append(ValidationError(
                    "output_path",
                    f"Parent directory does not exist: {parent_dir}",
                    str(parent_dir)
                ))
            
            if output_path.exists() and not self.overwrite_existing:
                errors.append(ValidationError(
                    "output_path",
                    f"Output file already exists and overwrite is disabled: {output_path}",
                    str(output_path)
                ))
        
        # For multiple file mode, check output directory
        elif self.output_mode == OutputMode.MULTIPLE_FILES:
            if not output_path.exists() and not self.create_directories:
                errors.append(ValidationError(
                    "output_path",
                    f"Output directory does not exist: {output_path}",
                    str(output_path)
                ))
            
            if output_path.exists() and not output_path.is_dir():
                errors.append(ValidationError(
                    "output_path",
                    f"Output path exists but is not a directory: {output_path}",
                    str(output_path)
                ))
        
        return errors
    
    def prepare_output_location(self) -> None:
        """Prepare output location by creating directories if needed."""
        if (self.output_mode == OutputMode.CONSOLE_ONLY or 
            not self.output_path or 
            not self.create_directories):
            return
        
        output_path = Path(self.output_path)
        
        if self.output_mode == OutputMode.SINGLE_FILE:
            # Create parent directory for single file
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        elif self.output_mode == OutputMode.MULTIPLE_FILES:
            # Create output directory for multiple files
            output_path.mkdir(parents=True, exist_ok=True)
    
    def should_skip_existing(self, output_file: Path) -> bool:
        """Check if existing output file should be skipped."""
        if not output_file.exists():
            return False
        
        return not self.overwrite_existing
    
    @property
    def description(self) -> str:
        """Get human-readable description of output specification."""
        format_desc = {
            OutputFormat.TAF: "TAF audio files",
            OutputFormat.MP3_SINGLE: "single MP3 file",
            OutputFormat.MP3_SEPARATE: "separate MP3 files",
            OutputFormat.INFO: "information display"
        }
        
        mode_desc = {
            OutputMode.SINGLE_FILE: "as single file",
            OutputMode.MULTIPLE_FILES: "as multiple files",
            OutputMode.IN_PLACE: "in place",
            OutputMode.CONSOLE_ONLY: "to console only"
        }
        
        desc = f"{format_desc.get(self.output_format, 'unknown format')} {mode_desc.get(self.output_mode, 'unknown mode')}"
        
        if self.output_path:
            desc += f" in {self.output_path}"
        
        if self.preserve_structure:
            desc += " (preserving directory structure)"
        
        return desc