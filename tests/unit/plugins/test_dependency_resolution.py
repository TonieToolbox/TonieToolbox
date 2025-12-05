#!/usr/bin/env python3
"""
Tests for plugin dependency resolution and initialization ordering.
"""
import pytest
from unittest.mock import Mock, MagicMock
from TonieToolbox.core.plugins.manager import PluginManager
from TonieToolbox.core.plugins.base import PluginManifest, PluginMetadata, BasePlugin


class MockPlugin(BasePlugin):
    """Mock plugin for testing."""
    
    def __init__(self, plugin_id: str, dependencies: list = None):
        super().__init__()
        self.plugin_id = plugin_id
        self.dependencies = dependencies or []
        self._initialized = False
        self._enabled = False
    
    def get_manifest(self) -> PluginManifest:
        """Return mock manifest with dependencies."""
        metadata = PluginMetadata(
            id=self.plugin_id,
            name=f"Test Plugin {self.plugin_id}",
            version="1.0.0",
            author="Test",
            description="Test plugin",
            plugin_type="tool"
        )
        
        # Build dependencies in manifest format
        plugin_deps = [{"id": dep_id} for dep_id in self.dependencies]
        
        manifest = PluginManifest(metadata=metadata)
        manifest.dependencies = {"plugins": plugin_deps}
        
        return manifest
    
    def initialize(self, context):
        self._initialized = True
        return True
    
    def enable(self):
        self._enabled = True
        return True


