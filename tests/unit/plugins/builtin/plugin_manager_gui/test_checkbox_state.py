#!/usr/bin/env python3
"""
Unit tests for installed plugin card checkbox state.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

try:
    from PyQt6.QtWidgets import QCheckBox
    from TonieToolbox.core.plugins.builtin.plugin_manager.ui.installed_plugin_card import InstalledPluginCard
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    pytestmark = pytest.mark.skip("PyQt6 not available")


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager."""
    manager = Mock()
    manager.is_plugin_enabled = Mock(return_value=False)
    return manager


@pytest.fixture
def mock_plugin():
    """Create a mock plugin with manifest."""
    plugin = Mock()
    manifest = Mock()
    metadata = Mock()
    metadata.name = "Test Plugin"
    metadata.display_name = None
    metadata.version = "1.0.0"
    metadata.author = "Test Author"
    metadata.description = "Test description"
    metadata.plugin_type = Mock(value="tool")
    manifest.metadata = metadata
    plugin.get_manifest = Mock(return_value=manifest)
    plugin.is_enabled = False
    return plugin


@patch('TonieToolbox.core.config.get_config_manager')
def test_checkbox_checked_when_loaded_and_enabled(mock_get_config, qtbot, mock_plugin_manager, mock_plugin):
    """Test checkbox is checked when plugin is loaded and enabled."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    # Setup: Plugin is loaded and enabled
    mock_plugin.is_enabled = True
    mock_plugin_manager.is_plugin_enabled.return_value = True
    
    # Create card
    card = InstalledPluginCard(
        plugin_id="com.test.plugin",
        plugin=mock_plugin,
        author="Test",
        plugin_name="plugin",
        plugin_path="/path/to/plugin",
        plugin_manager=mock_plugin_manager
    )
    qtbot.addWidget(card)
    
    # Assert: Checkbox should be checked
    assert card.enabled_checkbox.isChecked() is True


@patch('TonieToolbox.core.config.get_config_manager')
def test_checkbox_unchecked_when_in_disabled_list(mock_get_config, qtbot, mock_plugin_manager, mock_plugin):
    """Test checkbox is unchecked when plugin is in disabled list."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    # Setup: Plugin not enabled, and in disabled list
    mock_plugin_manager.is_plugin_enabled.return_value = False
    
    mock_config = Mock()
    mock_config.plugins.disabled_plugins = ['com.test.plugin']
    mock_get_config.return_value = mock_config
    
    # Create card
    card = InstalledPluginCard(
        plugin_id="com.test.plugin",
        plugin=mock_plugin,
        author="Test",
        plugin_name="plugin",
        plugin_path="/path/to/plugin",
        plugin_manager=mock_plugin_manager
    )
    qtbot.addWidget(card)
    
    # Assert: Checkbox should be unchecked
    assert card.enabled_checkbox.isChecked() is False


@patch('TonieToolbox.core.config.get_config_manager')
def test_checkbox_checked_when_not_loaded_but_not_disabled(mock_get_config, qtbot, mock_plugin_manager):
    """Test checkbox is checked when plugin is not loaded but not in disabled list."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    # Setup: Plugin not loaded (None), not enabled, but also not in disabled list
    mock_plugin_manager.is_plugin_enabled.return_value = False
    
    mock_config = Mock()
    mock_config.plugins.disabled_plugins = []  # Empty disabled list
    mock_get_config.return_value = mock_config
    
    # Create card with no plugin instance
    card = InstalledPluginCard(
        plugin_id="com.test.newplugin",
        plugin=None,  # Not loaded
        author="Test",
        plugin_name="newplugin",
        plugin_path="/path/to/newplugin",
        plugin_manager=mock_plugin_manager
    )
    qtbot.addWidget(card)
    
    # Assert: Checkbox should be checked (will be enabled on next load)
    assert card.enabled_checkbox.isChecked() is True


@patch('TonieToolbox.core.config.get_config_manager')
def test_checkbox_checked_when_config_unavailable(mock_get_config, qtbot, mock_plugin_manager, mock_plugin):
    """Test checkbox defaults to checked when config is unavailable."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    # Setup: Plugin not enabled, config access fails
    mock_plugin_manager.is_plugin_enabled.return_value = False
    mock_get_config.side_effect = Exception("Config unavailable")
    
    # Create card
    card = InstalledPluginCard(
        plugin_id="com.test.plugin",
        plugin=mock_plugin,
        author="Test",
        plugin_name="plugin",
        plugin_path="/path/to/plugin",
        plugin_manager=mock_plugin_manager
    )
    qtbot.addWidget(card)
    
    # Assert: Checkbox should default to checked when config unavailable
    assert card.enabled_checkbox.isChecked() is True


@patch('TonieToolbox.core.config.get_config_manager')
def test_checkbox_state_after_toggle(mock_get_config, qtbot, mock_plugin_manager, mock_plugin):
    """Test checkbox state reflects user toggle."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    # Setup
    mock_plugin_manager.is_plugin_enabled.return_value = True
    
    # Create card
    card = InstalledPluginCard(
        plugin_id="com.test.plugin",
        plugin=mock_plugin,
        author="Test",
        plugin_name="plugin",
        plugin_path="/path/to/plugin",
        plugin_manager=mock_plugin_manager
    )
    qtbot.addWidget(card)
    
    # Initial state: checked
    assert card.enabled_checkbox.isChecked() is True
    
    # User unchecks
    card.enabled_checkbox.setChecked(False)
    assert card.enabled_checkbox.isChecked() is False
    
    # User checks again
    card.enabled_checkbox.setChecked(True)
    assert card.enabled_checkbox.isChecked() is True
