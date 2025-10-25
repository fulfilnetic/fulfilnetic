#!/usr/bin/env python3
"""
Fulfillment Data Processing API
Flask backend that wraps aggregatev1.py and teamleader_converter.py
"""

import os
import sys
import tempfile
import uuid
import json
import traceback
from datetime import datetime, date
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import pandas as pd
import subprocess
import threading
import time
import zipfile

# Import our existing modules
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from aggregatev1 import main as aggregate_main, load_table, resolve_main_columns, resolve_admin, aggregate_main as agg_main, aggregate_admin
    from teamleader_converter import create_teamleader_invoice_data, load_aggregated_data
    from seller_filter import load_center_data, get_unique_sellers, filter_by_seller, save_filtered_data
    
    # Check which version we're using
    import inspect
    aggregate_file = inspect.getfile(load_table)
    print(f"✅ Successfully imported modules from current directory")
    print(f"📁 Using aggregatev1.py from: {aggregate_file}")
    
    # Read the version from the file
    with open(aggregate_file, 'r') as f:
        first_lines = f.read(200)
        if "v3.6.5 STRICT" in first_lines:
            print("✅ Using correct version: v3.6.5 STRICT")
        else:
            print("⚠️ Warning: May not be using the expected version")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    raise

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Global storage for job status
job_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def update_job_status(job_id, status, progress=0, message="", result=None, error=None):
    """Update job status for frontend polling"""
    job_status[job_id] = {
        'status': status,  # 'pending', 'processing', 'completed', 'error'
        'progress': progress,
        'message': message,
        'result': result,
        'error': error,
        'timestamp': datetime.now().isoformat()
    }

def process_aggregation_job(job_id, main_file_path, admin_file_path, config):
    """Background job for data aggregation using the original main() function"""
    try:
        print(f"🔄 Starting aggregation job {job_id}")
        print(f"📁 Main file: {main_file_path}")
        print(f"📁 Admin file: {admin_file_path}")
        print(f"⚙️ Config: {config}")
        
        update_job_status(job_id, 'processing', 10, "Preparing command-line arguments...")
        
        # Create output file path
        output_file = os.path.join(OUTPUT_FOLDER, f"aggregated_{job_id}.xlsx")
        
        # Build subprocess command
        cmd = ['python3', 'aggregatev1.py', '--input', main_file_path, '--admin', admin_file_path, '--output', output_file]
        
        # Add optional arguments based on config
        if config.get('seller_col'):
            cmd.extend(['--seller-col', config['seller_col']])
        if config.get('seller_name_col'):
            cmd.extend(['--seller-name-col', config['seller_name_col']])
        if config.get('fee_col'):
            cmd.extend(['--fee-col', config['fee_col']])
        if config.get('labels_col'):
            cmd.extend(['--labels-col', config['labels_col']])
        if config.get('admin_seller_col'):
            cmd.extend(['--admin-seller-col', config['admin_seller_col']])
        if config.get('storage_col'):
            cmd.extend(['--storage-col', config['storage_col']])
        if config.get('pim_col'):
            cmd.extend(['--pim-col', config['pim_col']])
        if config.get('encoding'):
            cmd.extend(['--encoding', config['encoding']])
        if config.get('no_header_filter'):
            cmd.append('--no-header-filter')
        
        # Always allow issues in API mode (equivalent to --allow-issues)
        cmd.append('--allow-issues')
        cmd.append('--verbose')
        
        print(f"🔧 Running command: {' '.join(cmd)}")
        
        update_job_status(job_id, 'processing', 30, "Running aggregation...")
        
        # Use subprocess to run the original script
        import subprocess
        
        # Run the aggregatev1.py script as a subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        output_text = result.stdout
        error_text = result.stderr
        
        print(f"📊 Subprocess return code: {result.returncode}")
        print(f"📊 Output: {output_text}")
        print(f"⚠️ Errors: {error_text}")
        
        # Check if the process failed
        if result.returncode != 0 and result.returncode != 2:  # 2 is the "issues detected" code
            raise RuntimeError(f"aggregatev1.py failed with return code {result.returncode}: {error_text}")
        
        update_job_status(job_id, 'processing', 80, "Processing completed, analyzing results...")
        
        # Check if output file was created
        if not os.path.exists(output_file):
            raise RuntimeError("Output file was not created")
        
        # Load the results to get summary statistics
        try:
            totals_df = pd.read_excel(output_file, sheet_name="Totals_by_Seller")
            issues_df = None
            try:
                issues_df = pd.read_excel(output_file, sheet_name="Data_Issues")
            except:
                pass  # No issues sheet
            
            # Filter out the TOTAL row for accurate counting
            totals_df_clean = totals_df[totals_df['Seller'] != 'TOTAL'].copy()
            
            # Prepare result summary (convert numpy types to Python types for JSON serialization)
            result = {
                'output_file': output_file,
                'total_sellers': int(len(totals_df_clean)),  # Exclude TOTAL row
                'total_issues': int(len(issues_df)) if issues_df is not None else 0,
                'has_issues': bool(issues_df is not None and len(issues_df) > 0),
                'summary_stats': {
                    'total_labels': float(totals_df_clean['Total Labels'].sum()) if 'Total Labels' in totals_df_clean.columns else 0.0,
                    'total_fees': float(totals_df_clean['Fulfilment Fee Total'].sum()) if 'Fulfilment Fee Total' in totals_df_clean.columns else 0.0
                },
                'output_log': str(output_text),
                'error_log': str(error_text)
            }
            
            if issues_df is not None and len(issues_df) > 0:
                update_job_status(job_id, 'completed', 100, f"Processing completed with {len(issues_df)} issues detected", result)
            else:
                update_job_status(job_id, 'completed', 100, "Processing completed successfully!", result)
                
        except Exception as e:
            # Even if we can't read the results, if the file exists, consider it successful
            result = {
                'output_file': output_file,
                'output_log': str(output_text),
                'error_log': str(error_text)
            }
            update_job_status(job_id, 'completed', 100, "Processing completed (results analysis failed)", result)
        
    except Exception as e:
        error_msg = f"Error during processing: {str(e)}"
        update_job_status(job_id, 'error', 0, error_msg, error=str(e))
        print(f"Job {job_id} error: {traceback.format_exc()}")

