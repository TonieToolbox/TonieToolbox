#!/bin/bash
#
# MkDocs Local Development Script
# Usage: ./scripts/docs-dev.sh [command]
#
# Commands:
#   setup    - Install documentation dependencies
#   serve    - Start local development server
#   build    - Build documentation locally
#   clean    - Clean build artifacts
#   test     - Test build and links
#   deploy   - Deploy to GitHub Pages (requires push access)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"
SITE_DIR="$PROJECT_ROOT/site"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    local python_version=$(python3 --version | cut -d' ' -f2)
    print_status "Using Python $python_version"
}

setup_docs() {
    print_status "Setting up documentation environment..."
    
    check_python
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$PROJECT_ROOT/venv-docs" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv-docs"
    fi
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv-docs/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install documentation requirements
    print_status "Installing documentation dependencies..."
    pip install -e ".[docs]"
    
    print_success "Documentation environment ready!"
    print_status "To activate: source venv-docs/bin/activate"
}

serve_docs() {
    print_status "Starting MkDocs development server..."
    
    # Check if virtual environment exists
    if [ ! -d "$PROJECT_ROOT/venv-docs" ]; then
        print_warning "Virtual environment not found. Running setup..."
        setup_docs
    fi
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv-docs/bin/activate"
    
    cd "$PROJECT_ROOT"
    
    print_status "Starting server on http://127.0.0.1:8000"
    print_status "Press Ctrl+C to stop"
    
    # Start MkDocs with live reload
    mkdocs serve --dev-addr=127.0.0.1:8000
}

build_docs() {
    print_status "Building documentation..."
    
    # Activate virtual environment if it exists
    if [ -d "$PROJECT_ROOT/venv-docs" ]; then
        source "$PROJECT_ROOT/venv-docs/bin/activate"
    else
        print_warning "Virtual environment not found. Make sure dependencies are installed."
    fi
    
    cd "$PROJECT_ROOT"
    
    # Clean previous build
    if [ -d "$SITE_DIR" ]; then
        print_status "Cleaning previous build..."
        rm -rf "$SITE_DIR"
    fi
    
    # Build documentation
    mkdocs build
    
    if [ $? -eq 0 ]; then
        print_success "Documentation built successfully!"
        print_status "Output directory: $SITE_DIR"
        
        # Show build statistics
        if command -v du &> /dev/null; then
            local size=$(du -sh "$SITE_DIR" | cut -f1)
            print_status "Build size: $size"
        fi
        
        local file_count=$(find "$SITE_DIR" -type f | wc -l)
        print_status "Generated files: $file_count"
        
    else
        print_error "Build failed!"
        exit 1
    fi
}

clean_docs() {
    print_status "Cleaning documentation artifacts..."
    
    # Remove build directory
    if [ -d "$SITE_DIR" ]; then
        rm -rf "$SITE_DIR"
        print_status "Removed build directory: $SITE_DIR"
    fi
    
    # Remove virtual environment if requested
    if [ "$1" == "--all" ]; then
        if [ -d "$PROJECT_ROOT/venv-docs" ]; then
            rm -rf "$PROJECT_ROOT/venv-docs"
            print_status "Removed virtual environment"
        fi
    fi
    
    print_success "Cleanup complete!"
}

test_docs() {
    print_status "Testing documentation build..."
    
    # Build first
    build_docs
    
    # Test for common issues
    print_status "Running documentation tests..."
    
    # Check for broken internal links (basic check)
    if command -v grep &> /dev/null; then
        local broken_links=$(find "$SITE_DIR" -name "*.html" -exec grep -l "href.*\.md" {} \; 2>/dev/null || true)
        if [ -n "$broken_links" ]; then
            print_warning "Found potential broken links (check manually):"
            echo "$broken_links"
        fi
    fi
    
    # Check for missing files
    local missing_images=$(find "$DOCS_DIR" -name "*.md" -exec grep -o "!\[.*\](.*)" {} \; | grep -v "http" | cut -d'(' -f2 | cut -d')' -f1 | sort -u)
    if [ -n "$missing_images" ]; then
        for img in $missing_images; do
            if [ ! -f "$DOCS_DIR/$img" ] && [ ! -f "$PROJECT_ROOT/$img" ]; then
                print_warning "Missing image: $img"
            fi
        done
    fi
    
    print_success "Documentation tests completed!"
    
    # Offer to serve locally for manual testing
    echo ""
    read -p "Open local server for manual testing? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        serve_docs
    fi
}

deploy_docs() {
    print_status "Deploying documentation to GitHub Pages..."
    
    # Check if we're in the right branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [ "$current_branch" != "main" ]; then
        print_warning "You're on branch '$current_branch', but deployment typically happens from 'main'"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "You have uncommitted changes"
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Activate virtual environment
    if [ -d "$PROJECT_ROOT/venv-docs" ]; then
        source "$PROJECT_ROOT/venv-docs/bin/activate"
    fi
    
    cd "$PROJECT_ROOT"
    
    # Deploy using mkdocs
    mkdocs gh-deploy --force
    
    print_success "Documentation deployed!"
    print_status "Check https://quentendo64.github.io/TonieToolbox/"
}

show_help() {
    echo "MkDocs Local Development Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup    - Install documentation dependencies in virtual environment"
    echo "  serve    - Start local development server (http://127.0.0.1:8000)"
    echo "  build    - Build documentation locally"
    echo "  clean    - Clean build artifacts (use --all to remove venv too)"
    echo "  test     - Test build and check for issues"
    echo "  deploy   - Deploy to GitHub Pages"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup          # First-time setup"
    echo "  $0 serve          # Start development server"
    echo "  $0 build          # Build for testing"
    echo "  $0 clean --all    # Remove all build artifacts and venv"
    echo ""
}

# Main script logic
case "${1:-help}" in
    setup)
        setup_docs
        ;;
    serve)
        serve_docs
        ;;
    build)
        build_docs
        ;;
    clean)
        clean_docs "$2"
        ;;
    test)
        test_docs
        ;;
    deploy)
        deploy_docs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac