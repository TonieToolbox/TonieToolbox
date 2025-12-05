#!/usr/bin/env python3
"""
Plugin manager for coordinating plugin loading, initialization, and lifecycle.
"""
import json
from typing import Dict, List, Optional, Callable, Tuple
from pathlib import Path
from packaging.version import Version
from ..utils import get_logger
from ..events import get_event_bus
from .base import BasePlugin, PluginContext, PluginManifest, PluginSource
from .registry import PluginRegistry
from .loader import PluginLoader
from .repository import PluginRepository
from .dependency_resolver import DependencyResolver
from .installer import PluginInstaller
from .trust import TrustManager, get_trust_manager
from .events import (
    PluginLoadedEvent,
    PluginUnloadedEvent,
    PluginErrorEvent,
    PluginEnabledEvent,
    PluginDisabledEvent,
    PluginInstalledEvent,
    PluginReloadedEvent,
    PluginGuiComponentsChangedEvent
)

logger = get_logger(__name__)

# Global plugin manager instance
_plugin_manager: Optional['PluginManager'] = None


def get_plugin_manager() -> 'PluginManager':
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        # Try to get config manager if not yet initialized
        try:
            from ..config import get_config_manager
            config_manager = get_config_manager()
        except:
            config_manager = None
        _plugin_manager = PluginManager(config_manager=config_manager)
    return _plugin_manager


