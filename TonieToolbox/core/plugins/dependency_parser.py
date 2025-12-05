#!/usr/bin/env python3
"""
Dependency parser for Python-style plugin dependency declarations.

Supports PEP 440 version specifiers:
- com.author.plugin>=1.0.0
- com.author.plugin>=1.0.0,<2.0.0
- com.author.plugin==1.5.0
- com.author.plugin~=1.4
"""
import re
from typing import Tuple, List, Optional
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion
from ..utils import get_logger

logger = get_logger(__name__)


class DependencyParseError(Exception):
    """Raised when dependency string parsing fails."""
    pass


def parse_dependency_string(dep_string: str) -> Tuple[str, Optional[SpecifierSet]]:
    """
    Parse a Python-style dependency string.
    
    Args:
        dep_string: Dependency string (e.g., "com.author.plugin>=1.0.0,<2.0.0")
        
    Returns:
        Tuple of (plugin_id, version_specifier)
        
    Raises:
        DependencyParseError: If parsing fails
        
    Examples:
        >>> parse_dependency_string("com.author.plugin")
        ('com.author.plugin', None)
        
        >>> parse_dependency_string("com.author.plugin>=1.0.0")
        ('com.author.plugin', SpecifierSet('>=1.0.0'))
        
        >>> parse_dependency_string("com.author.plugin>=1.0.0,<2.0.0")
        ('com.author.plugin', SpecifierSet('>=1.0.0,<2.0.0'))
    """
    if not dep_string or not isinstance(dep_string, str):
        raise DependencyParseError(f"Invalid dependency string: {dep_string}")
    
    dep_string = dep_string.strip()
    
    # Pattern: plugin_id followed by optional version specifiers
    # Matches: com.author.plugin>=1.0.0,<2.0.0
    pattern = r'^([a-zA-Z0-9._-]+)(.*)$'
    match = re.match(pattern, dep_string)
    
    if not match:
        raise DependencyParseError(f"Invalid dependency format: {dep_string}")
    
    plugin_id = match.group(1)
    version_spec_str = match.group(2).strip()
    
    # Validate plugin ID format (should be like com.author.plugin)
    if '.' not in plugin_id:
        logger.warning(f"Plugin ID '{plugin_id}' does not follow recommended format (com.author.plugin)")
    
    # Parse version specifier if present
    version_spec = None
    if version_spec_str:
        try:
            version_spec = SpecifierSet(version_spec_str)
        except InvalidSpecifier as e:
            raise DependencyParseError(f"Invalid version specifier '{version_spec_str}': {e}")
    
    return plugin_id, version_spec


def parse_dependencies(dependencies: List[str]) -> List[Tuple[str, Optional[SpecifierSet]]]:
    """
    Parse a list of dependency strings.
    
    Args:
        dependencies: List of dependency strings
        
    Returns:
        List of (plugin_id, version_specifier) tuples
        
    Raises:
        DependencyParseError: If any dependency fails to parse
    """
    parsed = []
    for dep in dependencies:
        try:
            parsed.append(parse_dependency_string(dep))
        except DependencyParseError as e:
            logger.error(f"Failed to parse dependency '{dep}': {e}")
            raise
    
    return parsed


def check_version_compatibility(
    installed_version: str,
    required_spec: Optional[SpecifierSet]
) -> bool:
    """
    Check if an installed version satisfies a requirement.
    
    Args:
        installed_version: Currently installed version string
        required_spec: Required version specifier (None means any version)
        
    Returns:
        True if compatible, False otherwise
        
    Examples:
        >>> check_version_compatibility("1.5.0", SpecifierSet(">=1.0.0,<2.0.0"))
        True
        
        >>> check_version_compatibility("2.0.0", SpecifierSet(">=1.0.0,<2.0.0"))
        False
    """
    if required_spec is None:
        return True  # No version requirement
    
    try:
        version = Version(installed_version)
        return version in required_spec
    except InvalidVersion as e:
        logger.error(f"Invalid version '{installed_version}': {e}")
        return False


def format_dependency(plugin_id: str, version_spec: Optional[SpecifierSet]) -> str:
    """
    Format a dependency as a string.
    
    Args:
        plugin_id: Plugin identifier
        version_spec: Optional version specifier
        
    Returns:
        Formatted dependency string
        
    Examples:
        >>> format_dependency("com.author.plugin", SpecifierSet(">=1.0.0"))
        'com.author.plugin>=1.0.0'
    """
    if version_spec is None:
        return plugin_id
    return f"{plugin_id}{version_spec}"


def get_dependency_conflicts(
    dependencies: List[Tuple[str, Optional[SpecifierSet]]],
    installed_plugins: dict[str, str]
) -> List[str]:
    """
    Check for dependency conflicts.
    
    Args:
        dependencies: List of (plugin_id, version_spec) tuples
        installed_plugins: Dict of {plugin_id: version} for installed plugins
        
    Returns:
        List of conflict messages (empty if no conflicts)
    """
    conflicts = []
    
    for plugin_id, required_spec in dependencies:
        if plugin_id in installed_plugins:
            installed_version = installed_plugins[plugin_id]
            if not check_version_compatibility(installed_version, required_spec):
                conflicts.append(
                    f"Plugin '{plugin_id}' version conflict: "
                    f"requires {required_spec}, but {installed_version} is installed"
                )
        else:
            # Plugin not installed - not a conflict, just missing
            pass
    
    return conflicts


def get_missing_dependencies(
    dependencies: List[Tuple[str, Optional[SpecifierSet]]],
    installed_plugins: dict[str, str]
) -> List[Tuple[str, Optional[SpecifierSet]]]:
    """
    Get list of missing dependencies.
    
    Args:
        dependencies: List of (plugin_id, version_spec) tuples
        installed_plugins: Dict of {plugin_id: version} for installed plugins
        
    Returns:
        List of missing (plugin_id, version_spec) tuples
    """
    missing = []
    
    for plugin_id, required_spec in dependencies:
        if plugin_id not in installed_plugins:
            missing.append((plugin_id, required_spec))
        elif not check_version_compatibility(installed_plugins[plugin_id], required_spec):
            # Version incompatible - also considered missing
            missing.append((plugin_id, required_spec))
    
    return missing


def suggest_compatible_version(
    available_versions: List[str],
    required_spec: Optional[SpecifierSet]
) -> Optional[str]:
    """
    Suggest a compatible version from available versions.
    
    Args:
        available_versions: List of available version strings
        required_spec: Required version specifier
        
    Returns:
        Latest compatible version or None
    """
    if required_spec is None:
        # No requirement - return latest version
        try:
            versions = [Version(v) for v in available_versions]
            return str(max(versions))
        except InvalidVersion:
            return available_versions[-1] if available_versions else None
    
    # Find all compatible versions
    compatible = []
    for ver_str in available_versions:
        try:
            version = Version(ver_str)
            if version in required_spec:
                compatible.append(version)
        except InvalidVersion:
            continue
    
    # Return latest compatible version
    if compatible:
        return str(max(compatible))
    
    return None
