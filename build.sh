#!/bin/bash
# Build script for mod-converter
# Creates standalone executables for Windows, Linux, macOS

set -e

echo "🔨 Building mod-converter..."

# Install dependencies
pip install -r requirements.txt

# Build with PyInstaller
pyinstaller \
    --onefile \
    --name mod-converter \
    --add-data "src:src" \
    --hidden-import toml \
    --console \
    main.py

echo "✅ Build complete: dist/mod-converter"

# Show output
ls -lh dist/
