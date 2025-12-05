#!/usr/bin/env python3
"""
Base plugin classes and interfaces for the TonieToolbox plugin system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path
from enum import Enum
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from threading import Thread, Lock
import time


class PluginType(Enum):
    """Types of plugins supported by TonieToolbox."""
    GUI = "gui"
    PROCESSOR = "processor"
    INTEGRATION = "integration"
    TOOL = "tool"
    THEME = "theme"
    LANGUAGE = "language"


class PluginSource(Enum):
    """Plugin installation source."""
    BUILTIN = "builtin"      # Core plugins shipped with application
    COMMUNITY = "community"  # User-installed from marketplace
    LOCAL = "local"          # User-developed local plugins


@dataclass
class PluginDependency:
    """Represents a plugin dependency with version constraints."""
    plugin_id: str
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    optional: bool = False


@dataclass
class PluginDependencies:
    """Container for plugin dependencies."""
    plugins: List[PluginDependency] = field(default_factory=list)
    python_packages: List[str] = field(default_factory=list)
    system_packages: List[str] = field(default_factory=list)


@dataclass
class PluginInstallInfo:
    """Information about plugin installation source."""
    source_type: str  # "git", "archive", "local"
    source_url: Optional[str] = None
    branch: Optional[str] = None
    commit: Optional[str] = None  # Git commit SHA (for git type)
    checksum: Optional[str] = None  # File checksum (for archive type)
    checksum_algorithm: str = "sha256"  # "sha256" or "sha512"
    subdirectory: Optional[str] = None


@dataclass
class PluginMetadata:
    """Metadata about a plugin."""
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str] = field(default_factory=list)
    homepage: Optional[str] = None
    license: Optional[str] = None
    min_tonietoolbox_version: Optional[str] = None
    max_tonietoolbox_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    repository: Optional[str] = None
    changelog_url: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
    verified: bool = False
    trust_level: str = "community"  # "official", "verified", "community"
    display_name: Optional[str] = None
    install_info: Optional[PluginInstallInfo] = None


@dataclass
class PluginManifest:
    """Plugin manifest containing metadata and configuration."""
    metadata: PluginMetadata
    config_schema: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    entry_point: Optional[str] = None


class PluginContext:
    """Context provided to plugins during initialization."""
    
    # Class-level shared services registry (shared across all plugins)
    _shared_services: Dict[str, Any] = {}
    
    def __init__(
        self,
        app_version: str,
        config_manager,
        event_bus,
        logger,
        plugin_dir: Path,
        translation_manager=None
    ):
        """
        Initialize plugin context.
        
        Args:
            app_version: TonieToolbox version
            config_manager: Configuration manager instance
            event_bus: Event bus for pub/sub
            logger: Logger instance
            plugin_dir: Directory where plugin is located
            translation_manager: Translation manager for i18n support
        """
        self.app_version = app_version
        self.config_manager = config_manager
        self.event_bus = event_bus
        self.logger = logger
        self.plugin_dir = plugin_dir
        self.translation_manager = translation_manager
        self._resources: Dict[str, Any] = {}
        self._plugin_namespace: Optional[str] = None
        self._background_tasks: Dict[str, Thread] = {}
        self._task_lock = Lock()
        self._plugin_manager: Any = None  # Will be set by manager
        self._plugin_registry: Any = None  # Will be set by manager
    
    def register_resource(self, key: str, resource: Any) -> None:
        """Register a resource that will be cleaned up on plugin unload."""
        self._resources[key] = resource
    
    def get_resource(self, key: str) -> Optional[Any]:
        """Get a registered resource."""
        return self._resources.get(key)
    
    def register_service(self, service_name: str, service_instance: Any) -> None:
        """
        Register a shared service accessible by all plugins.
        
        Args:
            service_name: Unique service identifier
            service_instance: Service instance to register
        """
        PluginContext._shared_services[service_name] = service_instance
        self.logger.info(f"Registered shared service: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """
        Get a shared service by name.
        
        Args:
            service_name: Service identifier
            
        Returns:
            Service instance or None if not found
        """
        return PluginContext._shared_services.get(service_name)
    
    def get_plugin_service(self, service_name: str) -> Optional[Any]:
        """
        Alias for get_service() with clearer naming.
        
        Args:
            service_name: Service identifier
            
        Returns:
            Service instance or None if not found
            
        Example:
            tonies_service = context.get_plugin_service('tonies_loader')
        """
        return self.get_service(service_name)
    
    def cleanup_resources(self) -> None:
        """Clean up all registered resources."""
        # Cancel background tasks
        self._cancel_all_tasks()
        
        # Clean up registered resources
        for resource in self._resources.values():
            if hasattr(resource, 'cleanup'):
                try:
                    resource.cleanup()
                except Exception as e:
                    self.logger.error(f"Error cleaning up resource: {e}")
        self._resources.clear()
    
    def set_plugin_namespace(self, plugin_id: str) -> None:
        """
        Set the plugin namespace for translations.
        
        This should be called automatically by the plugin manager during initialization.
        
        Args:
            plugin_id: Plugin identifier to use as namespace
        """
        self._plugin_namespace = plugin_id
        self.logger.debug(f"Plugin namespace set to: {plugin_id}")
    
    def tr(self, *keys, **kwargs) -> str:
        """
        Plugin-namespaced translation convenience method.
        
        Automatically prefixes translation keys with the plugin namespace.
        
        Args:
            *keys: Translation key path (will be prefixed with plugin_id)
            **kwargs: Format parameters for string formatting
            
        Returns:
            Translated string
            
        Example:
            # In plugin with id "tonies_viewer":
            context.tr("viewer", "title")  # Resolves to "tonies_viewer.viewer.title"
            context.tr("error", "not_found", item="Tonie")  # With formatting
        """
        if not self.translation_manager:
            # Fallback if translation manager not available
            return '.'.join(str(k) for k in keys)
        
        # Build full key path with namespace
        if self._plugin_namespace:
            full_keys = (self._plugin_namespace,) + keys
        else:
            full_keys = keys
        
        return self.translation_manager.translate(*full_keys, **kwargs)
    
    def get_cache_dir(self, plugin_id: Optional[str] = None, ensure_exists: bool = True) -> Path:
        """
        Get the cache directory for this plugin.
        
        Provides a centralized, standardized location for plugin cache data.
        Cache directory structure: ~/.tonietoolbox/cache/{plugin_name}/
        
        Args:
            plugin_id: Optional plugin ID override (uses _plugin_namespace if not provided)
            ensure_exists: Create directory if it doesn't exist (default: True)
            
        Returns:
            Path to plugin-specific cache directory
            
        Example:
            # In plugin with id "com.tonietoolbox.tonies_loader":
            cache_dir = context.get_cache_dir()  # ~/.tonietoolbox/cache/tonies_loader/
            cache_file = cache_dir / "data.json"
        """
        # Use provided plugin_id or fall back to namespace
        pid = plugin_id or self._plugin_namespace
        if not pid:
            raise ValueError("Plugin ID not set. Call set_plugin_namespace() first or provide plugin_id.")
        
        # Extract plugin name from ID (com.author.plugin_name -> plugin_name)
        parts = pid.split('.')
        if len(parts) < 3:
            raise ValueError(f"Invalid plugin ID format: {pid} (expected: com.author.plugin_name)")
        
        plugin_name = parts[-1]  # Last part is the plugin name
        
        # Get base cache directory from config or use default
        if self.config_manager:
            try:
                config_dir = Path(self.config_manager.get_setting('paths.config_dir') or Path.home() / '.tonietoolbox')
                cache_base = config_dir / 'cache'
            except Exception as e:
                self.logger.debug(f"Could not get cache dir from config: {e}")
                cache_base = Path.home() / '.tonietoolbox' / 'cache'
        else:
            cache_base = Path.home() / '.tonietoolbox' / 'cache'
        
        # Create plugin-specific cache directory
        cache_dir = cache_base / plugin_name
        cache_dir = cache_dir.expanduser()
        
        if ensure_exists:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Cache directory for {pid}: {cache_dir}")
        
        return cache_dir
    
    def get_data_dir(self, plugin_id: Optional[str] = None, ensure_exists: bool = True) -> Path:
        """
        Get the data directory for this plugin.
        
        Provides a centralized, standardized location for plugin persistent data.
        Data directory structure: ~/.tonietoolbox/data/{plugin_name}/
        
        Use this for persistent data that shouldn't be in cache (e.g., user settings,
        downloaded content, databases).
        
        Args:
            plugin_id: Optional plugin ID override (uses _plugin_namespace if not provided)
            ensure_exists: Create directory if it doesn't exist (default: True)
            
        Returns:
            Path to plugin-specific data directory
            
        Example:
            # In plugin with id "com.tonietoolbox.tonies_viewer":
            data_dir = context.get_data_dir()  # ~/.tonietoolbox/data/tonies_viewer/
            db_file = data_dir / "favorites.db"
        """
        # Use provided plugin_id or fall back to namespace
        pid = plugin_id or self._plugin_namespace
        if not pid:
            raise ValueError("Plugin ID not set. Call set_plugin_namespace() first or provide plugin_id.")
        
        # Extract plugin name from ID (com.author.plugin_name -> plugin_name)
        parts = pid.split('.')
        if len(parts) < 3:
            raise ValueError(f"Invalid plugin ID format: {pid} (expected: com.author.plugin_name)")
        
        plugin_name = parts[-1]  # Last part is the plugin name
        
        # Get base data directory from config or use default
        if self.config_manager:
            try:
                config_dir = Path(self.config_manager.get_setting('paths.config_dir') or Path.home() / '.tonietoolbox')
                data_base = config_dir / 'data'
            except Exception as e:
                self.logger.debug(f"Could not get data dir from config: {e}")
                data_base = Path.home() / '.tonietoolbox' / 'data'
        else:
            data_base = Path.home() / '.tonietoolbox' / 'data'
        
        # Create plugin-specific data directory
        data_dir = data_base / plugin_name
        data_dir = data_dir.expanduser()
        
        if ensure_exists:
            data_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Data directory for {pid}: {data_dir}")
        
        return data_dir
    
    # ========== Configuration Helper Methods ==========
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value for this plugin.
        
        Auto-namespaced to the plugin's ID for convenience.
        
        Args:
            key: Configuration key
            default: Default value if not set
            
        Returns:
            Configuration value
            
        Example:
            cache_ttl = context.get_config("cache_ttl", default=86400)
        """
        if not self._plugin_namespace:
            raise ValueError("Plugin namespace not set. Cannot access configuration.")
        
        if self.config_manager:
            return self.config_manager.plugins.get_plugin_config(
                self._plugin_namespace, key, default
            )
        return default
    
    def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value for this plugin.
        
        Auto-namespaced to the plugin's ID for convenience.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Example:
            context.set_config("auto_update", True)
        """
        if not self._plugin_namespace:
            raise ValueError("Plugin namespace not set. Cannot set configuration.")
        
        if self.config_manager:
            self.config_manager.plugins.set_plugin_config(
                self._plugin_namespace, key, value
            )
            self.config_manager.save_config()
    
    def get_all_config(self) -> Dict[str, Any]:
        """
        Get all configuration for this plugin (merged with schema defaults).
        
        Returns:
            Dictionary of all configuration
            
        Example:
            config = context.get_all_config()
            cache_ttl = config.get("cache_ttl", 86400)
        """
        if not self._plugin_namespace:
            raise ValueError("Plugin namespace not set. Cannot access configuration.")
        
        if self.config_manager:
            return self.config_manager.plugins.get_all_plugin_config(self._plugin_namespace)
        return {}
    
    # ========== HTTP Download & Caching Helper Methods ==========
    
    def download_file(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ) -> Optional[bytes]:
        """
        Download a file from a URL.
        
        Args:
            url: URL to download from
            headers: Optional HTTP headers
            timeout: Request timeout in seconds
            
        Returns:
            Downloaded file content as bytes, or None on failure
            
        Example:
            data = context.download_file("https://example.com/data.json")
        """
        try:
            # Build request with default user agent
            default_headers = {'User-Agent': f'TonieToolbox/{self.app_version}'}
            if headers:
                default_headers.update(headers)
            
            req = urllib.request.Request(url, headers=default_headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return None
    
    def is_cache_valid(
        self,
        cache_file: Path,
        ttl_hours: float = 24.0,
        timestamp_file: Optional[Path] = None
    ) -> bool:
        """
        Check if a cached file is still valid based on TTL.
        
        Args:
            cache_file: Path to cached file
            ttl_hours: Time-to-live in hours
            timestamp_file: Optional separate timestamp file (if None, uses cache_file mtime)
            
        Returns:
            True if cache is valid (exists and not expired)
            
        Example:
            if context.is_cache_valid(cache_file, ttl_hours=24):
                data = load_from_cache(cache_file)
        """
        if not cache_file.exists():
            return False
        
        try:
            if timestamp_file and timestamp_file.exists():
                # Use timestamp file
                with open(timestamp_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    cache_time = datetime.fromisoformat(timestamp_str)
            else:
                # Use file modification time
                cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            
            age = datetime.now() - cache_time
            return age < timedelta(hours=ttl_hours)
        except Exception as e:
            self.logger.debug(f"Invalid cache timestamp: {e}")
            return False
    
    def download_and_cache(
        self,
        url: str,
        filename: str,
        cache_ttl_hours: float = 24.0,
        force_refresh: bool = False,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Path]:
        """
        Download a file and cache it, or return cached version if valid.
        
        Args:
            url: URL to download from
            filename: Filename to save as in cache directory
            cache_ttl_hours: Cache time-to-live in hours
            force_refresh: Force download even if cache is valid
            headers: Optional HTTP headers
            
        Returns:
            Path to cached file, or None on failure
            
        Example:
            cached_file = context.download_and_cache(
                "https://example.com/data.json",
                "data.json",
                cache_ttl_hours=24
            )
        """
        cache_dir = self.get_cache_dir()
        cache_file = cache_dir / filename
        timestamp_file = cache_dir / f"{filename}.timestamp"
        
        # Check if cache is valid
        if not force_refresh and self.is_cache_valid(cache_file, cache_ttl_hours, timestamp_file):
            self.logger.debug(f"Using cached file: {cache_file}")
            return cache_file
        
        # Download
        self.logger.info(f"Downloading from {url}")
        data = self.download_file(url, headers=headers)
        
        if data:
            try:
                # Create parent directories if needed
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Save to cache
                cache_file.write_bytes(data)
                
                # Save timestamp
                with open(timestamp_file, 'w') as f:
                    f.write(datetime.now().isoformat())
                
                self.logger.debug(f"Cached to: {cache_file}")
                return cache_file
            except Exception as e:
                self.logger.error(f"Failed to cache file: {e}")
                return None
        
        # Download failed - return stale cache if available
        if cache_file.exists():
            self.logger.warning(f"Download failed, using stale cache: {cache_file}")
            return cache_file
        
        return None
    
    # ========== Resource File Management Methods ==========
    
    def get_resource_path(self, resource_path: str) -> Path:
        """
        Get the full path to a bundled resource file.
        
        Args:
            resource_path: Relative path within plugin directory
            
        Returns:
            Full path to resource
            
        Example:
            data_file = context.get_resource_path("data/tonies.json")
        """
        return self.plugin_dir / resource_path
    
    def list_resources(self, resource_dir: str = "") -> List[Path]:
        """
        List all files in a resource directory.
        
        Args:
            resource_dir: Relative directory path within plugin
            
        Returns:
            List of resource file paths
            
        Example:
            data_files = context.list_resources("data/")
        """
        dir_path = self.plugin_dir / resource_dir
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        return list(dir_path.rglob('*'))
    
    def resource_exists(self, resource_path: str) -> bool:
        """
        Check if a resource file exists.
        
        Args:
            resource_path: Relative path within plugin directory
            
        Returns:
            True if resource exists
            
        Example:
            if context.resource_exists("data/fallback.json"):
                data = load_fallback()
        """
        return (self.plugin_dir / resource_path).exists()
    
    def copy_resource_to_cache(self, resource_path: str, cache_filename: Optional[str] = None) -> Optional[Path]:
        """
        Copy a bundled resource to the cache directory.
        
        Args:
            resource_path: Relative path to resource in plugin directory
            cache_filename: Optional filename in cache (defaults to resource filename)
            
        Returns:
            Path to cached copy, or None on failure
            
        Example:
            cached = context.copy_resource_to_cache("data/fallback.json")
        """
        source = self.plugin_dir / resource_path
        if not source.exists():
            self.logger.error(f"Resource not found: {resource_path}")
            return None
        
        cache_dir = self.get_cache_dir()
        dest_name = cache_filename or source.name
        dest = cache_dir / dest_name
        
        try:
            import shutil
            shutil.copy2(source, dest)
            self.logger.debug(f"Copied resource to cache: {dest}")
            return dest
        except Exception as e:
            self.logger.error(f"Failed to copy resource: {e}")
            return None
    
    # ========== JSON Helper Methods ==========
    
    def load_json(self, file_path: Union[Path, str]) -> Optional[Any]:
        """
        Load JSON data from a file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data, or None on failure
            
        Example:
            data = context.load_json(cache_dir / "data.json")
        """
        try:
            path = Path(file_path)
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load JSON from {file_path}: {e}")
            return None
    
    def save_json(self, data: Any, file_path: Union[Path, str], pretty: bool = True) -> bool:
        """
        Save data as JSON to a file.
        
        Args:
            data: Data to serialize
            file_path: Path to save to
            pretty: Use pretty formatting (default: True)
            
        Returns:
            True if successful
            
        Example:
            context.save_json({"key": "value"}, cache_dir / "config.json")
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(data, f, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save JSON to {file_path}: {e}")
            return False
    
    def load_json_from_url(self, url: str, cache: bool = True, cache_ttl_hours: float = 24.0) -> Optional[Any]:
        """
        Download and parse JSON from a URL, with optional caching.
        
        Args:
            url: URL to download JSON from
            cache: Whether to cache the downloaded JSON
            cache_ttl_hours: Cache TTL in hours (if caching enabled)
            
        Returns:
            Parsed JSON data, or None on failure
            
        Example:
            data = context.load_json_from_url("https://api.example.com/data.json")
        """
        if cache:
            # Generate cache filename from URL
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cache_filename = f"json_{url_hash}.json"
            
            cached_file = self.download_and_cache(url, cache_filename, cache_ttl_hours)
            if cached_file:
                return self.load_json(cached_file)
            return None
        else:
            # Download without caching
            data = self.download_file(url)
            if data:
                try:
                    return json.loads(data.decode('utf-8'))
                except Exception as e:
                    self.logger.error(f"Failed to parse JSON: {e}")
            return None
    
    # ========== Background Task Management Methods ==========
    
    def run_background_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Run a function in a background thread.
        
        Args:
            func: Function to execute
            args: Positional arguments for function
            kwargs: Keyword arguments for function
            on_complete: Callback for successful completion (receives result)
            on_error: Callback for errors (receives exception)
            task_id: Optional task identifier (auto-generated if not provided)
            
        Returns:
            Task ID for tracking
            
        Example:
            def process_data():
                # Long-running operation
                return result
            
            task_id = context.run_background_task(
                process_data,
                on_complete=lambda result: print("Done!", result)
            )
        """
        if kwargs is None:
            kwargs = {}
        
        if task_id is None:
            task_id = f"task_{int(time.time() * 1000)}"
        
        def wrapper():
            try:
                result = func(*args, **kwargs)
                if on_complete:
                    on_complete(result)
            except Exception as e:
                self.logger.error(f"Background task error: {e}", exc_info=True)
                if on_error:
                    on_error(e)
            finally:
                with self._task_lock:
                    self._background_tasks.pop(task_id, None)
        
        thread = Thread(target=wrapper, daemon=True, name=f"plugin_{task_id}")
        
        with self._task_lock:
            self._background_tasks[task_id] = thread
        
        thread.start()
        self.logger.debug(f"Started background task: {task_id}")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a background task.
        
        Note: This only removes the task from tracking. Python threads cannot
        be forcefully terminated, so the task must check for cancellation.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was found and removed
        """
        with self._task_lock:
            thread = self._background_tasks.pop(task_id, None)
            if thread:
                self.logger.debug(f"Cancelled task: {task_id}")
                return True
        return False
    
    def _cancel_all_tasks(self) -> None:
        """Cancel all background tasks (called during cleanup)."""
        with self._task_lock:
            task_count = len(self._background_tasks)
            if task_count > 0:
                self.logger.debug(f"Cancelling {task_count} background tasks")
            self._background_tasks.clear()
    
    # ========== Permissions Helper Methods ==========
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if the plugin has a specific permission.
        
        Args:
            permission: Permission name (e.g., "network", "filesystem")
            
        Returns:
            True if permission is granted
            
        Example:
            if context.has_permission("network"):
                download_data()
        """
        if not self._plugin_registry or not self._plugin_namespace:
            return True  # Permissive if not properly initialized
        
        manifest = self._plugin_registry.get_manifest(self._plugin_namespace)
        if manifest:
            return permission in manifest.permissions
        return True
    
    def require_permission(self, permission: str) -> None:
        """
        Require a specific permission, raising an error if not granted.
        
        Args:
            permission: Permission name
            
        Raises:
            PermissionError: If permission is not granted
            
        Example:
            context.require_permission("network")
            download_data()  # Only executes if permission granted
        """
        if not self.has_permission(permission):
            raise PermissionError(
                f"Plugin '{self._plugin_namespace}' requires '{permission}' permission"
            )
    
    # ========== Plugin Dependency Helper Methods ==========
    
    def require_plugin(
        self,
        plugin_id: str,
        min_version: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Require another plugin to be loaded, raising an error if not available.
        
        Args:
            plugin_id: Required plugin ID
            min_version: Optional minimum version requirement
            error_message: Custom error message
            
        Raises:
            RuntimeError: If required plugin is not available
            
        Example:
            context.require_plugin("com.tonietoolbox.tonies_loader", min_version="1.0.0")
            service = context.get_service("tonies_loader")
        """
        if not self._plugin_registry:
            raise RuntimeError("Plugin registry not available")
        
        plugin = self._plugin_registry.get_plugin(plugin_id)
        if not plugin:
            msg = error_message or f"Required plugin not found: {plugin_id}"
            raise RuntimeError(msg)
        
        if min_version:
            manifest = self._plugin_registry.get_manifest(plugin_id)
            if manifest:
                from packaging.version import Version
                if Version(manifest.metadata.version) < Version(min_version):
                    msg = error_message or f"Plugin {plugin_id} version {manifest.metadata.version} is too old (need {min_version}+)"
                    raise RuntimeError(msg)
    
    def wait_for_plugin(
        self,
        plugin_id: str,
        timeout: float = 5.0,
        check_interval: float = 0.1
    ) -> bool:
        """
        Wait for another plugin to be loaded (useful for async loading).
        
        Args:
            plugin_id: Plugin ID to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check in seconds
            
        Returns:
            True if plugin was loaded within timeout
            
        Example:
            if context.wait_for_plugin("com.tonietoolbox.tonies_loader", timeout=5):
                service = context.get_service("tonies_loader")
        """
        if not self._plugin_registry:
            return False
        
        elapsed = 0.0
        while elapsed < timeout:
            if self._plugin_registry.get_plugin(plugin_id):
                return True
            time.sleep(check_interval)
            elapsed += check_interval
        
        return False
    
    # ========== Logging Helper Methods ==========
    
    def log_info(self, message: str) -> None:
        """
        Log an info message with plugin name prefix.
        
        Args:
            message: Log message
        """
        plugin_name = self._get_plugin_name()
        self.logger.info(f"[{plugin_name}] {message}")
    
    def log_debug(self, message: str) -> None:
        """
        Log a debug message with plugin name prefix.
        
        Args:
            message: Log message
        """
        plugin_name = self._get_plugin_name()
        self.logger.debug(f"[{plugin_name}] {message}")
    
    def log_error(self, message: str, exc_info: bool = False) -> None:
        """
        Log an error message with plugin name prefix.
        
        Args:
            message: Log message
            exc_info: Include exception information
        """
        plugin_name = self._get_plugin_name()
        self.logger.error(f"[{plugin_name}] {message}", exc_info=exc_info)
    
    def log_warning(self, message: str) -> None:
        """
        Log a warning message with plugin name prefix.
        
        Args:
            message: Log message
        """
        plugin_name = self._get_plugin_name()
        self.logger.warning(f"[{plugin_name}] {message}")
    
    def log_performance(self, operation: str, duration: float, details: Optional[str] = None) -> None:
        """
        Log performance metrics for an operation.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
            details: Optional additional details
        """
        plugin_name = self._get_plugin_name()
        msg = f"[{plugin_name}] Performance: {operation} completed in {duration:.3f}s"
        if details:
            msg += f" ({details})"
        self.logger.info(msg)
    
    def _get_plugin_name(self) -> str:
        """Get the plugin name for logging (extracts from namespace)."""
        if self._plugin_namespace:
            parts = self._plugin_namespace.split('.')
            return parts[-1] if len(parts) >= 3 else self._plugin_namespace
        return "UnknownPlugin"
    
    # ========== GUI Helper Methods ==========
    
    def get_application_icon(self) -> Optional[Any]:
        """
        Get the TonieToolbox application icon for use in plugin windows.
        
        Returns QIcon if PyQt6 is available, None otherwise.
        Plugins should use this to inherit the main application icon when
        no plugin-specific icon is configured.
        
        Returns:
            QIcon object with TonieToolbox logo, or None if PyQt6 unavailable
            
        Example:
            # Manual usage (legacy):
            icon = context.get_application_icon()
            if icon:
                self.setWindowIcon(icon)
            
            # Recommended: Use create_dialog() which sets icon automatically
            dialog = context.create_dialog(title="My Dialog", min_size=(800, 600))
        """
        try:
            from PyQt6.QtGui import QIcon, QPixmap
            from PyQt6.QtCore import QByteArray
            from TonieToolbox.core.config.application_constants import ICON_PNG_BASE64
            import base64
            
            # Decode the base64 logo
            logo_data = base64.b64decode(ICON_PNG_BASE64)
            
            # Create QByteArray and QPixmap
            byte_array = QByteArray(logo_data)
            pixmap = QPixmap()
            pixmap.loadFromData(byte_array, "PNG")
            
            # Create and return icon
            icon = QIcon(pixmap)
            self.log_debug("Application icon retrieved successfully")
            return icon
            
        except ImportError:
            self.log_debug("PyQt6 not available, cannot create application icon")
            return None
        except Exception as e:
            self.log_error(f"Failed to create application icon: {e}")
            return None
    
    def set_window_icon(self, window: Any, custom_icon_path: Optional[str] = None) -> bool:
        """
        Set window icon with automatic fallback to TonieToolbox icon.
        
        This is a convenience method that:
        1. Tries to load custom icon if path provided
        2. Falls back to TonieToolbox application icon
        3. Handles errors gracefully
        
        Args:
            window: QDialog, QMainWindow, or any QWidget with setWindowIcon()
            custom_icon_path: Optional path to custom icon file
            
        Returns:
            True if icon was set successfully
            
        Example:
            # Auto-inherit TonieToolbox icon:
            context.set_window_icon(my_dialog)
            
            # Use custom icon with fallback:
            context.set_window_icon(my_dialog, custom_icon_path="/path/to/icon.png")
        """
        try:
            if custom_icon_path:
                # Try to load custom icon
                from PyQt6.QtGui import QIcon
                custom_icon = QIcon(str(custom_icon_path))
                if not custom_icon.isNull():
                    window.setWindowIcon(custom_icon)
                    self.log_debug(f"Set custom window icon: {custom_icon_path}")
                    return True
                else:
                    self.log_warning(f"Custom icon file not valid: {custom_icon_path}, using TonieToolbox icon")
            
            # Use TonieToolbox application icon
            app_icon = self.get_application_icon()
            if app_icon:
                window.setWindowIcon(app_icon)
                self.log_debug("Set TonieToolbox application icon on window")
                return True
            
            return False
            
        except Exception as e:
            self.log_error(f"Failed to set window icon: {e}")
            return False
    
    def create_dialog(
        self,
        parent: Optional[Any] = None,
        title: Optional[str] = None,
        min_size: Optional[tuple] = None,
        custom_icon_path: Optional[str] = None
    ) -> Optional[Any]:
        """
        Create a QDialog with TonieToolbox icon automatically set.
        
        This factory method creates a dialog and automatically applies the
        TonieToolbox application icon (unless a custom icon path is provided).
        
        Args:
            parent: Parent widget
            title: Window title (optional)
            min_size: Tuple of (width, height) for minimum size
            custom_icon_path: Optional path to custom icon (falls back to TonieToolbox icon)
            
        Returns:
            QDialog instance with icon set, or None if PyQt6 unavailable
            
        Example:
            # Simple dialog with TonieToolbox icon:
            dialog = context.create_dialog(title="My Plugin", min_size=(800, 600))
            dialog.exec()
            
            # With custom icon:
            dialog = context.create_dialog(
                title="My Tool",
                custom_icon_path=context.get_resource_path("icons/custom.png")
            )
        """
        try:
            from PyQt6.QtWidgets import QDialog
            
            dialog = QDialog(parent)
            
            # Set title if provided
            if title:
                dialog.setWindowTitle(title)
            
            # Set minimum size if provided
            if min_size:
                dialog.setMinimumSize(min_size[0], min_size[1])
            
            # Set icon (custom or TonieToolbox default)
            self.set_window_icon(dialog, custom_icon_path)
            
            return dialog
            
        except ImportError:
            self.log_error("PyQt6 not available, cannot create dialog")
            return None
        except Exception as e:
            self.log_error(f"Failed to create dialog: {e}")
            return None


class BasePlugin(ABC):
    """
    Abstract base class for all TonieToolbox plugins.
    
    All plugins must inherit from this class and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the plugin."""
        self._context: Optional[PluginContext] = None
        self._enabled = False
    
    @abstractmethod
    def get_manifest(self) -> PluginManifest:
        """
        Get the plugin manifest containing metadata and configuration.
        
        Returns:
            PluginManifest with plugin information
        """
        pass
    
    @abstractmethod
    def initialize(self, context: PluginContext) -> bool:
        """
        Initialize the plugin with the given context.
        
        Called when the plugin is loaded. Register components, handlers, etc.
        
        Args:
            context: Plugin context with app services
            
        Returns:
            True if initialization succeeded, False otherwise
        """
        pass
    
    def enable(self) -> bool:
        """
        Enable the plugin.
        
        Called after successful initialization or when user enables the plugin.
        
        Returns:
            True if plugin was enabled successfully
        """
        self._enabled = True
        return True
    
    def disable(self) -> bool:
        """
        Disable the plugin.
        
        Called when user disables the plugin. Should stop all activities.
        
        Returns:
            True if plugin was disabled successfully
        """
        self._enabled = False
        return True
    
    def cleanup(self) -> None:
        """
        Clean up plugin resources.
        
        Called when plugin is unloaded. Must release all resources.
        """
        if self._context:
            self._context.cleanup_resources()
    
    @property
    def is_enabled(self) -> bool:
        """Check if plugin is currently enabled."""
        return self._enabled
    
    @property
    def context(self) -> Optional[PluginContext]:
        """Get the plugin context."""
        return self._context


class GUIPlugin(BasePlugin):
    """
    Base class for GUI plugins that add UI components.
    
    Example:
        ```python
        class MyGUIPlugin(GUIPlugin):
            def register_components(self, gui_registry):
                gui_registry.register_menu_item(
                    "Tools", "My Tool",
                    callback=self.show_my_tool
                )
                
            def show_my_tool(self):
                # Show custom dialog
                pass
        ```
    """
    
    @abstractmethod
    def register_components(self, gui_registry) -> None:
        """
        Register GUI components with the application.
        
        Args:
            gui_registry: GUI component registry for registering UI elements
        """
        pass


class ProcessorPlugin(BasePlugin):
    """
    Base class for plugins that add file processors or converters.
    
    Example:
        ```python
        class MyProcessorPlugin(ProcessorPlugin):
            def register_processors(self, processor_registry):
                processor_registry.register(
                    "my_format",
                    MyCustomProcessor
                )
        ```
    """
    
    @abstractmethod
    def register_processors(self, processor_registry) -> None:
        """
        Register processors with the application.
        
        Args:
            processor_registry: Processor registry for registering processors
        """
        pass


class IntegrationPlugin(BasePlugin):
    """
    Base class for plugins that integrate with external services.
    
    Example:
        ```python
        class CloudStoragePlugin(IntegrationPlugin):
            def register_integration(self, integration_registry):
                integration_registry.register(
                    "cloud_storage",
                    CloudStorageIntegration
                )
        ```
    """
    
    @abstractmethod
    def register_integration(self, integration_registry) -> None:
        """
        Register integration with the application.
        
        Args:
            integration_registry: Integration registry
        """
        pass


class ToolPlugin(BasePlugin):
    """
    Base class for plugins that add standalone tools.
    
    Example:
        ```python
        class BatchConverterPlugin(ToolPlugin):
            def register_tool(self, tool_registry):
                tool_registry.register(
                    "batch_converter",
                    BatchConverterTool
                )
        ```
    """
    
    @abstractmethod
    def register_tool(self, tool_registry) -> None:
        """
        Register tool with the application.
        
        Args:
            tool_registry: Tool registry
        """
        pass


def load_manifest_from_json(manifest_path: Path) -> PluginManifest:
    """
    Load a PluginManifest from a JSON file.
    
    This provides a single source of truth - plugins should define their manifest
    in manifest.json and use this helper in get_manifest().
    
    Args:
        manifest_path: Path to manifest.json file
        
    Returns:
        PluginManifest loaded from JSON
        
    Raises:
        FileNotFoundError: If manifest file doesn't exist
        ValueError: If manifest JSON is invalid
        
    Example:
        ```python
        class MyPlugin(BasePlugin):
            def get_manifest(self) -> PluginManifest:
                return load_manifest_from_json(Path(__file__).parent / "manifest.json")
        ```
    """
    import json
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in manifest file: {e}")
    
    # Parse install info if present
    install_info = None
    if 'install' in data:
        install_data = data['install']
        install_info = PluginInstallInfo(
            source_type=install_data.get('type', 'local'),
            source_url=install_data.get('url'),
            branch=install_data.get('branch'),
            commit=install_data.get('commit'),
            checksum=install_data.get('checksum'),
            checksum_algorithm=install_data.get('checksum_algorithm', 'sha256'),
            subdirectory=install_data.get('subdir')
        )
    
    # Parse dependencies
    dependencies_list = []
    if 'dependencies' in data:
        dep_data = data['dependencies']
        if isinstance(dep_data, dict):
            # Format: {"plugins": [...], "python": [...]}
            plugins_deps = dep_data.get('plugins', [])
            # Extract plugin IDs from dependency objects
            for dep in plugins_deps:
                if isinstance(dep, dict) and 'id' in dep:
                    dependencies_list.append(dep['id'])
                elif isinstance(dep, str):
                    dependencies_list.append(dep)
    
    # Create metadata
    metadata = PluginMetadata(
        id=data['id'],
        name=data['name'],
        version=data['version'],
        author=data['author'],
        description=data['description'],
        plugin_type=PluginType(data['plugin_type']),
        dependencies=dependencies_list if isinstance(dependencies_list, list) else [],
        homepage=data.get('homepage'),
        license=data.get('license'),
        min_tonietoolbox_version=data.get('min_tonietoolbox_version'),
        max_tonietoolbox_version=data.get('max_tonietoolbox_version'),
        tags=data.get('tags', []),
        repository=data.get('repository'),
        changelog_url=data.get('changelog_url'),
        screenshots=data.get('screenshots', []),
        verified=data.get('verified', False),
        trust_level=data.get('trust_level', 'community'),
        display_name=data.get('display_name'),
        install_info=install_info
    )
    
    # Create manifest
    return PluginManifest(
        metadata=metadata,
        config_schema=data.get('config_schema', {}),
        permissions=data.get('permissions', []),
        entry_point=data.get('entry_point')
    )
