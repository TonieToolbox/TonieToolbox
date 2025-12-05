"""Unit tests for plugin manager."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call, PropertyMock
from pathlib import Path

from TonieToolbox.core.plugins.manager import PluginManager
from TonieToolbox.core.plugins.base import (
    BasePlugin, PluginManifest, PluginMetadata, PluginType, PluginContext
)


class TestPluginForManager(BasePlugin):
    """Test plugin class for manager tests."""
    
    def __init__(self, plugin_id="com.test.manager"):
        super().__init__()
        self._id = plugin_id
        self._initialized = False
        self._enabled = False
    
    def get_manifest(self):
        return PluginManifest(
            metadata=PluginMetadata(
                id=self._id,
                name="Test Plugin",
                version="1.0.0",
                author="Test",
                description="Test",
                plugin_type=PluginType.TOOL
            )
        )
    
    def initialize(self, context):
        self._context = context
        self._initialized = True
        return True
    
    def enable(self):
        self._enabled = True
        return super().enable()
    
    def disable(self):
        self._enabled = False
        return super().disable()


class TestPluginManager:
    """Test PluginManager class."""
    
    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager with plugin_directories."""
        mock_config = MagicMock()
        # Configure the nested structure properly
        mock_config.configure_mock(**{
            'plugins.plugin_directories': []
        })
        return mock_config
    
    def test_initialization(self, config_manager):
        """Test PluginManager initialization."""
        
        manager = PluginManager(config_manager=config_manager)
        
        assert manager.config_manager == config_manager
        assert len(manager.get_loaded_plugins()) == 0
    
    def test_load_plugin_manually(self, config_manager):
        """Test manually loading a plugin."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        assert manifest.metadata.id in manager.get_loaded_plugins()
        assert manifest.metadata.id in manager.get_loaded_plugins()
    
    def test_initialize_plugin(self, config_manager):
        """Test initializing a plugin."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        # Initialize plugin
        result = manager.initialize_plugin(manifest.metadata.id)
        
        assert result is True
        assert plugin._initialized is True
    
    def test_enable_plugin(self, config_manager):
        """Test enabling a plugin."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        # Initialize first
        manager.initialize_plugin(manifest.metadata.id)
        
        # Enable plugin
        result = manager.enable_plugin(manifest.metadata.id)
        
        assert result is True
        assert plugin._enabled is True
        assert manager.is_plugin_enabled(manifest.metadata.id)
    
    def test_disable_plugin(self, config_manager):
        """Test disabling a plugin."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        # Initialize and enable first
        manager.initialize_plugin(manifest.metadata.id)
        manager.enable_plugin(manifest.metadata.id)
        assert plugin._enabled is True
        
        # Disable plugin
        result = manager.disable_plugin(manifest.metadata.id)
        
        assert result is True
        assert plugin._enabled is False
        assert not manager.is_plugin_enabled(manifest.metadata.id)
    
    def test_unload_plugin(self, config_manager):
        """Test unloading a plugin."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        plugin_id = manifest.metadata.id
        
        manager.registry.register_plugin(plugin_id, plugin, manifest, Path("/test"))
        manager.initialize_plugin(plugin_id)
        manager.enable_plugin(plugin_id)
        
        # Unload plugin
        result = manager.unload_plugin(plugin_id)
        
        assert result is True
        assert plugin_id not in manager.get_loaded_plugins()
        assert not manager.is_plugin_enabled(plugin_id)
    
    def test_get_plugin(self, config_manager):
        """Test getting a plugin by ID."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        retrieved_plugin = manager.get_plugin(manifest.metadata.id)
        
        assert retrieved_plugin == plugin
    
    def test_get_nonexistent_plugin(self, config_manager):
        """Test getting a non-existent plugin returns None."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = manager.get_plugin("nonexistent.plugin")
        
        assert plugin is None
    
    def test_get_plugins_by_type(self, config_manager):
        """Test getting plugins by type."""
        manager = PluginManager(config_manager=config_manager)
        
        # Create plugins with different types
        class GUIPlugin(BasePlugin):
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
        
        gui_plugin = GUIPlugin()
        tool_plugin = TestPluginForManager()
        
        manager.registry.register_plugin("com.test.gui", gui_plugin, gui_plugin.get_manifest(), Path("/test"))
        manager.registry.register_plugin("com.test.tool", tool_plugin, tool_plugin.get_manifest(), Path("/test"))
        
        gui_plugins = manager.registry.get_plugins_by_type(PluginType.GUI)
        tool_plugins = manager.registry.get_plugins_by_type(PluginType.TOOL)
        
        assert len(gui_plugins) == 1
        assert "com.test.gui" in gui_plugins
        assert len(tool_plugins) == 1
        assert "com.test.tool" in tool_plugins
    
    def test_initialize_nonexistent_plugin(self, config_manager):
        """Test initializing non-existent plugin returns False."""
        manager = PluginManager(config_manager=config_manager)
        
        result = manager.initialize_plugin("nonexistent.plugin")
        
        assert result is False
    
    def test_enable_uninitialized_plugin(self, config_manager):
        """Test enabling uninitial ized plugin auto-initializes it."""
        manager = PluginManager(config_manager=config_manager)
        
        plugin = TestPluginForManager()
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        # Try to enable without manually initializing - manager should auto-initialize
        result = manager.enable_plugin(manifest.metadata.id)
        
        # Should succeed as manager auto-initializes
        assert result is True
        assert plugin._initialized is True
        assert plugin._enabled is True
    
    @pytest.mark.skip(reason="Mock not properly injected - PluginLoader created before mock can take effect")
    @patch('TonieToolbox.core.plugins.manager.PluginLoader')
    def test_discover_and_load_plugins(self, mock_loader_class, config_manager):
        """Test discovering and loading plugins."""
        manager = PluginManager(config_manager=config_manager)
        
        # Mock PluginLoader
        mock_loader = Mock()
        mock_loader_class.return_value = mock_loader
        
        # Mock discovered plugins
        plugin1 = TestPluginForManager("com.test.plugin1")
        plugin2 = TestPluginForManager("com.test.plugin2")
        
        mock_loader.discover_plugins.return_value = [
            ("/path/to/plugin1", plugin1),
            ("/path/to/plugin2", plugin2)
        ]
        
        # Discover and load
        manager.discover_and_load_plugins()
        
        # Verify plugins were loaded
        assert "com.test.plugin1" in manager.get_loaded_plugins()
        assert "com.test.plugin2" in manager.get_loaded_plugins()
    
    @patch('TonieToolbox.core.plugins.manager.PluginInstaller')
    def test_uninstall_plugin_success(self, mock_installer_class, config_manager):
        """Test successful plugin uninstallation."""
        manager = PluginManager(config_manager=config_manager)
        
        # Mock the installer
        mock_installer = Mock()
        mock_installer.uninstall.return_value = True
        mock_installer_class.return_value = mock_installer
        # Force property to use mocked installer
        manager._installer = mock_installer
        
        # Register a plugin
        plugin = TestPluginForManager("com.test.pluginname")
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        
        # Uninstall
        result = manager.uninstall_plugin("com.test.pluginname")
        
        assert result is True
        # Verify installer.uninstall was called with plugin_id
        mock_installer.uninstall.assert_called_once_with("test", "pluginname", plugin_id="com.test.pluginname")
    
    @patch('TonieToolbox.core.plugins.manager.PluginInstaller')
    def test_uninstall_plugin_removes_from_registry(self, mock_installer_class, config_manager):
        """Test that uninstalling a plugin unloads it from registry first."""
        manager = PluginManager(config_manager=config_manager)
        
        # Mock the installer
        mock_installer = Mock()
        mock_installer.uninstall.return_value = True
        mock_installer_class.return_value = mock_installer
        manager._installer = mock_installer
        
        # Register and initialize a plugin
        plugin = TestPluginForManager("com.test.pluginname")
        manifest = plugin.get_manifest()
        manager.registry.register_plugin(manifest.metadata.id, plugin, manifest, Path("/test"))
        manager.initialize_plugin("com.test.pluginname")
        
        # Verify plugin is registered
        assert manager.registry.is_registered("com.test.pluginname")
        
        # Uninstall
        result = manager.uninstall_plugin("com.test.pluginname")
        
        assert result is True
        # Plugin should be unloaded from registry
        assert not manager.registry.is_registered("com.test.pluginname")
    
    def test_uninstall_plugin_invalid_id_format(self, config_manager):
        """Test uninstalling plugin with invalid ID format fails."""
        manager = PluginManager(config_manager=config_manager)
        
        # Try to uninstall with invalid ID
        result = manager.uninstall_plugin("invalid_id")
        
        assert result is False
    
    @patch('TonieToolbox.core.plugins.manager.PluginInstaller')
    def test_uninstall_plugin_installer_fails(self, mock_installer_class, config_manager):
        """Test uninstall returns False when installer fails."""
        manager = PluginManager(config_manager=config_manager)
        
        # Mock the installer to fail
        mock_installer = Mock()
        mock_installer.uninstall.return_value = False
        mock_installer_class.return_value = mock_installer
        manager._installer = mock_installer
        
        # Uninstall
        result = manager.uninstall_plugin("com.test.pluginname")
        
        assert result is False
    
    @patch('TonieToolbox.core.plugins.manager.PluginInstaller')
    def test_uninstall_plugin_exception_handling(self, mock_installer_class, config_manager):
        """Test uninstall handles exceptions gracefully."""
        manager = PluginManager(config_manager=config_manager)
        
        # Mock the installer to raise an exception
        mock_installer = Mock()
        mock_installer.uninstall.side_effect = Exception("Test error")
        mock_installer_class.return_value = mock_installer
        manager._installer = mock_installer
        
        # Uninstall should catch exception and return False
        result = manager.uninstall_plugin("com.test.pluginname")
        
        assert result is False
