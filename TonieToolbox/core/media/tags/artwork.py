#!/usr/bin/python3
"""
Artwork extraction and processing functionality.
"""
import os
import tempfile
import base64
from typing import Optional

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from ...config.application_constants import ARTWORK_NAMES, ARTWORK_EXTENSIONS
from ...utils import get_logger

logger = get_logger(__name__)


def extract_artwork(file_path: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Extract artwork from an audio file.
    
    Args:
        file_path: Path to the audio file
        output_path: Path where to save the extracted artwork.
                     If None, a temporary file will be created.
                     
    Returns:
        Path to the extracted artwork file, or None if no artwork was found
    """
    if not os.path.exists(file_path):
        logger.error("File not found: %s", file_path)
        return None
    
    try:
        file_ext = os.path.splitext(file_path.lower())[1]
        artwork_data = None
        mime_type = None
        
        # Handle MP3 files
        if file_ext == '.mp3':
            audio = mutagen.File(file_path)
            if audio.tags:
                for frame in audio.tags.values():
                    if frame.FrameID == 'APIC':
                        artwork_data = frame.data
                        mime_type = frame.mime
                        break
        
        # Handle FLAC files
        elif file_ext == '.flac':
            audio = FLAC(file_path)
            if audio.pictures:
                artwork_data = audio.pictures[0].data
                mime_type = audio.pictures[0].mime
        
        # Handle MP4/M4A/AAC files
        elif file_ext in ['.m4a', '.mp4', '.aac']:
            audio = MP4(file_path)
            if 'covr' in audio:
                artwork_data = audio['covr'][0]
                if isinstance(artwork_data, mutagen.mp4.MP4Cover):
                    if artwork_data.format == mutagen.mp4.MP4Cover.FORMAT_JPEG:
                        mime_type = 'image/jpeg'
                    elif artwork_data.format == mutagen.mp4.MP4Cover.FORMAT_PNG:
                        mime_type = 'image/png'
                    else:
                        mime_type = 'image/jpeg'
        
        # Handle OGG files (Vorbis/Opus)
        elif file_ext == '.ogg':
            try:
                audio = OggVorbis(file_path)
            except:
                try:
                    audio = OggOpus(file_path)
                except:
                    logger.debug("Could not determine OGG type for %s", file_path)
                    return None
                    
            if 'metadata_block_picture' in audio:
                picture_data = base64.b64decode(audio['metadata_block_picture'][0])
                flac_picture = Picture(data=picture_data)
                artwork_data = flac_picture.data
                mime_type = flac_picture.mime
        
        # Save artwork if found
        if artwork_data:
            # Determine file extension
            if mime_type == 'image/jpeg':
                ext = '.jpg'
            elif mime_type == 'image/png':
                ext = '.png'
            else:
                ext = '.jpg'  # Default to JPEG
            
            # Create output path if not provided
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                output_path = temp_file.name
                temp_file.close()
            elif not os.path.splitext(output_path)[1]:
                output_path += ext
            
            # Write artwork to file
            with open(output_path, 'wb') as f:
                f.write(artwork_data)
                
            logger.info("Extracted artwork saved to %s", output_path)
            return output_path
        else:
            logger.debug("No artwork found in file: %s", file_path)
            return None
            
    except Exception as e:
        logger.debug("Error extracting artwork: %s", e)
        return None


def find_cover_image(source_dir: str) -> Optional[str]:
    """
    Find a cover image in the source directory.
    
    Args:
        source_dir: Path to the directory to search for cover images
        
    Returns:
        Path to the found cover image, or None if not found
    """
    if not os.path.isdir(source_dir):
        return None
    
    cover_names = ARTWORK_NAMES
    image_extensions = ARTWORK_EXTENSIONS
    
    # First pass: exact matches
    for name in cover_names:
        for ext in image_extensions:
            cover_path = os.path.join(source_dir, name + ext)
            if os.path.exists(cover_path):
                logger.debug("Found cover image: %s", cover_path)
                return cover_path
            
            # Case-insensitive search
            for file in os.listdir(source_dir):
                if file.lower() == (name + ext).lower():
                    cover_path = os.path.join(source_dir, file)
                    logger.debug("Found cover image: %s", cover_path)
                    return cover_path
    
    # Second pass: partial matches
    for file in os.listdir(source_dir):
        file_lower = file.lower()
        file_ext = os.path.splitext(file_lower)[1]
        
        if file_ext in image_extensions:
            for name in cover_names:
                if name in file_lower:
                    cover_path = os.path.join(source_dir, file)
                    logger.debug("Found cover image: %s", cover_path)
                    return cover_path
    
    logger.debug("No cover image found in directory: %s", source_dir)
    return None