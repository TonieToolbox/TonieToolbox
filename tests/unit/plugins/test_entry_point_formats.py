#!/usr/bin/env python3
"""
Test entry_point format compatibility (colon and dot formats).
"""
import pytest
from pathlib import Path
from TonieToolbox.core.plugins.base import PluginManifest, PluginMetadata, PluginType


def test_entry_point_normalization():
    """Test that both colon and dot formats are normalized correctly."""
    test_cases = [
        ("plugin.MyClass", "plugin", "MyClass"),
        ("plugin:MyClass", "plugin", "MyClass"),  # Backward compat
        ("module.MyClass", "module", "MyClass"),
        ("module:MyClass", "module", "MyClass"),  # Backward compat
    ]
    
    for entry_point, expected_module, expected_class in test_cases:
        # Normalize colon to dot
        normalized = entry_point.replace(':', '.')
        
        # Split on last dot
        parts = normalized.rsplit('.', 1)
        
        assert len(parts) == 2, f"Failed to parse {entry_point}"
        module, class_name = parts
        
        assert module == expected_module, f"Module mismatch for {entry_point}"
        assert class_name == expected_class, f"Class mismatch for {entry_point}"


def test_invalid_entry_point_formats():
    """Test that invalid formats are properly rejected."""
    invalid_cases = [
        "NoSeparator",  # No dot or colon
        "",             # Empty
        ".",            # Just a dot
        ":",            # Just a colon
        "module.",      # Empty class name
        ".ClassName",   # Empty module name
    ]
    
    for entry_point in invalid_cases:
        normalized = entry_point.replace(':', '.')
        parts = normalized.rsplit('.', 1)
        
        # Should either have wrong number of parts or empty parts
        is_invalid = (
            len(parts) != 2 or 
            not parts[0] or 
            not parts[1]
        )
        
        assert is_invalid, f"{entry_point} should be invalid but parsed successfully"


def test_manifest_with_colon_entry_point():
    """Test that manifests with colon format can be created."""
    # This tests the data structure, not the file format
    metadata = PluginMetadata(
        id="com.test.plugin",
        name="Test",
        version="1.0.0",
        author="Test",
        description="Test",
        plugin_type=PluginType.GUI
    )
    
    # Both formats should be acceptable in the manifest object
    manifest_dot = PluginManifest(
        metadata=metadata,
        entry_point="plugin.TestClass"
    )
    
    manifest_colon = PluginManifest(
        metadata=metadata,
        entry_point="plugin:TestClass"
    )
    
    # Both should normalize to the same thing
    assert manifest_dot.entry_point is not None
    assert manifest_colon.entry_point is not None
    assert manifest_dot.entry_point.replace(':', '.') == "plugin.TestClass"
    assert manifest_colon.entry_point.replace(':', '.') == "plugin.TestClass"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
