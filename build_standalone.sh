#!/bin/bash
# Build standalone executable for fulfilnetic

echo "Building standalone executable..."

# Create the executable with explicit dependencies
pyinstaller --onefile \
    --name fulfilnetic \
    --hidden-import flask \
    --hidden-import flask_cors \
    --hidden-import pandas \
    --hidden-import numpy \
    --hidden-import openpyxl \
    --hidden-import xlsxwriter \
    --hidden-import werkzeug \
    --add-data "aggregatev1.py:." \
    --add-data "teamleader_converter.py:." \
    --add-data "storage.xlsx:." \
    app.py

echo "Build complete!"
echo "Executable created: dist/fulfilnetic"
echo ""
echo "To test:"
echo "1. Run: ./dist/fulfilnetic"
echo "2. Open Chrome extension"
echo "3. Test upload"
