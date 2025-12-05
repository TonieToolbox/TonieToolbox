#!/usr/bin/python3
"""
Mutagen-based artwork extraction implementation.
"""
import os
import base64
from typing import Optional

import mutagen
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from ..domain import ArtworkExtractor, ArtworkData, ArtworkExtractionError


class MutagenArtworkExtractor(ArtworkExtractor):
    """
    Concrete implementation of ArtworkExtractor using mutagen library.
    """
    
    def __init__(self, logger):
        """Initialize with logger."""
        self.logger = logger
        
    def extract_artwork(self, file_path: str) -> Optional[ArtworkData]:
        """
        Extract artwork from media file using mutagen.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            ArtworkData if found, None otherwise
            
        Raises:
            ArtworkExtractionError: If extraction fails
        """
        if not os.path.exists(file_path):
            raise ArtworkExtractionError(f"File not found: {file_path}")
        
        try:
            file_ext = os.path.splitext(file_path.lower())[1]
            artwork_data = None
            mime_type = None
            
            # Handle MP3 files
            if file_ext == '.mp3':
                artwork_data, mime_type = self._extract_from_mp3(file_path)
            
            # Handle FLAC files
            elif file_ext == '.flac':
                artwork_data, mime_type = self._extract_from_flac(file_path)
            
            # Handle MP4/M4A/AAC files
            elif file_ext in ['.m4a', '.mp4', '.aac']:
                artwork_data, mime_type = self._extract_from_mp4(file_path)
            
            # Handle OGG files
            elif file_ext == '.ogg':
                artwork_data, mime_type = self._extract_from_ogg(file_path)
            
            if artwork_data and mime_type:
                # Determine file extension from MIME type
                if mime_type == 'image/jpeg':
                    ext = '.jpg'
                elif mime_type == 'image/png':
                    ext = '.png'
                else:
                    ext = '.jpg'  # Default to JPEG
                
                return ArtworkData(
                    data=artwork_data,
                    mime_type=mime_type,
                    format_extension=ext
                )
            
            self.logger.debug("No artwork found in file: %s", file_path)
            return None
            
        except Exception as e:
            raise ArtworkExtractionError(f"Failed to extract artwork from {file_path}: {e}")
    
    def supports_format(self, file_path: str) -> bool:
        """Check if extractor supports the file format."""
        file_ext = os.path.splitext(file_path.lower())[1]
        return file_ext in ['.mp3', '.flac', '.m4a', '.mp4', '.aac', '.ogg']
    
    def _extract_from_mp3(self, file_path: str) -> tuple[Optional[bytes], Optional[str]]:
        """Extract artwork from MP3 file."""
        audio = mutagen.File(file_path)
        if audio and audio.tags:
            for frame in audio.tags.values():
                if frame.FrameID == 'APIC':
                    return frame.data, frame.mime
        return None, None
    
    def _extract_from_flac(self, file_path: str) -> tuple[Optional[bytes], Optional[str]]:
        """Extract artwork from FLAC file."""
        audio = FLAC(file_path)
        if audio.pictures:
            picture = audio.pictures[0]
            return picture.data, picture.mime
        return None, None
    
    def _extract_from_mp4(self, file_path: str) -> tuple[Optional[bytes], Optional[str]]:
        """Extract artwork from MP4 file."""
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
                return bytes(artwork_data), mime_type
        return None, None
    
    def _extract_from_ogg(self, file_path: str) -> tuple[Optional[bytes], Optional[str]]:
        """Extract artwork from OGG file."""
        try:
            audio = OggVorbis(file_path)
        except:
            try:
                audio = OggOpus(file_path)
            except:
                self.logger.debug("Could not determine OGG type for %s", file_path)
                return None, None
        
        if 'metadata_block_picture' in audio:
            picture_data = base64.b64decode(audio['metadata_block_picture'][0])
            flac_picture = Picture(data=picture_data)
            return flac_picture.data, flac_picture.mime
        
        return None, None