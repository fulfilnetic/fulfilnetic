#!/bin/bash

# Create delivery package for customer
# This script creates a clean distribution folder

set -e

PACKAGE_NAME="fulfillment-processor-v1.0"
PACKAGE_DIR="dist/$PACKAGE_NAME"

echo "📦 Creating delivery package..."

# Create distribution directory
mkdir -p "$PACKAGE_DIR"

# Copy essential files
echo "📋 Copying application files..."
cp app.py "$PACKAGE_DIR/"
cp index.html "$PACKAGE_DIR/"
cp aggregatev1.py "$PACKAGE_DIR/"
cp teamleader_converter.py "$PACKAGE_DIR/"
cp requirements.txt "$PACKAGE_DIR/"

# Copy deployment files
echo "📋 Copying deployment files..."
cp README.md "$PACKAGE_DIR/"
cp DEPLOYMENT.md "$PACKAGE_DIR/"
cp docker-compose.yml "$PACKAGE_DIR/"
cp Dockerfile "$PACKAGE_DIR/"
cp install.sh "$PACKAGE_DIR/"
cp install.bat "$PACKAGE_DIR/"
cp start.sh "$PACKAGE_DIR/"
cp start.bat "$PACKAGE_DIR/"
cp build.sh "$PACKAGE_DIR/"

# Make scripts executable
chmod +x "$PACKAGE_DIR"/*.sh

# Create directories
mkdir -p "$PACKAGE_DIR/uploads"
mkdir -p "$PACKAGE_DIR/outputs"

# Create a simple launcher script
cat > "$PACKAGE_DIR/LAUNCH.md" << 'EOF'
# Quick Launch Guide

## For Technical Users (Recommended)
1. Install Docker Desktop
2. Run: `docker-compose up -d`
3. Open: http://localhost:5001

## For Python Users
1. Run: `./install.sh` (Linux/macOS) or `install.bat` (Windows)
2. Run: `./start.sh` (Linux/macOS) or `start.bat` (Windows)
3. Open: http://localhost:5001

## For Non-Technical Users
Contact your IT department to set up the Docker option.
EOF

# Create archive
echo "🗜️ Creating archive..."
cd dist
tar -czf "$PACKAGE_NAME.tar.gz" "$PACKAGE_NAME"
zip -r "$PACKAGE_NAME.zip" "$PACKAGE_NAME"

echo "✅ Delivery package created!"
echo "📁 Location: dist/$PACKAGE_NAME/"
echo "📦 Archives: dist/$PACKAGE_NAME.tar.gz and dist/$PACKAGE_NAME.zip"
echo ""
echo "📋 Package contents:"
ls -la "$PACKAGE_NAME/"
echo ""
echo "🚀 Ready for delivery to customer!"

