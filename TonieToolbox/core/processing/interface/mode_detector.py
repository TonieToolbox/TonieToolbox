#!/usr/bin/env python3
"""
Enhanced mode detection for processing operations.

This module provides sophisticated mode detection capabilities that analyze
input specifications and context to determine the most appropriate processing mode.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
import glob

from ..domain import ProcessingMode, InputSpecification
from ..domain.value_objects.processing_mode import (
    SINGLE_FILE_MODE, FILES_TO_TAF_MODE, RECURSIVE_MODE, ANALYSIS_MODE, ProcessingModeType
)


class EnhancedModeDetector:
    """
    Enhanced mode detector for processing operations.
    
    Provides intelligent detection of processing modes based on input specifications,
    file patterns, directory structures, and processing context.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize enhanced mode detector."""
        from ...utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
        
        # Supported audio file extensions
        self.audio_extensions = {
            '.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', 
            '.opus', '.wma', '.taf', '.mp4', '.m4b'
        }
        
        # Special file types
        self.list_file_extensions = {'.lst', '.txt', '.m3u', '.pls'}
        self.playlist_extensions = {'.m3u', '.m3u8', '.pls', '.xspf'}
    
    def detect_mode(self, input_spec: Union[str, Path, InputSpecification],
                   output_spec: Optional[Union[str, Path]] = None,
                   context: Optional[Dict[str, Any]] = None) -> ProcessingMode:
        """
        Detect processing mode from input and output specifications.
        
        Args:
            input_spec: Input specification (path, pattern, or InputSpecification object)
            output_spec: Optional output specification
            context: Optional context information for mode detection
            
        Returns:
            Detected ProcessingMode
        """
        try:
            # Normalize inputs
            if isinstance(input_spec, InputSpecification):
                input_paths = input_spec.resolve_files()
                input_str = str(input_paths[0]) if input_paths else input_spec.input_path
            else:
                input_str = str(input_spec)
                input_paths = [Path(input_str)]
            
            output_str = str(output_spec) if output_spec else ""
            context = context or {}
            
            self.logger.debug(f"Detecting mode for input: {input_str}, output: {output_str}")
            
            # Check for explicit mode override in context
            if 'mode' in context:
                try:
                    return ProcessingMode[context['mode'].upper()]
                except (KeyError, AttributeError):
                    self.logger.warning(f"Invalid explicit mode '{context.get('mode')}', using auto-detection")
            
            # Analysis-only mode
            if self._is_analysis_mode(context):
                return ProcessingMode.ANALYZE_ONLY
            
            # Pattern-based detection
            if self._has_wildcards(input_str):
                return self._detect_wildcard_mode(input_str, output_str, context)
            
            # Single path detection
            input_path = Path(input_str)
            
            if not input_path.exists():
                # Non-existent path - assume pattern or single file
                return SINGLE_FILE_MODE
            
            if input_path.is_file():
                return self._detect_file_mode(input_path, output_str, context)
            
            if input_path.is_dir():
                return self._detect_directory_mode(input_path, output_str, context)
            
            # Default fallback
            return SINGLE_FILE_MODE
            
        except Exception as e:
            self.logger.error(f"Mode detection failed: {str(e)}")
            return SINGLE_FILE_MODE
    
    def analyze_input_structure(self, input_spec: Union[str, Path, InputSpecification]) -> Dict[str, Any]:
        """
        Analyze input structure and provide detailed information.
        
        Args:
            input_spec: Input specification to analyze
            
        Returns:
            Dictionary containing structure analysis
        """
        analysis = {
            'input_type': 'unknown',
            'file_count': 0,
            'total_size': 0,
            'formats': set(),
            'directory_depth': 0,
            'has_subdirs': False,
            'estimated_duration': 0.0,
            'special_files': [],
            'recommendations': []
        }
        
        try:
            # Normalize input
            if isinstance(input_spec, InputSpecification):
                paths = input_spec.resolve_files()
            else:
                input_str = str(input_spec)
                if self._has_wildcards(input_str):
                    paths = [Path(p) for p in glob.glob(input_str, recursive=True)]
                else:
                    paths = [Path(input_str)]
            
            if not paths:
                return analysis
            
            # Analyze each path
            for path in paths:
                if path.exists():
                    if path.is_file():
                        self._analyze_file(path, analysis)
                    elif path.is_dir():
                        self._analyze_directory(path, analysis)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
        except Exception as e:
            self.logger.error(f"Input structure analysis failed: {str(e)}")
        
        return analysis
    
    def suggest_output_structure(self, input_analysis: Dict[str, Any],
                               processing_mode: ProcessingMode) -> Dict[str, Any]:
        """
        Suggest optimal output structure based on input analysis and processing mode.
        
        Args:
            input_analysis: Result from analyze_input_structure
            processing_mode: Detected or specified processing mode
            
        Returns:
            Dictionary containing output structure suggestions
        """
        suggestions = {
            'recommended_format': 'taf',
            'preserve_structure': False,
            'single_output': False,
            'output_naming': 'preserve',
            'quality_recommendation': 'MEDIUM',
            'special_considerations': []
        }
        
        try:
            file_count = input_analysis.get('file_count', 0)
            has_subdirs = input_analysis.get('has_subdirs', False)
            
            # Mode-specific suggestions
            if processing_mode == SINGLE_FILE_MODE:
                suggestions.update({
                    'single_output': True,
                    'output_naming': 'preserve',
                    'preserve_structure': False
                })
            
            elif processing_mode == ProcessingMode.FILES_TO_TAF:
                suggestions.update({
                    'single_output': True,
                    'output_naming': 'combined',
                    'preserve_structure': False
                })
                
                if file_count > 20:
                    suggestions['special_considerations'].append(
                        "Large number of files - consider chapter marks"
                    )
            
            elif processing_mode == RECURSIVE_MODE:
                suggestions.update({
                    'preserve_structure': has_subdirs,
                    'output_naming': 'preserve',
                    'single_output': False
                })
                
                if has_subdirs:
                    suggestions['special_considerations'].append(
                        "Directory structure will be preserved in output"
                    )
            
            # Quality recommendations based on file count and size
            total_size = input_analysis.get('total_size', 0)
            
            if total_size > 1_000_000_000:  # > 1GB
                suggestions['quality_recommendation'] = 'MEDIUM'
                suggestions['special_considerations'].append(
                    "Large files detected - medium quality recommended for reasonable file sizes"
                )
            elif file_count > 50:
                suggestions['quality_recommendation'] = 'MEDIUM'
            else:
                suggestions['quality_recommendation'] = 'HIGH'
            
            # Format-specific considerations
            formats = input_analysis.get('formats', set())
            if 'flac' in formats:
                suggestions['special_considerations'].append(
                    "FLAC files detected - consider LOSSLESS quality to preserve audio quality"
                )
            
        except Exception as e:
            self.logger.error(f"Output structure suggestion failed: {str(e)}")
        
        return suggestions
    
    def validate_mode_compatibility(self, processing_mode: ProcessingMode,
                                  input_analysis: Dict[str, Any]) -> List[str]:
        """
        Validate that the processing mode is compatible with the input structure.
        
        Args:
            processing_mode: Processing mode to validate
            input_analysis: Input structure analysis
            
        Returns:
            List of warning messages (empty if fully compatible)
        """
        warnings = []
        
        try:
            file_count = input_analysis.get('file_count', 0)
            has_subdirs = input_analysis.get('has_subdirs', False)
            input_type = input_analysis.get('input_type', 'unknown')
            
            if processing_mode == SINGLE_FILE_MODE:
                if file_count > 1:
                    warnings.append(
                        f"Single file mode selected but {file_count} files detected. "
                        "Only the first file will be processed."
                    )
            
            elif processing_mode == ProcessingMode.FILES_TO_TAF:
                if file_count == 0:
                    warnings.append("No files found for combination into TAF")
                elif file_count > 100:
                    warnings.append(
                        f"Large number of files ({file_count}) for combination. "
                        "Consider using recursive mode with preserved structure."
                    )
            
            elif processing_mode == RECURSIVE_MODE:
                if input_type != 'directory':
                    warnings.append(
                        "Recursive mode works best with directory inputs"
                    )
                if not has_subdirs:
                    warnings.append(
                        "Recursive mode selected but no subdirectories detected. "
                        "Consider using files-to-TAF mode instead."
                    )
            
            elif processing_mode == ProcessingMode.ANALYZE_ONLY:
                if file_count > 1:
                    warnings.append(
                        f"Analysis mode with {file_count} files. "
                        "Only the first file will be analyzed."
                    )
        
        except Exception as e:
            self.logger.error(f"Mode compatibility validation failed: {str(e)}")
            warnings.append("Could not validate mode compatibility")
        
        return warnings
    
    def _is_analysis_mode(self, context: Dict[str, Any]) -> bool:
        """Check if this should be analysis-only mode."""
        return (context.get('analyze_only', False) or 
                context.get('analysis', False) or
                context.get('info', False))
    
    def _has_wildcards(self, path_str: str) -> bool:
        """Check if path contains wildcard characters."""
        return '*' in path_str or '?' in path_str or '[' in path_str
    
    def _detect_wildcard_mode(self, input_str: str, output_str: str, 
                            context: Dict[str, Any]) -> ProcessingMode:
        """Detect mode for wildcard patterns."""
        # Expand pattern to see what we get
        try:
            matching_files = glob.glob(input_str, recursive=context.get('recursive', False))
            file_count = len(matching_files)
            
            if file_count == 0:
                return SINGLE_FILE_MODE
            elif file_count == 1:
                return SINGLE_FILE_MODE
            else:
                # Multiple files - determine if combining or processing separately
                if output_str and not Path(output_str).is_dir():
                    # Single output file specified - combine files
                    return FILES_TO_TAF_MODE
                else:
                    # Multiple outputs or directory output - process separately
                    return RECURSIVE_MODE if context.get('recursive', False) else FILES_TO_TAF_MODE
                    
        except Exception:
            return SINGLE_FILE_MODE
    
    def _detect_file_mode(self, input_path: Path, output_str: str, 
                         context: Dict[str, Any]) -> ProcessingMode:
        """Detect mode for single file input."""
        
        # Check for special file types
        if input_path.suffix.lower() in self.list_file_extensions:
            return ProcessingMode.LIST_FILE
        
        if input_path.suffix.lower() in self.playlist_extensions:
            return ProcessingMode.FILES_TO_TAF
        
        # Check output to determine conversion direction
        if output_str:
            output_path = Path(output_str)
            
            if input_path.suffix.lower() == '.taf' and output_path.suffix.lower() != '.taf':
                return ProcessingMode.FROM_TAF
            elif input_path.suffix.lower() != '.taf' and output_path.suffix.lower() == '.taf':
                return ProcessingMode.TO_TAF
        
        return SINGLE_FILE_MODE
    
    def _detect_directory_mode(self, input_path: Path, output_str: str,
                             context: Dict[str, Any]) -> ProcessingMode:
        """Detect mode for directory input."""
        
        # Check if recursive processing is requested
        if context.get('recursive', False):
            return RECURSIVE_MODE
        
        # Check output specification
        if output_str:
            output_path = Path(output_str)
            
            if output_path.suffix.lower() == '.taf':
                # Single TAF output - combine all files
                return FILES_TO_TAF_MODE
            elif output_path.is_dir() or not output_path.suffix:
                # Directory output - process files separately
                return RECURSIVE_MODE
        
        # Default for directory - combine to single TAF
        return FILES_TO_TAF_MODE
    
    def _analyze_file(self, file_path: Path, analysis: Dict[str, Any]):
        """Analyze individual file and update analysis dictionary."""
        try:
            if file_path.suffix.lower() in self.audio_extensions:
                analysis['file_count'] += 1
                analysis['total_size'] += file_path.stat().st_size
                
                # Add format
                format_name = file_path.suffix.lower()[1:]  # Remove dot
                analysis['formats'].add(format_name)
                
                # Check for special files
                if file_path.suffix.lower() in self.list_file_extensions:
                    analysis['special_files'].append(f"List file: {file_path}")
                elif file_path.suffix.lower() in self.playlist_extensions:
                    analysis['special_files'].append(f"Playlist: {file_path}")
            
            analysis['input_type'] = 'file' if analysis['file_count'] == 1 else 'files'
            
        except Exception as e:
            self.logger.debug(f"File analysis failed for {file_path}: {str(e)}")
    
    def _analyze_directory(self, dir_path: Path, analysis: Dict[str, Any]):
        """Analyze directory and update analysis dictionary."""
        try:
            analysis['input_type'] = 'directory'
            
            # Calculate directory depth and check for subdirectories
            max_depth = 0
            
            for item in dir_path.rglob('*'):
                if item.is_file() and item.suffix.lower() in self.audio_extensions:
                    analysis['file_count'] += 1
                    analysis['total_size'] += item.stat().st_size
                    
                    # Add format
                    format_name = item.suffix.lower()[1:]  # Remove dot
                    analysis['formats'].add(format_name)
                    
                    # Calculate depth
                    relative_path = item.relative_to(dir_path)
                    depth = len(relative_path.parts) - 1
                    max_depth = max(max_depth, depth)
                
                elif item.is_dir():
                    analysis['has_subdirs'] = True
            
            analysis['directory_depth'] = max_depth
            
        except Exception as e:
            self.logger.debug(f"Directory analysis failed for {dir_path}: {str(e)}")
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate processing recommendations based on analysis."""
        recommendations = []
        
        file_count = analysis.get('file_count', 0)
        total_size = analysis.get('total_size', 0)
        has_subdirs = analysis.get('has_subdirs', False)
        formats = analysis.get('formats', set())
        
        if file_count == 0:
            recommendations.append("No audio files found in input")
        elif file_count == 1:
            recommendations.append("Single file detected - use single file processing mode")
        elif file_count <= 10:
            recommendations.append("Small number of files - consider combining into single TAF")
        elif file_count <= 50:
            recommendations.append("Medium number of files - evaluate if combination or separate processing is preferred")
        else:
            recommendations.append("Large number of files - consider recursive processing with structure preservation")
        
        if has_subdirs:
            recommendations.append("Subdirectories detected - recursive mode will preserve directory structure")
        
        if total_size > 2_000_000_000:  # > 2GB
            recommendations.append("Large total file size - consider quality settings to manage output size")
        
        if 'flac' in formats:
            recommendations.append("Lossless FLAC files detected - consider using LOSSLESS quality setting")
        
        mixed_formats = len(formats) > 2
        if mixed_formats:
            recommendations.append(f"Multiple audio formats detected: {', '.join(sorted(formats))}")
        
        return recommendations