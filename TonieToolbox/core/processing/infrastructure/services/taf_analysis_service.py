#!/usr/bin/env python3
"""
TAF File Analysis Infrastructure Service.

This service provides infrastructure-layer wrapper around the TAF analysis domain
module, adapting its domain models to the processing layer's interface requirements.

Architecture:
- Delegates TAF analysis to analysis/ domain module (avoiding duplication)
- Provides comparison and validation using domain services
- Adapts domain models (TafAnalysisResult) to Dict[str, Any] for processing layer
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import hashlib

from ...domain.models import ValidationResult
from ...domain.exceptions import ProcessingOperationError


class TafAnalysisService:
    """
    Infrastructure service for TAF file analysis.
    
    This service adapts the TAF analysis domain module for use in the processing
    infrastructure layer. It delegates actual analysis to the domain module to
    avoid code duplication while providing infrastructure-specific capabilities
    like file comparison.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize TAF analysis infrastructure service.
        
        Args:
            logger: Optional logger instance
        """
        from ....utils.logging import get_logger
        self.logger = logger or get_logger(__name__)
    
    def analyze_taf_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of TAF file using domain service.
        
        This method delegates to the analysis domain module to avoid duplication
        and converts the domain model to a dictionary for infrastructure layer use.
        
        Args:
            file_path: Path to TAF file to analyze
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ProcessingOperationError: If analysis fails
        """
        try:
            self.logger.info(f"Analyzing TAF file: {file_path}")
            
            if not file_path.exists():
                raise ProcessingOperationError(f"TAF file not found: {file_path}")
            
            # Delegate to domain module for actual analysis
            from ....analysis import analyze_taf_file as domain_analyze_taf_file
            
            domain_result = domain_analyze_taf_file(file_path)
            
            if not domain_result:
                raise ProcessingOperationError(f"TAF analysis failed for {file_path}")
            
            # Convert domain model to dictionary for infrastructure layer
            analysis_result = {
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'format': 'TAF',
                'valid': domain_result.header.valid if domain_result.header else False,
                'metadata': self._extract_metadata_from_domain_model(domain_result),
                'audio_info': self._extract_audio_info_from_domain_model(domain_result),
                'structure': self._extract_structure_from_domain_model(domain_result),
                'checksum': domain_result.sha1_hash if domain_result.sha1_hash else '',
                'errors': []
            }
            
            self.logger.info(f"TAF analysis completed: {file_path}")
            return analysis_result
            
        except Exception as e:
            error_msg = f"TAF analysis failed for {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise ProcessingOperationError(error_msg)
    
    def _extract_metadata_from_domain_model(self, domain_result) -> Dict[str, Any]:
        """Extract metadata from domain analysis result."""
        metadata = {}
        if domain_result.header:
            if domain_result.header.comments:
                metadata.update(domain_result.header.comments)
        return metadata
    
    def _extract_audio_info_from_domain_model(self, domain_result) -> Dict[str, Any]:
        """Extract audio information from domain analysis result."""
        audio_info = {}
        if domain_result.audio_analysis:
            audio_info = {
                'duration_seconds': domain_result.audio_analysis.duration_seconds,
                'bitrate_kbps': domain_result.audio_analysis.bitrate_kbps,
                'page_count': domain_result.audio_analysis.page_count,
                'alignment_okay': domain_result.audio_analysis.alignment_okay,
                'page_size_okay': domain_result.audio_analysis.page_size_okay
            }
        if domain_result.header:
            audio_info.update({
                'sample_rate': domain_result.header.sample_rate,
                'channels': domain_result.header.channels,
                'num_chapters': domain_result.header.num_chapters
            })
        return audio_info
    
    def _extract_structure_from_domain_model(self, domain_result) -> Dict[str, Any]:
        """Extract structure information from domain analysis result."""
        structure = {
            'chapters': []
        }
        if domain_result.chapters:
            structure['chapters'] = [
                {
                    'index': ch.index,
                    'offset': ch.offset,
                    'length': ch.length,
                    'duration_ms': ch.duration_ms
                }
                for ch in domain_result.chapters
            ]
        return structure
    
    def extract_taf_header(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract TAF file header information using domain service.
        
        Args:
            file_path: Path to TAF file
            
        Returns:
            Dictionary containing header information
        """
        try:
            from ....analysis import get_header_info
            
            # Use domain function to extract header
            with open(file_path, 'rb') as f:
                header_tuple = get_header_info(f)
            
            # Convert tuple to dictionary
            # header_tuple structure: (header, opus_info, file_size, audio_size, sha1, valid)
            if len(header_tuple) >= 6:
                header_obj, opus_info, file_size, audio_size, sha1, valid = header_tuple[:6]
                
                header_info = {
                    'valid': valid,
                    'file_size': file_size,
                    'audio_size': audio_size,
                    'sha1': sha1,
                    'sample_rate': opus_info.sample_rate if opus_info else 0,
                    'channels': opus_info.channels if opus_info else 0,
                    'num_chapters': header_obj.num_chapters if header_obj else 0,
                    'audio_length': header_obj.audio_length if header_obj else 0
                }
                
                return header_info
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Failed to extract TAF header from {file_path}: {str(e)}")
            return {}
    
    def extract_taf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from TAF file using domain service.
        
        Args:
            file_path: Path to TAF file
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            from ....analysis import analyze_taf_file as domain_analyze_taf_file
            
            domain_result = domain_analyze_taf_file(file_path)
            
            if not domain_result or not domain_result.header:
                return {}
            
            metadata = {}
            
            # Extract comments (metadata) from domain model
            if domain_result.header.comments:
                metadata.update(domain_result.header.comments)
            
            # Add file statistics
            file_stats = file_path.stat()
            metadata.update({
                'file_size': file_stats.st_size,
                'created_time': file_stats.st_ctime,
                'modified_time': file_stats.st_mtime
            })
            
            # Add audio analysis data if available
            if domain_result.audio_analysis:
                metadata.update({
                    'duration_seconds': domain_result.audio_analysis.duration_seconds,
                    'bitrate_kbps': domain_result.audio_analysis.bitrate_kbps
                })
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to extract TAF metadata from {file_path}: {str(e)}")
            return {}
    
    def validate_taf_file(self, file_path: Path) -> ValidationResult:
        """
        Validate TAF file format and integrity using domain service.
        
        Args:
            file_path: Path to TAF file to validate
            
        Returns:
            ValidationResult with validation status and any errors
        """
        errors = []
        warnings = []
        
        try:
            # Use domain validation function
            from ....analysis import check_tonie_file
            
            # Check file exists and is readable
            if not file_path.exists():
                errors.append(f"File does not exist: {file_path}")
                return ValidationResult(False, errors, warnings)
            
            if not file_path.is_file():
                errors.append(f"Path is not a file: {file_path}")
                return ValidationResult(False, errors, warnings)
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size < 4096:  # Minimum size for TAF header (4KB)
                errors.append(f"File too small to be valid TAF: {file_size} bytes")
                return ValidationResult(False, errors, warnings)
            
            # Use domain validation
            is_valid = check_tonie_file(str(file_path))
            
            if not is_valid:
                errors.append("TAF validation failed")
                return ValidationResult(False, errors, warnings)
            
            return ValidationResult(True, errors, warnings)
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return ValidationResult(False, errors, warnings)
    
    def _validate_taf_format(self, file_path: Path) -> ValidationResult:
        """Internal TAF format validation - delegates to validate_taf_file."""
        return self.validate_taf_file(file_path)
    
    def compare_taf_files(self, file1: Path, file2: Path) -> Dict[str, Any]:
        """
        Compare two TAF files and return differences.
        
        Args:
            file1: Path to first TAF file
            file2: Path to second TAF file
            
        Returns:
            Dictionary containing comparison results
        """
        try:
            comparison = {
                'files': [str(file1), str(file2)],
                'identical': False,
                'differences': [],
                'metadata_diff': {},
                'audio_diff': {},
                'file_size_diff': 0
            }
            
            # Check if files exist
            if not file1.exists() or not file2.exists():
                comparison['differences'].append("One or both files do not exist")
                return comparison
            
            # Compare file sizes
            size1 = file1.stat().st_size
            size2 = file2.stat().st_size
            comparison['file_size_diff'] = size2 - size1
            
            if size1 != size2:
                comparison['differences'].append(f"File size differs: {size1} vs {size2} bytes")
            
            # Compare checksums for quick identity check
            checksum1 = self._calculate_file_checksum(file1)
            checksum2 = self._calculate_file_checksum(file2)
            
            if checksum1 == checksum2:
                comparison['identical'] = True
                return comparison
            
            # Detailed comparison using domain analysis
            from ....analysis import analyze_taf_file as domain_analyze_taf_file
            
            try:
                result1 = domain_analyze_taf_file(file1)
                result2 = domain_analyze_taf_file(file2)
            except Exception as e:
                self.logger.error(f"Error analyzing files for comparison: {e}")
                comparison['error'] = str(e)
                comparison['differences'].append(f"Failed to analyze one or both files: {e}")
                return comparison
            
            if not result1 or not result2:
                comparison['differences'].append("Failed to analyze one or both files")
                return comparison
            
            # Compare headers
            if result1.header and result2.header:
                if result1.header.sample_rate != result2.header.sample_rate:
                    comparison['differences'].append(
                        f"Sample rate differs: {result1.header.sample_rate} vs {result2.header.sample_rate}"
                    )
                if result1.header.channels != result2.header.channels:
                    comparison['differences'].append(
                        f"Channels differ: {result1.header.channels} vs {result2.header.channels}"
                    )
                if result1.header.num_chapters != result2.header.num_chapters:
                    comparison['differences'].append(
                        f"Number of chapters differs: {result1.header.num_chapters} vs {result2.header.num_chapters}"
                    )
            
            # Compare metadata
            if result1.header and result2.header:
                meta1 = result1.header.comments or {}
                meta2 = result2.header.comments or {}
                
                for key in set(meta1.keys()) | set(meta2.keys()):
                    val1 = meta1.get(key)
                    val2 = meta2.get(key)
                    if val1 != val2:
                        comparison['metadata_diff'][key] = {'file1': val1, 'file2': val2}
            
            # Compare audio analysis
            if result1.audio_analysis and result2.audio_analysis:
                if abs(result1.audio_analysis.duration_seconds - result2.audio_analysis.duration_seconds) > 0.1:
                    comparison['audio_diff']['duration'] = {
                        'file1': result1.audio_analysis.duration_seconds,
                        'file2': result2.audio_analysis.duration_seconds
                    }
                if result1.audio_analysis.bitrate_kbps != result2.audio_analysis.bitrate_kbps:
                    comparison['audio_diff']['bitrate'] = {
                        'file1': result1.audio_analysis.bitrate_kbps,
                        'file2': result2.audio_analysis.bitrate_kbps
                    }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"TAF file comparison failed: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to calculate checksum for {file_path}: {str(e)}")
            return ""