class TestDependencyResolution:
    """Test plugin dependency resolution."""
    
    def test_simple_dependency_chain(self):
        """Test that plugins are ordered correctly with simple A -> B -> C chain."""
        manager = PluginManager()
        
        # Create plugins: C depends on B, B depends on A, A has no dependencies
        plugin_a = MockPlugin("plugin.a")
        plugin_b = MockPlugin("plugin.b", dependencies=["plugin.a"])
        plugin_c = MockPlugin("plugin.c", dependencies=["plugin.b"])
        
        # Register plugins
        manager.registry.register_plugin("plugin.a", plugin_a, plugin_a.get_manifest(), None)
        manager.registry.register_plugin("plugin.b", plugin_b, plugin_b.get_manifest(), None)
        manager.registry.register_plugin("plugin.c", plugin_c, plugin_c.get_manifest(), None)
        
        # Resolve initialization order
        ordered = manager._resolve_initialization_order(["plugin.a", "plugin.b", "plugin.c"])
        
        # Verify order: A must come before B, B must come before C
        assert ordered.index("plugin.a") < ordered.index("plugin.b")
        assert ordered.index("plugin.b") < ordered.index("plugin.c")
    
    def test_multiple_dependencies(self):
        """Test plugin with multiple dependencies."""
        manager = PluginManager()
        
        # Create plugins: D depends on both B and C
        plugin_a = MockPlugin("plugin.a")
        plugin_b = MockPlugin("plugin.b", dependencies=["plugin.a"])
        plugin_c = MockPlugin("plugin.c", dependencies=["plugin.a"])
        plugin_d = MockPlugin("plugin.d", dependencies=["plugin.b", "plugin.c"])
        
        # Register plugins
        manager.registry.register_plugin("plugin.a", plugin_a, plugin_a.get_manifest(), None)
        manager.registry.register_plugin("plugin.b", plugin_b, plugin_b.get_manifest(), None)
        manager.registry.register_plugin("plugin.c", plugin_c, plugin_c.get_manifest(), None)
        manager.registry.register_plugin("plugin.d", plugin_d, plugin_d.get_manifest(), None)
        
        # Resolve initialization order
        ordered = manager._resolve_initialization_order(["plugin.a", "plugin.b", "plugin.c", "plugin.d"])
        
        # Verify A comes first
        assert ordered[0] == "plugin.a"
        # Verify B and C come before D
        assert ordered.index("plugin.b") < ordered.index("plugin.d")
        assert ordered.index("plugin.c") < ordered.index("plugin.d")
    
    def test_no_dependencies(self):
        """Test plugins with no dependencies maintain some order."""
        manager = PluginManager()
        
        # Create independent plugins
        plugin_a = MockPlugin("plugin.a")
        plugin_b = MockPlugin("plugin.b")
        plugin_c = MockPlugin("plugin.c")
        
        # Register plugins
        manager.registry.register_plugin("plugin.a", plugin_a, plugin_a.get_manifest(), None)
        manager.registry.register_plugin("plugin.b", plugin_b, plugin_b.get_manifest(), None)
        manager.registry.register_plugin("plugin.c", plugin_c, plugin_c.get_manifest(), None)
        
        # Resolve initialization order
        ordered = manager._resolve_initialization_order(["plugin.c", "plugin.a", "plugin.b"])
        
        # All plugins should be present
        assert len(ordered) == 3
        assert set(ordered) == {"plugin.a", "plugin.b", "plugin.c"}
    
    def test_tonies_viewer_loader_dependency(self):
        """Test real-world case: ToniesViewer depends on ToniesLoader."""
        manager = PluginManager()
        
        # Create plugins mimicking the real scenario
        tonies_loader = MockPlugin("com.tonietoolbox.tonies_loader")
        tonies_viewer = MockPlugin("com.tonietoolbox.tonies_viewer", 
                                   dependencies=["com.tonietoolbox.tonies_loader"])
        
        # Register plugins
        manager.registry.register_plugin("com.tonietoolbox.tonies_loader", 
                                        tonies_loader, 
                                        tonies_loader.get_manifest(), 
                                        None)
        manager.registry.register_plugin("com.tonietoolbox.tonies_viewer", 
                                        tonies_viewer, 
                                        tonies_viewer.get_manifest(), 
                                        None)
        
        # Resolve initialization order
        ordered = manager._resolve_initialization_order([
            "com.tonietoolbox.tonies_viewer",
            "com.tonietoolbox.tonies_loader"
        ])
        
        # ToniesLoader must come before ToniesViewer
        assert ordered.index("com.tonietoolbox.tonies_loader") < ordered.index("com.tonietoolbox.tonies_viewer")
    
    def test_circular_dependency_handling(self):
        """Test that circular dependencies don't cause infinite loop."""
        manager = PluginManager()
        
        # Create circular dependency: A -> B -> A
        plugin_a = MockPlugin("plugin.a", dependencies=["plugin.b"])
        plugin_b = MockPlugin("plugin.b", dependencies=["plugin.a"])
        
        # Register plugins
        manager.registry.register_plugin("plugin.a", plugin_a, plugin_a.get_manifest(), None)
        manager.registry.register_plugin("plugin.b", plugin_b, plugin_b.get_manifest(), None)
        
        # Resolve initialization order (should not hang)
        ordered = manager._resolve_initialization_order(["plugin.a", "plugin.b"])
        
        # Both plugins should be in the result (order doesn't matter for circular deps)
        assert len(ordered) == 2
        assert set(ordered) == {"plugin.a", "plugin.b"}
    
    def test_missing_dependency_ignored(self):
        """Test that missing dependencies are gracefully ignored."""
        manager = PluginManager()
        
        # Plugin B depends on non-existent plugin C
        plugin_a = MockPlugin("plugin.a")
        plugin_b = MockPlugin("plugin.b", dependencies=["plugin.c"])  # C doesn't exist
        
        # Register only A and B
        manager.registry.register_plugin("plugin.a", plugin_a, plugin_a.get_manifest(), None)
        manager.registry.register_plugin("plugin.b", plugin_b, plugin_b.get_manifest(), None)
        
        # Resolve initialization order (should work despite missing dependency)
        ordered = manager._resolve_initialization_order(["plugin.a", "plugin.b"])
        
        # Both plugins should be present
        assert len(ordered) == 2
        assert set(ordered) == {"plugin.a", "plugin.b"}
