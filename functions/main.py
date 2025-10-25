from firebase_functions import https_fn
from firebase_admin import initialize_app
import json
import os
import tempfile
import uuid
import subprocess
import threading
from datetime import datetime

# Initialize Firebase Admin
initialize_app()

# In-memory storage for job statuses (in production, use a database)
job_status = {}

def convert_numpy_types(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    elif hasattr(obj, 'tolist'):  # numpy array
        return obj.tolist()
    else:
        return obj

@https_fn.on_request()
def fulfilnetic_api(req: https_fn.Request) -> https_fn.Response:
    """Main API function"""
    
    try:
        # Handle different routes
        if req.path == '/api/health':
            return https_fn.Response(json.dumps({'status': 'healthy', 'message': 'Firebase Function is working!'}))
        
        elif req.path == '/api/upload' and req.method == 'POST':
            return handle_upload_firebase(req)
        
        elif req.path.startswith('/api/process') and req.method == 'POST':
            return handle_process_firebase(req)
        
        elif req.path.startswith('/api/status/') and req.method == 'GET':
            job_id = req.path.split('/')[-1]
            return handle_status_firebase(job_id)
        
        elif req.path.startswith('/api/download/') and req.method == 'GET':
            job_id = req.path.split('/')[-1]
            return handle_download_firebase(job_id)
        
        elif req.path.startswith('/api/teamleader/') and req.method == 'POST':
            job_id = req.path.split('/')[-1]
            return handle_teamleader_conversion_firebase(job_id)
        
        else:
            return https_fn.Response(json.dumps({'error': 'Not found'}), status=404)
            
    except Exception as e:
        print(f"Error in Firebase Function: {str(e)}")
        return https_fn.Response(json.dumps({'error': str(e)}), status=500)

def handle_upload_firebase(req):
    """Handle file upload for Firebase Functions"""
    try:
        # For Firebase Functions, file uploads are handled differently
        # We'll need to implement this properly with multipart form data
        return https_fn.Response(json.dumps({'error': 'File upload needs proper implementation for Firebase Functions'}), status=501)
    except Exception as e:
        return https_fn.Response(json.dumps({'error': str(e)}), status=500)

def handle_process_firebase(req):
    """Handle processing request for Firebase Functions"""
    try:
        data = req.get_json()
        if not data or 'job_id' not in data:
            return https_fn.Response(json.dumps({'error': 'Job ID required'}), status=400)
        
        job_id = data['job_id']
        if job_id not in job_status:
            return https_fn.Response(json.dumps({'error': 'Job not found'}), status=404)
        
        # Start processing in background
        thread = threading.Thread(target=process_aggregation_job, args=(job_id,))
        thread.daemon = True
        thread.start()
        
        return https_fn.Response(json.dumps({'message': 'Processing started', 'job_id': job_id}))
    except Exception as e:
        return https_fn.Response(json.dumps({'error': str(e)}), status=500)

def process_aggregation_job(job_id):
    """Process the aggregation job in background"""
    try:
        print(f"🔄 Starting aggregation job: {job_id}")
        job_status[job_id]['status'] = 'processing'
        job_status[job_id]['progress'] = 10
        
        job_info = job_status[job_id]
        input_file = job_info['file_path']
        
        # Generate output filename
        base_name = os.path.splitext(job_info['filename'])[0]
        output_file = os.path.join('/tmp', f"{job_id}_output.xlsx")
        
        job_status[job_id]['progress'] = 20
        
        # Use subprocess to run the original script
        cmd = [
            'python3', 'aggregatev1.py',
            '--input', input_file,
            '--admin', 'storage.xlsx',  # You may need to upload this separately
            '--output', output_file,
            '--verbose'
        ]
        
        print(f"🚀 Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/workspace')
        
        job_status[job_id]['progress'] = 80
        
        if result.returncode != 0:
            print(f"❌ Script failed with return code: {result.returncode}")
            print(f"Error output: {result.stderr}")
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['error'] = result.stderr
            return
        
        # Parse the output to get summary statistics
        try:
            import pandas as pd
            
            # Read the Totals_by_Seller sheet
            totals_df = pd.read_excel(output_file, sheet_name='Totals_by_Seller')
            
            # Filter out the TOTAL row to avoid double counting
            totals_df_clean = totals_df[totals_df['Seller'] != 'TOTAL']
            
            # Read the Issues sheet if it exists
            try:
                issues_df = pd.read_excel(output_file, sheet_name='Issues')
            except:
                issues_df = None
            
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
                'output_log': str(result.stdout),
                'error_log': str(result.stderr)
            }
            
            job_status[job_id]['result'] = result
            job_status[job_id]['status'] = 'completed'
            job_status[job_id]['progress'] = 100
            job_status[job_id]['output_file'] = output_file
            
            print(f"✅ Job completed successfully: {job_id}")
            print(f"📊 Results: {result['total_sellers']} sellers, {result['total_issues']} issues")
            
        except Exception as e:
            print(f"❌ Error parsing results: {str(e)}")
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['error'] = f"Error parsing results: {str(e)}"
            
    except Exception as e:
        print(f"❌ Job failed: {str(e)}")
        job_status[job_id]['status'] = 'error'
        job_status[job_id]['error'] = str(e)

def handle_status_firebase(job_id):
    """Get job status for Firebase Functions"""
    if job_id not in job_status:
        return https_fn.Response(json.dumps({'error': 'Job not found'}), status=404)
    
    status = job_status[job_id].copy()
    
    # Convert numpy types for JSON serialization
    if 'result' in status:
        status['result'] = convert_numpy_types(status['result'])
    
    return https_fn.Response(json.dumps(status))

def handle_download_firebase(job_id):
    """Handle file download for Firebase Functions"""
    if job_id not in job_status:
        return https_fn.Response(json.dumps({'error': 'Job not found'}), status=404)
    
    job_info = job_status[job_id]
    if job_info['status'] != 'completed':
        return https_fn.Response(json.dumps({'error': 'Job not completed'}), status=400)
    
    output_file = job_info['output_file']
    if not os.path.exists(output_file):
        return https_fn.Response(json.dumps({'error': 'Output file not found'}), status=404)
    
    # For Firebase Functions, we need to return the file content as base64 or redirect
    # For now, return a simple response
    return https_fn.Response(json.dumps({'message': 'Download not yet implemented for Firebase'}), status=501)

def handle_teamleader_conversion_firebase(job_id):
    """Handle Teamleader conversion request for Firebase Functions"""
    if job_id not in job_status:
        return https_fn.Response(json.dumps({'error': 'Job not found'}), status=404)
    
    job_info = job_status[job_id]
    if job_info['status'] != 'completed':
        return https_fn.Response(json.dumps({'error': 'Job not completed'}), status=400)
    
    # Start Teamleader conversion in background
    thread = threading.Thread(target=process_teamleader_job, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return https_fn.Response(json.dumps({'message': 'Teamleader conversion started', 'job_id': job_id}))

def process_teamleader_job(job_id):
    """Process Teamleader conversion in background"""
    try:
        print(f"🔄 Starting Teamleader conversion job: {job_id}")
        job_status[job_id]['teamleader_status'] = 'processing'
        
        job_info = job_status[job_id]
        aggregated_file = job_info['output_file']
        
        print(f"📁 Using aggregated file: {aggregated_file}")
        print(f"📁 File exists: {os.path.exists(aggregated_file)}")
        
        if not os.path.exists(aggregated_file):
            raise FileNotFoundError(f"Aggregated file not found: {aggregated_file}")
        
        # Generate Teamleader output filename
        base_name = os.path.splitext(job_info['filename'])[0]
        teamleader_file = os.path.join('/tmp', f"{job_id}_teamleader.xlsx")
        
        print(f"📁 Teamleader output file: {teamleader_file}")
        
        # Use subprocess to run the teamleader converter
        cmd = [
            'python3', 'teamleader_converter.py',
            '--input', aggregated_file,
            '--output', teamleader_file
        ]
        
        print(f"🚀 Running Teamleader command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/workspace')
        
        if result.returncode != 0:
            print(f"❌ Teamleader script failed with return code: {result.returncode}")
            print(f"Error output: {result.stderr}")
            job_status[job_id]['teamleader_status'] = 'error'
            job_status[job_id]['teamleader_error'] = result.stderr
            return
        
        job_status[job_id]['teamleader_status'] = 'completed'
        job_status[job_id]['teamleader_file'] = teamleader_file
        
        print(f"✅ Teamleader conversion completed successfully: {job_id}")
        
    except Exception as e:
        print(f"❌ Teamleader job failed: {str(e)}")
        job_status[job_id]['teamleader_status'] = 'error'
        job_status[job_id]['teamleader_error'] = str(e)