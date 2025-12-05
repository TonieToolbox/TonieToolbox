#!/usr/bin/env python3
"""
Unit tests for plugin dependency checking in uninstall flow.
"""
import pytest
from pathlib import Path
import json
from unittest.mock import Mock, MagicMock, patch

try:
    from PyQt6.QtWidgets import QMessageBox
    from TonieToolbox.core.plugins.builtin.plugin_manager.ui.installed_tab import InstalledTab
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False
    pytestmark = pytest.mark.skip("PyQt6 not available")


@pytest.fixture
def mock_plugin_manager():
    """Create a mock plugin manager."""
    manager = Mock()
    manager.get_all_plugins = Mock(return_value={})
    manager.get_installed_plugins = Mock(return_value=[])
    manager.uninstall_plugin = Mock(return_value=True)
    manager.get_plugin = Mock(return_value=None)
    manager.disable_plugin = Mock()
    manager.unload_plugin = Mock()
    return manager


@pytest.fixture
def installed_tab(qtbot, mock_plugin_manager):
    """Create installed tab with mock manager."""
    if not HAS_PYQT6:
        pytest.skip("PyQt6 not available")
    
    tab = InstalledTab(mock_plugin_manager)
    qtbot.addWidget(tab)
    return tab


def test_get_dependent_plugins_no_dependencies(installed_tab, mock_plugin_manager):
    """Test _get_dependent_plugins when no plugins depend on target."""
    # Setup: No loaded plugins, no installed plugins
    mock_plugin_manager.get_all_plugins.return_value = {}
    mock_plugin_manager.get_installed_plugins.return_value = []
    
    # Act
    dependents = installed_tab._get_dependent_plugins("com.example.myplugin")
    
    # Assert
    assert dependents == []


def test_get_dependent_plugins_with_loaded_dependency(installed_tab, mock_plugin_manager):
    """Test _get_dependent_plugins when a loaded plugin depends on target."""
    # Setup: One loaded plugin that depends on target
    mock_plugin = Mock()
    mock_manifest = Mock()
    mock_manifest.metadata.dependencies = ["com.example.myplugin"]
    mock_plugin.get_manifest.return_value = mock_manifest
    
    mock_plugin_manager.get_all_plugins.return_value = {
        "com.example.dependent": mock_plugin
    }
    mock_plugin_manager.get_installed_plugins.return_value = []
    
    # Act
    dependents = installed_tab._get_dependent_plugins("com.example.myplugin")
    
    # Assert
    assert "com.example.dependent" in dependents


def test_get_dependent_plugins_with_unloaded_dependency(installed_tab, mock_plugin_manager, tmp_path):
    """Test _get_dependent_plugins when an unloaded plugin depends on target."""
    # Setup: Create manifest file for unloaded plugin
    plugin_dir = tmp_path / "dependent_plugin"
    plugin_dir.mkdir()
    
    manifest_data = {
        "id": "com.example.unloaded_dependent",
        "dependencies": {
            "plugins": ["com.example.myplugin"]
        }
    }
    
    manifest_path = plugin_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f)
    
    mock_plugin_manager.get_all_plugins.return_value = {}
    mock_plugin_manager.get_installed_plugins.return_value = [
        {"path": str(plugin_dir)}
    ]
    
    # Act
    dependents = installed_tab._get_dependent_plugins("com.example.myplugin")
    
    # Assert
    assert "com.example.unloaded_dependent" in dependents


def test_get_dependent_plugins_ignores_self(installed_tab, mock_plugin_manager):
    """Test _get_dependent_plugins ignores the plugin itself."""
    # Setup: Plugin depends on itself (edge case)
    mock_plugin = Mock()
    mock_manifest = Mock()
    mock_manifest.metadata.dependencies = ["com.example.myplugin"]
    mock_plugin.get_manifest.return_value = mock_manifest
    
    mock_plugin_manager.get_all_plugins.return_value = {
        "com.example.myplugin": mock_plugin
    }
    mock_plugin_manager.get_installed_plugins.return_value = []
    
    # Act
    dependents = installed_tab._get_dependent_plugins("com.example.myplugin")
    
    # Assert
    assert "com.example.myplugin" not in dependents


