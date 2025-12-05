#!/usr/bin/python3
"""
Icon utility functions for desktop integration.
Handles conversion between different icon formats and base64 encoding.
"""
import os
import base64
from typing import Optional
from ..config.application_constants import ICON_ICO_BASE64, ICON_PNG_BASE64
from . import get_logger

logger = get_logger(__name__)


def ico_to_base64(ico_path: str) -> str:
    """
    Convert an ICO file to a base64 string.
    
    Args:
        ico_path: Path to the ICO file
        
    Returns:
        Base64 encoded string of the ICO file
        
    Raises:
        FileNotFoundError: If the ICO file doesn't exist
    """
    if not os.path.exists(ico_path):
        raise FileNotFoundError(f"ICO file not found: {ico_path}")
    
    with open(ico_path, "rb") as ico_file:
        ico_bytes = ico_file.read()
    
    base64_string = base64.b64encode(ico_bytes).decode('utf-8')
    return base64_string


def base64_to_ico(base64_string: str, output_path: str) -> str:
    """
    Convert a base64 string back to an ICO file.
    
    Args:
        base64_string: Base64 encoded string of the ICO file
        output_path: Path where to save the ICO file
        
    Returns:
        Path to the saved ICO file
        
    Raises:
        ValueError: If base64_string is invalid or cannot be decoded
        OSError: If output directory cannot be created
        PermissionError: If insufficient permissions to write file
    """
    ico_bytes = base64.b64decode(base64_string)
    
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_path, "wb") as ico_file:
        ico_file.write(ico_bytes)
    
    return output_path


def base64_to_png(output_path: str) -> Optional[str]:
    """
    Convert the embedded PNG base64 data to a PNG file.
    
    Args:
        output_path: Path where to save the PNG file
        
    Returns:
        Path to the saved PNG file or None if failed
        
    Raises:
        ValueError: If ICON_PNG_BASE64 constant is invalid
        OSError: If output directory cannot be created
        PermissionError: If insufficient permissions to write file
    """
    try:
        png_bytes = base64.b64decode(ICON_PNG_BASE64)
        
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_path, "wb") as png_file:
            png_file.write(png_bytes)
        
        logger.debug(f"Created PNG icon at: {output_path}")
        return output_path
        
    except Exception as e:
        logger.warning(f"Failed to write PNG icon: {e}")
        return None


def create_icon(output_path: str, prefer_png: bool = True) -> Optional[str]:
    """
    Create an icon file (PNG or ICO) at the specified path.
    
    Args:
        output_path: Path where to save the icon file
        prefer_png: Whether to prefer PNG format over ICO
        
    Returns:
        Path to the created icon file or None if failed
    """
    if prefer_png and output_path.endswith('.png'):
        return base64_to_png(output_path)
    elif output_path.endswith('.ico'):
        return base64_to_ico(ICON_ICO_BASE64, output_path)
    else:
        # Try PNG first if preferred
        if prefer_png:
            png_path = output_path if output_path.endswith('.png') else f"{output_path}.png"
            result = base64_to_png(png_path)
            if result:
                return result
        
        # Fallback to ICO
        ico_path = output_path if output_path.endswith('.ico') else f"{output_path}.ico"
        return base64_to_ico(ICON_ICO_BASE64, ico_path)