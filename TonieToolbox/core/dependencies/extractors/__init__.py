#!/usr/bin/python3
"""
Archive Extractors for Dependency Packages.

This module provides extraction functionality for various archive formats including ZIP, TAR,
TAR.GZ, TAR.BZ2, and TAR.XZ. Handles decompression with progress tracking, directory structure
preservation, and error handling. Used for extracting downloaded dependency binaries and tools
like FFmpeg from compressed archives.
"""
import os
import sys
import tempfile
import shutil
import zipfile
import tarfile
from typing import List
from tqdm.auto import tqdm
from ..base import BaseExtractor
from ...utils import get_logger

logger = get_logger(__name__)


class ZipExtractor(BaseExtractor):
    """Extractor for ZIP archives."""
    
    def can_extract(self, archive_path: str) -> bool:
        """Check if this is a ZIP file."""
        return archive_path.lower().endswith('.zip')
    
    def extract(self, archive_path: str, extract_dir: str) -> bool:
        """Extract a ZIP archive."""
        try:
            self.logger.info("Extracting ZIP archive: %s", archive_path)
            os.makedirs(extract_dir, exist_ok=True)
            
            temp_extract_dir = tempfile.mkdtemp(prefix="tonietoolbox_extract_")
            self.logger.debug("Using temporary extraction directory: %s", temp_extract_dir)
            
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                files_extracted = zip_ref.namelist()
                total_size = sum(info.file_size for info in zip_ref.infolist())
                
                self.logger.debug("ZIP contains %d files, total size: %d bytes", 
                                len(files_extracted), total_size)                
                if total_size > 50*1024*1024:  # 50MB threshold
                    with tqdm(
                        total=total_size, 
                        unit='B', 
                        unit_scale=True, 
                        desc="Extracting ZIP"
                    ) as pbar:
                        for file in zip_ref.infolist():
                            zip_ref.extract(file, temp_extract_dir)
                            pbar.update(file.file_size)
                    print("")  # Add newline after progress
                else:
                    zip_ref.extractall(temp_extract_dir)
            
            # Move extracted contents to final location
            self._move_extracted_contents(temp_extract_dir, extract_dir, archive_path)
            
            # Cleanup
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            
            self.logger.info("ZIP extraction completed successfully")
            return True
            
        except zipfile.BadZipFile as e:
            self.logger.error("Bad ZIP file: %s", str(e))
            return False
        except Exception as e:
            self.logger.error("Failed to extract ZIP %s: %s", archive_path, e)
            return False


class TarExtractor(BaseExtractor):
    """Extractor for TAR archives (including compressed variants)."""
    
    def can_extract(self, archive_path: str) -> bool:
        """Check if this is a TAR file."""
        lower_path = archive_path.lower()
        return (lower_path.endswith(('.tar', '.tar.gz', '.tgz', '.tar.xz', '.txz')) or
                lower_path.endswith('.tar.bz2'))
    
    def extract(self, archive_path: str, extract_dir: str) -> bool:
        """Extract a TAR archive."""
        try:
            self.logger.info("Extracting TAR archive: %s", archive_path)
            os.makedirs(extract_dir, exist_ok=True)
            
            temp_extract_dir = tempfile.mkdtemp(prefix="tonietoolbox_extract_")
            self.logger.debug("Using temporary extraction directory: %s", temp_extract_dir)
            
            # Determine compression mode
            mode = self._get_tar_mode(archive_path)
            
            with tarfile.open(archive_path, mode) as tar_ref:
                files_extracted = tar_ref.getnames()
                self.logger.debug("TAR contains %d files", len(files_extracted))
                if sys.version_info >= (3, 12):
                    tar_ref.extractall(path=temp_extract_dir, filter='data')
                else:
                    tar_ref.extractall(path=temp_extract_dir)
            
            # Move extracted contents to final location
            self._move_extracted_contents(temp_extract_dir, extract_dir, archive_path)
            
            # Cleanup
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            
            self.logger.info("TAR extraction completed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed to extract TAR %s: %s", archive_path, e)
            return False
    
    def _get_tar_mode(self, archive_path: str) -> str:
        """Determine the appropriate mode for opening the TAR file."""
        lower_path = archive_path.lower()
        
        if lower_path.endswith(('.tar.gz', '.tgz')):
            return 'r:gz'
        elif lower_path.endswith(('.tar.xz', '.txz')):
            return 'r:xz'
        elif lower_path.endswith('.tar.bz2'):
            return 'r:bz2'
        else:
            return 'r'


