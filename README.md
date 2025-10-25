# Fulfillment Data Processing System

A Chrome extension and Flask backend for processing fulfillment data and converting it to Teamleader import format.

## Quick Start

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Flask server:**
   ```bash
   ./start.sh
   ```
   Or manually:
   ```bash
   source venv/bin/activate && python app.py
   ```

3. **Load the Chrome extension:**
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" and select the `chrome-extension` folder

4. **Use the system:**
   - Click the Chrome extension icon
   - Upload your CSV file
   - Process the data
   - Download the results

## Files

- `app.py` - Flask backend server
- `aggregatev1.py` - Main data processing script
- `teamleader_converter.py` - Converts data to Teamleader format
- `index.html` - Web interface
- `chrome-extension/` - Chrome extension files
- `requirements.txt` - Python dependencies

## Usage

The system processes fulfillment data by:
1. Aggregating costs by seller
2. Identifying data quality issues
3. Converting to Teamleader import format

Access the web interface at: http://localhost:5001