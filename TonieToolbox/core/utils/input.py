#!/usr/bin/python3
"""
Input processing and normalization for TonieToolbox.

This module handles input file/path processing and normalization.
"""

import os
from typing import Tuple


class InputProcessor:
    """Handles input file/path processing and normalization."""
    
    @staticmethod
    def normalize_input_path(input_path: str) -> str:
        """
        Normalize input path by removing quotes, trailing slashes, and handling shell escape sequences.
        
        Args:
            input_path: Raw input path from command line
            
        Returns:
            Normalized path string
        """
        if not input_path:
            return input_path
            
        # Remove surrounding quotes
        normalized = input_path.strip('"\'')
        
        # Handle shell escape sequences (e.g., "\ " -> " ")
        # This is important for paths with spaces that get shell-escaped
        import re
        # Replace escaped spaces and other common shell escapes
        normalized = re.sub(r'\\(.)', r'\1', normalized)
        
        # Remove trailing slashes (but not if it's the root directory)
        if len(normalized) > 1 and normalized.endswith(('/', '\\')):
            normalized = normalized.rstrip('/\\')
            
        return normalized
    
    @staticmethod
    def determine_input_type(input_path: str) -> Tuple[str, bool]:
        """
        Determine input type and whether it exists.
        
        Args:
            input_path: Path to analyze
            
        Returns:
            Tuple of (type, exists) where type is 'file', 'directory', or 'pattern'
        """
        if os.path.isfile(input_path):
            return 'file', True
        elif os.path.isdir(input_path):
            return 'directory', True
        elif '*' in input_path or input_path.endswith('/*'):
            return 'pattern', os.path.exists(os.path.dirname(input_path))
        else:
            return 'file', False
    
    @staticmethod
    def convert_directory_to_pattern(input_path: str) -> str:
        """
        Convert directory path to pattern for file matching.
        
        Args:
            input_path: Directory path
            
        Returns:
            Pattern string for file matching
        """
        if os.path.isdir(input_path):
            return input_path + "/*"
        return input_path