class PluginManager:
    """
    Manages the complete plugin lifecycle:
    - Discovery and loading
    - Initialization with context
    - Enable/disable management
    - Unloading and cleanup
    """
    
    def __init__(self, config_manager=None, app_version: str = "1.0.0"):
        """
        Initialize the plugin manager.
        
        Args:
            config_manager: Configuration manager instance
            app_version: Application version
        """
        self.config_manager = config_manager
        self.app_version = app_version
        self.event_bus = get_event_bus()
        
        self.registry = PluginRegistry()
        self.loader = PluginLoader(config_manager=config_manager)
        self.trust_manager = get_trust_manager(config_manager=config_manager)
        
        self._initialized_plugins: Dict[str, bool] = {}
        
        # Initialize marketplace components
        self._repository: Optional[PluginRepository] = None
        self._dependency_resolver: Optional[DependencyResolver] = None
        self._installer: Optional[PluginInstaller] = None
        
        logger.info("Plugin manager initialized")
    
    def add_plugin_directory(self, directory: Path) -> None:
        """
        Add a custom plugin directory.
        
        Args:
            directory: Path to plugin directory
        """
        self.loader.add_plugin_directory(directory)
    
    def discover_and_load_plugins(self) -> int:
        """
        Discover and load all available plugins.
        
        Returns:
            Number of plugins successfully loaded
        """
        # Get disabled plugins list from config
        disabled_plugins = []
        if self.config_manager:
            disabled_plugins = self.config_manager.plugins.disabled_plugins
        
        plugin_tuples = self.loader.load_all_plugins()
        loaded_count = 0
        
        for plugin, plugin_dir, source in plugin_tuples:
            try:
                manifest = plugin.get_manifest()
                plugin_id = manifest.metadata.id
                
                # Check if plugin is disabled in configuration
                if plugin_id in disabled_plugins:
                    logger.info(f"Plugin '{plugin_id}' is disabled in configuration")
                    continue
                
                # Check if plugin is already registered
                if self.registry.is_registered(plugin_id):
                    logger.warning(f"Plugin '{plugin_id}' is already loaded")
                    continue
                
                # Register the plugin with its actual directory and source
                if self.registry.register_plugin(plugin_id, plugin, manifest, plugin_dir, source):
                    loaded_count += 1
                    self.event_bus.publish(PluginLoadedEvent(
                        plugin_id=plugin_id,
                        plugin_name=manifest.metadata.name,
                        plugin_version=manifest.metadata.version
                    ))
                    logger.info(f"Loaded plugin: {manifest.metadata.name} v{manifest.metadata.version} (source: {source.value})")
                
            except Exception as e:
                logger.error(f"Failed to load plugin: {e}", exc_info=True)
                if hasattr(plugin, 'get_manifest'):
                    try:
                        manifest = plugin.get_manifest()
                        self.event_bus.publish(PluginErrorEvent(
                            plugin_id=manifest.metadata.id,
                            error_message=str(e),
                            error_type=type(e).__name__
                        ))
                    except:
                        pass
        
        logger.info(f"Successfully loaded {loaded_count} plugins")
        return loaded_count
    
    def _resolve_initialization_order(self, plugin_ids: List[str]) -> List[str]:
        """
        Resolve plugin initialization order based on dependencies using topological sort.
        
        Args:
            plugin_ids: List of plugin IDs to initialize
            
        Returns:
            List of plugin IDs in dependency-resolved order
        """
        # Build dependency graph
        dependency_graph: Dict[str, List[str]] = {}
        all_plugins = set(plugin_ids)
        
        for plugin_id in plugin_ids:
            plugin = self.registry.get_plugin(plugin_id)
            if not plugin:
                continue
            
            manifest = plugin.get_manifest()
            dependencies = []
            
            # Extract plugin dependencies from manifest
            if hasattr(manifest, 'dependencies') and manifest.dependencies:
                if isinstance(manifest.dependencies, dict):
                    plugin_deps = manifest.dependencies.get('plugins', [])
                    for dep in plugin_deps:
                        if isinstance(dep, dict):
                            dep_id = dep.get('id')
                            if dep_id and dep_id in all_plugins:
                                dependencies.append(dep_id)
            
            dependency_graph[plugin_id] = dependencies
        
        # Topological sort using Kahn's algorithm
        # in_degree tracks how many plugins depend on each plugin (reversed dependencies)
        in_degree = {plugin_id: 0 for plugin_id in plugin_ids}
        
        # Count incoming edges: if A depends on B, increment A's in-degree
        for plugin_id in plugin_ids:
            for dependency in dependency_graph.get(plugin_id, []):
                in_degree[plugin_id] += 1
        
        # Queue of plugins with no dependencies (in-degree = 0)
        queue = [plugin_id for plugin_id in plugin_ids if in_degree[plugin_id] == 0]
        result = []
        
        while queue:
            # Sort queue for deterministic ordering
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            # Find all plugins that depend on current and reduce their in-degree
            for plugin_id in plugin_ids:
                if current in dependency_graph.get(plugin_id, []):
                    in_degree[plugin_id] -= 1
                    if in_degree[plugin_id] == 0:
                        queue.append(plugin_id)
        
        # Check for circular dependencies
        if len(result) != len(plugin_ids):
            remaining = set(plugin_ids) - set(result)
            logger.warning(f"Circular dependency detected among plugins: {remaining}")
            # Add remaining plugins to end
            result.extend(sorted(remaining))
        
        logger.debug(f"Resolved plugin initialization order: {result}")
        return result
    
    def get_loaded_plugins(self) -> List[str]:
        """
        Get list of all loaded plugin IDs.
        
        Returns:
            List of plugin identifiers
        """
        return self.registry.get_all_plugin_ids()
    
    def initialize_plugin(self, plugin_id: str) -> bool:
        """
        Initialize a plugin with context.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if initialization succeeded
        """
        plugin = self.registry.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin '{plugin_id}' not found")
            return False
        
        if self._initialized_plugins.get(plugin_id, False):
            logger.warning(f"Plugin '{plugin_id}' is already initialized")
            return True
        
        try:
            # Get translation manager
            translation_manager = None
            try:
                from ..gui.i18n import get_translation_manager
                translation_manager = get_translation_manager()
            except ImportError:
                logger.debug("Translation manager not available (GUI not loaded)")
            
            # Load plugin translations if available
            plugin_dir = self.registry.get_plugin_dir(plugin_id) or Path.cwd()
            if translation_manager:
                self._load_plugin_translations(plugin_id, plugin_dir, translation_manager)
            
            # Create plugin context
            context = PluginContext(
                app_version=self.app_version,
                config_manager=self.config_manager,
                event_bus=self.event_bus,
                logger=logger,
                plugin_dir=plugin_dir,
                translation_manager=translation_manager
            )
            
            # Set plugin namespace for translations
            context.set_plugin_namespace(plugin_id)
            
            # Set plugin manager and registry references
            context._plugin_manager = self
            context._plugin_registry = self.registry
            
            # Initialize the plugin
            if plugin.initialize(context):
                plugin._context = context
                self._initialized_plugins[plugin_id] = True
                logger.info(f"Initialized plugin: {plugin_id}")
                return True
            else:
                logger.error(f"Plugin initialization failed: {plugin_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing plugin '{plugin_id}': {e}", exc_info=True)
            self.event_bus.publish(PluginErrorEvent(
                plugin_id=plugin_id,
                error_message=str(e),
                error_type=type(e).__name__
            ))
            return False
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """
        Enable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if plugin was enabled
        """
        plugin = self.registry.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin '{plugin_id}' not found")
            return False
        
        # Initialize if needed
        if not self._initialized_plugins.get(plugin_id, False):
            if not self.initialize_plugin(plugin_id):
                return False
        
        try:
            if plugin.enable():
                # Remove from disabled plugins list to persist enable state
                if self.config_manager:
                    disabled_plugins = self.config_manager.plugins.disabled_plugins
                    if plugin_id in disabled_plugins:
                        disabled_plugins.remove(plugin_id)
                        self.config_manager.plugins.disabled_plugins = disabled_plugins
                        self.config_manager.save_config()
                        logger.debug(f"Removed '{plugin_id}' from disabled plugins list")
                
                self.event_bus.publish(PluginEnabledEvent(plugin_id=plugin_id))
                logger.info(f"Enabled plugin: {plugin_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error enabling plugin '{plugin_id}': {e}", exc_info=True)
            self.event_bus.publish(PluginErrorEvent(
                plugin_id=plugin_id,
                error_message=str(e),
                error_type=type(e).__name__
            ))
            return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """
        Disable a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if plugin was disabled
        """
        plugin = self.registry.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin '{plugin_id}' not found")
            return False
        
        try:
            if plugin.disable():
                # Add to disabled plugins list to persist disable state
                if self.config_manager:
                    disabled_plugins = self.config_manager.plugins.disabled_plugins
                    if plugin_id not in disabled_plugins:
                        disabled_plugins.append(plugin_id)
                        self.config_manager.plugins.disabled_plugins = disabled_plugins
                        self.config_manager.save_config()
                        logger.debug(f"Added '{plugin_id}' to disabled plugins list")
                
                self.event_bus.publish(PluginDisabledEvent(plugin_id=plugin_id))
                logger.info(f"Disabled plugin: {plugin_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error disabling plugin '{plugin_id}': {e}", exc_info=True)
            return False
    
    def unload_plugin(self, plugin_id: str, reason: Optional[str] = None) -> bool:
        """
        Unload a plugin and clean up resources.
        
        Args:
            plugin_id: Plugin identifier
            reason: Optional reason for unloading
            
        Returns:
            True if plugin was unloaded
        """
        plugin = self.registry.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin '{plugin_id}' not found")
            return False
        
        try:
            # Disable if enabled
            if plugin.is_enabled:
                plugin.disable()
            
            # Get component categories before cleanup for event
            component_categories = list(self.registry.component_registry.get_registered_by_plugin(plugin_id).keys())
            
            # Cleanup
            plugin.cleanup()
            
            # Unload plugin translations
            try:
                from ..gui.i18n import get_translation_manager
                translation_manager = get_translation_manager()
                translation_manager.unload_plugin_translations(plugin_id)
            except ImportError:
                pass  # Translation manager not available
            
            # Unregister (this also removes all plugin components)
            if self.registry.unregister_plugin(plugin_id):
                if plugin_id in self._initialized_plugins:
                    del self._initialized_plugins[plugin_id]
                
                # Emit GUI components changed event if plugin had GUI components
                if component_categories:
                    self.event_bus.publish(PluginGuiComponentsChangedEvent(
                        plugin_id=plugin_id,
                        change_type='removed',
                        component_categories=component_categories
                    ))
                
                self.event_bus.publish(PluginUnloadedEvent(
                    plugin_id=plugin_id,
                    reason=reason
                ))
                logger.info(f"Unloaded plugin: {plugin_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error unloading plugin '{plugin_id}': {e}", exc_info=True)
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get a plugin instance."""
        return self.registry.get_plugin(plugin_id)
    
    def load_plugin_at_runtime(self, plugin_path: Path, auto_enable: bool = True) -> bool:
        """
        Load a plugin at runtime from a specific path.
        
        Args:
            plugin_path: Path to plugin directory
            auto_enable: Automatically enable plugin after loading
            
        Returns:
            True if plugin was loaded and initialized successfully
        """
        try:
            # Load the plugin
            plugin = self.loader.load_plugin(plugin_path)
            if not plugin:
                logger.error(f"Failed to load plugin from {plugin_path}")
                return False
            
            # Get manifest and plugin ID
            manifest = plugin.get_manifest()
            plugin_id = manifest.metadata.id
            
            # Check if already registered
            if self.registry.is_registered(plugin_id):
                logger.warning(f"Plugin '{plugin_id}' is already loaded")
                return False
            
            # Determine source
            source = self.loader.get_plugin_source(plugin_path)
            
            # Register the plugin
            if not self.registry.register_plugin(plugin_id, plugin, manifest, plugin_path, source):
                return False
            
            # Emit loaded event
            self.event_bus.publish(PluginLoadedEvent(
                plugin_id=plugin_id,
                plugin_name=manifest.metadata.name,
                plugin_version=manifest.metadata.version
            ))
            
            # Initialize the plugin
            if not self.initialize_plugin(plugin_id):
                self.registry.unregister_plugin(plugin_id)
                return False
            
            # Auto-enable if requested and not in disabled list
            disabled_plugins = []
            if self.config_manager:
                disabled_plugins = self.config_manager.plugins.disabled_plugins
            
            if auto_enable and plugin_id not in disabled_plugins:
                if self.enable_plugin(plugin_id):
                    # Emit GUI components changed if it's a GUI plugin
                    if manifest.metadata.plugin_type.value == "gui":
                        self.event_bus.publish(PluginGuiComponentsChangedEvent(
                            plugin_id=plugin_id,
                            change_type='added'
                        ))
                    logger.info(f"Loaded and enabled plugin at runtime: {manifest.metadata.name}")
                else:
                    logger.warning(f"Loaded but failed to enable plugin: {manifest.metadata.name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading plugin at runtime from {plugin_path}: {e}", exc_info=True)
            return False
    
    def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin (unload then load again).
        Useful for development and updating plugins without restart.
        
        Args:
            plugin_id: Plugin ID to reload
            
        Returns:
            True if reload successful
        """
        try:
            # Get plugin directory before unloading
            plugin_dir = self.registry.get_plugin_dir(plugin_id)
            if not plugin_dir:
                logger.error(f"Cannot reload '{plugin_id}': plugin directory not found")
                return False
            
            # Check if plugin was enabled
            was_enabled = self.is_plugin_enabled(plugin_id)
            
            # Get plugin name for event
            manifest = self.registry.get_manifest(plugin_id)
            plugin_name = manifest.metadata.name if manifest else plugin_id
            
            # Unload the plugin
            if not self.unload_plugin(plugin_id, reason="Reloading"):
                return False
            
            # Load the plugin again
            if not self.load_plugin_at_runtime(plugin_dir, auto_enable=was_enabled):
                return False
            
            # Emit reload event
            self.event_bus.publish(PluginReloadedEvent(
                plugin_id=plugin_id,
                plugin_name=plugin_name
            ))
            
            logger.info(f"Successfully reloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error reloading plugin '{plugin_id}': {e}", exc_info=True)
            return False
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all registered plugins."""
        return self.registry.get_all_plugins()
    
    def get_enabled_plugins(self) -> Dict[str, BasePlugin]:
        """Get all enabled plugins."""
        return self.registry.get_enabled_plugins()
    
    def is_plugin_enabled(self, plugin_id: str) -> bool:
        """
        Check if a plugin is enabled.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            True if plugin is enabled
        """
        return plugin_id in self.registry.get_enabled_plugins()
    
    def get_installed_plugins(self) -> List[Dict[str, str]]:
        """
        Get list of all installed plugins from disk.
        
        Returns:
            List of dicts with plugin installation info
        """
        return self.installer.get_installed_plugins()
    
    def get_component_registry(self):
        """Get the component registry."""
        return self.registry.component_registry
    
    # ===== Marketplace Integration =====
    
    @property
    def repository(self) -> PluginRepository:
        """Get or create the plugin repository client."""
        if self._repository is None:
            repo_urls = None
            if self.config_manager:
                repo_urls = self.config_manager.plugins.repository_urls
            self._repository = PluginRepository(
                repository_urls=repo_urls,
                config_manager=self.config_manager
            )
        return self._repository
    
    def _get_dependency_resolver(self) -> DependencyResolver:
        """Get or create the dependency resolver with current installed plugins."""
        # Get currently installed plugins (from disk, not just loaded ones)
        installed = {}
        
        # First, get all loaded plugins (fast)
        for pid in self.get_loaded_plugins():
            m = self.registry.get_manifest(pid)
            if m:
                installed[pid] = m.metadata.version
        
        # Also check installed plugins that might not be loaded yet
        try:
            installed_plugins = self.get_installed_plugins()
            for plugin_info in installed_plugins:
                plugin_id = plugin_info.get('id')
                version = plugin_info.get('version')
                
                # Add if not already in the list (loaded plugins take priority)
                if plugin_id and version and plugin_id not in installed:
                    installed[plugin_id] = version
        except Exception as e:
            self.logger.debug(f"Could not get installed plugins for dependency resolver: {e}")
        
        return DependencyResolver(self.repository, installed)
    
    @property
    def installer(self) -> PluginInstaller:
        """Get or create the plugin installer."""
        if self._installer is None:
            install_dir = Path.home() / ".tonietoolbox" / "plugins"
            if self.config_manager:
                install_dir = Path(self.config_manager.plugins.install_location)
            self._installer = PluginInstaller(install_dir, self.repository)
        return self._installer
    
    def search_community_plugins(
        self,
        query: Optional[str] = None,
        plugin_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None
    ) -> List[PluginManifest]:
        """
        Search for plugins in the community repository.
        
        Args:
            query: Search term (matches name, description)
            plugin_type: Filter by plugin type
            tags: Filter by tags
            author: Filter by author
            
        Returns:
            List of matching plugin manifests
        """
        from .base import PluginType
        
        type_filter = None
        if plugin_type:
            try:
                type_filter = PluginType(plugin_type)
            except ValueError:
                logger.warning(f"Invalid plugin type: {plugin_type}")
        
        return self.repository.search_plugins(
            query=query,
            plugin_type=type_filter,
            tags=tags,
            author=author
        )
    
    def get_plugin_updates(self) -> Dict[str, str]:
        """
        Check for available updates for installed plugins.
        
        Returns:
            Dictionary mapping plugin_id to latest version
        """
        updates = {}
        
        for plugin_id in self.get_loaded_plugins():
            manifest = self.registry.get_manifest(plugin_id)
            if not manifest:
                continue
            
            # Extract author and name from plugin ID
            parts = plugin_id.split('.')
            if len(parts) < 3:
                continue
            
            current_version = manifest.metadata.version
            
            # Check for latest version using plugin ID
            latest_version = self.repository.get_latest_version(plugin_id)
            
            if latest_version and Version(latest_version) > Version(current_version):
                updates[plugin_id] = latest_version
                logger.info(f"Update available for {plugin_id}: {current_version} → {latest_version}")
        
        return updates
    
    def install_from_repository(
        self,
        author: str,
        plugin_name: str,
        version: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Install a plugin from the community repository.
        
        Args:
            author: Plugin author
            plugin_name: Plugin name
            version: Plugin version (latest if None)
            progress_callback: Optional progress callback
            
        Returns:
            True if installation succeeded
        """
        try:
            # Construct plugin_id from author and plugin_name
            plugin_id = f"com.{author}.{plugin_name}"
            
            # Get version if not specified
            if version is None:
                version = self.repository.get_latest_version(plugin_id)
                if not version:
                    logger.error(f"Could not determine latest version for {plugin_id}")
                    return False
            
            # Fetch manifest
            manifest = self.repository.fetch_manifest(plugin_id, version)
            if not manifest:
                logger.error(f"Manifest not found: {author}/{plugin_name} v{version}")
                return False
            
            # Check if plugin is verified (if required)
            if self.config_manager and not self.config_manager.plugins.allow_unverified:
                if not manifest.metadata.verified:
                    logger.error(f"Plugin {manifest.metadata.id} is not verified")
                    return False
            
            # Resolve and install with dependencies
            return self.resolve_and_install(manifest, progress_callback)
            
        except Exception as e:
            logger.error(f"Failed to install {author}/{plugin_name}: {e}", exc_info=True)
            return False
    
    def resolve_and_install(
        self,
        manifest: PluginManifest,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Resolve dependencies and install a plugin.
        
        Args:
            manifest: Plugin manifest
            progress_callback: Optional progress callback
            
        Returns:
            True if installation succeeded
        """
        try:
            plugin_id = manifest.metadata.id
            
            if progress_callback:
                progress_callback(f"Resolving dependencies for {manifest.metadata.name}...", 0)
            
            # Create dependency resolver with current state
            resolver = self._get_dependency_resolver()
            
            # Resolve dependencies
            plugin_deps, python_deps, warnings = resolver.resolve(
                plugin_id=plugin_id,
                plugin_version=manifest.metadata.version,
                manifest=manifest
            )
            
            # Show warnings
            for warning in warnings:
                logger.warning(f"Dependency warning: {warning}")
            
            # Install Python dependencies (requires confirmation in GUI)
            if python_deps:
                if progress_callback:
                    progress_callback(f"Installing {len(python_deps)} Python packages...", 10)
                
                logger.info(f"Python dependencies required: {python_deps}")
                
                # Check if verification is enabled
                if self.config_manager and self.config_manager.plugins.verify_checksums:
                    # In a real implementation, this would prompt the user
                    logger.warning("Python dependencies require user confirmation")
                    # For now, we'll auto-install
                    if not self.installer.install_python_dependencies(python_deps):
                        logger.error("Failed to install Python dependencies")
                        return False
            
            # Install plugin dependencies in order
            total_plugins = len(plugin_deps) + 1  # +1 for target plugin
            for idx, (dep_id, dep_version) in enumerate(plugin_deps):
                # Skip if already installed
                if self.registry.is_registered(dep_id):
                    logger.info(f"Dependency {dep_id} already installed")
                    continue
                
                # Fetch dependency manifest
                dep_parts = dep_id.split('.')
                if len(dep_parts) < 3:
                    logger.error(f"Invalid dependency plugin ID: {dep_id}")
                    return False
                
                dep_manifest = self.repository.fetch_manifest(dep_id, dep_version)
                if not dep_manifest:
                    logger.error(f"Could not fetch manifest for dependency: {dep_id} v{dep_version}")
                    return False
                
                if progress_callback:
                    percent = 20 + int((idx / total_plugins) * 60)
                    progress_callback(f"Installing dependency {dep_manifest.metadata.name}...", percent)
                
                if not self.installer.install(dep_manifest):
                    logger.error(f"Failed to install dependency: {dep_id}")
                    return False
            
            # Install the target plugin
            if progress_callback:
                progress_callback(f"Installing {manifest.metadata.name}...", 80)
            
            if not self.installer.install(manifest, progress_callback):
                logger.error(f"Failed to install plugin: {plugin_id}")
                return False
            
            # Load and initialize the plugin
            if progress_callback:
                progress_callback("Loading plugin...", 95)
            
            # Reload plugins to pick up the new installation
            self.discover_and_load_plugins()
            
            if progress_callback:
                progress_callback("Installation complete", 100)
            
            logger.info(f"Successfully installed {plugin_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve and install plugin: {e}", exc_info=True)
            return False
    
    def update_plugin(
        self,
        plugin_id: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> bool:
        """
        Update a plugin to the latest version.
        
        Args:
            plugin_id: Plugin identifier
            progress_callback: Optional progress callback
            
        Returns:
            True if update succeeded
        """
        try:
            # Try to get current manifest from loaded plugin first
            current_manifest = self.registry.get_manifest(plugin_id)
            current_version = None
            
            if current_manifest:
                current_version = current_manifest.metadata.version
            else:
                # Plugin not loaded, try to read manifest from disk
                logger.debug(f"Plugin {plugin_id} not loaded, reading manifest from disk")
                installed_plugins = self.get_installed_plugins()
                
                for plugin_info in installed_plugins:
                    from pathlib import Path
                    import json
                    
                    manifest_path = Path(plugin_info['path']) / "manifest.json"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path, 'r') as f:
                                manifest_data = json.load(f)
                                if manifest_data.get('id') == plugin_id:
                                    current_version = manifest_data.get('version')
                                    break
                        except Exception as e:
                            logger.debug(f"Failed to read manifest from {manifest_path}: {e}")
                
                if not current_version:
                    logger.error(f"Plugin not found: {plugin_id}")
                    return False
            
            # Get latest version
            latest_version = self.repository.get_latest_version(plugin_id)
            if not latest_version:
                logger.error(f"Could not determine latest version for {plugin_id}")
                return False
            
            if Version(latest_version) <= Version(current_version):
                logger.info(f"Plugin {plugin_id} is already up to date ({current_version})")
                return True
            
            # Fetch new manifest
            new_manifest = self.repository.fetch_manifest(plugin_id, latest_version)
            if not new_manifest:
                logger.error(f"Could not fetch manifest for {plugin_id} v{latest_version}")
                return False
            
            # Unload current plugin if it's loaded
            if self.registry.is_registered(plugin_id):
                if progress_callback:
                    progress_callback(f"Unloading plugin...", 10)
                
                self.unload_plugin(plugin_id, reason="Updating to new version")
            
            # Install new version (which includes dependency resolution)
            return self.resolve_and_install(new_manifest, progress_callback)
            
        except Exception as e:
            logger.error(f"Failed to update plugin {plugin_id}: {e}", exc_info=True)
            return False
    
    def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        Uninstall a plugin from the system.
        
        This removes the plugin files and its associated cache directory.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if uninstallation succeeded
        """
        try:
            # Extract author and name
            parts = plugin_id.split('.')
            if len(parts) < 3:
                logger.error(f"Invalid plugin ID format: {plugin_id}")
                return False
            
            author = parts[1]
            plugin_name = parts[2]
            
            # Unload the plugin first
            if self.registry.is_registered(plugin_id):
                self.unload_plugin(plugin_id, reason="Uninstalling")
            
            # Uninstall from filesystem (including cache cleanup)
            if self.installer.uninstall(author, plugin_name, plugin_id=plugin_id):
                logger.info(f"Successfully uninstalled {plugin_id}")
                return True
            else:
                logger.error(f"Failed to uninstall {plugin_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error uninstalling plugin {plugin_id}: {e}", exc_info=True)
            return False
    
    def _load_plugin_translations(self, plugin_id: str, plugin_dir: Path, translation_manager) -> None:
        """
        Load plugin translations from i18n directory.
        
        Scans the plugin's i18n/translations/ directory for *.json files
        and loads them into the translation manager under the plugin namespace.
        
        Args:
            plugin_id: Plugin identifier (used as namespace)
            plugin_dir: Path to plugin directory
            translation_manager: Translation manager instance
        """
        i18n_dir = plugin_dir / "i18n" / "translations"
        
        if not i18n_dir.exists():
            logger.debug(f"No translations found for plugin: {plugin_id}")
            return
        
        loaded_count = 0
        for trans_file in i18n_dir.glob("*.json"):
            language_code = trans_file.stem
            try:
                with open(trans_file, 'r', encoding='utf-8') as f:
                    translation_data = json.load(f)
                
                if translation_manager.load_plugin_translation(
                    plugin_id, language_code, translation_data
                ):
                    loaded_count += 1
                    logger.debug(f"Loaded {language_code} translation for {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to load translation from {trans_file}: {e}")
        
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} translation(s) for plugin: {plugin_id}")
