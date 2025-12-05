#!/usr/bin/python3
"""
HTTP downloader implementation.
"""
import os
import sys
import tempfile
import concurrent.futures
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm.auto import tqdm
import shutil
from typing import Optional
from ..base import BaseDownloader
from ...config import get_config_manager

# Default user agent for HTTP requests
DEFAULT_USER_AGENT = "TonieToolbox/2.0"
from ...utils import get_logger

logger = get_logger(__name__)


class HttpDownloader(BaseDownloader):
    """HTTP downloader with multipart support and retry logic."""
    
    def __init__(self):
        super().__init__()
        self.config_manager = get_config_manager()
        self.session = self._create_session()
    
    def _get_network_setting(self, key: str, default_value):
        """Helper to get network settings with fallback to defaults."""
        setting_key = f"dependencies.network.{key}"
        try:
            return self.config_manager.get_setting(setting_key)
        except:
            return default_value
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry capabilities."""
        session = requests.Session()
        retry_strategy = Retry(
            total=self._get_network_setting('max_retries', 3),
            backoff_factor=self._get_network_setting('retry_backoff', 0.3),
            status_forcelist=[500, 502, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _configure_tqdm(self) -> dict:
        """Configure tqdm for various environments."""
        is_notebook = 'ipykernel' in sys.modules
        tqdm.monitor_interval = 0
        return {
            'file': sys.stdout,
            'leave': True,
            'dynamic_ncols': True,
            'mininterval': 0.5,
            'smoothing': 0.2,
            'ncols': 100 if not is_notebook else None,
            'disable': False
        }
    
    def download(self, url: str, destination: str, **kwargs) -> bool:
        """
        Download a file using single-threaded approach.
        
        Args:
            url: The URL to download from
            destination: Local path to save the file
            **kwargs: Additional options (chunk_size, timeout, use_tqdm)
            
        Returns:
            bool: True if download successful, False otherwise
        """
        chunk_size = kwargs.get('chunk_size', 8192)
        timeout = kwargs.get('timeout', self._get_network_setting('connection_timeout', 30))
        use_tqdm = kwargs.get('use_tqdm', True)
        
        try:
            self.logger.info("Downloading %s to %s", url, destination)
            headers = {'User-Agent': DEFAULT_USER_AGENT}
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
            
            # Get file size
            head_response = self.session.head(url, headers=headers, timeout=timeout)
            head_response.raise_for_status()
            file_size = int(head_response.headers.get('Content-Length', 0))
            self.logger.debug("File size: %d bytes", file_size)
            
            # Download with streaming
            response = self.session.get(url, headers=headers, stream=True, timeout=timeout)
            response.raise_for_status()
            
            desc = os.path.basename(destination)
            if len(desc) > 25:
                desc = desc[:22] + "..."
            
            with open(destination, 'wb') as out_file:
                if use_tqdm and file_size > 0:
                    pbar = tqdm(
                        total=file_size, 
                        unit='B', 
                        unit_scale=True, 
                        desc=desc, 
                        **self._configure_tqdm()
                    )
                    try:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if not chunk:
                                continue
                            out_file.write(chunk)
                            pbar.update(len(chunk))
                    finally:
                        pbar.close()
                        print("")  # Add newline after progress bar
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        downloaded += len(chunk)
                        out_file.write(chunk)
                        if file_size > 0:
                            percent = downloaded * 100 / file_size
                            self.logger.debug("Download progress: %.1f%%", percent)
            
            self.logger.info("Download completed successfully")
            return True
            
        except requests.exceptions.SSLError as e:
            self.logger.error("Failed to download %s: SSL Error: %s", url, e)
            if sys.platform == 'darwin':
                self.logger.error("SSL certificate verification failed on macOS. This is a known issue.")
                self.logger.error("You can solve this by running: /Applications/Python 3.x/Install Certificates.command")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to download %s: %s", url, e)
            return False
        except Exception as e:
            self.logger.error("Unexpected error downloading %s: %s", url, e)
            return False
    
    def download_multipart(self, url: str, destination: str, **kwargs) -> bool:
        """
        Download a file using multiple concurrent connections.
        
        Args:
            url: The URL to download from  
            destination: Local path to save the file
            **kwargs: Additional options (num_parts, chunk_size, timeout)
            
        Returns:
            bool: True if download successful, False otherwise
        """
        num_parts = kwargs.get('num_parts', 4)
        chunk_size = kwargs.get('chunk_size', 8192)
        timeout = kwargs.get('timeout', self._get_network_setting('connection_timeout', 30))
        
        try:
            self.logger.info("Starting multi-part download of %s with %d parts", url, num_parts)
            headers = {'User-Agent': DEFAULT_USER_AGENT}
            
            # Get file size and check if server supports range requests
            response = self.session.head(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            file_size = int(response.headers.get('Content-Length', 0))
            if file_size <= 0:
                self.logger.warning("Multi-part download requested but Content-Length not available, falling back to regular download")
                return self.download(url, destination, **kwargs)
            
            if file_size < num_parts * 1024 * 1024 * 5:  # 5MB per part minimum
                self.logger.debug("File size too small for efficient multi-part download, using regular download")
                return self.download(url, destination, **kwargs)
            
            # Calculate byte ranges for each part
            part_size = file_size // num_parts
            ranges = [(i * part_size, min((i + 1) * part_size - 1, file_size - 1)) 
                     for i in range(num_parts)]
            
            # Ensure last part covers any remaining bytes
            if ranges[-1][1] < file_size - 1:
                ranges[-1] = (ranges[-1][0], file_size - 1)
            
            # Create temporary directory for parts
            temp_dir = tempfile.mkdtemp(prefix="tonietoolbox_download_")
            part_files = [os.path.join(temp_dir, f"part_{i}") for i in range(num_parts)]
            
            def download_part(part_idx: int) -> bool:
                """Download a single part of the file."""
                start, end = ranges[part_idx]
                part_path = part_files[part_idx]
                headers_with_range = headers.copy()
                headers_with_range['Range'] = f'bytes={start}-{end}'
                part_size_bytes = end - start + 1
                
                try:
                    response = self.session.get(url, headers=headers_with_range, 
                                              stream=True, timeout=timeout)
                    response.raise_for_status()
                    
                    desc = f"Part {part_idx+1}/{num_parts}"
                    with tqdm(
                        total=part_size_bytes, 
                        unit='B', 
                        unit_scale=True, 
                        desc=desc, 
                        position=part_idx,
                        **self._configure_tqdm()
                    ) as pbar:
                        with open(part_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=chunk_size):
                                if not chunk:
                                    continue
                                f.write(chunk)
                                pbar.update(len(chunk))
                    return True
                    
                except Exception as e:
                    self.logger.error("Error downloading part %d: %s", part_idx, str(e))
                    return False
            
            # Download all parts concurrently
            self.logger.info("Starting concurrent download of %d parts...", num_parts)
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_parts) as executor:
                futures = [executor.submit(download_part, i) for i in range(num_parts)]
                all_successful = all(future.result() for future in concurrent.futures.as_completed(futures))
            
            if not all_successful:
                self.logger.error("One or more parts failed to download")
                self._cleanup_temp_files(part_files, temp_dir)
                return False
            
            # Combine parts into final file
            self.logger.info("All parts downloaded successfully, combining into final file")
            with open(destination, 'wb') as outfile:
                for part_file in part_files:
                    with open(part_file, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)
                    os.remove(part_file)
            
            os.rmdir(temp_dir)
            self.logger.info("Multi-part download completed successfully")
            return True
            
        except Exception as e:
            self.logger.error("Failed multi-part download: %s", str(e))
            self.logger.info("Falling back to regular download method")
            return self.download(url, destination, **kwargs)
    
    def smart_download(self, url: str, destination: str, **kwargs) -> bool:
        """
        Intelligently choose between single and multi-part download.
        
        Args:
            url: The URL to download from
            destination: Local path to save the file
            **kwargs: Additional options
            
        Returns:
            bool: True if download successful, False otherwise
        """
        use_multipart = kwargs.get('use_multipart', True)
        min_size_for_multipart = kwargs.get('min_size_for_multipart', 10485760)
        
        try:
            if not use_multipart:
                return self.download(url, destination, **kwargs)
            
            # Check file size to determine download method
            response = self.session.head(url, timeout=30)
            file_size = int(response.headers.get('Content-Length', 0))
            
            if file_size >= min_size_for_multipart and use_multipart:
                self.logger.info("File size (%d bytes) is suitable for multi-part download", file_size)
                print(f"Starting multi-part download of {os.path.basename(destination)} ({file_size/1024/1024:.1f} MB)")
                return self.download_multipart(url, destination, **kwargs)
            else:
                self.logger.debug("Using standard download method (file size: %d bytes)", file_size)
                return self.download(url, destination, **kwargs)
                
        except Exception as e:
            self.logger.warning("Error determining download method: %s, falling back to standard download", e)
            return self.download(url, destination, **kwargs)
    
    def download_with_mirrors(self, url: str, destination: str, mirrors: list = None, **kwargs) -> bool:
        """
        Try downloading from primary URL and fallback to mirrors.
        
        Args:
            url: Primary URL to download from
            destination: Local path to save the file
            mirrors: List of mirror URLs to try if primary fails
            **kwargs: Additional options
            
        Returns:
            bool: True if download successful from any source, False otherwise
        """
        self.logger.debug("Starting download with primary URL and %s mirrors", 
                         "0" if mirrors is None else len(mirrors))
        
        # Try primary URL
        if self.smart_download(url, destination, **kwargs):
            self.logger.debug("Download successful from primary URL")
            return True
        
        # Try mirrors if primary failed
        if mirrors:
            for i, mirror_url in enumerate(mirrors, 1):
                self.logger.info("Primary download failed, trying mirror %d of %d", 
                                i, len(mirrors))
                if self.smart_download(mirror_url, destination, **kwargs):
                    self.logger.info("Download successful from mirror %d", i)
                    return True
        
        self.logger.error("All download attempts failed")
        return False
    
    def supports_multipart(self) -> bool:
        """HTTP downloader supports multipart downloads."""
        return True
    
    def _cleanup_temp_files(self, part_files: list, temp_dir: str):
        """Clean up temporary files and directory."""
        try:
            for part_file in part_files:
                if os.path.exists(part_file):
                    os.remove(part_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            self.logger.warning("Failed to cleanup temporary files: %s", e)