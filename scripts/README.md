# TonieToolbox Scripts

This directory contains utility scripts for TonieToolbox development and maintenance.

## Available Scripts

### tests.py

Comprehensive test runner for TonieToolbox with virtual environment management.

**Features:**
- Automatic virtual environment setup for isolated testing
- Test categorization (unit, integration, functional)
- Coverage reporting
- Dependency checking
- Clean test artifact management

**Usage:**

```bash
# Set up test environment (first time only)
make test-setup
# or
python3 scripts/tests.py --setup-venv

# Run all tests
make test
# or
python3 scripts/tests.py

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-functional    # Functional tests only

# Run with coverage report
make test-coverage
# or
python3 scripts/tests.py --coverage

# Check test dependencies
make test-deps
# or
python3 scripts/tests.py --check-deps

# Clean test environment
make test-clean
# or
python3 scripts/tests.py --clean-venv

# Verbose output
python3 scripts/tests.py --verbose

# Pass additional pytest arguments
python3 scripts/tests.py --category unit -- -k test_specific_function
```

**Test Categories:**
- `unit`: Fast, isolated component testing
- `integration`: Component interaction testing
- `functional`: End-to-end feature testing

**Virtual Environment:**
- Location: `venv/test/`
- Automatically created and managed by the script
- Isolated from system Python and other project virtual environments

### release.py

Release management automation for TonieToolbox.

**Features:**
- Semantic versioning (patch, minor, major)
- Pre-release support (alpha, beta, rc)
- Automatic version bumping
- Git tagging
- CHANGELOG.md integration

**Usage:**

```bash
# Create releases (interactive)
make release-patch    # x.y.Z
make release-minor    # x.Y.0
make release-major    # X.0.0

# Create pre-releases (interactive)
make alpha TYPE=patch    # x.y.z-alpha.N
make beta TYPE=minor     # x.Y.0-beta.N
make rc TYPE=major       # X.0.0-rc.N

# Direct usage with message parameter
make release TYPE=patch MESSAGE="Bug fixes"
make pre-release TYPE=minor PREREL=alpha MESSAGE="New feature testing"

# Direct script usage
python3 scripts/release.py --type patch --message "Bug fixes"
python3 scripts/release.py --type minor --pre-release alpha --message "Testing new features"
```

### docs-dev.sh

Documentation development helper script.

**Usage:**

```bash
# Set up docs environment and start server
bash scripts/docs-dev.sh

# Or use Makefile targets
make docs-setup
make docs-serve
make docs-build
```

## Development Workflow

### Testing Workflow

1. **Initial Setup** (one time):
   ```bash
   make test-setup
   ```

2. **Development Cycle**:
   ```bash
   # Make code changes
   # Run relevant tests
   make test-unit
   
   # Fix issues
   # Run all tests
   make test
   
   # Check coverage
   make test-coverage
   ```

3. **Before Committing**:
   ```bash
   # Ensure all tests pass
   make test
   
   # Check coverage (target: 70%+)
   make test-coverage
   ```

### Release Workflow

1. **Pre-release Testing**:
   ```bash
   # Create alpha for testing
   make alpha TYPE=patch MESSAGE="Testing bug fixes"
   
   # Test thoroughly
   # Create beta when stable
   make beta TYPE=patch MESSAGE="Bug fixes ready for wider testing"
   
   # Final testing
   # Create release candidate
   make rc TYPE=patch MESSAGE="Final testing before release"
   ```

2. **Final Release**:
   ```bash
   # All tests pass, ready to release
   make release-patch MESSAGE="Bug fixes and improvements"
   ```

## Script Development Guidelines

When adding new scripts:

1. **Follow Python best practices**:
   - Type hints for all functions
   - Comprehensive docstrings
   - Error handling with meaningful messages

2. **Add to Makefile**:
   - Create convenient targets for common operations
   - Document in `make help` output

3. **Update this README**:
   - Document usage and features
   - Provide examples
   - Explain integration with development workflow

4. **Test thoroughly**:
   - Test on all supported platforms (Windows, Linux, macOS)
   - Handle edge cases gracefully
   - Provide helpful error messages

## Troubleshooting

### Test environment issues

**Problem**: Tests fail with import errors
```bash
# Solution: Recreate test environment
make test-clean
make test-setup
```

**Problem**: Virtual environment creation fails
```bash
# Solution: Ensure python3-venv is installed
# Ubuntu/Debian:
sudo apt install python3-venv
# Fedora:
sudo dnf install python3-virtualenv
```

**Problem**: Tests run but use wrong Python version
```bash
# Solution: Check virtual environment Python
./venv/test/bin/python --version

# Should be 3.12+ as specified in pyproject.toml
```

### Coverage issues

**Problem**: Coverage report shows 0% coverage
```bash
# Solution: Ensure pytest-cov is installed
./venv/test/bin/pip list | grep pytest-cov

# Reinstall if missing
make test-clean
make test-setup
```

## Additional Resources

- [Testing Architecture](../tests/TEST_ARCHITECTURE.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Main README](../README.md)
