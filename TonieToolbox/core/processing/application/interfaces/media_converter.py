#!/usr/bin/env python3
"""
Media converter interface.

This interface defines operations for media conversion and processing.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass

from ...domain import ProcessingOptions, ProcessingResult


@dataclass
class ConversionProgress:
    """Progress information for media conversion."""
    
    current_file: str
    files_completed: int
    total_files: int
    current_file_progress: float  # 0.0 to 1.0
    overall_progress: float       # 0.0 to 1.0
    estimated_time_remaining: Optional[float] = None  # seconds
    current_operation: str = "Processing"


class MediaConverter(ABC):
    """
    Abstract interface for media conversion operations.
    
    Defines the contract for audio file conversion, combining, splitting, and processing
    operations. Implementations must support TAF format conversion, multi-file combining,
    normalization, and progress tracking for long-running operations.
    
    Example:
        >>> from pathlib import Path
        >>> from TonieToolbox.core.processing.domain import ProcessingOptions
        >>> 
        >>> # Implementations must provide these methods
        >>> class CustomConverter(MediaConverter):
        ...     def convert_to_taf(self, input_path, output_path, options, progress_callback=None):
        ...         # Implementation for TAF conversion
        ...         return True
        ...     
        ...     def convert_from_taf(self, input_path, output_path, output_format, options, progress_callback=None):
        ...         # Implementation for TAF export
        ...         return True
        ...     
        ...     def combine_files_to_taf(self, input_paths, output_path, options, progress_callback=None):
        ...         # Implementation for multi-file combining
        ...         return True
        ...     
        ...     # ... implement other abstract methods
        >>> 
        >>> # Usage of converter implementation
        >>> options = ProcessingOptions(bitrate=96)
        >>> converter = CustomConverter()
        >>> success = converter.convert_to_taf(
        ...     Path('input.mp3'),
        ...     Path('output.taf'),
        ...     options
        ... )
    """
    
    @abstractmethod
    def convert_to_taf(self, input_path: Path, output_path: Path,
                      options: ProcessingOptions,
                      progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """
        Convert audio file to TAF format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output TAF file
            options: Processing options for conversion
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if conversion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def convert_from_taf(self, input_path: Path, output_path: Path,
                        output_format: str,
                        options: ProcessingOptions,
                        progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """
        Convert TAF file to other audio format.
        
        Args:
            input_path: Path to input TAF file
            output_path: Path for output audio file
            output_format: Target format ('mp3', 'wav', etc.)
            options: Processing options for conversion
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if conversion successful, False otherwise
        """
        pass
    
    @abstractmethod
    def combine_files_to_taf(self, input_paths: List[Path], output_path: Path,
                           options: ProcessingOptions,
                           progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """
        Combine multiple audio files into single TAF file.
        
        Args:
            input_paths: List of input audio file paths
            output_path: Path for output TAF file
            options: Processing options for conversion
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if combination successful, False otherwise
        """
        pass
    
    @abstractmethod
    def split_taf_file(self, input_path: Path, output_directory: Path,
                      split_points: List[float],
                      options: ProcessingOptions,
                      progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> List[Path]:
        """
        Split TAF file at specified time points.
        
        Args:
            input_path: Path to input TAF file
            output_directory: Directory for output files
            split_points: List of time points in seconds
            options: Processing options for splitting
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of output file paths
        """
        pass
    
    @abstractmethod
    def normalize_audio(self, input_path: Path, output_path: Path,
                       options: ProcessingOptions,
                       target_level: float = -23.0,
                       progress_callback: Optional[Callable[[ConversionProgress], None]] = None) -> bool:
        """
        Normalize audio levels in file.
        
        Args:
            input_path: Path to input file
            output_path: Path for normalized output
            target_level: Target LUFS level for normalization
            options: Processing options
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if normalization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_audio_info(self, file_path: Path) -> Dict[str, Any]:
        """
        Get audio file information.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Dictionary with audio information (duration, format, bitrate, etc.)
        """
        pass
    
    @abstractmethod
    def validate_audio_file(self, file_path: Path) -> bool:
        """
        Validate audio file integrity.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if file is valid audio, False otherwise
        """
        pass
    
    @abstractmethod
    def get_supported_input_formats(self) -> List[str]:
        """Get list of supported input audio formats."""
        pass
    
    @abstractmethod
    def get_supported_output_formats(self) -> List[str]:
        """Get list of supported output audio formats."""
        pass
    
    @abstractmethod
    def estimate_conversion_time(self, file_path: Path, 
                               target_format: str,
                               options: ProcessingOptions) -> Optional[float]:
        """
        Estimate conversion time for file.
        
        Args:
            file_path: Path to input file
            target_format: Target format for conversion
            options: Processing options
            
        Returns:
            Estimated time in seconds, or None if cannot estimate
        """
        pass