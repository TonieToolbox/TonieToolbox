#!/usr/bin/env python3
"""
Dependency resolver for plugin dependencies.

Handles resolving plugin and Python dependencies, checking for conflicts,
and determining installation order.
"""
from typing import List, Dict, Tuple, Optional, Set
from packaging import version
from ..utils import get_logger
from .base import PluginManifest, PluginDependency, PluginDependencies
from .repository import PluginRepository

logger = get_logger(__name__)


class DependencyConflict(Exception):
    """Raised when dependency conflicts are detected."""
    pass


class DependencyResolver:
    """
    Resolves plugin dependencies and detects conflicts.
    
    Features:
    - Dependency graph construction
    - Circular dependency detection
    - Version conflict detection
    - Installation order calculation
    """
    
    def __init__(self, repository: PluginRepository, installed_plugins: Dict[str, str]):
        """
        Initialize the dependency resolver.
        
        Args:
            repository: PluginRepository instance
            installed_plugins: Dict of {plugin_id: version} for currently installed plugins
        """
        self.repository = repository
        self.installed_plugins = installed_plugins
        logger.debug(f"DependencyResolver initialized with {len(installed_plugins)} installed plugins")
    
    def resolve(
        self,
        plugin_id: str,
        plugin_version: str,
        manifest: PluginManifest
    ) -> Tuple[List[Tuple[str, str]], List[str], List[str]]:
        """
        Resolve all dependencies for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            plugin_version: Plugin version
            manifest: Plugin manifest
            
        Returns:
            Tuple of:
            - List of (plugin_id, version) to install (in order)
            - List of Python packages to install
            - List of warnings about potential conflicts
            
        Raises:
            DependencyConflict: If unresolvable conflicts detected
        """
        if not manifest.metadata.dependencies:
            logger.debug(f"No dependencies for {plugin_id}")
            return [], [], []
        
        # Build dependency graph
        graph = self._build_dependency_graph(plugin_id, plugin_version, manifest)
        
        # Check for circular dependencies
        self._check_circular_dependencies(graph)
        
        # Resolve plugin dependencies
        all_deps = self._resolve_plugin_dependencies(graph, manifest.metadata.dependencies)
        
        # Filter out the target plugin itself (only return actual dependencies)
        plugin_deps = [(dep_id, dep_ver) for dep_id, dep_ver in all_deps if dep_id != plugin_id]
        
        # Check for conflicts
        warnings = self._check_conflicts(plugin_deps)
        
        # Get Python dependencies (currently not stored separately, so empty)
        python_deps = []
        
        logger.info(f"Resolved {len(plugin_deps)} plugin dependencies and {len(python_deps)} Python packages")
        return plugin_deps, python_deps, warnings
    
    def _build_dependency_graph(
        self,
        plugin_id: str,
        plugin_version: str,
        manifest: PluginManifest,
        graph: Optional[Dict[str, Set[str]]] = None,
        visited: Optional[Set[str]] = None
    ) -> Dict[str, Set[str]]:
        """Build a dependency graph recursively."""
        if graph is None:
            graph = {}
        if visited is None:
            visited = set()
        
        if plugin_id in visited:
            return graph
        
        visited.add(plugin_id)
        dependencies = set()
        
        if manifest.metadata.dependencies:
            for dep_id in manifest.metadata.dependencies:
                dependencies.add(dep_id)
                
                # Recursively fetch dependencies of dependencies
                # Get latest version for dependency
                dep_version = self.repository.get_latest_version(dep_id)
                
                if dep_version:
                    dep_manifest = self.repository.fetch_manifest(dep_id, dep_version)
                    if dep_manifest:
                        self._build_dependency_graph(
                            dep_id,
                            dep_version,
                            dep_manifest,
                            graph,
                            visited
                        )
        
        graph[plugin_id] = dependencies
        return graph
    
    def _check_circular_dependencies(self, graph: Dict[str, Set[str]]) -> None:
        """
        Check for circular dependencies in the graph.
        
        Raises:
            DependencyConflict: If circular dependency detected
        """
        def has_cycle(node: str, visiting: Set[str], visited: Set[str]) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            
            visiting.add(node)
            for neighbor in graph.get(node, set()):
                if has_cycle(neighbor, visiting, visited):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False
        
        visiting: Set[str] = set()
        visited: Set[str] = set()
        
        for node in graph:
            if has_cycle(node, visiting, visited):
                raise DependencyConflict(f"Circular dependency detected involving {node}")
        
        logger.debug("No circular dependencies detected")
    
    def _resolve_plugin_dependencies(
        self,
        graph: Dict[str, Set[str]],
        dependencies: List[str]
    ) -> List[Tuple[str, str]]:
        """
        Resolve plugin dependencies and return installation order.
        
        Args:
            graph: Dependency graph
            dependencies: List of plugin IDs
        
        Returns:
            List of (plugin_id, version) in installation order
        """
        result = []
        resolved = set(self.installed_plugins.keys())
        
        def resolve_node(node: str) -> None:
            if node in resolved:
                return
            
            # Resolve dependencies first
            for dep_id in graph.get(node, set()):
                resolve_node(dep_id)
            
            # Get latest version for this plugin
            install_version = self.repository.get_latest_version(node)
            
            if install_version:
                result.append((node, install_version))
                resolved.add(node)
        
        # Resolve all nodes
        for node in graph:
            resolve_node(node)
        
        return result
    
    def _check_conflicts(self, plugin_deps: List[Tuple[str, str]]) -> List[str]:
        """
        Check for version conflicts with installed plugins.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        for plugin_id, new_version in plugin_deps:
            if plugin_id in self.installed_plugins:
                installed_version = self.installed_plugins[plugin_id]
                
                try:
                    installed_ver = version.parse(installed_version)
                    new_ver = version.parse(new_version)
                    
                    if new_ver > installed_ver:
                        warnings.append(
                            f"Plugin {plugin_id} will be upgraded from {installed_version} to {new_version}. "
                            f"This may break compatibility with other plugins that depend on the older version."
                        )
                    elif new_ver < installed_ver:
                        warnings.append(
                            f"Plugin {plugin_id} is already installed with a newer version ({installed_version}). "
                            f"Required version is {new_version}. Installation may cause issues."
                        )
                except Exception as e:
                    logger.warning(f"Could not compare versions for {plugin_id}: {e}")
        
        return warnings
    
    def check_python_dependencies(self, packages: List[str]) -> Tuple[List[str], List[str]]:
        """
        Check which Python packages need to be installed.
        
        Args:
            packages: List of package specifications (e.g., ["requests>=2.28.0"])
            
        Returns:
            Tuple of (missing_packages, installed_packages)
        """
        missing = []
        installed = []
        
        for package_spec in packages:
            # Parse package name (before >=, ==, etc.)
            package_name = package_spec.split('>=')[0].split('==')[0].split('<')[0].strip()
            
            try:
                import importlib
                importlib.import_module(package_name)
                installed.append(package_spec)
                logger.debug(f"Python package already installed: {package_name}")
            except ImportError:
                missing.append(package_spec)
                logger.debug(f"Python package missing: {package_name}")
        
        return missing, installed
