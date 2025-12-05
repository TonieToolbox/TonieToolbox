#!/usr/bin/env python3
"""
Plugin registry for tracking loaded plugins and their components.
"""
from typing import Dict, List, Optional, Type, Any, Callable
from pathlib import Path
from ..utils import get_logger
from .base import BasePlugin, PluginManifest, PluginType, PluginSource

logger = get_logger(__name__)


class ComponentRegistry:
    """Registry for plugin-registered components with ownership tracking."""
    
    def __init__(self):
        """Initialize the component registry."""
        self._components: Dict[str, Dict[str, Any]] = {}
        self._component_owners: Dict[str, Dict[str, str]] = {}  # category -> {name -> plugin_id}
    
    def register(self, category: str, name: str, component: Any, plugin_id: Optional[str] = None) -> None:
        """
        Register a component.
        
        Args:
            category: Component category (e.g., "menu_items", "processors")
            name: Component name/identifier
            component: The component to register
            plugin_id: ID of plugin registering this component (for ownership tracking)
        """
        if category not in self._components:
            self._components[category] = {}
            self._component_owners[category] = {}
        
        self._components[category][name] = component
        if plugin_id:
            self._component_owners[category][name] = plugin_id
        logger.debug(f"Registered component '{name}' in category '{category}' (owner: {plugin_id})")
    
    def unregister(self, category: str, name: str) -> bool:
        """
        Unregister a component.
        
        Args:
            category: Component category
            name: Component name
            
        Returns:
            True if component was unregistered
        """
        if category in self._components and name in self._components[category]:
            del self._components[category][name]
            logger.debug(f"Unregistered component '{name}' from category '{category}'")
            return True
        return False
    
    def get(self, category: str, name: str) -> Optional[Any]:
        """Get a registered component."""
        return self._components.get(category, {}).get(name)
    
    def get_all(self, category: str) -> Dict[str, Any]:
        """Get all components in a category."""
        return self._components.get(category, {}).copy()
    
    def clear_category(self, category: str) -> None:
        """Clear all components in a category."""
        if category in self._components:
            self._components[category].clear()
            self._component_owners[category].clear()
    
    def get_registered_by_plugin(self, plugin_id: str) -> Dict[str, List[str]]:
        """
        Get all components registered by a specific plugin.
        
        Args:
            plugin_id: Plugin ID to search for
            
        Returns:
            Dict mapping category -> list of component names
        """
        result: Dict[str, List[str]] = {}
        for category, owners in self._component_owners.items():
            components = [name for name, owner in owners.items() if owner == plugin_id]
            if components:
                result[category] = components
        return result
    
    def unregister_all_for_plugin(self, plugin_id: str) -> int:
        """
        Unregister all components belonging to a plugin.
        
        Args:
            plugin_id: Plugin ID whose components to remove
            
        Returns:
            Number of components unregistered
        """
        count = 0
        components_to_remove = self.get_registered_by_plugin(plugin_id)
        
        for category, component_names in components_to_remove.items():
            for name in component_names:
                if self.unregister(category, name):
                    count += 1
        
        logger.debug(f"Unregistered {count} components for plugin '{plugin_id}'")
        return count


class PluginRegistry:
    """
    Registry for managing loaded plugins and their metadata.
    """
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, BasePlugin] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._plugin_dirs: Dict[str, Path] = {}
        self._plugin_sources: Dict[str, PluginSource] = {}  # Track plugin installation source
        self._component_registry = ComponentRegistry()
        logger.info("Plugin registry initialized")
    
    def register_plugin(
        self,
        plugin_id: str,
        plugin: BasePlugin,
        manifest: PluginManifest,
        plugin_dir: Path,
        source: PluginSource = PluginSource.COMMUNITY
    ) -> bool:
        """
        Register a plugin in the registry.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin: Plugin instance
            manifest: Plugin manifest
            plugin_dir: Directory where plugin is located
            source: Plugin installation source (builtin, community, local)
            
        Returns:
            True if plugin was registered successfully
        """
        if plugin_id in self._plugins:
            logger.warning(f"Plugin '{plugin_id}' is already registered")
            return False
        
        self._plugins[plugin_id] = plugin
        self._manifests[plugin_id] = manifest
        self._plugin_dirs[plugin_id] = plugin_dir
        self._plugin_sources[plugin_id] = source
        logger.info(f"Registered plugin: {manifest.metadata.name} v{manifest.metadata.version} (source: {source.value})")
        return True
    
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin from the registry.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if plugin was unregistered
        """
        if plugin_id not in self._plugins:
            logger.warning(f"Plugin '{plugin_id}' is not registered")
            return False
        
        # Clean up all plugin components
        self._component_registry.unregister_all_for_plugin(plugin_id)
        
        del self._plugins[plugin_id]
        del self._manifests[plugin_id]
        del self._plugin_dirs[plugin_id]
        if plugin_id in self._plugin_sources:
            del self._plugin_sources[plugin_id]
        logger.info(f"Unregistered plugin: {plugin_id}")
        return True
    
    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Get a plugin instance by ID."""
        return self._plugins.get(plugin_id)
    
    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get a plugin's manifest by ID."""
        return self._manifests.get(plugin_id)
    
    def get_plugin_dir(self, plugin_id: str) -> Optional[Path]:
        """Get a plugin's directory by ID."""
        return self._plugin_dirs.get(plugin_id)
    
    def get_all_plugin_ids(self) -> List[str]:
        """
        Get all registered plugin IDs.
        
        Returns:
            List of plugin IDs
        """
        return list(self._plugins.keys())
    
    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """Get all registered plugins."""
        return self._plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> Dict[str, BasePlugin]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Type of plugins to retrieve
            
        Returns:
            Dictionary of plugin_id -> plugin instance
        """
        return {
            plugin_id: plugin
            for plugin_id, plugin in self._plugins.items()
            if self._manifests[plugin_id].metadata.plugin_type == plugin_type
        }
    
    def get_enabled_plugins(self) -> Dict[str, BasePlugin]:
        """Get all currently enabled plugins."""
        return {
            plugin_id: plugin
            for plugin_id, plugin in self._plugins.items()
            if plugin.is_enabled
        }
    
    def is_registered(self, plugin_id: str) -> bool:
        """Check if a plugin is registered."""
        return plugin_id in self._plugins
    
    def get_plugin_source(self, plugin_id: str) -> Optional[PluginSource]:
        """Get the source of a plugin."""
        return self._plugin_sources.get(plugin_id)
    
    def get_plugins_by_source(self, source: PluginSource) -> Dict[str, BasePlugin]:
        """
        Get all plugins from a specific source.
        
        Args:
            source: Plugin source to filter by
            
        Returns:
            Dictionary of plugin_id -> plugin instance
        """
        return {
            plugin_id: plugin
            for plugin_id, plugin in self._plugins.items()
            if self._plugin_sources.get(plugin_id) == source
        }
    
    @property
    def component_registry(self) -> ComponentRegistry:
        """Get the component registry."""
        return self._component_registry
