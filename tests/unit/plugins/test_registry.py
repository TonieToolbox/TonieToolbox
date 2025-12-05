"""Unit tests for plugin registry."""

import pytest
from unittest.mock import Mock
from pathlib import Path

from TonieToolbox.core.plugins.registry import PluginRegistry, ComponentRegistry
from TonieToolbox.core.plugins.base import (
    BasePlugin, PluginManifest, PluginMetadata, PluginType
)


class TestPluginClass(BasePlugin):
    """Test plugin class for registry tests."""
    
    def get_manifest(self):
        return PluginManifest(
            metadata=PluginMetadata(
                id="com.test.registry",
                name="Test Plugin",
                version="1.0.0",
                author="Test",
                description="Test",
                plugin_type=PluginType.TOOL
            )
        )
    
    def initialize(self, context):
        return True


class TestPluginRegistry:
    """Test PluginRegistry class."""
    
    def test_register_plugin(self):
        """Test registering a plugin."""
        registry = PluginRegistry()
        plugin = TestPluginClass()
        manifest = plugin.get_manifest()
        
        registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        assert registry.is_registered(manifest.metadata.id)
        assert registry.get_plugin(manifest.metadata.id) == plugin
        assert registry.get_manifest(manifest.metadata.id) == manifest
    
    def test_unregister_plugin(self):
        """Test unregistering a plugin."""
        registry = PluginRegistry()
        plugin = TestPluginClass()
        manifest = plugin.get_manifest()
        plugin_id = manifest.metadata.id
        
        registry.register_plugin(plugin_id, plugin, manifest, Path("/test"))
        assert registry.is_registered(plugin_id)
        
        registry.unregister_plugin(plugin_id)
        assert not registry.is_registered(plugin_id)
        assert registry.get_plugin(plugin_id) is None
    
    def test_get_all_plugins(self):
        """Test getting all registered plugins."""
        registry = PluginRegistry()
        plugin1 = TestPluginClass()
        plugin2 = TestPluginClass()
        
        registry.register_plugin("plugin1", plugin1, plugin1.get_manifest(), Path("/test1"))
        registry.register_plugin("plugin2", plugin2, plugin2.get_manifest(), Path("/test2"))
        
        all_plugins = registry.get_all_plugins()
        assert len(all_plugins) == 2
        assert "plugin1" in all_plugins
        assert "plugin2" in all_plugins
    
    def test_get_plugins_by_type(self):
        """Test getting plugins by type."""
        registry = PluginRegistry()
        
        # Create plugins with different types
        class GUITestPlugin(BasePlugin):
            def get_manifest(self):
                return PluginManifest(
                    metadata=PluginMetadata(
                        id="com.test.gui",
                        name="GUI Plugin",
                        version="1.0.0",
                        author="Test",
                        description="Test",
                        plugin_type=PluginType.GUI
                    )
                )
            def initialize(self, context):
                return True
        
        gui_plugin = GUITestPlugin()
        tool_plugin = TestPluginClass()
        
        registry.register_plugin("gui", gui_plugin, gui_plugin.get_manifest(), Path("/test/gui"))
        registry.register_plugin("tool", tool_plugin, tool_plugin.get_manifest(), Path("/test/tool"))
        
        gui_plugins = registry.get_plugins_by_type(PluginType.GUI)
        tool_plugins = registry.get_plugins_by_type(PluginType.TOOL)
        
        assert len(gui_plugins) == 1
        assert "gui" in gui_plugins
        assert len(tool_plugins) == 1
        assert "tool" in tool_plugins


class TestComponentRegistry:
    """Test ComponentRegistry class."""
    
    def test_register_component(self):
        """Test registering a component."""
        registry = ComponentRegistry()
        
        registry.register("menu_items", "test_item", {"label": "Test"})
        
        assert registry.get("menu_items", "test_item") is not None
        assert registry.get("menu_items", "test_item") == {"label": "Test"}
    
    def test_unregister_component(self):
        """Test unregistering a component."""
        registry = ComponentRegistry()
        
        registry.register("menu_items", "test_item", {"label": "Test"})
        assert registry.get("menu_items", "test_item") is not None
        
        registry.unregister("menu_items", "test_item")
        assert registry.get("menu_items", "test_item") is None
    
    def test_get_all_components(self):
        """Test getting all components of a category."""
        registry = ComponentRegistry()
        
        registry.register("menu_items", "item1", {"label": "Item 1"})
        registry.register("menu_items", "item2", {"label": "Item 2"})
        registry.register("dialogs", "dialog1", {"title": "Dialog 1"})
        
        menu_items = registry.get_all("menu_items")
        dialogs = registry.get_all("dialogs")
        
        assert len(menu_items) == 2
        assert "item1" in menu_items
        assert "item2" in menu_items
        assert len(dialogs) == 1
        assert "dialog1" in dialogs
    
    def test_get_nonexistent_component(self):
        """Test getting a non-existent component returns None."""
        registry = ComponentRegistry()
        
        assert registry.get("menu_items", "nonexistent") is None
    
    def test_clear_category(self):
        """Test clearing all components in a category."""
        registry = ComponentRegistry()
        
        registry.register("menu_items", "item1", {"label": "Item 1"})
        registry.register("menu_items", "item2", {"label": "Item 2"})
        
        registry.clear_category("menu_items")
        
        assert len(registry.get_all("menu_items")) == 0
    
    def test_multiple_categories(self):
        """Test managing multiple component categories."""
        registry = ComponentRegistry()
        
        registry.register("menu_items", "item1", {"label": "Item 1"})
        registry.register("toolbar_buttons", "button1", {"icon": "icon.png"})
        registry.register("dialogs", "dialog1", {"title": "Dialog"})
        
        assert registry.get("menu_items", "item1") is not None
        assert registry.get("toolbar_buttons", "button1") is not None
        assert registry.get("dialogs", "dialog1") is not None
        
        # Categories should be independent
        registry.clear_category("menu_items")
        assert registry.get("menu_items", "item1") is None
        assert registry.get("toolbar_buttons", "button1") is not None
        assert registry.get("dialogs", "dialog1") is not None
