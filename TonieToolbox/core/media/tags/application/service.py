#!/usr/bin/python3
"""
Application service for coordinating media tag operations.
This layer orchestrates domain services and infrastructure implementations.
"""
import os
from typing import Dict, List, Optional, Any
import logging

from ..domain import (
    MediaTagCollection, ArtworkData,
    TagNormalizationService, FilenameFormattingService, AlbumAnalysisService,
    TagReader, ArtworkExtractor, FileSystemService, CoverImageFinder
)
from ..infrastructure import (
    MutagenTagReaderFactory, MutagenArtworkExtractor, 
    StandardFileSystemService, StandardCoverImageFinder
)


class MediaTagService:
    """
    Application service that coordinates all media tag operations.
    This is the main entry point for tag processing functionality.
    """
    
    def __init__(
        self,
        tag_mappings: Dict[str, str],
        value_replacements: Dict[str, str],
        artwork_names: List[str],
        artwork_extensions: List[str],
        logger: logging.Logger
    ):
        """
        Initialize media tag service with dependencies.
        
        Args:
            tag_mappings: Mapping from format-specific to standardized tag names
            value_replacements: Value replacement rules for normalization
            artwork_names: List of cover image filename patterns
            artwork_extensions: List of supported image extensions
            logger: Logger instance
        """
        self.logger = logger
        
        # Initialize infrastructure services
        self.fs_service = StandardFileSystemService()
        self.tag_reader_factory = MutagenTagReaderFactory(logger)
        self.artwork_extractor = MutagenArtworkExtractor(logger)
        self.cover_finder = StandardCoverImageFinder(artwork_names, artwork_extensions, logger)
        
        # Initialize domain services
        self.tag_normalizer = TagNormalizationService(value_replacements, logger)
        self.filename_formatter = FilenameFormattingService(logger)
        
        # Create album analyzer with first available reader
        dummy_reader = self.tag_reader_factory.create_reader("dummy.mp3")
        if dummy_reader:
            self.album_analyzer = AlbumAnalysisService(dummy_reader, self.fs_service, logger)
        else:
            self.album_analyzer = None
    
    def get_file_tags(self, file_path: str, normalize: bool = True) -> Dict[str, str]:
        """
        Extract standardized tags from a media file.
        
        Args:
            file_path: Path to the media file
            normalize: Whether to normalize tag values
            
        Returns:
            Dictionary with standardized tag names and values
        
        Example:
            Extract normalized tags from an MP3 file::
            
                service = MediaTagService(tag_mappings, value_replacements, 
                                         artwork_names, artwork_extensions, logger)
                tags = service.get_file_tags('song.mp3')
                print(tags)
                # Output: {'artist': 'The Beatles', 'title': 'Yesterday', 
                #          'album': 'Help!', 'date': '1965'}
            
            Extract raw tags without normalization::
            
                tags = service.get_file_tags('song.mp3', normalize=False)
                # May contain original casing and format-specific values
            
            Handle missing tags gracefully::
            
                tags = service.get_file_tags('instrumental.mp3')
                artist = tags.get('artist', 'Unknown Artist')
                title = tags.get('title', 'Untitled')
        """
        reader = self.tag_reader_factory.create_reader(file_path)
        if not reader:
            self.logger.warning("No tag reader available for file: %s", file_path)
            return {}
        
        try:
            tags = reader.read_tags(file_path)
            
            if normalize:
                tags = self.tag_normalizer.normalize_collection(tags)
            
            return tags.get_standardized_tags()
            
        except Exception as e:
            self.logger.error("Error reading tags from %s: %s", file_path, e)
            return {}
    
    def get_all_file_tags(self, file_path: str) -> Dict[str, Any]:
        """
        Extract ALL tags from a media file with detailed information.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Dictionary with detailed tag information including original keys
        
        Example:
            Get detailed tag information including original ID3 keys::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                all_tags = service.get_all_file_tags('song.mp3')
                for key, info in all_tags.items():
                    print(f"{info['original']} -> {info['readable']}: {info['value']}")
                # Output:
                # TPE1 -> artist: The Beatles
                # TIT2 -> title: Yesterday
                # TALB -> album: Help!
            
            Access both original and normalized tag names::
            
                all_tags = service.get_all_file_tags('audio.flac')
                if 'ARTIST' in all_tags:
                    original_key = all_tags['ARTIST']['original']  # 'ARTIST'
                    readable_key = all_tags['ARTIST']['readable']  # 'artist'
                    value = all_tags['ARTIST']['value']            # 'Artist Name'
        """
        reader = self.tag_reader_factory.create_reader(file_path)
        if not reader:
            return {}
        
        try:
            tags = reader.read_tags(file_path)
            
            # Convert to the expected format with original/readable/value structure
            result = {}
            for key, tag in tags.tags.items():
                result[tag.original_key or key] = {
                    'original': tag.original_key or key,
                    'readable': key,
                    'value': tag.value
                }
            
            return result
            
        except Exception as e:
            self.logger.error("Error reading all tags from %s: %s", file_path, e)
            return {}
    
    def extract_album_info(self, directory: str) -> Dict[str, str]:
        """
        Extract common album information from audio files in a directory.
        
        Args:
            directory: Directory containing audio files
            
        Returns:
            Dictionary with album metadata
        
        Example:
            Extract album metadata from a folder of audio files::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                album_info = service.extract_album_info('/music/The Beatles/Help!')
                print(album_info)
                # Output: {'artist': 'The Beatles', 'album': 'Help!', 
                #          'date': '1965', 'genre': 'Rock'}
            
            Use album info as defaults for processing::
            
                album_info = service.extract_album_info(folder_path)
                for audio_file in audio_files:
                    file_tags = service.get_file_tags(audio_file)
                    # Use album info as fallback
                    artist = file_tags.get('artist') or album_info.get('artist')
                    album = file_tags.get('album') or album_info.get('album')
        """
        if not self.album_analyzer:
            self.logger.warning("Album analyzer not available")
            return {}
        
        # Import here to avoid circular imports
        from ...conversion import filter_directories
        
        # Get audio files in directory
        audio_files = filter_directories(self.fs_service.list_files(directory, "*"))
        
        if not audio_files:
            self.logger.debug("No audio files found in directory: %s", directory)
            return {}
        
        try:
            album_tags = self.album_analyzer.extract_album_info(directory, audio_files)
            normalized_tags = self.tag_normalizer.normalize_collection(album_tags)
            return normalized_tags.get_standardized_tags()
            
        except Exception as e:
            self.logger.error("Error extracting album info from %s: %s", directory, e)
            return {}
    
    def format_metadata_filename(self, metadata: Dict[str, str], template: str = "{tracknumber} - {title}") -> str:
        """
        Format a filename using metadata and template.
        
        Args:
            metadata: Dictionary with tag data
            template: Format template string
            
        Returns:
            Formatted filename
        
        Example:
            Format filename with track number and title::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                metadata = {'tracknumber': '01', 'title': 'Yesterday', 'artist': 'The Beatles'}
                filename = service.format_metadata_filename(metadata)
                print(filename)
                # Output: '01 - Yesterday'
            
            Custom template with multiple fields::
            
                template = "{artist} - {album} - {tracknumber} - {title}"
                filename = service.format_metadata_filename(metadata, template)
                # Output: 'The Beatles - Help! - 01 - Yesterday'
            
            Handle missing fields gracefully::
            
                metadata = {'title': 'Untitled'}
                filename = service.format_metadata_filename(metadata, "{tracknumber} - {title}")
                # Output: 'Untitled' (missing tracknumber omitted)
        """
        # Convert dict to MediaTagCollection for processing
        tags = {}
        for key, value in metadata.items():
            from ..domain import MediaTag
            tags[key] = MediaTag(key=key, value=str(value))
        
        tag_collection = MediaTagCollection(tags=tags)
        return self.filename_formatter.format_filename(tag_collection, template)
    
    def normalize_tag_value(self, value: str) -> str:
        """
        Normalize a single tag value.
        
        Args:
            value: Tag value to normalize
            
        Returns:
            Normalized value
        """
        from ..domain import MediaTag
        tag = MediaTag(key="temp", value=value)
        normalized = self.tag_normalizer.normalize_tag(tag)
        return normalized.value
    
    def extract_artwork(self, file_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Extract artwork from a media file.
        
        Args:
            file_path: Path to the media file
            output_path: Output path for artwork file
            
        Returns:
            Path to extracted artwork file, or None if not found
        
        Example:
            Extract artwork to default temporary location::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                artwork_path = service.extract_artwork('song.mp3')
                if artwork_path:
                    print(f"Artwork saved to: {artwork_path}")
                    # Use artwork_path for display or processing
                else:
                    print("No artwork found")
            
            Extract artwork to specific location::
            
                artwork_path = service.extract_artwork('song.mp3', 'cover.jpg')
                # Artwork saved as cover.jpg
            
            Extract and display artwork in GUI::
            
                artwork_path = service.extract_artwork(audio_file)
                if artwork_path:
                    pixmap = QPixmap(artwork_path)
                    label.setPixmap(pixmap)
                    os.unlink(artwork_path)  # Clean up temp file
        """
        try:
            artwork = self.artwork_extractor.extract_artwork(file_path)
            if not artwork:
                return None
            
            # Generate output path if not provided
            if not output_path:
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(suffix=artwork.format_extension, delete=False)
                output_path = temp_file.name
                temp_file.close()
            elif not os.path.splitext(output_path)[1]:
                output_path += artwork.format_extension
            
            # Write artwork to file
            with open(output_path, 'wb') as f:
                f.write(artwork.data)
            
            self.logger.info("Extracted artwork saved to %s", output_path)
            return output_path
            
        except Exception as e:
            self.logger.error("Error extracting artwork from %s: %s", file_path, e)
            return None
    
    def find_cover_image(self, directory: str) -> Optional[str]:
        """
        Find a cover image in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            Path to cover image if found, None otherwise
        
        Example:
            Find cover image for album processing::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                cover_path = service.find_cover_image('/music/The Beatles/Help!')
                if cover_path:
                    print(f"Found cover: {cover_path}")
                    # Use for TAF file or display
                else:
                    # Try extracting from audio file
                    audio_files = os.listdir(directory)
                    if audio_files:
                        cover_path = service.extract_artwork(audio_files[0])
        """
        return self.cover_finder.find_cover_image(directory)
    
    def get_file_metadata(self, file_path: str) -> Dict[str, str]:
        """
        Get comprehensive metadata for a file including tags and file info.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with complete metadata
        
        Example:
            Get complete file metadata for processing::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                metadata = service.get_file_metadata('song.mp3')
                print(f"File: {metadata['file_name']}")
                print(f"Size: {metadata['file_size']} bytes")
                print(f"Artist: {metadata.get('artist', 'Unknown')}")
                print(f"Title: {metadata.get('title', 'Unknown')}")
            
            Use metadata for filename generation::
            
                metadata = service.get_file_metadata(audio_file)
                template = "{artist} - {title}"
                output_name = service.format_metadata_filename(metadata, template)
                # Output: 'The Beatles - Yesterday'
        """
        metadata = {}
        
        # Add file information
        if self.fs_service.exists(file_path):
            stat = os.stat(file_path)
            metadata['file_name'] = os.path.basename(file_path)
            metadata['file_size'] = str(stat.st_size)
            metadata['file_path'] = file_path
        
        # Add tag information
        tags = self.get_file_tags(file_path)
        metadata.update(tags)
        
        return metadata
    
    def get_folder_metadata(self, folder_path: str) -> Dict[str, Any]:
        """
        Get metadata for all audio files in a folder.
        
        Args:
            folder_path: Path to folder
            
        Returns:
            Dictionary with folder metadata
        
        Example:
            Get complete folder metadata for batch processing::
            
                service = MediaTagService(tag_mappings, value_replacements,
                                         artwork_names, artwork_extensions, logger)
                folder_meta = service.get_folder_metadata('/music/album')
                print(f"Folder: {folder_meta['folder_path']}")
                print(f"Album: {folder_meta['album_info'].get('album')}")
                print(f"Files: {len(folder_meta['files'])}")
                
                for file_meta in folder_meta['files']:
                    print(f"  - {file_meta['file_name']}: {file_meta.get('title')}")
            
            Use folder metadata for album conversion::
            
                folder_meta = service.get_folder_metadata(album_dir)
                album_name = folder_meta['album_info'].get('album', 'Unknown Album')
                output_file = f"{album_name}.taf"
                
                # Process all files
                for file_meta in folder_meta['files']:
                    process_audio_file(file_meta['file_path'])
        """
        # Import here to avoid circular imports
        from ...conversion import filter_directories
        
        metadata = {
            'folder_path': folder_path,
            'files': [],
            'album_info': {}
        }
        
        # Get all audio files
        audio_files = filter_directories(self.fs_service.list_files(folder_path, "*"))
        
        # Get metadata for each file
        for file_path in audio_files:
            file_metadata = self.get_file_metadata(file_path)
            metadata['files'].append(file_metadata)
        
        # Get album info
        metadata['album_info'] = self.extract_album_info(folder_path)
        
        return metadata