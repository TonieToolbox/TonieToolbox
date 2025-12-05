"""Tests for plugin manifest loading and validation."""
import pytest
import json
from pathlib import Path
from TonieToolbox.core.plugins import (
    load_manifest_from_json,
    PluginManifest,
    PluginType,
    PluginManifestError
)


@pytest.fixture
def valid_manifest_dict():
    """Valid manifest dictionary."""
    return {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "gui",
        "entry_point": "plugin:TestPlugin",
        "dependencies": {
            "plugins": []
        },
        "config_schema": {},
        "permissions": []
    }


@pytest.fixture
def manifest_file(tmp_path, valid_manifest_dict):
    """Create a temporary manifest.json file."""
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(valid_manifest_dict, f)
    return manifest_path


def test_load_manifest_from_json_valid(manifest_file):
    """Test loading a valid manifest file."""
    manifest = load_manifest_from_json(manifest_file)
    
    assert isinstance(manifest, PluginManifest)
    assert manifest.metadata.id == "com.test.plugin"
    assert manifest.metadata.name == "Test Plugin"
    assert manifest.metadata.version == "1.0.0"
    assert manifest.metadata.author == "Test Author"
    assert manifest.metadata.plugin_type == PluginType.GUI
    assert manifest.entry_point == "plugin:TestPlugin"


def test_load_manifest_missing_file():
    """Test loading non-existent manifest file."""
    with pytest.raises(FileNotFoundError):
        load_manifest_from_json(Path("/nonexistent/manifest.json"))


def test_load_manifest_invalid_json(tmp_path):
    """Test loading manifest with invalid JSON."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{ invalid json }")
    
    with pytest.raises(ValueError):
        load_manifest_from_json(manifest_path)


def test_load_manifest_missing_required_fields(tmp_path):
    """Test loading manifest with missing required fields."""
    manifest_path = tmp_path / "manifest.json"
    incomplete_manifest = {
        "id": "com.test.plugin",
        "name": "Test Plugin"
        # Missing: version, author, description, plugin_type
    }
    with open(manifest_path, 'w') as f:
        json.dump(incomplete_manifest, f)
    
    with pytest.raises((KeyError, AttributeError)):
        load_manifest_from_json(manifest_path)


def test_load_manifest_invalid_plugin_type(tmp_path):
    """Test loading manifest with invalid plugin type."""
    manifest_path = tmp_path / "manifest.json"
    invalid_manifest = {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "invalid_type"
    }
    with open(manifest_path, 'w') as f:
        json.dump(invalid_manifest, f)
    
    with pytest.raises(ValueError):
        load_manifest_from_json(manifest_path)


def test_manifest_with_dependencies(tmp_path):
    """Test loading manifest with plugin dependencies."""
    manifest_path = tmp_path / "manifest.json"
    manifest_dict = {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "gui",
        "dependencies": {
            "plugins": [
                {"id": "com.other.plugin", "version": ">=1.0.0"}
            ]
        }
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest_dict, f)
    
    manifest = load_manifest_from_json(manifest_path)
    assert len(manifest.metadata.dependencies) == 1
    assert "com.other.plugin" in manifest.metadata.dependencies


def test_manifest_with_config_schema(tmp_path):
    """Test loading manifest with configuration schema."""
    manifest_path = tmp_path / "manifest.json"
    manifest_dict = {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "gui",
        "config_schema": {
            "setting1": {
                "type": "string",
                "default": "value",
                "description": "A setting"
            }
        }
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest_dict, f)
    
    manifest = load_manifest_from_json(manifest_path)
    assert "setting1" in manifest.config_schema
    assert manifest.config_schema["setting1"]["type"] == "string"


def test_manifest_all_plugin_types(tmp_path):
    """Test loading manifests for all plugin types."""
    for plugin_type in PluginType:
        manifest_path = tmp_path / f"manifest_{plugin_type.value}.json"
        manifest_dict = {
            "id": f"com.test.{plugin_type.value}",
            "name": f"Test {plugin_type.value} Plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "description": f"A test {plugin_type.value} plugin",
            "plugin_type": plugin_type.value
        }
        with open(manifest_path, 'w') as f:
            json.dump(manifest_dict, f)
        
        manifest = load_manifest_from_json(manifest_path)
        assert manifest.metadata.plugin_type == plugin_type


def test_manifest_with_mixed_dependency_formats(tmp_path):
    """Test loading manifest with mixed dependency formats (objects and strings)."""
    manifest_path = tmp_path / "manifest.json"
    manifest_dict = {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "gui",
        "dependencies": {
            "plugins": [
                {"id": "com.plugin.one", "version": ">=1.0.0"},
                "com.plugin.two",  # String format
                {"id": "com.plugin.three"}
            ]
        }
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest_dict, f)
    
    manifest = load_manifest_from_json(manifest_path)
    assert len(manifest.metadata.dependencies) == 3
    assert "com.plugin.one" in manifest.metadata.dependencies
    assert "com.plugin.two" in manifest.metadata.dependencies
    assert "com.plugin.three" in manifest.metadata.dependencies


@pytest.mark.skip(reason="Legacy dependency format (simple string list) not supported in current implementation")
def test_manifest_with_legacy_dependency_format(tmp_path):
    """Test loading manifest with legacy dependency format (simple list)."""
    manifest_path = tmp_path / "manifest.json"
    manifest_dict = {
        "id": "com.test.plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "A test plugin",
        "plugin_type": "gui",
        "dependencies": ["com.legacy.plugin1", "com.legacy.plugin2"]
    }
    with open(manifest_path, 'w') as f:
        json.dump(manifest_dict, f)
    
    manifest = load_manifest_from_json(manifest_path)
    assert len(manifest.metadata.dependencies) == 2
    assert "com.legacy.plugin1" in manifest.metadata.dependencies
    assert "com.legacy.plugin2" in manifest.metadata.dependencies
