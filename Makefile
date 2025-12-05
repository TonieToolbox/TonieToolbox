# TonieToolbox Documentation Makefile
# Simple commands for local documentation development

.PHONY: docs-setup docs-serve docs-build docs-clean docs-test help clean clean-all test test-unit test-integration test-functional test-coverage test-setup test-deps test-clean test-setup-multi-version test-multi-version test-clean-multi-version release release-patch release-minor release-major pre-release alpha beta rc build install

# Default help target
help:
	@echo "TonieToolbox Commands"
	@echo ""
	@echo "Build & Install:"
	@echo "  build       - Build the package"
	@echo "  install     - Install the package locally"
	@echo ""
	@echo "Documentation:"
	@echo "  docs-setup  - Install documentation dependencies"
	@echo "  docs-serve  - Start local development server"
	@echo "  docs-build  - Build documentation locally"
	@echo "  docs-clean  - Clean build artifacts"
	@echo "  docs-test   - Test documentation build"
	@echo ""
	@echo "Testing:"
	@echo "  test        - Run all tests"
	@echo "  test-unit   - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-functional  - Run functional tests only"
	@echo "  test-coverage    - Run tests with coverage report"
	@echo "  test-setup  - Set up test environment"
	@echo "  test-deps   - Check test dependencies"
	@echo "  test-clean  - Clean test artifacts and virtual environment"
	@echo ""
	@echo "Multi-Version Testing:"
	@echo "  test-setup-multi-version - Set up test environments for all Python versions"
	@echo "  test-multi-version       - Run tests with all available Python versions"
	@echo "  test-clean-multi-version - Clean multi-version test environments"
	@echo "  EXCLUDE_VERSIONS='3.10 3.11' - Exclude specific Python versions"
	@echo ""
	@echo "Release Management:"
	@echo "  release-patch   - Create patch release (develop → main)"
	@echo "  release-minor   - Create minor release (develop → main)"
	@echo "  release-major   - Create major release (develop → main)"
	@echo "  alpha TYPE=patch|minor|major - Create alpha pre-release"
	@echo "  beta TYPE=patch|minor|major  - Create beta pre-release"
	@echo "  rc TYPE=patch|minor|major    - Create release candidate"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       - Remove temporary Python files (.pyc, __pycache__, etc.)"
	@echo "  clean-all   - Full cleanup including docs and virtual environments"
	@echo ""
	@echo "Quick start:"
	@echo "  make docs-setup  # First time only"
	@echo "  make docs-serve  # Start development server"
	@echo "  make test-setup  # Set up testing environment"
	@echo "  make test       # Run all tests"

# Build the package
build:
	@echo "Building TonieToolbox package..."
	@if python3 -c "import build" 2>/dev/null; then \
		python3 -m build; \
	else \
		echo "Installing build package in virtual environment..."; \
		python3 -m venv ./venv/build 2>/dev/null || true; \
		./venv/build/bin/pip install --upgrade pip build; \
		echo "Using virtual environment for build..."; \
		./venv/build/bin/python -m build; \
	fi
	@echo "✓ Package built successfully!"
	@echo "  Output: dist/"

# Install the package locally
install:
	@echo "Installing TonieToolbox locally..."
	@if python3 -m venv ./venv/install 2>/dev/null; then \
		echo "Creating virtual environment for installation..."; \
		./venv/install/bin/pip install --upgrade pip; \
		./venv/install/bin/pip install -e .; \
		echo "✓ TonieToolbox installed in virtual environment!"; \
		echo "  To use: ./venv/install/bin/tonietoolbox --help"; \
		echo "  To activate: source ./venv/install/bin/activate"; \
	else \
		echo "Attempting system installation..."; \
		python3 -m pip install --upgrade pip --break-system-packages; \
		python3 -m pip install -e . --break-system-packages; \
		echo "✓ TonieToolbox installed system-wide!"; \
		echo "  You can now use: tonietoolbox --help"; \
	fi

# Install documentation dependencies
docs-setup:
	@echo "Setting up documentation environment..."
	@python3 -m venv ./venv/docs || true
	@./venv/docs/bin/pip install --upgrade pip
	@./venv/docs/bin/pip install -e .[docs]
	@echo "✓ Documentation environment ready!"
	@echo "  To activate manually: source ./venv/docs/bin/activate"

# Start development server
docs-serve:
	@echo "Starting MkDocs development server..."
	@if [ ! -d "./venv/docs" ]; then \
		echo "Virtual environment not found. Running setup..."; \
		make docs-setup; \
	fi
	@echo "Server will be available at: http://127.0.0.1:8000"
	@echo "Press Ctrl+C to stop"
	@./venv/docs/bin/mkdocs serve --dev-addr=127.0.0.1:8000

# Build documentation
docs-build:
	@echo "Building documentation..."
	@if [ ! -d "./venv/docs" ]; then \
		echo "Virtual environment not found. Running setup..."; \
		make docs-setup; \
	fi
	@./venv/docs/bin/mkdocs build
	@echo "✓ Documentation built successfully!"
	@echo "  Output: site/"

