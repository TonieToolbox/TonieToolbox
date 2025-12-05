#!/usr/bin/env python3
"""
TeddyCloud integration adapter.

This module provides concrete implementation of UploadService interface
for integrating with TeddyCloud servers.
"""

import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
import logging
import aiohttp
import aiofiles
from dataclasses import dataclass

from ...application.interfaces.upload_service import UploadService, UploadProgress
from ...domain import ProcessingOptions


@dataclass
class TeddyCloudConnection:
    """Configuration for TeddyCloud server connection."""
    hostname: str
    port: int = 80
    username: Optional[str] = None
    password: Optional[str] = None
    use_https: bool = False
    
    @property
    def base_url(self) -> str:
        """Get base URL for TeddyCloud server."""
        protocol = 'https' if self.use_https else 'http'
        return f"{protocol}://{self.hostname}:{self.port}"


class TeddyCloudAdapter(UploadService):
    """
    Concrete implementation of UploadService for TeddyCloud integration.
    
    This adapter handles all communication with TeddyCloud servers,
    including file uploads, metadata management, and server status checks.
    """
    
    def __init__(self, connection: TeddyCloudConnection, 
                 logger: Optional[logging.Logger] = None):
        """
        Initialize TeddyCloud adapter.
        
        Args:
            connection: TeddyCloud server connection configuration
            logger: Optional logger instance
        """
        self.connection = connection
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def test_connection(self) -> bool:
        """Test connection to TeddyCloud server."""
        try:
            await self._ensure_session()
            
            # Test basic connectivity
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    self.logger.info(f"TeddyCloud connection successful: {data.get('version', 'unknown version')}")
                    return True
                else:
                    self.logger.warning(f"TeddyCloud returned status {response.status}")
                    return False
                    
        except asyncio.TimeoutError:
            self.logger.error("TeddyCloud connection timeout")
            return False
        except Exception as e:
            self.logger.error(f"TeddyCloud connection failed: {str(e)}")
            return False
    
    async def upload_taf_file(self, file_path: Path, tonie_id: str,
                            metadata: Optional[Dict[str, Any]] = None,
                            progress_callback: Optional[Callable[[UploadProgress], None]] = None) -> bool:
        """Upload TAF file to TeddyCloud server."""
        try:
            await self._ensure_authenticated()
            
            self.logger.info(f"Uploading {file_path} to TeddyCloud for Tonie {tonie_id}")
            
            # Prepare upload data
            upload_data = {
                'tonie_id': tonie_id,
                'overwrite': True  # Default behavior
            }
            
            if metadata:
                upload_data.update(metadata)
            
            # Read file for upload
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            
            # Create multipart form data
            data = aiohttp.FormData()
            data.add_field('tonie_id', tonie_id)
            data.add_field('file', file_data, filename=file_path.name, content_type='audio/ogg')
            
            # Add metadata fields
            if metadata:
                for key, value in metadata.items():
                    if key != 'tonie_id':  # Avoid duplicate
                        data.add_field(key, str(value))
            
            # Upload with progress monitoring
            return await self._upload_with_progress(
                data, file_path, progress_callback
            )
            
        except Exception as e:
            self.logger.error(f"TAF upload failed for {file_path}: {str(e)}")
            return False
    
    async def download_tonie_content(self, tonie_id: str, output_path: Path,
                                   progress_callback: Optional[Callable[[UploadProgress], None]] = None) -> bool:
        """Download content from TeddyCloud for specific Tonie."""
        try:
            await self._ensure_authenticated()
            
            self.logger.info(f"Downloading content for Tonie {tonie_id} to {output_path}")
            
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/tonies/{tonie_id}/content",
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes for large files
            ) as response:
                
                if response.status == 200:
                    # Get total size for progress
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    # Download with progress updates
                    async with aiofiles.open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Update progress
                            if progress_callback and total_size > 0:
                                progress = UploadProgress(
                                    current_file=str(output_path),
                                    bytes_transferred=downloaded,
                                    total_bytes=total_size,
                                    transfer_rate=0.0,  # Could calculate this
                                    files_completed=0 if downloaded < total_size else 1,
                                    total_files=1
                                )
                                progress_callback(progress)
                    
                    self.logger.info(f"Download completed: {output_path}")
                    return True
                else:
                    self.logger.error(f"Download failed with status {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Download failed for Tonie {tonie_id}: {str(e)}")
            return False
    
    async def get_tonie_list(self) -> List[Dict[str, Any]]:
        """Get list of Tonies from TeddyCloud."""
        try:
            await self._ensure_authenticated()
            
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/tonies",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    tonies = data.get('tonies', [])
                    self.logger.debug(f"Retrieved {len(tonies)} Tonies from TeddyCloud")
                    return tonies
                else:
                    self.logger.error(f"Failed to get Tonie list: status {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to get Tonie list: {str(e)}")
            return []
    
    async def get_tonie_metadata(self, tonie_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for specific Tonie."""
        try:
            await self._ensure_authenticated()
            
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/tonies/{tonie_id}",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(f"Retrieved metadata for Tonie {tonie_id}")
                    return data
                else:
                    self.logger.warning(f"Tonie {tonie_id} not found or access denied")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get metadata for Tonie {tonie_id}: {str(e)}")
            return None
    
    async def update_tonie_metadata(self, tonie_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for specific Tonie."""
        try:
            await self._ensure_authenticated()
            
            async with self._session.patch(
                f"{self.connection.base_url}/api/v1/tonies/{tonie_id}",
                json=metadata,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status in (200, 204):
                    self.logger.info(f"Updated metadata for Tonie {tonie_id}")
                    return True
                else:
                    self.logger.error(f"Failed to update metadata: status {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to update metadata for Tonie {tonie_id}: {str(e)}")
            return False
    
    async def delete_tonie_content(self, tonie_id: str) -> bool:
        """Delete content for specific Tonie."""
        try:
            await self._ensure_authenticated()
            
            async with self._session.delete(
                f"{self.connection.base_url}/api/v1/tonies/{tonie_id}/content",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status in (200, 204):
                    self.logger.info(f"Deleted content for Tonie {tonie_id}")
                    return True
                else:
                    self.logger.error(f"Failed to delete content: status {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to delete content for Tonie {tonie_id}: {str(e)}")
            return False
    
    async def get_server_status(self) -> Optional[Dict[str, Any]]:
        """Get TeddyCloud server status and configuration."""
        try:
            await self._ensure_session()
            
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/status",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug("Retrieved server status")
                    return data
                else:
                    self.logger.warning(f"Server status request failed: {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get server status: {str(e)}")
            return None
    
    async def search_tonies(self, query: str) -> List[Dict[str, Any]]:
        """Search for Tonies matching query."""
        try:
            await self._ensure_authenticated()
            
            params = {'q': query, 'limit': 100}
            
            async with self._session.get(
                f"{self.connection.base_url}/api/v1/tonies/search",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    self.logger.debug(f"Found {len(results)} Tonies matching '{query}'")
                    return results
                else:
                    self.logger.warning(f"Search failed: status {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {str(e)}")
            return []
    
    async def get_upload_capabilities(self) -> Dict[str, Any]:
        """Get server upload capabilities and limitations."""
        try:
            status = await self.get_server_status()
            if not status:
                return {}
            
            # Extract relevant capability information
            capabilities = {
                'max_file_size': status.get('max_upload_size', 100 * 1024 * 1024),  # 100MB default
                'supported_formats': status.get('supported_formats', ['ogg', 'mp3']),
                'concurrent_uploads': status.get('max_concurrent_uploads', 3),
                'requires_auth': status.get('authentication_required', False)
            }
            
            return capabilities
            
        except Exception as e:
            self.logger.error(f"Failed to get upload capabilities: {str(e)}")
            return {}
    
    async def _ensure_session(self):
        """Ensure HTTP session is created."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers={'User-Agent': 'TonieToolbox/1.0'}
            )
    
    async def _close_session(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _ensure_authenticated(self):
        """Ensure we are authenticated with TeddyCloud if required."""
        await self._ensure_session()
        
        if not self._authenticated and (self.connection.username and self.connection.password):
            await self._authenticate()
    
    async def _authenticate(self):
        """Authenticate with TeddyCloud server."""
        try:
            auth_data = {
                'username': self.connection.username,
                'password': self.connection.password
            }
            
            async with self._session.post(
                f"{self.connection.base_url}/api/v1/auth/login",
                json=auth_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    token = data.get('token')
                    
                    if token:
                        # Add authorization header for future requests
                        self._session.headers.update({
                            'Authorization': f'Bearer {token}'
                        })
                        self._authenticated = True
                        self.logger.info("TeddyCloud authentication successful")
                    else:
                        raise Exception("No token received from authentication")
                else:
                    raise Exception(f"Authentication failed with status {response.status}")
                    
        except Exception as e:
            self.logger.error(f"TeddyCloud authentication failed: {str(e)}")
            raise
    
    async def _upload_with_progress(self, data: aiohttp.FormData, file_path: Path,
                                  progress_callback: Optional[Callable[[UploadProgress], None]]) -> bool:
        """Upload data with progress monitoring."""
        try:
            # Calculate total size (approximate)
            total_size = file_path.stat().st_size
            
            async with self._session.post(
                f"{self.connection.base_url}/api/v1/tonies/upload",
                data=data,
                timeout=aiohttp.ClientTimeout(total=600)  # 10 minutes for large files
            ) as response:
                
                if response.status in (200, 201):
                    # Final progress update
                    if progress_callback:
                        progress = UploadProgress(
                            current_file=str(file_path),
                            bytes_transferred=total_size,
                            total_bytes=total_size,
                            transfer_rate=0.0,
                            files_completed=1,
                            total_files=1
                        )
                        progress_callback(progress)
                    
                    self.logger.info(f"Upload successful: {file_path}")
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Upload failed with status {response.status}: {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Upload error for {file_path}: {str(e)}")
            return False


class TeddyCloudConnectionManager:
    """
    Manager for TeddyCloud connections and configuration.
    
    Handles connection pooling, configuration validation,
    and connection lifecycle management.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize connection manager."""
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._connections: Dict[str, TeddyCloudConnection] = {}
        self._active_adapters: Dict[str, TeddyCloudAdapter] = {}
    
    def add_connection(self, name: str, connection: TeddyCloudConnection):
        """Add named connection configuration."""
        self._connections[name] = connection
        self.logger.info(f"Added TeddyCloud connection '{name}': {connection.hostname}:{connection.port}")
    
    def remove_connection(self, name: str):
        """Remove connection configuration."""
        if name in self._connections:
            del self._connections[name]
            self.logger.info(f"Removed TeddyCloud connection '{name}'")
    
    def get_connection(self, name: str) -> Optional[TeddyCloudConnection]:
        """Get connection configuration by name."""
        return self._connections.get(name)
    
    def list_connections(self) -> List[str]:
        """Get list of available connection names."""
        return list(self._connections.keys())
    
    async def get_adapter(self, name: str) -> Optional[TeddyCloudAdapter]:
        """Get or create adapter for named connection."""
        if name not in self._connections:
            self.logger.error(f"No connection configuration for '{name}'")
            return None
        
        if name not in self._active_adapters:
            connection = self._connections[name]
            adapter = TeddyCloudAdapter(connection, self.logger)
            
            # Test connection before adding to active adapters
            if await adapter.test_connection():
                self._active_adapters[name] = adapter
            else:
                self.logger.error(f"Failed to establish connection '{name}'")
                return None
        
        return self._active_adapters[name]
    
    async def close_all_connections(self):
        """Close all active adapter connections."""
        for name, adapter in self._active_adapters.items():
            try:
                await adapter._close_session()
                self.logger.debug(f"Closed connection '{name}'")
            except Exception as e:
                self.logger.error(f"Error closing connection '{name}': {str(e)}")
        
        self._active_adapters.clear()
    
    def validate_connection_config(self, connection: TeddyCloudConnection) -> List[str]:
        """Validate connection configuration and return any errors."""
        errors = []
        
        if not connection.hostname:
            errors.append("Hostname is required")
        
        if connection.port <= 0 or connection.port > 65535:
            errors.append("Port must be between 1 and 65535")
        
        if connection.username and not connection.password:
            errors.append("Password is required when username is provided")
        
        return errors