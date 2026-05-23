#!/bin/bash

################################################################################
# Local Documentation Build & Deployment Test Script
#
# This script simulates the GitHub Actions workflow locally to test:
# 1. Documentation build process
# 2. Artifact preparation
# 3. GitHub Pages file structure
#
# Usage:
#   ./scripts/test-docs-build.sh [--deploy] [--clean] [--serve]
#
# Options:
#   --deploy    Simulate full deployment to temporary gh-pages branch
#   --clean     Clean up test artifacts after script completes
#   --serve     Start local web server to view built docs
#   --help      Show this help message
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCS_OUTPUT="${PROJECT_ROOT}/docs/site"
TEST_DEPLOY_DIR="${PROJECT_ROOT}/.docs-test-deploy"
TEST_GH_PAGES_DIR="${PROJECT_ROOT}/.docs-test-gh-pages"

# Parse command line arguments
DO_DEPLOY=false
DO_CLEAN=false
DO_SERVE=false

for arg in "$@"; do
    case $arg in
        --deploy)
            DO_DEPLOY=true
            shift
            ;;
        --clean)
            DO_CLEAN=true
            shift
            ;;
        --serve)
            DO_SERVE=true
            shift
            ;;
        --help)
            cat "$0" | head -n 30
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 1
            ;;
    esac
done

# Helper functions
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Cleanup function
cleanup() {
    if [ "$DO_CLEAN" = true ]; then
        print_header "Cleaning Up Test Artifacts"
        rm -rf "$TEST_DEPLOY_DIR" "$TEST_GH_PAGES_DIR"
        print_success "Test artifacts cleaned"
    fi
}

# Set up trap to run cleanup on exit
trap cleanup EXIT

# Main workflow
print_header "Documentation Build Test"

# Step 1: Check dependencies
print_info "Checking dependencies..."
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is not installed"
    exit 1
fi
print_success "Poetry found"

# Step 2: Clean previous builds
print_info "Cleaning previous builds..."
rm -rf "$DOCS_OUTPUT"
print_success "Previous builds cleaned"

# Step 3: Install dependencies
print_header "Installing Dependencies"
cd "$PROJECT_ROOT"
poetry install --quiet 2>/dev/null || {
    print_info "Installing dependencies..."
    poetry install
}
print_success "Dependencies installed"

# Step 4: Build documentation
print_header "Building Documentation"
print_info "Running: poetry run poe docs"
poetry run poe docs

if [ ! -d "$DOCS_OUTPUT" ]; then
    print_error "Documentation build failed: output directory not found at $DOCS_OUTPUT"
    exit 1
fi
print_success "Documentation built successfully"

# Step 5: Verify build output
print_header "Verifying Build Output"
FILE_COUNT=$(find "$DOCS_OUTPUT" -type f | wc -l)
DIR_COUNT=$(find "$DOCS_OUTPUT" -type d | wc -l)
print_success "Built $(($FILE_COUNT)) files in $(($DIR_COUNT)) directories"

# Check for index.html
if [ -f "$DOCS_OUTPUT/index.html" ]; then
    print_success "Found index.html"
else
    print_error "index.html not found in output"
    exit 1
fi

# List structure
print_info "Build structure:"
cd "$DOCS_OUTPUT"
find . -maxdepth 2 -type d | sort | sed 's/^/  /'

# Step 6: Prepare deployment test (if --deploy flag)
if [ "$DO_DEPLOY" = true ]; then
    print_header "Simulating GitHub Pages Deployment"

    # Create test deployment structure
    print_info "Preparing deployment structure..."
    mkdir -p "$TEST_DEPLOY_DIR"

    # Copy docs
    cp -r "$DOCS_OUTPUT"/* "$TEST_DEPLOY_DIR/"

    # Add .nojekyll file
    touch "$TEST_DEPLOY_DIR/.nojekyll"
    print_success "Created .nojekyll file"

    # Verify deployment structure
    print_info "Deployment structure:"
    ls -la "$TEST_DEPLOY_DIR" | tail -n +4 | awk '{print "  " $NF}'

    print_success "Deployment simulation complete"
    print_info "Test deployment directory: $TEST_DEPLOY_DIR"
fi

# Step 7: Serve docs (if --serve flag)
if [ "$DO_SERVE" = true ]; then
    print_header "Starting Local Web Server"
    print_info "Serving documentation at http://localhost:8000"
    print_info "Press Ctrl+C to stop the server"

    cd "$DOCS_OUTPUT"
    python3 -m http.server 8000
fi

# Final summary
print_header "Test Summary"
print_success "Documentation build test completed successfully"
echo ""
echo "Next steps:"
echo "  1. Review the built documentation:"
echo "     open '$DOCS_OUTPUT/index.html'"
echo "  2. Or serve locally for interactive testing:"
echo "     make docs-serve"
echo ""
if [ "$DO_DEPLOY" = true ]; then
    echo "  3. Review deployment structure:"
    echo "     ls -la '$TEST_DEPLOY_DIR'"
    echo ""
fi
echo "When ready, commit and push to main branch to trigger GitHub Actions workflow."
