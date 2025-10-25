#!/bin/bash

# Firebase Deployment Script
# Run this after installing Node.js and Firebase CLI

echo "🚀 Firebase Deployment Script"
echo "============================="

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Please install Node.js from: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Set up npm global path
export PATH=~/.npm-global/bin:$PATH

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "📦 Installing Firebase CLI..."
    npm install -g firebase-tools
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Firebase CLI"
        exit 1
    fi
fi

echo "✅ Firebase CLI found: $(firebase --version)"

# Check if user is logged in
if ! firebase projects:list &> /dev/null; then
    echo "🔐 Please login to Firebase:"
    firebase login
fi

# Check if .firebaserc exists
if [ ! -f ".firebaserc" ]; then
    echo "🔧 Setting up Firebase project..."
    firebase init
fi

# Prepare deployment files
echo "📦 Preparing deployment files..."

# Copy Python scripts to functions directory
cp aggregatev1.py functions/ 2>/dev/null || echo "⚠️ aggregatev1.py not found"
cp teamleader_converter.py functions/ 2>/dev/null || echo "⚠️ teamleader_converter.py not found"

# Ensure public directory exists
mkdir -p public

echo "✅ Files prepared"

# Deploy to Firebase
echo "🚀 Deploying to Firebase..."
firebase deploy

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Get your Firebase URL from the deployment output"
    echo "2. Update chrome-extension/popup.js with your Firebase URL"
    echo "3. Test the Chrome extension"
    echo "4. Package for Chrome Web Store"
else
    echo "❌ Deployment failed"
    exit 1
fi