class ExtractorManager:
    """Manager for handling different archive formats."""
    
    def __init__(self):
        self.extractors = [
            ZipExtractor(),
            TarExtractor()
        ]
        self.logger = get_logger(f"{__name__}.ExtractorManager")
    
    def extract_archive(self, archive_path: str, extract_dir: str) -> bool:
        """
        Extract an archive using the appropriate extractor.
        
        Args:
            archive_path: Path to the archive file
            extract_dir: Directory to extract to
            
        Returns:
            bool: True if extraction successful, False otherwise
        """
        for extractor in self.extractors:
            if extractor.can_extract(archive_path):
                self.logger.debug("Using %s for %s", 
                                extractor.__class__.__name__, archive_path)
                success = extractor.extract(archive_path, extract_dir)
                
                if success:
                    # Remove archive file after successful extraction
                    try:
                        self.logger.debug("Removing archive file: %s", archive_path)
                        os.remove(archive_path)
                        self.logger.debug("Archive file removed successfully")
                    except Exception as e:
                        self.logger.warning("Failed to remove archive file: %s (error: %s)", 
                                          archive_path, e)
                
                return success
        
        self.logger.error("Unsupported archive format: %s", archive_path)
        return False
    
    def _move_extracted_contents(self, temp_extract_dir: str, extract_dir: str, archive_path: str):
        """Move extracted contents to the final directory, handling special cases."""
        dependency_name = os.path.basename(extract_dir)
        
        # Special handling for FFmpeg archives
        if dependency_name == 'ffmpeg':
            self._handle_ffmpeg_extraction(temp_extract_dir, extract_dir)
        else:
            self._handle_generic_extraction(temp_extract_dir, extract_dir)
    
    def _handle_ffmpeg_extraction(self, temp_extract_dir: str, extract_dir: str):
        """Handle FFmpeg-specific extraction logic."""
        # Look for nested FFmpeg directories
        ffmpeg_patterns = [
            "ffmpeg-master-latest-win64-gpl",
            "ffmpeg-master-latest-linux64-gpl"
        ]
        
        for pattern in ffmpeg_patterns:
            nested_path = os.path.join(temp_extract_dir, pattern, "bin")
            if os.path.exists(nested_path):
                self.logger.debug("Found nested FFmpeg bin directory: %s", nested_path)
                for file in os.listdir(nested_path):
                    src = os.path.join(nested_path, file)
                    dst = os.path.join(extract_dir, file)
                    self.logger.debug("Moving %s to %s", src, dst)
                    shutil.move(src, dst)
                return
        
        # Look for any bin directory in the extracted files
        for root, dirs, _ in os.walk(temp_extract_dir):
            if "bin" in dirs:
                bin_dir = os.path.join(root, "bin")
                self.logger.debug("Found nested bin directory: %s", bin_dir)
                for file in os.listdir(bin_dir):
                    src = os.path.join(bin_dir, file)
                    dst = os.path.join(extract_dir, file)
                    self.logger.debug("Moving %s to %s", src, dst)
                    shutil.move(src, dst)
                return
        
        # Fallback: move all files from temp directory
        self._handle_generic_extraction(temp_extract_dir, extract_dir)
    
    def _handle_generic_extraction(self, temp_extract_dir: str, extract_dir: str):
        """Handle generic extraction by moving all files."""
        self.logger.debug("Moving all files from temp directory")
        for item in os.listdir(temp_extract_dir):
            src = os.path.join(temp_extract_dir, item)
            dst = os.path.join(extract_dir, item)
            
            if os.path.isfile(src):
                self.logger.debug("Moving file %s to %s", src, dst)
                shutil.move(src, dst)
            else:
                self.logger.debug("Moving directory %s to %s", src, dst)
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)


# Add the _move_extracted_contents method to BaseExtractor
BaseExtractor._move_extracted_contents = ExtractorManager._move_extracted_contents
BaseExtractor._handle_ffmpeg_extraction = ExtractorManager._handle_ffmpeg_extraction
BaseExtractor._handle_generic_extraction = ExtractorManager._handle_generic_extraction