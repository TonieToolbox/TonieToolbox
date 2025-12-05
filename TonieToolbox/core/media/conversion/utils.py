#!/usr/bin/python3
"""
File processing utilities for audio conversion.
"""
import os
import glob
from ...utils import get_logger

logger = get_logger(__name__)


def get_input_files(input_filename: str) -> list[str]:
    """
    Get a list of input files to process.
    Supports direct file paths, directory paths, glob patterns, and .lst files.
    
    Args:
        input_filename (str): Input file pattern or list file path
        
    Returns:
        list[str]: List of input file paths
        
    Raises:
        FileNotFoundError: If .lst file specified but doesn't exist
        PermissionError: If .lst file cannot be read due to permissions
        UnicodeDecodeError: If .lst file encoding is not UTF-8 compatible
    """
    from . import filter_directories
    
    logger.trace("Entering get_input_files(input_filename=%s)", input_filename)
    logger.debug("Getting input files for pattern: %s", input_filename)
    
    if input_filename.endswith(".lst"):
        logger.debug("Processing list file: %s", input_filename)
        list_dir = os.path.dirname(os.path.abspath(input_filename))
        input_files = []
        
        with open(input_filename, 'r', encoding='utf-8') as file_list:
            for line_num, line in enumerate(file_list, 1):
                fname = line.strip()
                if not fname or fname.startswith('#'):
                    logger.trace("Skipping empty line or comment at line %d", line_num)
                    continue
                
                fname = fname.strip('"\'')
                if os.path.isabs(fname) or (len(fname) > 1 and fname[1] == ':'):
                    full_path = fname
                    logger.trace("Using absolute path from line %d: %s", line_num, full_path)
                else:
                    full_path = os.path.join(list_dir, fname)
                    logger.trace("Using relative path from line %d: %s -> %s", line_num, fname, full_path)
                
                if os.path.isdir(full_path):
                    logger.debug("Path is a directory, finding audio files in: %s", full_path)
                    dir_glob = os.path.join(full_path, "*")
                    dir_files = sorted(filter_directories(glob.glob(dir_glob)))
                    if dir_files:
                        input_files.extend(dir_files)
                        logger.debug("Found %d audio files in directory from line %d", len(dir_files), line_num)
                    else:
                        logger.warning("No audio files found in directory at line %d: %s", line_num, full_path)
                elif os.path.isfile(full_path):
                    input_files.append(full_path)
                    logger.trace("Added file from line %d: %s", line_num, full_path)
                else:
                    logger.warning("File not found at line %d: %s", line_num, full_path)
        
        logger.debug("Found %d files in list file", len(input_files))
    else:
        logger.debug("Processing input path: %s", input_filename)
        input_files = sorted(filter_directories(glob.glob(input_filename)))
        
        if input_files:
            logger.debug("Found %d files matching exact pattern", len(input_files))
        else:
            _, ext = os.path.splitext(input_filename)
            if not ext:
                wildcard_pattern = input_filename + ".*"
                logger.debug("No extension in pattern, trying with wildcard: %s", wildcard_pattern)
                input_files = sorted(filter_directories(glob.glob(wildcard_pattern)))
                
                if not input_files and os.path.exists(os.path.dirname(input_filename)):
                    potential_dir = input_filename
                    if os.path.isdir(potential_dir):
                        logger.debug("Treating input as directory: %s", potential_dir)
                        dir_glob = os.path.join(potential_dir, "*")
                        input_files = sorted(filter_directories(glob.glob(dir_glob)))
                        if input_files:
                            logger.debug("Found %d audio files in directory", len(input_files))
                
                if input_files:
                    logger.debug("Found %d files after trying alternatives", len(input_files))
                else:
                    logger.warning("No files found for pattern %s even after trying alternatives", input_filename)
    
    logger.trace("Exiting get_input_files() with %d files", len(input_files))
    return input_files


def append_to_filename(output_filename: str, tag: str) -> str:
    """
    Append a tag to a filename, preserving the extension.
    
    Args:
        output_filename (str): Original filename
        tag (str): Tag to append (typically an 8-character hex value)
        
    Returns:
        str: Modified filename with tag
    """
    logger.trace("Entering append_to_filename(output_filename=%s, tag=%s)", output_filename, tag)
    logger.debug("Appending tag '%s' to filename: %s", tag, output_filename)
    
    pos = output_filename.rfind('.')
    if pos == -1:
        result = f"{output_filename}_{tag}"
        logger.debug("No extension found, result: %s", result)
        logger.trace("Exiting append_to_filename() with result=%s", result)
        return result
    else:
        result = f"{output_filename[:pos]}_{tag}{output_filename[pos:]}"
        logger.debug("Extension found, result: %s", result)
        logger.trace("Exiting append_to_filename() with result=%s", result)
        return result