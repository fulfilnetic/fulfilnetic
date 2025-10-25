@echo off
REM Fulfillment Data Processor - Startup Script (Windows)
REM This script starts the Flask application

echo 🚀 Starting Fulfillment Data Processor...

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment and start the app
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

echo 🌐 Starting web server...
echo 📱 Open your browser and go to: http://localhost:5001
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