def process_teamleader_job(job_id, aggregated_file_path, invoice_date, start_invoice_number):
    """Background job for Teamleader conversion"""
    try:
        print(f"🔄 Starting Teamleader conversion job {job_id}")
        print(f"📁 Aggregated file: {aggregated_file_path}")
        print(f"📅 Invoice date: {invoice_date}")
        print(f"🔢 Start invoice number: {start_invoice_number}")
        
        update_job_status(job_id, 'processing', 20, "Loading aggregated data...")
        
        # Check if the aggregated file exists
        if not os.path.exists(aggregated_file_path):
            raise RuntimeError(f"Aggregated file not found: {aggregated_file_path}")
        
        print(f"✅ Aggregated file exists: {os.path.getsize(aggregated_file_path)} bytes")
        
        # Load aggregated data
        df = load_aggregated_data(aggregated_file_path)
        print(f"✅ Loaded aggregated data: {len(df)} rows")
        
        update_job_status(job_id, 'processing', 50, "Creating Teamleader invoice data...")
        
        # Create Teamleader data
        teamleader_df = create_teamleader_invoice_data(df, invoice_date, start_invoice_number)
        print(f"✅ Created Teamleader data: {len(teamleader_df)} rows")
        
        update_job_status(job_id, 'processing', 80, "Generating output file...")
        
        # Create output file
        output_file = os.path.join(OUTPUT_FOLDER, f"teamleader_{job_id}.xlsx")
        teamleader_df.to_excel(output_file, index=False, sheet_name="Teamleader Import")
        print(f"✅ Created output file: {output_file}")
        
        # Prepare result summary
        result = {
            'output_file': output_file,
            'total_customers': int(teamleader_df['Naam van de klant'].nunique()),
            'total_invoice_lines': int(len(teamleader_df)),
            'invoice_date': str(invoice_date.isoformat()),
            'start_invoice_number': int(start_invoice_number)
        }
        
        print(f"✅ Teamleader conversion completed: {result}")
        update_job_status(job_id, 'completed', 100, "Teamleader conversion completed!", result)
        
    except Exception as e:
        error_msg = f"Error during Teamleader conversion: {str(e)}"
        print(f"❌ Teamleader conversion error: {error_msg}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        update_job_status(job_id, 'error', 0, error_msg, error=str(e))

@app.route('/')
def index():
    """Serve the main HTML interface"""
    return send_file('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Upload main and admin data files"""
    try:
        print(f"Upload request received. Files: {list(request.files.keys())}")
        
        if 'main_file' not in request.files or 'admin_file' not in request.files:
            print("Missing required files")
            return jsonify({'error': 'Both main_file and admin_file are required'}), 400
        
        main_file = request.files['main_file']
        admin_file = request.files['admin_file']
        
        print(f"Main file: {main_file.filename}, Admin file: {admin_file.filename}")
        
        if main_file.filename == '' or admin_file.filename == '':
            print("Empty filenames")
            return jsonify({'error': 'No files selected'}), 400
        
        if not (allowed_file(main_file.filename) and allowed_file(admin_file.filename)):
            print(f"Invalid file types: {main_file.filename}, {admin_file.filename}")
            return jsonify({'error': 'Invalid file type. Only Excel and CSV files are allowed'}), 400
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        print(f"Generated job ID: {job_id}")
        
        # Save files
        main_filename = secure_filename(f"{job_id}_main_{main_file.filename}")
        admin_filename = secure_filename(f"{job_id}_admin_{admin_file.filename}")
        
        main_path = os.path.join(UPLOAD_FOLDER, main_filename)
        admin_path = os.path.join(UPLOAD_FOLDER, admin_filename)
        
        print(f"Saving files to: {main_path}, {admin_path}")
        
        main_file.save(main_path)
        admin_file.save(admin_path)
        
        # Verify files were saved
        if os.path.exists(main_path) and os.path.exists(admin_path):
            print(f"Files saved successfully. Sizes: {os.path.getsize(main_path)}, {os.path.getsize(admin_path)}")
        else:
            print("Error: Files were not saved properly")
            return jsonify({'error': 'Failed to save files'}), 500
        
        # Initialize job status
        update_job_status(job_id, 'pending', 0, "Files uploaded successfully")
        
        result = {
            'job_id': job_id,
            'main_file': main_filename,
            'admin_file': admin_filename,
            'message': 'Files uploaded successfully',
            'file_sizes': {
                'main': os.path.getsize(main_path),
                'admin': os.path.getsize(admin_path)
            }
        }
        
        print(f"Upload successful: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def start_processing():
    """Start aggregation processing"""
    try:
        data = request.get_json()
        job_id = data.get('job_id')
        config = data.get('config', {})
        
        if not job_id:
            return jsonify({'error': 'job_id is required'}), 400
        
        # Check if job exists
        if job_id not in job_status:
            return jsonify({'error': 'Job not found'}), 404
        
        # Get file paths
        main_file = None
        admin_file = None
        
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(f"{job_id}_main_"):
                main_file = os.path.join(UPLOAD_FOLDER, filename)
            elif filename.startswith(f"{job_id}_admin_"):
                admin_file = os.path.join(UPLOAD_FOLDER, filename)
        
        if not main_file or not admin_file:
            return jsonify({'error': 'Required files not found'}), 404
        
        # Start background processing
        thread = threading.Thread(
            target=process_aggregation_job,
            args=(job_id, main_file, admin_file, config)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Processing started'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start processing: {str(e)}'}), 500

@app.route('/api/teamleader', methods=['POST'])
def start_teamleader_conversion():
    """Start Teamleader conversion"""
    try:
        data = request.get_json()
        aggregated_file = data.get('aggregated_file')
        invoice_date_str = data.get('invoice_date')
        start_invoice_number = data.get('start_invoice_number', 1)
        
        if not aggregated_file or not invoice_date_str:
            return jsonify({'error': 'aggregated_file and invoice_date are required'}), 400
        
        # Parse invoice date
        try:
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        update_job_status(job_id, 'pending', 0, "Starting Teamleader conversion")
        
        # Start background processing
        thread = threading.Thread(
            target=process_teamleader_job,
            args=(job_id, aggregated_file, invoice_date, start_invoice_number)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Teamleader conversion started'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start Teamleader conversion: {str(e)}'}), 500

@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get job status"""
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job_status[job_id])

@app.route('/api/download/<job_id>', methods=['GET'])
def download_file(job_id):
    """Download processed file"""
    if job_id not in job_status:
        return jsonify({'error': 'Job not found'}), 404
    
    job = job_status[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Job not completed'}), 400
    
    output_file = job['result']['output_file']
    if not os.path.exists(output_file):
        return jsonify({'error': 'Output file not found'}), 404
    
    return send_file(output_file, as_attachment=True)

@app.route('/api/sellers', methods=['GET'])
def get_sellers():
    """Get list of available sellers from center.csv"""
    try:
        # Look for center.csv file - try multiple patterns
        center_file = None
        
        # First, try to find the most recent main file
        main_files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('_main_center.csv') or filename.endswith('_main_center.xlsx'):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                main_files.append((file_path, os.path.getmtime(file_path)))
        
        if main_files:
            # Sort by modification time (most recent first) and take the first one
            main_files.sort(key=lambda x: x[1], reverse=True)
            center_file = main_files[0][0]
        
        if not center_file:
            return jsonify({'error': 'Center data file not found. Please upload files first.'}), 404
        
        # Load center data and get sellers
        df = load_center_data(center_file)
        unique_sellers, seller_col = get_unique_sellers(df)
        
        return jsonify({
            'sellers': unique_sellers,
            'seller_column': seller_col,
            'total_records': len(df),
            'source_file': os.path.basename(center_file)
        })
        
    except Exception as e:
        print(f"Error in get_sellers: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to load sellers: {str(e)}'}), 500

@app.route('/api/filter-seller', methods=['POST'])
def filter_seller():
    """Filter center data by seller"""
    try:
        data = request.get_json()
        seller_value = data.get('seller')
        
        if not seller_value:
            return jsonify({'error': 'Seller value is required'}), 400
        
        # Look for center.csv file - use same logic as get_sellers
        center_file = None
        
        # First, try to find the most recent main file
        main_files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('_main_center.csv') or filename.endswith('_main_center.xlsx'):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                main_files.append((file_path, os.path.getmtime(file_path)))
        
        if main_files:
            # Sort by modification time (most recent first) and take the first one
            main_files.sort(key=lambda x: x[1], reverse=True)
            center_file = main_files[0][0]
        
        if not center_file:
            return jsonify({'error': 'Center data file not found. Please upload files first.'}), 404
        
        # Load center data
        df = load_center_data(center_file)
        unique_sellers, seller_col = get_unique_sellers(df)
        
        # Filter by seller
        filtered_df = filter_by_seller(df, seller_value, seller_col)
        
        if len(filtered_df) == 0:
            return jsonify({'error': f'No records found for seller "{seller_value}"'}), 404
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_seller_name = "".join(c for c in str(seller_value) if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_seller_name = safe_seller_name.replace(' ', '_')
        output_filename = f"seller_{safe_seller_name}_{timestamp}.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Save filtered data
        if save_filtered_data(filtered_df, output_path, seller_value):
            return jsonify({
                'output_file': output_path,
                'filename': output_filename,
                'total_records': len(filtered_df),
                'seller': seller_value
            })
        else:
            return jsonify({'error': 'Failed to save filtered data'}), 500
            
    except Exception as e:
        print(f"Error in filter_seller: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to filter seller: {str(e)}'}), 500

@app.route('/api/download-seller/<filename>', methods=['GET'])
def download_seller_file(filename):
    """Download seller filtered file"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/download-all-sellers', methods=['POST'])
def download_all_sellers():
    """Download all sellers as a ZIP file"""
    try:
        # Look for center.csv file - use same logic as other endpoints
        center_file = None
        
        # First, try to find the most recent main file
        main_files = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.endswith('_main_center.csv') or filename.endswith('_main_center.xlsx'):
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                main_files.append((file_path, os.path.getmtime(file_path)))
        
        if main_files:
            # Sort by modification time (most recent first) and take the first one
            main_files.sort(key=lambda x: x[1], reverse=True)
            center_file = main_files[0][0]
        
        if not center_file:
            return jsonify({'error': 'Center data file not found. Please upload files first.'}), 404
        
        # Load center data
        df = load_center_data(center_file)
        unique_sellers, seller_col = get_unique_sellers(df)
        
        if not unique_sellers:
            return jsonify({'error': 'No sellers found in the data'}), 404
        
        # Create ZIP file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"all_sellers_{timestamp}.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        
        processed_count = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for seller in unique_sellers:
                try:
                    # Filter data for this seller
                    filtered_df = filter_by_seller(df, seller, seller_col)
                    
                    if len(filtered_df) > 0:
                        # Create Excel file in memory
                        safe_seller_name = "".join(c for c in str(seller) if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_seller_name = safe_seller_name.replace(' ', '_')
                        excel_filename = f"seller_{safe_seller_name}.xlsx"
                        
                        # Create temporary Excel file
                        temp_excel = os.path.join(OUTPUT_FOLDER, f"temp_{excel_filename}")
                        filtered_df.to_excel(temp_excel, index=False, sheet_name='Seller Data')
                        
                        # Add to ZIP
                        zipf.write(temp_excel, excel_filename)
                        
                        # Clean up temp file
                        os.remove(temp_excel)
                        processed_count += 1
                        
                except Exception as e:
                    print(f"Error processing seller '{seller}': {e}")
                    continue
        
        return jsonify({
            'zip_file': zip_path,
            'zip_filename': zip_filename,
            'total_sellers': len(unique_sellers),
            'processed_sellers': processed_count
        })
        
    except Exception as e:
        print(f"Error in download_all_sellers: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create ZIP file: {str(e)}'}), 500

@app.route('/api/download-zip/<filename>', methods=['GET'])
def download_zip_file(filename):
    """Download ZIP file containing all seller data"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'ZIP file not found'}), 404
    
    return send_file(file_path, as_attachment=True)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