# Clean build artifacts
docs-clean:
	@echo "Cleaning documentation artifacts..."
	@rm -rf site/
	@echo "✓ Cleanup complete!"

# Clean everything including virtual environment
docs-clean-all: docs-clean
	@echo "Removing virtual environment..."
	@rm -rf ./venv/docs/
	@echo "✓ Full cleanup complete!"

# Test documentation build
docs-test: docs-build
	@echo "Testing documentation..."
	@echo "✓ Build successful - documentation ready for deployment"
	@echo ""
	@echo "To test manually, run: make docs-serve"

# Quick development workflow
docs-dev: docs-setup docs-serve

# Clean temporary Python files and directories
clean:
	@echo "Cleaning temporary Python files..."
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name ".coverage" -delete
	@find . -type f -name ".DS_Store" -delete
	@find . -type f -name "Thumbs.db" -delete
	@find . -type f -name "*.log" -delete
	@find . -type f -name "*.tmp" -delete
	@find . -type f -name "*.temp" -delete
	@find . -type f -name "*.bak" -delete
	@find . -type f -name "*.backup" -delete
	@find . -type f -name "*.swp" -delete
	@find . -type f -name "*.swo" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "test" -path "*/venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "test*" -path "*/venv/*" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -f temp_basic_test.py 2>/dev/null || true
	@echo "✓ Temporary files cleaned!"

# Testing targets - delegate to scripts/tests.py for complex logic
test:
	@echo "Running all tests..."
	@python3 scripts/tests.py --verbose

test-unit:
	@echo "Running unit tests..."
	@python3 scripts/tests.py --category unit --verbose

test-integration:
	@echo "Running integration tests..."
	@python3 scripts/tests.py --category integration --verbose

test-functional:
	@echo "Running functional tests..."
	@python3 scripts/tests.py --category functional --verbose

test-coverage:
	@echo "Running tests with coverage report..."
	@python3 scripts/tests.py --coverage --verbose

test-setup:
	@echo "Setting up test environment..."
	@python3 scripts/tests.py --setup-venv

test-deps:
	@echo "Checking test dependencies..."
	@python3 scripts/tests.py --check-deps

test-clean:
	@echo "Cleaning test artifacts..."
	@python3 scripts/tests.py --clean-venv

# Multi-version Python testing
# Discovers all installed Python 3.x versions and creates separate test environments
PYTHON_VERSIONS := $(shell for v in 3.10 3.11 3.12 3.13 3.14 3.15; do \
	python$$v --version >/dev/null 2>&1 && echo $$v; \
done)

# Allow exclusions via EXCLUDE_VERSIONS variable
# Usage: make test-setup-multi-version EXCLUDE_VERSIONS="3.10 3.11"
EXCLUDE_VERSIONS ?=
FILTERED_VERSIONS := $(filter-out $(EXCLUDE_VERSIONS),$(PYTHON_VERSIONS))

test-setup-multi-version:
	@echo "Setting up multi-version test environments..."
	@echo "Available Python versions: $(PYTHON_VERSIONS)"
	@if [ -n "$(EXCLUDE_VERSIONS)" ]; then \
		echo "Excluding versions: $(EXCLUDE_VERSIONS)"; \
	fi
	@echo "Setting up environments for: $(FILTERED_VERSIONS)"
	@echo ""
	@for version in $(FILTERED_VERSIONS); do \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "Setting up Python $$version environment..."; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		venv_path="venv/test-py$$version"; \
		if [ -d "$$venv_path" ]; then \
			echo "Virtual environment already exists: $$venv_path"; \
		else \
			echo "Creating virtual environment: $$venv_path"; \
			python$$version -m venv $$venv_path || { \
				echo "✗ Failed to create venv for Python $$version"; \
				continue; \
			}; \
		fi; \
		echo "Installing dependencies..."; \
		$$venv_path/bin/pip install --upgrade pip --quiet || { \
			echo "✗ Failed to upgrade pip for Python $$version"; \
			continue; \
		}; \
		$$venv_path/bin/pip install -e .[test] --quiet || { \
			echo "✗ Failed to install dependencies for Python $$version"; \
			continue; \
		}; \
		echo "✓ Python $$version environment ready: $$venv_path"; \
		echo ""; \
	done
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ Multi-version test environments setup complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

test-multi-version:
	@echo "Running tests with multiple Python versions..."
	@echo "Available Python versions: $(PYTHON_VERSIONS)"
	@if [ -n "$(EXCLUDE_VERSIONS)" ]; then \
		echo "Excluding versions: $(EXCLUDE_VERSIONS)"; \
	fi
	@echo "Testing with: $(FILTERED_VERSIONS)"
	@echo ""
	@if [ -z "$(FILTERED_VERSIONS)" ]; then \
		echo "✗ No Python versions available for testing"; \
		echo "  Install Python 3.10+ or check EXCLUDE_VERSIONS"; \
		exit 1; \
	fi
	@failed_versions=""; \
	passed_versions=""; \
	for version in $(FILTERED_VERSIONS); do \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		echo "Testing with Python $$version..."; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		venv_path="venv/test-py$$version"; \
		if [ ! -d "$$venv_path" ]; then \
			echo "✗ Environment not found: $$venv_path"; \
			echo "  Run: make test-setup-multi-version"; \
			failed_versions="$$failed_versions $$version"; \
			echo ""; \
			continue; \
		fi; \
		if $$venv_path/bin/python -m pytest tests/ --venv-path $$venv_path $(PYTEST_ARGS); then \
			echo "✓ Python $$version: PASSED"; \
			passed_versions="$$passed_versions $$version"; \
		else \
			echo "✗ Python $$version: FAILED"; \
			failed_versions="$$failed_versions $$version"; \
		fi; \
		echo ""; \
	done; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "Multi-version test results:"; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	if [ -n "$$passed_versions" ]; then \
		echo "✓ Passed:$$passed_versions"; \
	fi; \
	if [ -n "$$failed_versions" ]; then \
		echo "✗ Failed:$$failed_versions"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		exit 1; \
	fi; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✓ All versions passed!"

test-clean-multi-version:
	@echo "Cleaning multi-version test environments..."
	@for version in $(PYTHON_VERSIONS); do \
		venv_path="venv/test-py$$version"; \
		if [ -d "$$venv_path" ]; then \
			echo "Removing $$venv_path..."; \
			rm -rf $$venv_path; \
		fi; \
	done
	@echo "✓ Multi-version test environments cleaned!"

# Quick test workflow for development
test-dev: test-setup test

# Full cleanup including documentation and virtual environments
clean-all: clean docs-clean-all test-clean
	@echo "Cleaning build and install virtual environments..."
	@rm -rf ./venv/ 2>/dev/null || true
	@echo "✓ Full project cleanup complete!"

# Release Management
# Interactive release targets that prompt for release message
release-patch:
	@echo "Creating patch release (develop → main)..."
	@read -p "Enter release message: " message && \
	python3 scripts/release.py --type patch --message "$$message"

release-minor:
	@echo "Creating minor release (develop → main)..."
	@read -p "Enter release message: " message && \
	python3 scripts/release.py --type minor --message "$$message"

release-major:
	@echo "Creating major release (develop → main)..."
	@read -p "Enter release message: " message && \
	python3 scripts/release.py --type major --message "$$message"

# Pre-release targets with interactive prompts
alpha:
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make alpha TYPE=patch MESSAGE='Your message'"; \
		echo "Valid types: patch, minor, major"; \
		exit 1; \
	fi
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Creating $(TYPE) alpha pre-release (stay on develop)..."; \
		read -p "Enter release message: " message && \
		python3 scripts/release.py --type $(TYPE) --pre-release alpha --message "$$message"; \
	else \
		python3 scripts/release.py --type $(TYPE) --pre-release alpha --message "$(MESSAGE)"; \
	fi

beta:
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make beta TYPE=patch MESSAGE='Your message'"; \
		echo "Valid types: patch, minor, major"; \
		exit 1; \
	fi
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Creating $(TYPE) beta pre-release (stay on develop)..."; \
		read -p "Enter release message: " message && \
		python3 scripts/release.py --type $(TYPE) --pre-release beta --message "$$message"; \
	else \
		python3 scripts/release.py --type $(TYPE) --pre-release beta --message "$(MESSAGE)"; \
	fi

rc:
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make rc TYPE=patch MESSAGE='Your message'"; \
		echo "Valid types: patch, minor, major"; \
		exit 1; \
	fi
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Creating $(TYPE) release candidate (stay on develop)..."; \
		read -p "Enter release message: " message && \
		python3 scripts/release.py --type $(TYPE) --pre-release rc --message "$$message"; \
	else \
		python3 scripts/release.py --type $(TYPE) --pre-release rc --message "$(MESSAGE)"; \
	fi

# Direct release targets with message parameter
# Usage: make release MESSAGE="Your release message"
release: 
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE parameter required. Usage: make release MESSAGE='Your message'"; \
		exit 1; \
	fi
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make release TYPE=patch MESSAGE='Your message'"; \
		echo "Valid types: patch, minor, major"; \
		exit 1; \
	fi
	@python3 scripts/release.py --type $(TYPE) --message "$(MESSAGE)"

pre-release:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE parameter required. Usage: make pre-release MESSAGE='Your message'"; \
		exit 1; \
	fi
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make pre-release TYPE=patch MESSAGE='Your message'"; \
		echo "Valid types: patch, minor, major"; \
		exit 1; \
	fi
	@if [ -z "$(PREREL)" ]; then \
		echo "Error: PREREL parameter required. Usage: make pre-release TYPE=patch PREREL=alpha MESSAGE='Your message'"; \
		echo "Valid pre-release types: alpha, beta, rc"; \
		exit 1; \
	fi
	@python3 scripts/release.py --type $(TYPE) --pre-release $(PREREL) --message "$(MESSAGE)"