#!/usr/bin/env python3
"""
Plugin loader for discovering and loading plugins from disk.
"""
import importlib.util
import sys
from pathlib import Path
from typing import List, Optional, Type, Tuple
from ..utils import get_logger
from .base import BasePlugin, PluginManifest, PluginSource

logger = get_logger(__name__)


class PluginLoader:
    """
    Loads plugins from the filesystem.
    
    Plugins can be loaded from:
    - Built-in plugins directory
    - User plugins directory (~/.tonietoolbox/plugins/)
    - Custom plugin directories from configuration
    """
    
    def __init__(self, builtin_plugin_dir: Optional[Path] = None, config_manager=None):
        """
        Initialize the plugin loader.
        
        Args:
            builtin_plugin_dir: Directory containing built-in plugins
            config_manager: Configuration manager for reading plugin settings
        """
        self.config_manager = config_manager
        self.builtin_plugin_dir = builtin_plugin_dir or Path(__file__).parent / "builtin"
        self.user_plugin_dir = Path.home() / ".tonietoolbox" / "plugins"
        self.custom_plugin_dirs: List[Path] = []
        
        # Load plugin directories from configuration
        if self.config_manager:
            configured_dirs = self.config_manager.plugins.plugin_directories
            for dir_path in configured_dirs:
                self.add_plugin_directory(Path(dir_path))
        
        logger.info("Plugin loader initialized")
    
    def add_plugin_directory(self, directory: Path) -> None:
        """
        Add a custom plugin directory to search.
        
        Args:
            directory: Path to plugin directory
        """
        if directory.exists() and directory.is_dir():
            self.custom_plugin_dirs.append(directory)
            logger.info(f"Added plugin directory: {directory}")
        else:
            logger.warning(f"Plugin directory does not exist: {directory}")
    
    def get_plugin_source(self, plugin_dir: Path) -> PluginSource:
        """
        Determine the source of a plugin based on its directory.
        
        Args:
            plugin_dir: Path to plugin directory
            
        Returns:
            PluginSource indicating where the plugin came from
        """
        try:
            # Check if plugin is in builtin directory
            if plugin_dir.is_relative_to(self.builtin_plugin_dir):
                return PluginSource.BUILTIN
            # Check if plugin is in user directory
            elif plugin_dir.is_relative_to(self.user_plugin_dir):
                return PluginSource.COMMUNITY
            # Check if plugin is in any custom directory
            else:
                for custom_dir in self.custom_plugin_dirs:
                    if plugin_dir.is_relative_to(custom_dir):
                        return PluginSource.LOCAL
                # Default to local if not in known directories
                return PluginSource.LOCAL
        except (ValueError, TypeError):
            # is_relative_to may fail on some platforms/paths
            return PluginSource.LOCAL
    
    def discover_plugins(self) -> List[Path]:
        """
        Discover all available plugin directories.
        
        Returns:
            List of paths to plugin directories
        """
        plugin_dirs = []
        
        # Scan builtin plugins (if enabled in config)
        load_builtin = True
        if self.config_manager:
            load_builtin = self.config_manager.plugins.load_builtin_plugins
        
        if load_builtin and self.builtin_plugin_dir.exists():
            plugin_dirs.extend(self._scan_directory(self.builtin_plugin_dir))
            logger.debug(f"Scanned builtin plugins: {self.builtin_plugin_dir}")
        elif not load_builtin:
            logger.info("Built-in plugins disabled in configuration")
        
        # Scan user plugins
        if self.user_plugin_dir.exists():
            plugin_dirs.extend(self._scan_directory(self.user_plugin_dir))
            logger.debug(f"Scanned user plugins: {self.user_plugin_dir}")
        
        # Scan custom directories (from config)
        for custom_dir in self.custom_plugin_dirs:
            if custom_dir.exists():
                plugin_dirs.extend(self._scan_directory(custom_dir))
                logger.debug(f"Scanned custom plugin directory: {custom_dir}")
        
        logger.info(f"Discovered {len(plugin_dirs)} plugins")
        return plugin_dirs
    
    def _scan_directory(self, directory: Path) -> List[Path]:
        """
        Scan a directory for plugin packages.
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of plugin directory paths
        """
        plugin_dirs = []
        
        # Check if the directory itself is a plugin (contains plugin.py)
        # Note: We check for plugin.py specifically, not __init__.py, to avoid
        # treating every Python package as a plugin
        if (directory / "plugin.py").exists():
            plugin_dirs.append(directory)
            return plugin_dirs
        
        # Otherwise scan subdirectories recursively
        # This handles both flat structure (builtin/) and nested structure (user/author/plugin/)
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if subdirectory itself is a plugin
                if (item / "plugin.py").exists():
                    plugin_dirs.append(item)
                # Or if it contains __init__.py (legacy plugin structure)
                elif (item / "__init__.py").exists():
                    # Check if it's actually a plugin by looking for BasePlugin subclass
                    # For now, accept it as a potential plugin
                    plugin_dirs.append(item)
                else:
                    # Not a plugin itself, scan its subdirectories (for author/plugin structure)
                    plugin_dirs.extend(self._scan_directory(item))
        
        return plugin_dirs
    
    def _load_manifest(self, plugin_dir: Path) -> Optional['PluginManifest']:
        """
        Load plugin manifest from manifest.json.
        
        Args:
            plugin_dir: Plugin directory
            
        Returns:
            PluginManifest or None if not found or invalid
        """
        try:
            from .base import load_manifest_from_json
            manifest_file = plugin_dir / "manifest.json"
            if manifest_file.exists():
                return load_manifest_from_json(manifest_file)
        except Exception as e:
            logger.debug(f"Could not load manifest from {plugin_dir}: {e}")
        return None
    
    def load_plugin(self, plugin_dir: Path, manifest: Optional['PluginManifest'] = None) -> Optional[BasePlugin]:
        """
        Load a plugin from a directory.
        
        Args:
            plugin_dir: Path to plugin directory
            manifest: Optional pre-loaded manifest (for entry_point support)
            
        Returns:
            Loaded plugin instance or None if loading failed
        """
        try:
            # Try plugin.py first, then __init__.py
            plugin_file = plugin_dir / "plugin.py"
            if not plugin_file.exists():
                plugin_file = plugin_dir / "__init__.py"
            
            if not plugin_file.exists():
                logger.error(f"No plugin.py or __init__.py found in {plugin_dir}")
                return None
            
            # Load manifest if not provided to get plugin_id for module naming
            if manifest is None:
                manifest = self._load_manifest(plugin_dir)
            
            # Get plugin_id from manifest for cleaner module naming
            plugin_id = manifest.metadata.id if manifest else None
            
            # If manifest with entry_point is provided, use it
            if manifest and manifest.entry_point:
                return self._load_plugin_from_entry_point(plugin_dir, plugin_file, manifest.entry_point, plugin_id)
            else:
                # Fallback to auto-discovery
                return self._auto_discover_plugin(plugin_dir, plugin_file, plugin_id)
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {plugin_dir}: {e}", exc_info=True)
            return None
    
    def _load_plugin_from_entry_point(
        self, 
        plugin_dir: Path, 
        plugin_file: Path, 
        entry_point: str,
        plugin_id: Optional[str] = None
    ) -> Optional[BasePlugin]:
        """
        Load plugin using explicit entry_point.
        
        Args:
            plugin_dir: Plugin directory
            plugin_file: Path to plugin.py or __init__.py
            entry_point: Entry point string (e.g., "plugin.MyPluginClass")
            plugin_id: Plugin ID from manifest for module naming
            
        Returns:
            Loaded plugin instance or None
        """
        try:
            # Parse entry point: "module.ClassName" or "module:ClassName" (backward compat)
            # Normalize colon to dot for consistency
            normalized_entry_point = entry_point.replace(':', '.')
            
            parts = normalized_entry_point.rsplit('.', 1)
            if len(parts) != 2:
                logger.error(f"Invalid entry_point format: {entry_point}. Expected 'module.ClassName' or 'module:ClassName'")
                return None
            
            module_name_in_plugin, class_name = parts
            
            # Determine the actual file to import
            if module_name_in_plugin == "plugin":
                target_file = plugin_dir / "plugin.py"
            elif module_name_in_plugin == "__init__":
                target_file = plugin_dir / "__init__.py"
            else:
                target_file = plugin_dir / f"{module_name_in_plugin}.py"
            
            if not target_file.exists():
                logger.error(f"Entry point module file not found: {target_file}")
                return None
            
            # Load the module with plugin ID for cleaner logging
            if plugin_id:
                module_name = f"TonieToolbox.plugin.{plugin_id}"
            else:
                module_name = f"tonietoolbox_plugin_{plugin_dir.name}_{module_name_in_plugin}"
            spec = importlib.util.spec_from_file_location(module_name, target_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {target_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Get the plugin class
            if not hasattr(module, class_name):
                logger.error(f"Class '{class_name}' not found in {target_file}")
                return None
            
            plugin_class = getattr(module, class_name)
            
            # Verify it's a BasePlugin subclass
            if not (isinstance(plugin_class, type) and issubclass(plugin_class, BasePlugin)):
                logger.error(f"{class_name} is not a subclass of BasePlugin")
                return None
            
            # Instantiate the plugin
            plugin = plugin_class()
            logger.info(f"Loaded plugin from entry_point: {entry_point}")
            return plugin
            
        except Exception as e:
            logger.error(f"Failed to load plugin from entry_point '{entry_point}': {e}", exc_info=True)
            return None
    
    def _auto_discover_plugin(self, plugin_dir: Path, plugin_file: Path, plugin_id: Optional[str] = None) -> Optional[BasePlugin]:
        """
        Auto-discover plugin class (legacy fallback method).
        
        Args:
            plugin_dir: Plugin directory
            plugin_file: Path to plugin.py or __init__.py
            plugin_id: Plugin ID from manifest for module naming
            
        Returns:
            Loaded plugin instance or None
        """
        try:
            # Try to import the plugin module with plugin ID for cleaner logging
            if plugin_id:
                module_name = f"TonieToolbox.plugin.{plugin_id}"
            else:
                module_name = f"tonietoolbox_plugin_{plugin_dir.name}"
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {plugin_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find the plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr is not BasePlugin and
                    not getattr(attr, '__abstractmethods__', None)):  # Skip abstract classes
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                logger.error(f"No plugin class found in {plugin_file}")
                return None
            
            # Instantiate the plugin
            plugin = plugin_class()
            logger.info(f"Loaded plugin via auto-discovery: {plugin_class.__name__} from {plugin_dir}")
            return plugin
            
        except Exception as e:
            logger.error(f"Auto-discovery failed for {plugin_dir}: {e}", exc_info=True)
            return None
    
    def load_all_plugins(self) -> List[Tuple[BasePlugin, Path, PluginSource]]:
        """
        Discover and load all available plugins.
        
        Returns:
            List of tuples (plugin_instance, plugin_dir_path, plugin_source)
        """
        plugins = []
        plugin_dirs = self.discover_plugins()
        
        for plugin_dir in plugin_dirs:
            plugin = self.load_plugin(plugin_dir)
            if plugin:
                source = self.get_plugin_source(plugin_dir)
                plugins.append((plugin, plugin_dir, source))
        
        logger.info(f"Loaded {len(plugins)} plugins successfully")
        return plugins
