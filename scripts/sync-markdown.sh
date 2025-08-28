#!/bin/sh

# Sync markdown files from notebooks/proposals to src/services/proposals
# Creates symbolic links for all .md files in notebooks/proposals

set -e  # Exit on any error

# Get script directory and project root in a POSIX-compatible way
SCRIPT_DIR=$(dirname "$(readlink -f "$0" 2>/dev/null || realpath "$0" 2>/dev/null || echo "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

NOTEBOOKS_DIR="$PROJECT_ROOT/notebooks/proposals"
PROPOSALS_DIR="$PROJECT_ROOT/src/services/proposals"

echo "📝 Syncing markdown files..."
echo "Source: $NOTEBOOKS_DIR"
echo "Target: $PROPOSALS_DIR"

# Check if directories exist
if [ ! -d "$NOTEBOOKS_DIR" ]; then
    echo "❌ Error: notebooks/proposals directory not found at $NOTEBOOKS_DIR"
    exit 1
fi

if [ ! -d "$PROPOSALS_DIR" ]; then
    echo "❌ Error: src/services/proposals directory not found at $PROPOSALS_DIR"
    exit 1
fi

# Remove existing .md files in target directory
echo "🧹 Cleaning existing markdown files..."
find "$PROPOSALS_DIR" -name "*.md" -delete 2>/dev/null || true

# Copy markdown files
echo "📄 Copying markdown files..."

COPY_COUNT=0
for md_file in "$NOTEBOOKS_DIR"/*.md; do
    if [ -f "$md_file" ]; then
        filename=$(basename "$md_file")
        # Copy file to target directory
        cp "$md_file" "$PROPOSALS_DIR/$filename"
        echo "   ✓ $filename"
        COPY_COUNT=$((COPY_COUNT + 1))
    fi
done

if [ $COPY_COUNT -eq 0 ]; then
    echo "⚠️  No markdown files found in $NOTEBOOKS_DIR"
else
    echo "✅ Successfully copied $COPY_COUNT markdown files"
fi

echo "🎉 Markdown sync completed!"