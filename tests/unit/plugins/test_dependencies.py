"""Tests for dependency parsing and version checking."""
import pytest
from typing import List, Tuple, Optional
from packaging.specifiers import SpecifierSet
from TonieToolbox.core.plugins.dependency_parser import (
    parse_dependency_string,
    parse_dependencies,
    check_version_compatibility,
    get_dependency_conflicts,
    get_missing_dependencies,
    suggest_compatible_version,
    DependencyParseError
)


def test_parse_simple_dependency():
    """Test parsing a simple plugin dependency without version."""
    plugin_id, spec = parse_dependency_string("com.test.plugin")
    
    assert plugin_id == "com.test.plugin"
    assert spec is None


def test_parse_dependency_with_exact_version():
    """Test parsing dependency with exact version."""
    plugin_id, spec = parse_dependency_string("com.test.plugin==1.0.0")
    
    assert plugin_id == "com.test.plugin"
    assert isinstance(spec, SpecifierSet)
    assert "1.0.0" in spec
    assert "1.0.1" not in spec


def test_parse_dependency_with_minimum_version():
    """Test parsing dependency with minimum version."""
    plugin_id, spec = parse_dependency_string("com.test.plugin>=1.0.0")
    
    assert plugin_id == "com.test.plugin"
    assert "1.0.0" in spec
    assert "1.5.0" in spec
    assert "0.9.0" not in spec


def test_parse_dependency_with_version_range():
    """Test parsing dependency with version range."""
    plugin_id, spec = parse_dependency_string("com.test.plugin>=1.0.0,<2.0.0")
    
    assert plugin_id == "com.test.plugin"
    assert "1.0.0" in spec
    assert "1.9.9" in spec
    assert "2.0.0" not in spec
    assert "0.9.0" not in spec


def test_parse_dependency_with_compatible_version():
    """Test parsing dependency with compatible version operator."""
    plugin_id, spec = parse_dependency_string("com.test.plugin~=1.2.0")
    
    assert plugin_id == "com.test.plugin"
    assert "1.2.0" in spec
    assert "1.2.5" in spec
    assert "1.3.0" not in spec


def test_parse_dependency_with_multiple_conditions():
    """Test parsing dependency with multiple version conditions."""
    plugin_id, spec = parse_dependency_string("com.test.plugin>=1.0.0,!=1.5.0,<2.0.0")
    
    assert plugin_id == "com.test.plugin"
    assert "1.0.0" in spec
    assert "1.4.9" in spec
    assert "1.5.0" not in spec
    assert "1.5.1" in spec
    assert "2.0.0" not in spec


def test_parse_invalid_dependency_format():
    """Test parsing malformed dependency string."""
    with pytest.raises(DependencyParseError):
        parse_dependency_string("")
    
    with pytest.raises(DependencyParseError):
        parse_dependency_string("invalid>>1.0.0")


def test_parse_dependencies_list():
    """Test parsing multiple dependencies."""
    dependencies = [
        "com.test.plugin1>=1.0.0",
        "com.test.plugin2==2.0.0",
        "com.test.plugin3"
    ]
    
    result = parse_dependencies(dependencies)
    
    assert len(result) == 3
    # Result is a list of tuples (plugin_id, specifier_set)
    plugin_ids = [plugin_id for plugin_id, _ in result]
    assert "com.test.plugin1" in plugin_ids
    assert "com.test.plugin2" in plugin_ids
    assert "com.test.plugin3" in plugin_ids


def test_check_version_compatibility_exact():
    """Test version compatibility check with exact match."""
    spec_exact = SpecifierSet("==1.0.0")
    assert check_version_compatibility("1.0.0", spec_exact) is True
    assert check_version_compatibility("1.0.1", spec_exact) is False


def test_check_version_compatibility_range():
    """Test version compatibility check with version range."""
    spec_range = SpecifierSet(">=1.0.0,<2.0.0")
    assert check_version_compatibility("1.5.0", spec_range) is True
    assert check_version_compatibility("2.0.0", spec_range) is False
    assert check_version_compatibility("0.9.0", spec_range) is False


def test_check_version_compatibility_no_spec():
    """Test version compatibility check with no version spec."""
    assert check_version_compatibility("1.0.0", None) is True
    assert check_version_compatibility("999.0.0", None) is True


def test_get_dependency_conflicts():
    """Test detection of dependency version conflicts."""
    installed = {
        "com.test.plugin1": "1.0.0",
        "com.test.plugin2": "0.5.0",  # Too old
        "com.test.plugin3": "3.0.0"   # Too new
    }
    
    required = [
        ("com.test.plugin1", SpecifierSet(">=1.0.0")),
        ("com.test.plugin2", SpecifierSet(">=1.0.0")),
        ("com.test.plugin3", SpecifierSet("<2.0.0"))
    ]
    
    conflicts = get_dependency_conflicts(required, installed)
    
    assert len(conflicts) == 2
    assert any("plugin2" in c for c in conflicts)
    assert any("plugin3" in c for c in conflicts)


def test_get_missing_dependencies():
    """Test detection of missing dependencies."""
    installed = {
        "com.test.plugin1": "1.0.0"
    }
    
    required = [
        ("com.test.plugin1", SpecifierSet(">=1.0.0")),
        ("com.test.plugin2", SpecifierSet(">=1.0.0")),
        ("com.test.plugin3", None)
    ]
    
    missing = get_missing_dependencies(required, installed)
    
    assert len(missing) == 2
    assert any(m[0] == "com.test.plugin2" for m in missing)
    assert any(m[0] == "com.test.plugin3" for m in missing)


def test_suggest_compatible_version():
    """Test version suggestion for compatibility."""
    available = ["1.0.0", "1.5.0", "2.0.0", "2.5.0"]
    spec = SpecifierSet(">=1.0.0,<2.0.0")
    
    suggested = suggest_compatible_version(available, spec)
    
    assert suggested == "1.5.0"  # Latest compatible version


def test_suggest_compatible_version_no_match():
    """Test version suggestion when no compatible version exists."""
    available = ["0.5.0", "0.9.0"]
    spec = SpecifierSet(">=1.0.0")
    
    suggested = suggest_compatible_version(available, spec)
    
    assert suggested is None


def test_suggest_compatible_version_no_spec():
    """Test version suggestion with no version requirement."""
    available = ["1.0.0", "1.5.0", "2.0.0"]
    
    suggested = suggest_compatible_version(available, None)
    
    assert suggested == "2.0.0"  # Latest version
