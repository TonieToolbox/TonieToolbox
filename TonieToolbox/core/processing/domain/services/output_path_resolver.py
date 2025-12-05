#!/usr/bin/env python3
"""
Output path resolution domain service.

This service contains pure business logic for resolving output paths
with template support. It follows Clean Architecture principles with
no external dependencies.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging

from ..value_objects.input_specification import InputSpecification
from ..exceptions import ValidationError


class OutputPathResolver:
    """
    Domain service for resolving output paths with template support.
    
    This service encapsulates the business rules for:
    - Determining output paths from input specifications
    - Applying directory templates (output_to_template)
    - Applying filename templates (name_template)
    - Handling .taf extension requirements
    - Default path generation strategies
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the output path resolver.
        
        Args:
            logger: Optional logger for debugging
        """
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def resolve_output_path(
        self,
        input_path: Path,
        explicit_output_path: Optional[Path] = None,
        output_directory_template: Optional[str] = None,
        filename_template: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        use_templates: bool = False
    ) -> Path:
        """
        Resolve the complete output path for a processing operation.
        
        This method implements the business rules for output path resolution:
        1. If explicit_output_path is provided, use it directly
        2. If use_templates and templates provided, apply them with metadata
        3. Otherwise, use smart default path generation
        
        Args:
            input_path: The input file or directory path
            explicit_output_path: Explicitly provided output path (highest priority)
            output_directory_template: Template for output directory (e.g., "{albumartist}/{album}")
            filename_template: Template for filename (e.g., "{artist} - {album}")
            metadata: Metadata dictionary for template substitution
            use_templates: Whether to use template-based path generation
            
        Returns:
            Resolved output path with .taf extension
            
        Raises:
            ValidationError: If path resolution fails
        """
        self.logger.debug(f"Resolving output path for input: {input_path}")
        self.logger.debug(f"Templates enabled: {use_templates}, output_dir_template: {output_directory_template}, filename_template: {filename_template}")
        
        # Priority 1: Explicit output path provided
        if explicit_output_path:
            output_path = explicit_output_path
            self.logger.debug(f"Using explicit output path: {output_path}")
        
        # Priority 2: Template-based path generation
        elif use_templates and (output_directory_template or filename_template):
            output_path = self._resolve_template_based_path(
                input_path=input_path,
                output_directory_template=output_directory_template,
                filename_template=filename_template,
                metadata=metadata or {}
            )
            self.logger.debug(f"Generated template-based path: {output_path}")
        
        # Priority 3: Smart default path generation
        else:
            output_path = self._generate_default_path(input_path)
            self.logger.debug(f"Generated default path: {output_path}")
        
        # Ensure .taf extension
        output_path = self._ensure_taf_extension(output_path)
        
        return output_path
    
    def _resolve_template_based_path(
        self,
        input_path: Path,
        output_directory_template: Optional[str],
        filename_template: Optional[str],
        metadata: Dict[str, Any]
    ) -> Path:
        """
        Resolve output path using templates and metadata.
        
        Business rules:
        - output_directory_template: Specifies output directory structure (no .taf)
        - filename_template: Specifies filename (may include .taf)
        - If directory template contains .taf, strip it (user error)
        - Combine directory + filename for final path
        
        Args:
            input_path: Input file/directory path
            output_directory_template: Directory template
            filename_template: Filename template
            metadata: Metadata for substitution
            
        Returns:
            Resolved path (directory + filename)
        """
        from ....utils.filename import apply_template_to_path, guess_output_filename
        
        # Resolve output directory
        if output_directory_template:
            output_dir = self._apply_directory_template(output_directory_template, metadata)
        else:
            # No directory template - use input directory or current directory
            if input_path.is_dir():
                output_dir = input_path
            else:
                output_dir = input_path.parent
        
        # Resolve filename
        if filename_template:
            filename = self._apply_filename_template(filename_template, metadata)
        else:
            # No filename template - use smart guess from input
            base_filename = guess_output_filename(str(input_path))
            filename = f"{base_filename}.taf"
        
        # Combine directory and filename
        return output_dir / filename
    
    def _apply_directory_template(self, template: str, metadata: Dict[str, Any]) -> Path:
        """
        Apply directory template with metadata.
        
        Business rule: If template contains .taf extension, strip it (user error).
        
        Args:
            template: Directory template string
            metadata: Metadata for substitution
            
        Returns:
            Resolved directory path
        """
        from ....utils.filename import apply_template_to_path
        
        resolved = apply_template_to_path(template, metadata)
        if not resolved:
            self.logger.warning(f"Directory template '{template}' produced no result, using current directory")
            return Path.cwd()
        
        dir_path = Path(resolved)
        
        # Strip .taf extension if user accidentally included it
        if dir_path.suffix.lower() == '.taf':
            self.logger.debug("Stripping .taf extension from directory template (user error)")
            dir_path = dir_path.with_suffix('')
        
        return dir_path
    
    def _apply_filename_template(self, template: str, metadata: Dict[str, Any]) -> str:
        """
        Apply filename template with metadata.
        
        Business rule: Filename template may include .taf or not.
        
        Args:
            template: Filename template string
            metadata: Metadata for substitution
            
        Returns:
            Resolved filename
        """
        from ....utils.filename import apply_template_to_path
        
        resolved = apply_template_to_path(template, metadata)
        if not resolved:
            self.logger.warning(f"Filename template '{template}' produced no result, using 'output.taf'")
            return "output.taf"
        
        # Extract just the filename part (in case template included path separators)
        filename = Path(resolved).name
        
        return filename
    
    def _generate_default_path(self, input_path: Path) -> Path:
        """
        Generate smart default output path based on input.
        
        Business rules:
        - For directories: Use directory name as base filename
        - For files: Use file stem as base filename
        - Output in same directory as input
        
        Args:
            input_path: Input file or directory
            
        Returns:
            Default output path
        """
        from ....utils.filename import guess_output_filename
        
        base_filename = guess_output_filename(str(input_path))
        
        if input_path.is_dir():
            # Output inside the directory
            output_path = input_path / f"{base_filename}.taf"
        else:
            # Output alongside the file
            output_path = input_path.parent / f"{base_filename}.taf"
        
        return output_path
    
    def _ensure_taf_extension(self, path: Path) -> Path:
        """
        Ensure the path has .taf extension.
        
        Business rule: All TonieToolbox outputs must have .taf extension.
        
        Args:
            path: Path to check/modify
            
        Returns:
            Path with .taf extension
        """
        if path.suffix.lower() != '.taf':
            self.logger.debug(f"Adding .taf extension to: {path}")
            return path.with_suffix('.taf')
        return path
    
    def resolve_metadata_from_input(
        self,
        input_path: Path,
        tag_service: Any = None
    ) -> Dict[str, Any]:
        """
        Extract metadata from input file for template processing.
        
        This method coordinates with the media tag service to extract
        both normalized tags (artist, album) and original ID3 tags (TPE1, TALB).
        
        Args:
            input_path: Input file path
            tag_service: Media tag service instance
            
        Returns:
            Dictionary of metadata for template substitution
        """
        if not tag_service:
            self.logger.debug("No tag service provided, returning empty metadata")
            return {}
        
        metadata = {}
        
        try:
            # Get normalized tags
            tags = tag_service.get_file_tags(str(input_path))
            if tags:
                metadata.update({k: v for k, v in tags.items()})
            
            # Get original ID3/format-specific tags
            all_tags = tag_service.get_all_file_tags(str(input_path))
            if all_tags:
                for tag_data in all_tags.values():
                    original_key = tag_data.get('original')
                    readable_key = tag_data.get('readable')
                    value = tag_data.get('value')
                    
                    if original_key and readable_key and value:
                        # Add original key if different from readable
                        if original_key != readable_key:
                            metadata[original_key] = value
            
            self.logger.debug(f"Extracted {len(metadata)} metadata fields from {input_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {input_path}: {e}")
        
        return metadata
    
    def find_representative_audio_file(self, directory: Path) -> Optional[Path]:
        """
        Find a representative audio file in a directory for metadata extraction.
        
        Business rule: Use first audio file found (mp3, flac, wav, m4a, ogg).
        
        Args:
            directory: Directory to search
            
        Returns:
            Path to first audio file found, or None
        """
        if not directory.is_dir():
            return None
        
        audio_extensions = ['.mp3', '.flac', '.wav', '.m4a', '.ogg']
        
        for ext in audio_extensions:
            files = list(directory.glob(f'*{ext}'))
            if files:
                self.logger.debug(f"Found representative audio file: {files[0]}")
                return files[0]
        
        self.logger.debug(f"No audio files found in {directory}")
        return None
