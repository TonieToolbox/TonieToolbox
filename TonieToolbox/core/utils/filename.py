#!/usr/bin/python3
"""
Module for generating intelligent output filenames for TonieToolbox.
"""
import os
import re
from pathlib import Path
from typing import List, Optional
from .logging import get_logger
logger = get_logger(__name__)
def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters and trimming.
    Args:
        filename (str): The filename to sanitize
    Returns:
        str: A sanitized filename
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    sanitized = sanitized.strip('. \t')
    if not sanitized:
        return "tonie"
    return sanitized
def guess_output_filename(input_filename: str, input_files: list[str] = None) -> str:
    """
    Generate a sensible output filename based on input file or directory.
    Logic:
    1. For .lst files: 
       a. First try to extract filename from comments (# filename:, # output:, # name:)
       b. Fall back to using the lst filename without extension
    2. For directories: Use the directory name
    3. For single files: Use the filename without extension
    4. For multiple files: Use the common parent directory name
    
    .lst files can contain comments to specify the output filename:
    - # filename: My_Audiobook_Name
    - # output: Custom_Output_Name
    - # name: "My Special Story"
    
    Args:
        input_filename (str): The input filename or pattern
        input_files (list[str] | None): List of resolved input files (optional)
    Returns:
        str: Generated output filename without extension
    """
    logger.debug("Guessing output filename from input: %s", input_filename)
    if input_filename.lower().endswith('.lst'):
        # First try to extract filename from comments
        comment_filename = extract_filename_from_lst_comments(input_filename)
        if comment_filename:
            logger.debug("Using filename from .lst comment: %s", comment_filename)
            return comment_filename
        
        # Fall back to using the .lst file name
        base = os.path.basename(input_filename)
        name = os.path.splitext(base)[0]
        logger.debug("Using .lst file name as fallback: %s", name)
        return sanitize_filename(name)
    if input_filename.endswith('/*') or input_filename.endswith('\\*'):
        dir_path = input_filename[:-2]
        dir_name = os.path.basename(os.path.normpath(dir_path))
        logger.debug("Using directory name: %s", dir_name)
        return sanitize_filename(dir_name)
    if os.path.isdir(input_filename):
        dir_name = os.path.basename(os.path.normpath(input_filename))
        logger.debug("Using directory name: %s", dir_name)
        return sanitize_filename(dir_name)
    if not input_files or len(input_files) == 1:
        file_path = input_files[0] if input_files else input_filename
        base = os.path.basename(file_path)
        name = os.path.splitext(base)[0]
        logger.debug("Using single file name: %s", name)
        return sanitize_filename(name)
    try:
        common_path = os.path.commonpath([os.path.abspath(f) for f in input_files])
        dir_name = os.path.basename(common_path)
        if len(dir_name) <= 1 or len(common_path) < 4:
            dir_name = os.path.basename(os.path.dirname(os.path.abspath(input_files[0])))
        logger.debug("Using common parent directory: %s", dir_name)
        return sanitize_filename(dir_name)
    except ValueError:
        logger.debug("Could not determine common path, using generic name")
        return "tonie_collection"

def extract_filename_from_lst_comments(lst_filename: str) -> Optional[str]:
    """
    Extract output filename from comments in a .lst file.
    
    Looks for comments in the following formats:
    - # filename: my_audiobook
    - # output: my_audiobook
    - # name: my_audiobook
    
    Args:
        lst_filename (str): Path to the .lst file
        
    Returns:
        Optional[str]: Extracted filename without extension, or None if not found
        
    Raises:
        FileNotFoundError: If the .lst file doesn't exist
        PermissionError: If the .lst file cannot be read due to permissions
        UnicodeDecodeError: If the file encoding is not UTF-8 compatible
    """
    try:
        with open(lst_filename, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if line.startswith('#'):
                    # Remove the # and strip whitespace
                    comment = line[1:].strip()                    
                    # Check for various comment formats
                    for prefix in ['filename:', 'output:', 'name:']:
                        if comment.lower().startswith(prefix):
                            # Extract the value after the prefix
                            filename = comment[len(prefix):].strip()
                            if filename:
                                # Remove quotes if present
                                filename = filename.strip('"\'')
                                # Remove .lst extension if present (to prevent double extension)
                                if filename.lower().endswith('.lst'):
                                    filename = os.path.splitext(filename)[0]
                                sanitized = sanitize_filename(filename)
                                logger.debug("Found filename in .lst comment at line %d: %s", line_num, sanitized)
                                return sanitized
                            
        logger.debug("No filename comment found in .lst file: %s", lst_filename)
        return None
        
    except Exception as e:
        logger.warning("Error reading .lst file for filename extraction: %s", e)
        return None


def apply_template_to_path(template: str, metadata: dict) -> str:
    """
    Apply metadata to a path template and ensure the path is valid.
    
    Args:
        template: String template with {tag} placeholders
        metadata: Dictionary of tag values
        
    Returns:
        Formatted path with placeholders replaced by actual values, or None if invalid
        
    Raises:
        ValueError: If template or metadata is None/empty
        KeyError: If a required placeholder in template is missing from metadata
    """
    if not template or not metadata:
        return None
    try:
        formatted_path = template
        for tag, value in metadata.items():
            if value:
                safe_value = re.sub(r'[<>:"|?*]', '_', str(value))
                safe_value = safe_value.replace('/', ' - ')
                safe_value = safe_value.strip('. \t')
                if not safe_value:
                    safe_value = "unknown"
                placeholder = '{' + tag + '}'
                formatted_path = formatted_path.replace(placeholder, safe_value)
        if re.search(r'{[^}]+}', formatted_path):
            return None
        formatted_path = os.path.normpath(formatted_path)
        return formatted_path
    except Exception as e:
        logger.error(f"Error applying template to path: {e}")
        return None


def ensure_directory_exists(file_path: str) -> None:
    """
    Create the directory structure for a given file path if it doesn't exist.
    
    Args:
        file_path: Path to a file whose directory structure should be created
        
    Raises:
        OSError: If directory creation fails due to permissions or disk space
        PermissionError: If insufficient permissions to create directories
    """
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)