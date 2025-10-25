#!/bin/bash

# Fulfillment Data Processor - Installation Script (Linux/macOS)
# This script sets up the Python environment and installs dependencies

set -e  # Exit on any error

echo "🚀 Installing Fulfillment Data Processor..."

# Check Python version
echo "📋 Checking Python version..."
python3 --version || {
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
}

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

echo "✅ Installation complete!"
echo ""
echo "To start the application, run:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate && python app.py"

