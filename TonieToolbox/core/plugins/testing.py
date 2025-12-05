#!/usr/bin/env python3
"""
Plugin testing and validation utilities.

Provides comprehensive validation for plugin manifests, entry points,
dependencies, and installation without actually installing.
"""
import json
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ..utils import get_logger
from .base import PluginManifest, PluginType, BasePlugin, load_manifest_from_json
from .dependency_parser import parse_dependency_string, check_version_compatibility
from .plugin_config import PluginConfigManager
from .exceptions import (
    PluginError,
    PluginManifestError,
    PluginLoadError,
    PluginDependencyError,
    PluginConfigurationError
)

logger = get_logger(__name__)


class TestResult(Enum):
    """Test result status."""
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️  WARN"
    SKIP = "⏭️  SKIP"


@dataclass
class TestCase:
    """Individual test case result."""
    name: str
    result: TestResult
    message: str
    details: Optional[str] = None


@dataclass
class PluginTestReport:
    """Complete plugin validation report."""
    plugin_path: Path
    plugin_id: Optional[str]
    plugin_name: Optional[str]
    test_cases: List[TestCase]
    overall_status: TestResult
    
    @property
    def passed(self) -> bool:
        """Check if all tests passed or only warnings."""
        return all(tc.result in (TestResult.PASS, TestResult.WARN, TestResult.SKIP) 
                   for tc in self.test_cases)
    
    @property
    def failed_tests(self) -> List[TestCase]:
        """Get list of failed tests."""
        return [tc for tc in self.test_cases if tc.result == TestResult.FAIL]
    
    def format_report(self) -> str:
        """Format the report as human-readable text."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"Plugin Test Report: {self.plugin_name or 'Unknown'}")
        lines.append("=" * 80)
        lines.append(f"Path: {self.plugin_path}")
        if self.plugin_id:
            lines.append(f"ID: {self.plugin_id}")
        lines.append("")
        
        # Group by result type
        for result_type in [TestResult.FAIL, TestResult.WARN, TestResult.PASS, TestResult.SKIP]:
            tests = [tc for tc in self.test_cases if tc.result == result_type]
            if tests:
                lines.append(f"{result_type.value} Tests ({len(tests)}):")
                for tc in tests:
                    lines.append(f"  {tc.result.value} {tc.name}: {tc.message}")
                    if tc.details:
                        for detail_line in tc.details.split('\n'):
                            lines.append(f"      {detail_line}")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append(f"Overall Status: {self.overall_status.value}")
        if self.passed:
            lines.append("✅ Plugin is ready for use!")
        else:
            lines.append(f"❌ Plugin has {len(self.failed_tests)} failing test(s)")
        lines.append("=" * 80)
        
        return '\n'.join(lines)


class PluginTester:
    """
    Comprehensive plugin validation tool.
    
    Tests manifests, entry points, dependencies, and configuration
    without actually installing the plugin.
    """
    
    def __init__(self):
        """Initialize the plugin tester."""
        self.test_cases: List[TestCase] = []
    
    def test_plugin(self, plugin_path: Path) -> PluginTestReport:
        """
        Run comprehensive tests on a plugin.
        
        Args:
            plugin_path: Path to plugin directory or manifest.json file
            
        Returns:
            PluginTestReport with detailed results
        """
        self.test_cases = []
        
        # Resolve plugin directory
        if plugin_path.is_file() and plugin_path.name == "manifest.json":
            plugin_dir = plugin_path.parent
            manifest_path = plugin_path
        elif plugin_path.is_dir():
            plugin_dir = plugin_path
            manifest_path = plugin_dir / "manifest.json"
        else:
            return PluginTestReport(
                plugin_path=plugin_path,
                plugin_id=None,
                plugin_name=None,
                test_cases=[TestCase(
                    name="Path Validation",
                    result=TestResult.FAIL,
                    message="Invalid plugin path - must be directory or manifest.json file"
                )],
                overall_status=TestResult.FAIL
            )
        
        # Run all test suites
        manifest = self._test_manifest_exists(manifest_path)
        if manifest:
            plugin_id = manifest.metadata.id
            plugin_name = manifest.metadata.name
            
            self._test_manifest_validity(manifest_path)
            self._test_manifest_required_fields(manifest)
            self._test_plugin_type(manifest)
            self._test_entry_point(plugin_dir, manifest)
            self._test_dependencies(manifest)
            self._test_config_schema(manifest)
            self._test_import(plugin_dir, manifest)
            self._test_instantiation(plugin_dir, manifest)
        else:
            plugin_id = None
            plugin_name = None
        
        # Determine overall status
        overall = self._determine_overall_status()
        
        return PluginTestReport(
            plugin_path=plugin_path,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            test_cases=self.test_cases,
            overall_status=overall
        )
    
    def _test_manifest_exists(self, manifest_path: Path) -> Optional[PluginManifest]:
        """Test if manifest.json exists and is readable."""
        if not manifest_path.exists():
            self.test_cases.append(TestCase(
                name="Manifest Existence",
                result=TestResult.FAIL,
                message="manifest.json not found"
            ))
            return None
        
        try:
            manifest = load_manifest_from_json(manifest_path)
            self.test_cases.append(TestCase(
                name="Manifest Existence",
                result=TestResult.PASS,
                message="manifest.json found and loaded"
            ))
            return manifest
        except Exception as e:
            self.test_cases.append(TestCase(
                name="Manifest Existence",
                result=TestResult.FAIL,
                message=f"Failed to load manifest: {e}"
            ))
            return None
    
    def _test_manifest_validity(self, manifest_path: Path) -> None:
        """Test if manifest.json is valid JSON."""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                json.load(f)
            self.test_cases.append(TestCase(
                name="Manifest JSON Validity",
                result=TestResult.PASS,
                message="Valid JSON format"
            ))
        except json.JSONDecodeError as e:
            self.test_cases.append(TestCase(
                name="Manifest JSON Validity",
                result=TestResult.FAIL,
                message=f"Invalid JSON: {e}"
            ))
    
    def _test_manifest_required_fields(self, manifest: PluginManifest) -> None:
        """Test if all required manifest fields are present."""
        required = ['id', 'name', 'version', 'author', 'description', 'plugin_type']
        missing = []
        
        for field in required:
            if not getattr(manifest.metadata, field, None):
                missing.append(field)
        
        if missing:
            self.test_cases.append(TestCase(
                name="Required Fields",
                result=TestResult.FAIL,
                message=f"Missing required fields: {', '.join(missing)}"
            ))
        else:
            self.test_cases.append(TestCase(
                name="Required Fields",
                result=TestResult.PASS,
                message="All required fields present"
            ))
    
    def _test_plugin_type(self, manifest: PluginManifest) -> None:
        """Test if plugin type is valid."""
        try:
            plugin_type = manifest.metadata.plugin_type
            if plugin_type in list(PluginType):
                self.test_cases.append(TestCase(
                    name="Plugin Type",
                    result=TestResult.PASS,
                    message=f"Valid plugin type: {plugin_type.value}"
                ))
            else:
                self.test_cases.append(TestCase(
                    name="Plugin Type",
                    result=TestResult.FAIL,
                    message=f"Invalid plugin type: {plugin_type}"
                ))
        except Exception as e:
            self.test_cases.append(TestCase(
                name="Plugin Type",
                result=TestResult.FAIL,
                message=f"Error validating plugin type: {e}"
            ))
    
    def _test_entry_point(self, plugin_dir: Path, manifest: PluginManifest) -> None:
        """Test if entry_point is valid."""
        entry_point = manifest.entry_point
        
        if not entry_point:
            self.test_cases.append(TestCase(
                name="Entry Point",
                result=TestResult.WARN,
                message="No entry_point specified - will use auto-discovery"
            ))
            return
        
        # Parse entry_point (e.g., "plugin:MyPlugin")
        if ':' not in entry_point:
            self.test_cases.append(TestCase(
                name="Entry Point",
                result=TestResult.FAIL,
                message=f"Invalid entry_point format: {entry_point} (expected module:class)"
            ))
            return
        
        module_name, class_name = entry_point.split(':', 1)
        module_path = plugin_dir / f"{module_name}.py"
        
        if not module_path.exists():
            self.test_cases.append(TestCase(
                name="Entry Point",
                result=TestResult.FAIL,
                message=f"Entry point module not found: {module_path}"
            ))
            return
        
        self.test_cases.append(TestCase(
            name="Entry Point",
            result=TestResult.PASS,
            message=f"Entry point module exists: {module_name}:{class_name}"
        ))
    
    def _test_dependencies(self, manifest: PluginManifest) -> None:
        """Test dependency declarations."""
        dependencies = manifest.metadata.dependencies
        
        if not dependencies:
            self.test_cases.append(TestCase(
                name="Dependencies",
                result=TestResult.SKIP,
                message="No dependencies declared"
            ))
            return
        
        invalid_deps = []
        for dep in dependencies:
            try:
                parse_dependency_string(dep)
            except Exception as e:
                invalid_deps.append(f"{dep}: {e}")
        
        if invalid_deps:
            self.test_cases.append(TestCase(
                name="Dependencies",
                result=TestResult.FAIL,
                message=f"Invalid dependency declarations",
                details='\n'.join(invalid_deps)
            ))
        else:
            self.test_cases.append(TestCase(
                name="Dependencies",
                result=TestResult.PASS,
                message=f"{len(dependencies)} dependencies validated"
            ))
    
    def _test_config_schema(self, manifest: PluginManifest) -> None:
        """Test config schema validity."""
        schema = manifest.config_schema
        
        if not schema:
            self.test_cases.append(TestCase(
                name="Config Schema",
                result=TestResult.SKIP,
                message="No config schema defined"
            ))
            return
        
        # Validate schema structure
        errors = []
        for key, config in schema.items():
            if 'type' not in config:
                errors.append(f"{key}: missing 'type' field")
            elif config['type'] not in ['string', 'integer', 'boolean', 'array', 'object']:
                errors.append(f"{key}: invalid type '{config['type']}'")
        
        if errors:
            self.test_cases.append(TestCase(
                name="Config Schema",
                result=TestResult.FAIL,
                message="Invalid config schema",
                details='\n'.join(errors)
            ))
        else:
            self.test_cases.append(TestCase(
                name="Config Schema",
                result=TestResult.PASS,
                message=f"{len(schema)} config options validated"
            ))
    
    def _test_import(self, plugin_dir: Path, manifest: PluginManifest) -> None:
        """Test if plugin module can be imported."""
        entry_point = manifest.entry_point
        
        if not entry_point:
            self.test_cases.append(TestCase(
                name="Import Test",
                result=TestResult.SKIP,
                message="Skipped - no entry_point specified"
            ))
            return
        
        module_name = entry_point.split(':')[0]
        module_path = plugin_dir / f"{module_name}.py"
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                self.test_cases.append(TestCase(
                    name="Import Test",
                    result=TestResult.PASS,
                    message=f"Successfully imported {module_name}"
                ))
                
                # Clean up
                del sys.modules[module_name]
            else:
                self.test_cases.append(TestCase(
                    name="Import Test",
                    result=TestResult.FAIL,
                    message=f"Failed to create module spec for {module_name}"
                ))
        except Exception as e:
            self.test_cases.append(TestCase(
                name="Import Test",
                result=TestResult.FAIL,
                message=f"Import failed: {e}"
            ))
    
    def _test_instantiation(self, plugin_dir: Path, manifest: PluginManifest) -> None:
        """Test if plugin class can be instantiated."""
        entry_point = manifest.entry_point
        
        if not entry_point:
            self.test_cases.append(TestCase(
                name="Instantiation Test",
                result=TestResult.SKIP,
                message="Skipped - no entry_point specified"
            ))
            return
        
        module_name, class_name = entry_point.split(':', 1)
        module_path = plugin_dir / f"{module_name}.py"
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Get plugin class
                plugin_class = getattr(module, class_name)
                
                # Check if it's a BasePlugin subclass
                if not issubclass(plugin_class, BasePlugin):
                    self.test_cases.append(TestCase(
                        name="Instantiation Test",
                        result=TestResult.FAIL,
                        message=f"{class_name} is not a BasePlugin subclass"
                    ))
                else:
                    # Try to instantiate (without calling initialize)
                    try:
                        plugin_instance = plugin_class()
                        self.test_cases.append(TestCase(
                            name="Instantiation Test",
                            result=TestResult.PASS,
                            message=f"Successfully instantiated {class_name}"
                        ))
                    except Exception as e:
                        self.test_cases.append(TestCase(
                            name="Instantiation Test",
                            result=TestResult.WARN,
                            message=f"Instantiation raised exception: {e}"
                        ))
                
                # Clean up
                del sys.modules[module_name]
        except Exception as e:
            self.test_cases.append(TestCase(
                name="Instantiation Test",
                result=TestResult.FAIL,
                message=f"Failed to test instantiation: {e}"
            ))
    
    def _determine_overall_status(self) -> TestResult:
        """Determine overall test status."""
        if any(tc.result == TestResult.FAIL for tc in self.test_cases):
            return TestResult.FAIL
        elif any(tc.result == TestResult.WARN for tc in self.test_cases):
            return TestResult.WARN
        else:
            return TestResult.PASS


def test_plugin_cli(plugin_path: str) -> int:
    """
    CLI entry point for testing a plugin.
    
    Args:
        plugin_path: Path to plugin directory or manifest.json
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    path = Path(plugin_path).resolve()
    
    print("🧪 TonieToolbox Plugin Tester")
    print()
    
    tester = PluginTester()
    report = tester.test_plugin(path)
    
    print(report.format_report())
    
    return 0 if report.passed else 1
