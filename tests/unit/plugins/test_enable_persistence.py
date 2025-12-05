#!/usr/bin/env python3
"""
Unit tests for plugin enable/disable persistence.
"""
import pytest
from unittest.mock import Mock, MagicMock
from TonieToolbox.core.plugins.manager import PluginManager
from TonieToolbox.core.plugins.base import BasePlugin, PluginManifest, PluginMetadata, PluginType


@pytest.fixture
def mock_config_manager():
    """Create a mock config manager."""
    config_manager = Mock()
    plugins_config = Mock()
    plugins_config.disabled_plugins = []
    plugins_config.plugin_directories = []  # Add this for PluginLoader
    config_manager.plugins = plugins_config
    config_manager.save_config = Mock()
    return config_manager


@pytest.fixture
def plugin_manager(mock_config_manager):
    """Create a plugin manager with mock config."""
    return PluginManager(config_manager=mock_config_manager)


@pytest.fixture
def mock_plugin():
    """Create a mock plugin."""
    plugin = Mock(spec=BasePlugin)
    plugin.is_enabled = False
    plugin.initialize = Mock(return_value=True)
    plugin.enable = Mock(return_value=True)
    plugin.disable = Mock(return_value=True)
    
    # Mock manifest
    manifest = PluginManifest(
        metadata=PluginMetadata(
            id="com.example.testplugin",
            name="Test Plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin",
            plugin_type=PluginType.TOOL
        )
    )
    plugin.get_manifest = Mock(return_value=manifest)
    
    return plugin


def test_enable_plugin_removes_from_disabled_list(plugin_manager, mock_plugin, mock_config_manager):
    """Test enabling a plugin removes it from disabled_plugins list."""
    plugin_id = "com.example.testplugin"
    
    # Setup: Plugin is in disabled list
    mock_config_manager.plugins.disabled_plugins = [plugin_id]
    
    # Register and initialize plugin
    plugin_manager.registry.register_plugin(
        plugin_id,
        mock_plugin,
        mock_plugin.get_manifest(),
        Mock()
    )
    plugin_manager._initialized_plugins[plugin_id] = True
    
    # Act: Enable the plugin
    result = plugin_manager.enable_plugin(plugin_id)
    
    # Assert
    assert result is True
    mock_plugin.enable.assert_called_once()
    
    # Check that plugin was removed from disabled list
    assert plugin_id not in mock_config_manager.plugins.disabled_plugins
    mock_config_manager.save_config.assert_called_once()


def test_enable_plugin_no_config_manager(plugin_manager, mock_plugin):
    """Test enabling a plugin without config manager doesn't crash."""
    plugin_id = "com.example.testplugin"
    plugin_manager.config_manager = None
    
    # Register and initialize plugin
    plugin_manager.registry.register_plugin(
        plugin_id,
        mock_plugin,
        mock_plugin.get_manifest(),
        Mock()
    )
    plugin_manager._initialized_plugins[plugin_id] = True
    
    # Act: Enable the plugin
    result = plugin_manager.enable_plugin(plugin_id)
    
    # Assert: Should work without config manager
    assert result is True
    mock_plugin.enable.assert_called_once()


def test_disable_plugin_adds_to_disabled_list(plugin_manager, mock_plugin, mock_config_manager):
    """Test disabling a plugin adds it to disabled_plugins list."""
    plugin_id = "com.example.testplugin"
    
    # Setup: Plugin is enabled
    mock_plugin.is_enabled = True
    mock_config_manager.plugins.disabled_plugins = []
    
    # Register plugin
    plugin_manager.registry.register_plugin(
        plugin_id,
        mock_plugin,
        mock_plugin.get_manifest(),
        Mock()
    )
    
    # Act: Disable the plugin
    result = plugin_manager.disable_plugin(plugin_id)
    
    # Assert
    assert result is True
    mock_plugin.disable.assert_called_once()
    
    # Check that plugin was added to disabled list
    assert plugin_id in mock_config_manager.plugins.disabled_plugins
    mock_config_manager.save_config.assert_called_once()


def test_disable_plugin_already_in_list(plugin_manager, mock_plugin, mock_config_manager):
    """Test disabling a plugin that's already in disabled list doesn't duplicate."""
    plugin_id = "com.example.testplugin"
    
    # Setup: Plugin already in disabled list
    mock_plugin.is_enabled = True
    mock_config_manager.plugins.disabled_plugins = [plugin_id]
    
    # Register plugin
    plugin_manager.registry.register_plugin(
        plugin_id,
        mock_plugin,
        mock_plugin.get_manifest(),
        Mock()
    )
    
    # Act: Disable the plugin
    result = plugin_manager.disable_plugin(plugin_id)
    
    # Assert
    assert result is True
    mock_plugin.disable.assert_called_once()
    
    # Check that plugin is in list only once
    assert mock_config_manager.plugins.disabled_plugins.count(plugin_id) == 1


def test_enable_disable_cycle_persists_correctly(plugin_manager, mock_plugin, mock_config_manager):
    """Test enable/disable cycle maintains correct persistence state."""
    plugin_id = "com.example.testplugin"
    
    # Setup
    mock_config_manager.plugins.disabled_plugins = []
    
    # Register and initialize plugin
    plugin_manager.registry.register_plugin(
        plugin_id,
        mock_plugin,
        mock_plugin.get_manifest(),
        Mock()
    )
    plugin_manager._initialized_plugins[plugin_id] = True
    
    # Act 1: Enable plugin
    plugin_manager.enable_plugin(plugin_id)
    
    # Assert 1: Not in disabled list
    assert plugin_id not in mock_config_manager.plugins.disabled_plugins
    
    # Act 2: Disable plugin
    mock_plugin.is_enabled = True  # Simulate enabled state
    plugin_manager.disable_plugin(plugin_id)
    
    # Assert 2: Now in disabled list
    assert plugin_id in mock_config_manager.plugins.disabled_plugins
    
    # Act 3: Enable again
    mock_plugin.is_enabled = False
    plugin_manager.enable_plugin(plugin_id)
    
    # Assert 3: Still not in disabled list
    assert plugin_id not in mock_config_manager.plugins.disabled_plugins
    
    # Config should have been saved 2 times (enable removed it once, disable added it once)
    # Second enable doesn't save because it's not in the disabled list
    assert mock_config_manager.save_config.call_count == 2
