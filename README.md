# Fulfillment Data Processor

A web-based application for processing fulfillment data and converting it to Teamleader import format.

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
docker-compose up -d
```
Then open: http://localhost:5001

### Option 2: Python Installation
```bash
# Linux/macOS
./install.sh
./start.sh

# Windows
install.bat
start.bat
```

## 📋 Features

- **Web Interface**: Easy-to-use drag-and-drop interface
- **Data Processing**: Aggregates fulfillment data with configurable options
- **Teamleader Integration**: Converts processed data to Teamleader import format
- **Real-time Progress**: Monitor processing status in real-time
- **Error Handling**: Comprehensive error reporting and validation
- **File Management**: Automatic cleanup of temporary files

## 🛠️ System Requirements

- **Python**: 3.8 or higher (3.12 recommended)
- **Memory**: Minimum 4GB RAM
- **Storage**: 500MB free space
- **Network**: Port 5001 available

## 📁 File Structure

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
├── Dockerfile           # Docker image definition
└── DEPLOYMENT.md        # Detailed deployment guide
```

## 🔧 Configuration

The application can be configured by modifying `app.py`:

- **Port**: Change `port=5001` to use a different port
- **File Limits**: Modify upload size limits
- **Processing Options**: Adjust default settings

## 📊 Usage

1. **Upload Files**: Drag and drop CSV and Excel files
2. **Configure**: Set invoice date and starting invoice number
3. **Process**: Click "Start Processing" and monitor progress
4. **Download**: Get processed results when complete

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```python
# In app.py, change the port:
app.run(debug=False, host='0.0.0.0', port=5002)
```

#### Python Version Issues
- Ensure Python 3.8+ is installed
- Use Docker for consistent environment

#### File Upload Errors
- Check file formats (CSV, XLSX)
- Verify file sizes (max 50MB per file)
- Ensure files are not corrupted

### Getting Help

1. Check the terminal/console for error messages
2. Verify all dependencies are installed
3. Ensure file permissions are correct
4. Contact support with specific error details

## 🔒 Security

- Application runs locally only
- No data is sent to external servers
- Files are processed on your machine
- Temporary files are cleaned up automatically

## 📈 Performance

- **Small files** (< 10MB): Process in seconds
- **Medium files** (10-50MB): Process in minutes
- **Large files** (> 50MB): May take several minutes

## 🔄 Updates

### Docker
```bash
docker-compose pull
docker-compose up -d
```

### Python
1. Replace application files
2. Restart the application

## 📞 Support

For technical support or questions:
- Check the logs for error details
- Ensure system requirements are met
- Contact: [Your Contact Information]

## 📄 License

[Your License Information]

---

**Version**: 1.0.0  
**Last Updated**: October 2025