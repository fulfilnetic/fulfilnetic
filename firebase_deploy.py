#!/usr/bin/env python3
"""
Firebase Deployment Helper
This script helps deploy your Flask app to Firebase Functions using Python
"""

import os
import subprocess
import json
import shutil
from pathlib import Path

def check_requirements():
    """Check if we have the necessary tools"""
    print("🔍 Checking requirements...")
    
    # Check if we have the necessary files
    required_files = [
        'functions/main.py',
        'functions/requirements.txt', 
        'firebase.json',
        'aggregatev1.py',
        'teamleader_converter.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files found")
    return True

def setup_firebase_project():
    """Set up Firebase project configuration"""
    print("🔧 Setting up Firebase project...")
    
    # Create .firebaserc if it doesn't exist
    if not os.path.exists('.firebaserc'):
        project_id = input("Enter your Firebase project ID: ").strip()
        if not project_id:
            print("❌ Project ID is required")
            return False
        
        firebase_config = {
            "projects": {
                "default": project_id
            }
        }
        
        with open('.firebaserc', 'w') as f:
            json.dump(firebase_config, f, indent=2)
        
        print(f"✅ Created .firebaserc with project: {project_id}")
    
    return True

def prepare_deployment():
    """Prepare files for deployment"""
    print("📦 Preparing deployment files...")
    
    # Copy Python scripts to functions directory
    scripts_to_copy = ['aggregatev1.py', 'teamleader_converter.py']
    
    for script in scripts_to_copy:
        if os.path.exists(script):
            shutil.copy2(script, f'functions/{script}')
            print(f"✅ Copied {script} to functions/")
    
    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)
    
    # Create a simple index.html if it doesn't exist
    if not os.path.exists('public/index.html'):
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Fulfillment Data Processor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        h1 { text-align: center; margin-bottom: 30px; }
        .info {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .step {
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }
        .code {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Fulfillment Data Processor</h1>
        
        <div class="info">
            <h2>📋 Chrome Extension Required</h2>
            <p>This backend service works with a Chrome extension for the best user experience.</p>
        </div>
        
        <div class="step">
            <h3>🔧 API Endpoints</h3>
            <div class="code">
                POST /api/upload - Upload files<br>
                POST /api/process - Start processing<br>
                GET /api/status/{job_id} - Check status<br>
                GET /api/download/{job_id} - Download results<br>
                POST /api/teamleader - Convert to Teamleader format
            </div>
        </div>
        
        <div class="step">
            <h3>📱 Chrome Extension</h3>
            <p>Install the Chrome extension to use this service with a beautiful, user-friendly interface.</p>
        </div>
    </div>
</body>
</html>"""
        
        with open('public/index.html', 'w') as f:
            f.write(html_content)
        
        print("✅ Created public/index.html")
    
    print("✅ Deployment files prepared")
    return True

def install_firebase_cli():
    """Try to install Firebase CLI"""
    print("🔧 Attempting to install Firebase CLI...")
    
    # Try different methods to install Firebase CLI
    methods = [
        # Method 1: Try npm if available
        ['npm', 'install', '-g', 'firebase-tools'],
        # Method 2: Try with curl
        ['curl', '-sL', 'https://firebase.tools', '|', 'bash'],
    ]
    
    for method in methods:
        try:
            print(f"Trying: {' '.join(method)}")
            result = subprocess.run(method, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✅ Firebase CLI installed successfully")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"❌ Method failed: {e}")
            continue
    
    print("❌ Could not install Firebase CLI automatically")
    return False

def main():
    """Main deployment function"""
    print("🚀 Firebase Deployment Helper")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Set up Firebase project
    if not setup_firebase_project():
        return False
    
    # Prepare deployment files
    if not prepare_deployment():
        return False
    
    # Try to install Firebase CLI
    if not install_firebase_cli():
        print("\n📋 Manual Installation Required:")
        print("1. Install Node.js from: https://nodejs.org/")
        print("2. Run: npm install -g firebase-tools")
        print("3. Run: firebase login")
        print("4. Run: firebase deploy")
        return False
    
    print("\n🎉 Ready to deploy!")
    print("Run: firebase deploy")
    
    return True

if __name__ == "__main__":
    main()

