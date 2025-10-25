@echo off
REM Fulfillment Data Processor - Installation Script (Windows)
REM This script sets up the Python environment and installs dependencies

echo 🚀 Installing Fulfillment Data Processor...

REM Check Python version
echo 📋 Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

echo ✅ Installation complete!
echo.
echo To start the application, run:
echo   start.bat
echo.
echo Or manually:
echo   venv\Scripts\activate.bat ^&^& python app.py
pause

