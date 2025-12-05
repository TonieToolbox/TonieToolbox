#!/usr/bin/env python3
"""
Unit tests for recursive plugin discovery (author/plugin structure).
"""
import pytest
from pathlib import Path
from unittest.mock import Mock
from TonieToolbox.core.plugins.loader import PluginLoader


@pytest.fixture
def temp_plugin_structure(tmp_path):
    """Create a temporary plugin directory structure."""
    # Create nested author/plugin structure
    author_dir = tmp_path / "test_author"
    author_dir.mkdir()
    
    plugin1_dir = author_dir / "plugin1"
    plugin1_dir.mkdir()
    (plugin1_dir / "plugin.py").write_text("# Plugin 1")
    (plugin1_dir / "manifest.json").write_text('{"id": "test.plugin1"}')
    
    plugin2_dir = author_dir / "plugin2"
    plugin2_dir.mkdir()
    (plugin2_dir / "plugin.py").write_text("# Plugin 2")
    (plugin2_dir / "manifest.json").write_text('{"id": "test.plugin2"}')
    
    # Create a flat structure plugin for comparison
    flat_plugin = tmp_path / "flat_plugin"
    flat_plugin.mkdir()
    (flat_plugin / "plugin.py").write_text("# Flat plugin")
    (flat_plugin / "manifest.json").write_text('{"id": "test.flat"}')
    
    return tmp_path


def test_scan_directory_finds_nested_plugins(temp_plugin_structure):
    """Test that _scan_directory recursively finds plugins in nested structure."""
    loader = PluginLoader()
    
    # Scan the root directory
    plugin_dirs = loader._scan_directory(temp_plugin_structure)
    
    # Should find all 3 plugins (2 nested + 1 flat)
    assert len(plugin_dirs) == 3
    
    # Verify all plugins are found
    plugin_names = [p.name for p in plugin_dirs]
    assert "plugin1" in plugin_names
    assert "plugin2" in plugin_names
    assert "flat_plugin" in plugin_names


def test_scan_directory_ignores_hidden_dirs(tmp_path):
    """Test that _scan_directory ignores hidden directories."""
    # Create hidden directory with plugin
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "plugin.py").write_text("# Hidden")
    
    # Create normal plugin
    normal_dir = tmp_path / "normal"
    normal_dir.mkdir()
    (normal_dir / "plugin.py").write_text("# Normal")
    
    loader = PluginLoader()
    plugin_dirs = loader._scan_directory(tmp_path)
    
    # Should only find normal plugin, not hidden
    assert len(plugin_dirs) == 1
    assert plugin_dirs[0].name == "normal"


def test_scan_directory_handles_empty_dirs(tmp_path):
    """Test that _scan_directory handles empty directories."""
    # Create empty directory structure
    (tmp_path / "empty1").mkdir()
    (tmp_path / "empty2").mkdir()
    
    # Create one actual plugin
    plugin_dir = tmp_path / "actual_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("# Plugin")
    
    loader = PluginLoader()
    plugin_dirs = loader._scan_directory(tmp_path)
    
    # Should only find the actual plugin
    assert len(plugin_dirs) == 1
    assert plugin_dirs[0].name == "actual_plugin"


def test_scan_directory_stops_at_plugin_level(tmp_path):
    """Test that _scan_directory doesn't recurse into plugin directories."""
    # Create plugin with nested structure inside it
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("# Main plugin")
    
    # Create subdirectory inside plugin (should not be treated as separate plugin)
    subdir = plugin_dir / "submodule"
    subdir.mkdir()
    (subdir / "plugin.py").write_text("# Not a separate plugin")
    
    loader = PluginLoader()
    plugin_dirs = loader._scan_directory(tmp_path)
    
    # Should only find the top-level plugin
    assert len(plugin_dirs) == 1
    assert plugin_dirs[0].name == "my_plugin"


def test_scan_directory_three_levels_deep(tmp_path):
    """Test scanning with 3 levels: root/author/category/plugin."""
    # Create even deeper nesting
    author_dir = tmp_path / "author"
    author_dir.mkdir()
    
    category_dir = author_dir / "gui_plugins"
    category_dir.mkdir()
    
    plugin_dir = category_dir / "my_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("# Deep plugin")
    
    loader = PluginLoader()
    plugin_dirs = loader._scan_directory(tmp_path)
    
    # Should find the deeply nested plugin
    assert len(plugin_dirs) == 1
    assert plugin_dirs[0].name == "my_plugin"
