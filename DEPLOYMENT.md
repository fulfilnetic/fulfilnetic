# Fulfillment Data Processor - Deployment Guide

## Overview
This application provides a web-based interface for processing fulfillment data and converting it to Teamleader import format.

## System Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Linux
- **Python**: 3.8 or higher (3.12 recommended)
- **Memory**: Minimum 4GB RAM
- **Storage**: 500MB free space
- **Network**: Port 5001 available for web interface

## Deployment Options

### Option 1: Docker Container (Recommended)
**Best for**: Technical users, consistent environments, easy updates

#### Prerequisites
- Docker Desktop installed
- Basic command line knowledge

#### Installation
1. Download the `docker-compose.yml` file
2. Run: `docker-compose up -d`
3. Access at: `http://localhost:5001`

#### Benefits
- ✅ No Python installation required
- ✅ Consistent across all systems
- ✅ Easy updates and maintenance
- ✅ Isolated environment

### Option 2: Python Virtual Environment
**Best for**: Users comfortable with Python, development environments

#### Prerequisites
- Python 3.8+ installed
- Basic command line knowledge

#### Installation
1. Download all project files
2. Run: `./install.sh` (Linux/macOS) or `install.bat` (Windows)
3. Run: `./start.sh` (Linux/macOS) or `start.bat` (Windows)
4. Access at: `http://localhost:5001`

#### Benefits
- ✅ Direct Python integration
- ✅ Easy debugging and customization
- ✅ No Docker knowledge required

### Option 3: Standalone Executable
**Best for**: Non-technical users, simple deployment

#### Prerequisites
- Windows 10/11 or macOS 10.15+

#### Installation
1. Download the executable file
2. Double-click to run
3. Access at: `http://localhost:5001`

#### Benefits
- ✅ No installation required
- ✅ Works on any compatible system
- ✅ Simple for end users

## File Structure
```
fulfillment-processor/
├── app.py                 # Main Flask application
├── index.html            # Web interface
├── aggregatev1.py        # Core processing logic
├── teamleader_converter.py # Teamleader conversion
├── requirements.txt      # Python dependencies
├── start.sh             # Startup script (Linux/macOS)
├── start.bat            # Startup script (Windows)
├── install.sh           # Installation script (Linux/macOS)
├── install.bat          # Installation script (Windows)
├── docker-compose.yml   # Docker configuration
└── README.md            # User documentation
```

## Usage Instructions

### 1. Upload Files
- Drag and drop your CSV and Excel files
- Or click "Choose Files" to browse
- Supported formats: CSV, XLSX

### 2. Configure Settings
- Set invoice date
- Set starting invoice number
- Choose processing options

### 3. Process Data
- Click "Start Processing"
- Monitor progress in real-time
- Download results when complete

## Troubleshooting

### Common Issues

#### Port 5001 Already in Use
**Solution**: Change port in `app.py`:
```python
app.run(debug=False, host='0.0.0.0', port=5002)  # Change to 5002
```

#### Python Version Issues
**Solution**: Use Docker option or ensure Python 3.8+

#### File Upload Errors
**Solution**: Check file formats and sizes (max 50MB per file)

### Getting Help
- Check the logs in the terminal/console
- Ensure all dependencies are installed
- Verify file permissions

## Security Notes
- Application runs locally only
- No data is sent to external servers
- Files are processed on your machine
- Temporary files are cleaned up automatically

## Updates
- **Docker**: `docker-compose pull && docker-compose up -d`
- **Python**: Replace files and restart
- **Executable**: Download new version

## Support
For technical support, contact: [Your Contact Information]