def test_handle_uninstall_blocks_when_dependencies_exist(installed_tab, mock_plugin_manager, qtbot, monkeypatch):
    """Test _handle_uninstall shows warning when dependencies exist."""
    # Setup: Mock dependency check to return dependents
    mock_warning = Mock(return_value=QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, 'warning', mock_warning)
    
    installed_tab._get_dependent_plugins = Mock(return_value=["com.example.dependent"])
    
    # Act
    installed_tab._handle_uninstall("com.example.myplugin")
    
    # Assert
    mock_warning.assert_called_once()
    call_args = mock_warning.call_args[0]
    assert "Cannot Uninstall" in call_args[1]
    assert "com.example.dependent" in call_args[2]
    
    # Should not proceed to uninstall
    mock_plugin_manager.uninstall_plugin.assert_not_called()


def test_handle_uninstall_proceeds_when_no_dependencies(installed_tab, mock_plugin_manager, qtbot, monkeypatch):
    """Test _handle_uninstall proceeds when no dependencies exist."""
    # Setup: No dependencies, user confirms
    installed_tab._get_dependent_plugins = Mock(return_value=[])
    
    mock_question = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)
    
    mock_info = Mock()
    monkeypatch.setattr(QMessageBox, 'information', mock_info)
    
    # Act
    installed_tab._handle_uninstall("com.example.myplugin")
    
    # Assert
    mock_question.assert_called_once()
    mock_plugin_manager.uninstall_plugin.assert_called_once_with("com.example.myplugin")
    mock_info.assert_called_once()


def test_handle_uninstall_user_cancels(installed_tab, mock_plugin_manager, qtbot, monkeypatch):
    """Test _handle_uninstall respects user cancellation."""
    # Setup: No dependencies, user cancels
    installed_tab._get_dependent_plugins = Mock(return_value=[])
    
    mock_question = Mock(return_value=QMessageBox.StandardButton.No)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)
    
    # Act
    installed_tab._handle_uninstall("com.example.myplugin")
    
    # Assert
    mock_question.assert_called_once()
    mock_plugin_manager.uninstall_plugin.assert_not_called()


def test_handle_uninstall_disables_loaded_plugin(installed_tab, mock_plugin_manager, qtbot, monkeypatch):
    """Test _handle_uninstall disables and unloads plugin if loaded."""
    # Setup: Plugin is loaded
    installed_tab._get_dependent_plugins = Mock(return_value=[])
    
    mock_plugin = Mock()
    mock_plugin_manager.get_plugin.return_value = mock_plugin
    
    mock_question = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)
    
    mock_info = Mock()
    monkeypatch.setattr(QMessageBox, 'information', mock_info)
    
    # Act
    installed_tab._handle_uninstall("com.example.myplugin")
    
    # Assert
    mock_plugin_manager.disable_plugin.assert_called_once_with("com.example.myplugin")
    mock_plugin_manager.unload_plugin.assert_called_once_with("com.example.myplugin")
    mock_plugin_manager.uninstall_plugin.assert_called_once_with("com.example.myplugin")


def test_handle_uninstall_handles_errors(installed_tab, mock_plugin_manager, qtbot, monkeypatch):
    """Test _handle_uninstall handles errors gracefully."""
    # Setup: Uninstall raises exception
    installed_tab._get_dependent_plugins = Mock(return_value=[])
    
    mock_plugin_manager.uninstall_plugin.side_effect = Exception("Uninstall failed")
    
    mock_question = Mock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, 'question', mock_question)
    
    mock_critical = Mock()
    monkeypatch.setattr(QMessageBox, 'critical', mock_critical)
    
    # Act
    installed_tab._handle_uninstall("com.example.myplugin")
    
    # Assert
    mock_critical.assert_called_once()
    call_args = mock_critical.call_args[0]
    assert "Error" in call_args[1]
    assert "Uninstall failed" in call_args[2]
