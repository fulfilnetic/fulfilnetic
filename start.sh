#!/bin/bash
# Startup script for Fulfillment Data Processor

echo "🚀 Starting Fulfillment Data Processor..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p uploads outputs

# Start the Flask application
echo "Starting Flask application..."
echo "Open your browser and go to: http://localhost:5001"
echo "Press Ctrl+C to stop the server"
echo ""

python app.py
