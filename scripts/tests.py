#!/usr/bin/env python3
"""Test runner script for TonieToolbox.

Handles test execution with virtual environment management, dependency checking,
and test categorization (unit, integration, functional).
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class TestRunner:
    """Manages test execution and environment setup."""

    def __init__(self, project_root: Optional[Path] = None, venv_path: Optional[Path] = None):
        """Initialize test runner.
        
        Args:
            project_root: Root directory of the project. Defaults to script parent.
            venv_path: Path to virtual environment. Defaults to venv/test.
        """
        self.script_dir = Path(__file__).parent
        self.project_root = project_root or self.script_dir.parent
        self.venv_dir = venv_path or (self.project_root / "venv" / "test")
        self.python_exe = self.venv_dir / "bin" / "python"
        self.pip_exe = self.venv_dir / "bin" / "pip"
        
    def venv_exists(self) -> bool:
        """Check if test virtual environment exists."""
        return self.venv_dir.exists() and self.python_exe.exists()
    
    def setup_venv(self, verbose: bool = False) -> bool:
        """Set up test virtual environment.
        
        Args:
            verbose: Enable verbose output
            
        Returns:
            True if setup successful, False otherwise
        """
        print("Setting up test virtual environment...")
        
        try:
            # Create virtual environment
            if self.venv_exists():
                print(f"Virtual environment already exists at: {self.venv_dir}")
            else:
                print(f"Creating virtual environment at: {self.venv_dir}")
                subprocess.run(
                    [sys.executable, "-m", "venv", str(self.venv_dir)],
                    check=True,
                    cwd=self.project_root
                )
            
            # Upgrade pip
            print("Upgrading pip...")
            subprocess.run(
                [str(self.pip_exe), "install", "--upgrade", "pip"],
                check=True,
                capture_output=not verbose
            )
            
            # Install test dependencies
            print("Installing test dependencies...")
            subprocess.run(
                [str(self.pip_exe), "install", "-e", ".[test]"],
                check=True,
                cwd=self.project_root,
                capture_output=not verbose
            )
            
            print("✓ Test environment ready!")
            print(f"  Virtual environment: {self.venv_dir}")
            print(f"  Python: {self.python_exe}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to set up test environment: {e}", file=sys.stderr)
            return False
    
    def clean_venv(self) -> bool:
        """Remove test virtual environment and artifacts.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        print("Cleaning test artifacts...")
        
        try:
            # Remove virtual environment
            if self.venv_dir.exists():
                print(f"Removing virtual environment: {self.venv_dir}")
                shutil.rmtree(self.venv_dir)
            
            # Remove pytest cache
            pytest_cache = self.project_root / ".pytest_cache"
            if pytest_cache.exists():
                print(f"Removing pytest cache: {pytest_cache}")
                shutil.rmtree(pytest_cache)
            
            # Remove coverage data
            coverage_file = self.project_root / ".coverage"
            if coverage_file.exists():
                print(f"Removing coverage data: {coverage_file}")
                coverage_file.unlink()
            
            htmlcov = self.project_root / "htmlcov"
            if htmlcov.exists():
                print(f"Removing coverage report: {htmlcov}")
                shutil.rmtree(htmlcov)
            
            print("✓ Test artifacts cleaned!")
            return True
            
        except Exception as e:
            print(f"✗ Failed to clean test artifacts: {e}", file=sys.stderr)
            return False
    
    def check_dependencies(self) -> bool:
        """Check if test dependencies are installed.
        
        Returns:
            True if all dependencies available, False otherwise
        """
        print("Checking test dependencies...")
        
        if not self.venv_exists():
            print("✗ Test virtual environment not found")
            print("  Run: make test-setup")
            return False
        
        required_packages = ["pytest", "pytest-mock", "pytest-qt"]
        optional_packages = ["pytest-cov", "pytest-xdist", "pytest-timeout"]
        
        try:
            # Check required packages
            result = subprocess.run(
                [str(self.pip_exe), "list", "--format=freeze"],
                check=True,
                capture_output=True,
                text=True
            )
            
            installed = result.stdout.lower()
            missing_required = []
            missing_optional = []
            
            for pkg in required_packages:
                if pkg.lower() not in installed:
                    missing_required.append(pkg)
            
            for pkg in optional_packages:
                if pkg.lower() not in installed:
                    missing_optional.append(pkg)
            
            if missing_required:
                print("✗ Missing required packages:")
                for pkg in missing_required:
                    print(f"  - {pkg}")
                print("\nRun: make test-setup")
                return False
            
            print("✓ All required dependencies installed")
            
            if missing_optional:
                print("\nOptional packages not installed:")
                for pkg in missing_optional:
                    print(f"  - {pkg}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to check dependencies: {e}", file=sys.stderr)
            return False
    
    def run_tests(
        self,
        category: Optional[str] = None,
        coverage: bool = False,
        verbose: bool = False,
        extra_args: Optional[List[str]] = None
    ) -> int:
        """Run tests with pytest.
        
        Args:
            category: Test category (unit, integration, functional)
            coverage: Enable coverage reporting
            verbose: Enable verbose output
            extra_args: Additional pytest arguments
            
        Returns:
            Exit code from pytest
        """
        if not self.venv_exists():
            print("✗ Test virtual environment not found", file=sys.stderr)
            print("  Run: make test-setup", file=sys.stderr)
            return 1
        
        # Build pytest command
        cmd = [str(self.python_exe), "-m", "pytest"]
        
        # Pass venv path to tests if not default
        default_venv = self.project_root / "venv" / "test"
        if self.venv_dir != default_venv:
            cmd.extend(["--venv-path", str(self.venv_dir)])
        
        # Add category marker if specified
        if category:
            cmd.extend(["-m", category])
            print(f"Running {category} tests...")
        else:
            print("Running all tests...")
        
        # Add coverage if requested
        if coverage:
            cmd.extend([
                "--cov=TonieToolbox",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        # Add verbosity
        if verbose:
            cmd.append("-v")
        
        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)
        
        # Run tests
        try:
            print(f"Command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root
            )
            return result.returncode
            
        except Exception as e:
            print(f"✗ Failed to run tests: {e}", file=sys.stderr)
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run TonieToolbox tests with proper environment management"
    )
    
    # Virtual environment
    parser.add_argument(
        "--venv-path",
        type=Path,
        help="Path to virtual environment (default: venv/test)"
    )
    
    # Test execution
    parser.add_argument(
        "--category",
        choices=["unit", "integration", "functional"],
        help="Run specific test category"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Environment management
    parser.add_argument(
        "--setup-venv",
        action="store_true",
        help="Set up test virtual environment"
    )
    parser.add_argument(
        "--clean-venv",
        action="store_true",
        help="Clean test virtual environment and artifacts"
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check test dependencies"
    )
    
    # Parse arguments
    args, extra_args = parser.parse_known_args()
    
    # Initialize test runner with custom venv path if provided
    runner = TestRunner(venv_path=args.venv_path)
    
    # Handle environment management commands
    if args.setup_venv:
        success = runner.setup_venv(verbose=args.verbose)
        return 0 if success else 1
    
    if args.clean_venv:
        success = runner.clean_venv()
        return 0 if success else 1
    
    if args.check_deps:
        success = runner.check_dependencies()
        return 0 if success else 1
    
    # Run tests
    return runner.run_tests(
        category=args.category,
        coverage=args.coverage,
        verbose=args.verbose,
        extra_args=extra_args
    )


if __name__ == "__main__":
    sys.exit(main())
