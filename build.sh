#!/bin/bash

# Build script for creating standalone executable
# Requires PyInstaller: pip install pyinstaller

echo "🔨 Building standalone executable..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Create the executable
echo "📦 Creating executable..."
pyinstaller --onefile \
    --add-data "index.html:." \
    --add-data "requirements.txt:." \
    --hidden-import "pandas" \
    --hidden-import "numpy" \
    --hidden-import "flask" \
    --hidden-import "openpyxl" \
    --name "FulfillmentProcessor" \
    app.py

echo "✅ Executable created in dist/FulfillmentProcessor"
echo "📁 You can distribute this single file to customers"

