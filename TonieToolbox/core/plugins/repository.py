#!/usr/bin/env python3
"""
Plugin repository client for accessing the TonieToolbox community plugin repository.

Handles fetching plugin manifests, searching, and downloading from the community repository.
"""
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
from pathlib import Path
from ..utils import get_logger
from ..config import ConfigManager
from .base import PluginManifest, PluginMetadata, PluginDependencies, PluginDependency, PluginInstallInfo, PluginType
from .trust import TrustManager

logger = get_logger(__name__)


class PluginRepository:
    """
    Client for accessing the TonieToolbox community plugin repository.
    
    Default repository: https://raw.githubusercontent.com/TonieToolbox/tonietoolbox_plugins/main/
    Structure: /manifests/{author}/{plugin_name}/{version}/manifest.json
    
    The repository uses plugin IDs (format: com.author.pluginname) as the primary
    identifier. Directory paths are automatically derived from plugin IDs:
    - Plugin ID: com.tonietoolbox.tonies_loader
    - Directory: manifests/tonietoolbox/tonies_loader/{version}/
    
    Note: Author names are normalized to lowercase for directory structure.
    """
    
    DEFAULT_REPOSITORY_URL = "https://raw.githubusercontent.com/TonieToolbox/tonietoolbox_plugins/main/"
    
    def __init__(self, repository_urls: Optional[List[str]] = None, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the plugin repository client.
        
        Args:
            repository_urls: List of repository URLs to search. If None, uses default.
            config_manager: Configuration manager for syncing verified authors.
        """
        if repository_urls is None:
            repository_urls = [self.DEFAULT_REPOSITORY_URL]
        
        # Normalize URLs to ensure they end with /
        self.repository_urls = [url if url.endswith('/') else url + '/' for url in repository_urls]
        self._manifest_cache: Dict[str, PluginManifest] = {}
        self._config_manager = config_manager
        self._trust_manager = TrustManager(config_manager)
        
        # Sync verified authors on initialization
        self._sync_verified_authors()
        
        logger.info(f"PluginRepository initialized with {len(self.repository_urls)} repositories")
    
    def fetch_manifest(self, plugin_id: str, version: str) -> Optional[PluginManifest]:
        """
        Fetch a specific plugin manifest from the repository.
        
        Args:
            plugin_id: Plugin ID (e.g., "com.tonietoolbox.tonies_loader")
            version: Plugin version
            
        Returns:
            PluginManifest or None if not found
        """
        # Parse plugin ID: com.author.pluginname
        parts = plugin_id.split('.')
        if len(parts) != 3 or parts[0] != 'com':
            logger.error(f"Invalid plugin ID format: {plugin_id} (expected: com.author.pluginname)")
            return None
        
        author = parts[1].lower()  # Normalize to lowercase for directory structure
        plugin_name = parts[2]
        
        cache_key = f"{plugin_id}/{version}"
        
        # Check cache first
        if cache_key in self._manifest_cache:
            logger.debug(f"Using cached manifest for {cache_key}")
            return self._manifest_cache[cache_key]
        
        # Try each repository
        for repo_url in self.repository_urls:
            manifest_url = f"{repo_url}manifests/{author}/{plugin_name}/{version}/manifest.json"
            logger.debug(f"Fetching manifest from {manifest_url}")
            
            try:
                with urllib.request.urlopen(manifest_url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    manifest = self._parse_manifest(data)
                    
                    # Cache the manifest
                    self._manifest_cache[cache_key] = manifest
                    logger.info(f"Fetched manifest for {plugin_id} v{version}")
                    return manifest
                    
            except urllib.error.URLError as e:
                logger.debug(f"Failed to fetch from {manifest_url}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error parsing manifest from {manifest_url}: {e}")
                continue
        
        logger.warning(f"Manifest not found: {plugin_id} v{version}")
        return None
    
    def get_plugin_versions(self, plugin_id: str) -> List[str]:
        """
        Get all available versions of a plugin.
        
        Args:
            plugin_id: Plugin ID (e.g., "com.tonietoolbox.tonies_loader")
            
        Returns:
            List of version strings (e.g., ["1.0.0", "1.1.0", "2.0.0"])
        """
        # This requires listing directory contents which isn't directly supported
        # by raw.githubusercontent.com. We need to use GitHub API or maintain
        # a versions index file.
        
        # For now, we'll try common versions or implement a versions.json file
        logger.warning("get_plugin_versions not yet fully implemented - requires versions.json")
        return []
    
    def search_plugins(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[PluginType] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        refresh_trust: bool = True
    ) -> List[PluginManifest]:
        """
        Search for plugins matching criteria.
        
        Args:
            query: Search term (matches name, description)
            plugin_type: Filter by plugin type
            tags: Filter by tags
            author: Filter by author
            refresh_trust: Whether to refresh verified authors list (default: True)
            
        Returns:
            List of matching plugin manifests
        """
        # Refresh verified authors list when searching
        if refresh_trust:
            self._sync_verified_authors()
        
        # This requires an index file in the repository
        # We'll implement this by fetching an index.json file
        
        results = []
        for repo_url in self.repository_urls:
            index_url = f"{repo_url}index.json"
            
            try:
                with urllib.request.urlopen(index_url, timeout=10) as response:
                    index_data = json.loads(response.read().decode('utf-8'))
                    
                    for entry in index_data.get('plugins', []):
                        # Get latest version from versions array
                        versions = entry.get('versions', [])
                        if not versions:
                            logger.warning(f"Plugin {entry.get('id')} has no versions array")
                            continue
                        
                        latest_version = versions[0]
                        
                        # Fetch full manifest using plugin ID
                        manifest = self.fetch_manifest(
                            entry['id'],
                            latest_version
                        )
                        
                        if manifest and self._matches_filters(manifest, query, plugin_type, tags, author):
                            results.append(manifest)
                            
            except Exception as e:
                logger.debug(f"Failed to fetch index from {index_url}: {e}")
                continue
        
        logger.info(f"Search returned {len(results)} plugins")
        return results
    
    def get_latest_version(self, plugin_id: str) -> Optional[str]:
        """
        Get the latest version number for a plugin.
        
        Args:
            plugin_id: Plugin ID (e.g., "com.tonietoolbox.tonies_loader")
            
        Returns:
            Latest version string or None
        """
        # Check index for latest version (first item in versions array)
        for repo_url in self.repository_urls:
            index_url = f"{repo_url}index.json"
            
            try:
                with urllib.request.urlopen(index_url, timeout=10) as response:
                    index_data = json.loads(response.read().decode('utf-8'))
                    
                    for entry in index_data.get('plugins', []):
                        if entry['id'] == plugin_id:
                            # Get first version from versions array (already sorted newest first)
                            versions = entry.get('versions', [])
                            if versions:
                                return versions[0]
                            return None
                            
            except Exception as e:
                logger.debug(f"Failed to fetch index: {e}")
                continue
        
        return None
    
    def _parse_manifest(self, data: Dict[str, Any]) -> PluginManifest:
        """Parse JSON data into PluginManifest object."""
        # Parse install info
        install_info = None
        if 'install' in data:
            install_data = data['install']
            install_info = PluginInstallInfo(
                source_type=install_data['type'],
                source_url=install_data.get('url'),
                branch=install_data.get('branch'),
                checksum=install_data.get('checksum'),
                checksum_algorithm=install_data.get('checksum_algorithm', 'sha512'),
                subdirectory=install_data.get('subdir')
            )
        
        # Parse dependencies
        dependencies_list = []
        if 'dependencies' in data:
            dep_data = data['dependencies']
            for dep in dep_data.get('plugins', []):
                if isinstance(dep, dict) and 'id' in dep:
                    dependencies_list.append(dep['id'])
                elif isinstance(dep, str):
                    dependencies_list.append(dep)
        
        # Parse metadata
        author = data['author']
        
        # Determine trust level based on author
        trust_level = self._trust_manager.get_trust_level(author, data['id'])
        
        metadata = PluginMetadata(
            id=data['id'],
            name=data['name'],
            version=data['version'],
            author=author,
            description=data['description'],
            plugin_type=PluginType(data['plugin_type']),
            dependencies=dependencies_list,
            homepage=data.get('homepage'),
            license=data.get('license'),
            min_tonietoolbox_version=data.get('min_tonietoolbox_version'),
            max_tonietoolbox_version=data.get('max_tonietoolbox_version'),
            tags=data.get('tags', []),
            repository=data.get('repository'),
            changelog_url=data.get('changelog_url'),
            screenshots=data.get('screenshots', []),
            verified=data.get('verified', False),
            trust_level=trust_level,
            display_name=data.get('display_name'),
            install_info=install_info
        )
        
        return PluginManifest(
            metadata=metadata,
            config_schema=data.get('config_schema', {}),
            permissions=data.get('permissions', []),
            entry_point=data.get('entry_point')
        )
    
    def _matches_filters(
        self,
        manifest: PluginManifest,
        query: Optional[str],
        plugin_type: Optional[PluginType],
        tags: Optional[List[str]],
        author: Optional[str]
    ) -> bool:
        """Check if manifest matches filter criteria."""
        # Filter by author
        if author and manifest.metadata.author != author:
            return False
        
        # Filter by plugin type
        if plugin_type and manifest.metadata.plugin_type != plugin_type:
            return False
        
        # Filter by tags
        if tags:
            manifest_tags = set(manifest.metadata.tags)
            if not any(tag in manifest_tags for tag in tags):
                return False
        
        # Filter by query (name or description)
        if query:
            query_lower = query.lower()
            if (query_lower not in manifest.metadata.name.lower() and
                query_lower not in manifest.metadata.description.lower()):
                return False
        
        return True
    
    def _sync_verified_authors(self) -> None:
        """
        Sync verified authors from repository index.json to local config.
        
        This allows the repository maintainer to promote authors to verified status
        without requiring a new TonieToolbox release.
        """
        if not self._config_manager:
            logger.debug("No config manager - skipping verified authors sync")
            return
        
        for repo_url in self.repository_urls:
            index_url = f"{repo_url}index.json"
            
            try:
                with urllib.request.urlopen(index_url, timeout=10) as response:
                    index_data = json.loads(response.read().decode('utf-8'))
                    
                    # Get verified authors from index
                    repo_verified = index_data.get('verified_authors', [])
                    
                    if not repo_verified:
                        logger.debug(f"No verified authors in {repo_url}")
                        continue
                    
                    # Get current local verified authors
                    current_verified = set(self._config_manager.plugins.verified_authors)
                    repo_verified_set = set(repo_verified)
                    
                    # Add any new verified authors from repository
                    new_authors = repo_verified_set - current_verified
                    if new_authors:
                        for author in new_authors:
                            self._trust_manager.add_verified_author(author)
                        logger.info(f"Added {len(new_authors)} verified authors from repository: {', '.join(new_authors)}")
                    else:
                        logger.debug(f"No new verified authors to sync from {repo_url}")
                    
                    # Successfully synced from at least one repository
                    return
                    
            except urllib.error.URLError as e:
                logger.debug(f"Failed to fetch index from {index_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error syncing verified authors from {index_url}: {e}")
                continue
        
        logger.debug("Verified authors sync completed")
    
    def refresh_trust_list(self) -> bool:
        """
        Manually refresh the verified authors list from repositories.
        
        Returns:
            True if successfully synced from at least one repository
        """
        logger.info("Manually refreshing verified authors list...")
        try:
            self._sync_verified_authors()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh trust list: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Clear the manifest cache."""
        self._manifest_cache.clear()
        logger.debug("Manifest cache cleared")
