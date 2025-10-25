#!/bin/bash

# Simple Firebase deployment script
# This script helps deploy your Flask app to Firebase Functions

echo "🚀 Firebase Deployment Helper"
echo "=============================="

# Check if we have the necessary files
if [ ! -f "functions/main.py" ]; then
    echo "❌ functions/main.py not found"
    exit 1
fi

if [ ! -f "firebase.json" ]; then
    echo "❌ firebase.json not found"
    exit 1
fi

echo "✅ All necessary files found"

# Create a simple deployment package
echo "📦 Creating deployment package..."

# Copy Python scripts to functions directory
cp aggregatev1.py functions/
cp teamleader_converter.py functions/

echo "✅ Files copied to functions directory"

# Create a simple HTML file for hosting
cat > public/index.html << 'EOF'
<!DOCTYPE html>
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
        h1 {
            text-align: center;
            margin-bottom: 30px;
        }
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
        .warning {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Fulfillment Data Processor</h1>
        
        <div class="info">
            <h2>📋 Installation Instructions</h2>
            <p>This application is designed to work with a Chrome extension for the best user experience.</p>
        </div>
        
        <div class="step">
            <h3>Step 1: Install Chrome Extension</h3>
            <p>Download and install the Chrome extension from the provided package.</p>
        </div>
        
        <div class="step">
            <h3>Step 2: Use the Extension</h3>
            <p>Click the extension icon in your Chrome browser to start processing fulfillment data.</p>
        </div>
        
        <div class="warning">
            <h3>⚠️ Important</h3>
            <p>This backend service is running on Firebase Functions. The Chrome extension will communicate with this service to process your data.</p>
        </div>
        
        <div class="info">
            <h3>🔧 API Endpoints</h3>
            <p>The following endpoints are available:</p>
            <div class="code">
                POST /api/upload - Upload files<br>
                POST /api/process - Start processing<br>
                GET /api/status/{job_id} - Check status<br>
                GET /api/download/{job_id} - Download results
            </div>
        </div>
    </div>
</body>
</html>
EOF

echo "✅ Created public/index.html"

echo ""
echo "🎉 Deployment package ready!"
echo ""
echo "Next steps:"
echo "1. Install Node.js from: https://nodejs.org/"
echo "2. Run: npm install -g firebase-tools"
echo "3. Run: firebase login"
echo "4. Run: firebase init"
echo "5. Run: firebase deploy"
echo ""
echo "Or use the Chrome extension directly with your local Flask app for testing."

