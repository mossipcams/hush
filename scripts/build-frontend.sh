#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "Building Hush frontend..."

cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build for production
echo "Running production build..."
NODE_ENV=production npm run build

echo "Build complete! Output files:"
ls -la "$PROJECT_ROOT/custom_components/hush/"*.js 2>/dev/null || echo "No JS files found yet"
