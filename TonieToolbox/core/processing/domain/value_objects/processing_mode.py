#!/usr/bin/env python3
"""
Processing mode value object.

This module defines the ProcessingMode value object that represents
different types of processing operations in the domain.
"""

from enum import Enum, auto
from typing import Dict, Set, Optional
from dataclasses import dataclass


class ProcessingModeType(Enum):
    """Enumeration of available processing modes."""
    
    SINGLE_FILE = auto()          # Process single file or combine multiple files into one TAF
    FILES_TO_TAF = auto()         # Convert individual files to separate TAF files
    RECURSIVE = auto()            # Process folders recursively
    ANALYSIS = auto()             # File analysis operations (info, split, compare, etc.)
    
    def __str__(self):
        return self.name.lower()


@dataclass(frozen=True)
class ProcessingMode:
    """Value object representing a processing mode with its characteristics."""
    
    mode_type: ProcessingModeType
    supports_batch: bool = False
    supports_upload: bool = True
    requires_output_dir: bool = True
    supports_recursive: bool = False
    
    def __post_init__(self):
        """Validate processing mode configuration."""
        # Validate mode-specific constraints
        if self.mode_type == ProcessingModeType.RECURSIVE and not self.supports_batch:
            raise ValueError("Recursive mode must support batch processing")
        
        if self.mode_type == ProcessingModeType.FILES_TO_TAF and not self.supports_batch:
            raise ValueError("Files to TAF mode must support batch processing")
    
    @property
    def name(self) -> str:
        """Get the mode name."""
        return str(self.mode_type)
    
    @property
    def description(self) -> str:
        """Get human-readable description of the mode."""
        descriptions = {
            ProcessingModeType.SINGLE_FILE: "Process single file or combine multiple files into one TAF",
            ProcessingModeType.FILES_TO_TAF: "Convert individual files to separate TAF files", 
            ProcessingModeType.RECURSIVE: "Process folders recursively with automatic structure detection",
            ProcessingModeType.ANALYSIS: "Analyze existing TAF files (info, split, compare, convert, play)"
        }
        return descriptions.get(self.mode_type, "Unknown processing mode")
    
    def can_handle_multiple_files(self) -> bool:
        """Check if mode can handle multiple input files."""
        return self.supports_batch or self.mode_type == ProcessingModeType.SINGLE_FILE
    
    def requires_taf_input(self) -> bool:
        """Check if mode requires TAF files as input."""
        return self.mode_type == ProcessingModeType.ANALYSIS
    
    def produces_multiple_outputs(self) -> bool:
        """Check if mode produces multiple output files."""
        return self.mode_type in (ProcessingModeType.FILES_TO_TAF, ProcessingModeType.RECURSIVE)


# Predefined processing modes
SINGLE_FILE_MODE = ProcessingMode(
    mode_type=ProcessingModeType.SINGLE_FILE,
    supports_batch=False,
    supports_upload=True,
    requires_output_dir=False,
    supports_recursive=False
)

FILES_TO_TAF_MODE = ProcessingMode(
    mode_type=ProcessingModeType.FILES_TO_TAF,
    supports_batch=True,
    supports_upload=True,
    requires_output_dir=True,
    supports_recursive=False
)

RECURSIVE_MODE = ProcessingMode(
    mode_type=ProcessingModeType.RECURSIVE,
    supports_batch=True,
    supports_upload=True,
    requires_output_dir=True,
    supports_recursive=True
)

ANALYSIS_MODE = ProcessingMode(
    mode_type=ProcessingModeType.ANALYSIS,
    supports_batch=False,
    supports_upload=False,
    requires_output_dir=False,
    supports_recursive=False
)


class ProcessingModeRegistry:
    """Registry for all available processing modes."""
    
    _modes: Dict[ProcessingModeType, ProcessingMode] = {
        ProcessingModeType.SINGLE_FILE: SINGLE_FILE_MODE,
        ProcessingModeType.FILES_TO_TAF: FILES_TO_TAF_MODE,
        ProcessingModeType.RECURSIVE: RECURSIVE_MODE,
        ProcessingModeType.ANALYSIS: ANALYSIS_MODE
    }
    
    @classmethod
    def get_mode(cls, mode_type: ProcessingModeType) -> ProcessingMode:
        """Get processing mode by type."""
        if mode_type not in cls._modes:
            raise ValueError(f"Unknown processing mode type: {mode_type}")
        return cls._modes[mode_type]
    
    @classmethod
    def get_all_modes(cls) -> Dict[ProcessingModeType, ProcessingMode]:
        """Get all available processing modes."""
        return cls._modes.copy()
    
    @classmethod
    def get_modes_supporting_upload(cls) -> Set[ProcessingMode]:
        """Get all modes that support upload operations."""
        return {mode for mode in cls._modes.values() if mode.supports_upload}
    
    @classmethod
    def get_modes_supporting_batch(cls) -> Set[ProcessingMode]:
        """Get all modes that support batch processing."""
        return {mode for mode in cls._modes.values() if mode.supports_batch}