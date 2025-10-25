# Firebase + Chrome Extension Deployment Guide

## 🚀 Quick Setup

### Step 1: Deploy to Firebase

1. **Install Firebase CLI**:
   ```bash
   npm install -g firebase-tools
   ```

2. **Login to Firebase**:
   ```bash
   firebase login
   ```

3. **Initialize Firebase project**:
   ```bash
   firebase init
   ```
   - Select "Functions" and "Hosting"
   - Choose your Firebase project
   - Use Python for Functions
   - Use `public` as public directory

4. **Deploy**:
   ```bash
   firebase deploy
   ```

### Step 2: Update Chrome Extension

1. **Get your Firebase URL**:
   - After deployment, you'll get a URL like: `https://your-project.web.app`
   - Update `API_BASE_URL` in `chrome-extension/popup.js`

2. **Load Extension in Chrome**:
   - Open Chrome → Extensions → Developer mode
   - Click "Load unpacked"
   - Select the `chrome-extension` folder

### Step 3: Test

1. **Open the extension** in Chrome
2. **Upload your test files**
3. **Process the data**
4. **Download results**

## 🔧 Configuration

### Firebase Functions
- **Runtime**: Python 3.12
- **Memory**: 1GB (adjust in `firebase.json`)
- **Timeout**: 60 seconds (adjust in `firebase.json`)

### Chrome Extension
- **Permissions**: File access, storage
- **Host permissions**: Your Firebase domain

## 📦 Distribution

### For Customers:
1. **Package the extension** as a `.zip` file
2. **Upload to Chrome Web Store** (or distribute directly)
3. **Customers install** with one click

### Benefits:
- ✅ **No technical setup** required
- ✅ **Works on any computer** with Chrome
- ✅ **Automatic updates** through Chrome
- ✅ **Professional delivery** method

## 🛠️ Troubleshooting

### Common Issues:

#### Firebase Functions Timeout
- Increase timeout in `firebase.json`
- Optimize Python code for faster processing

#### Chrome Extension CORS Errors
- Ensure Firebase URL is correct
- Check host permissions in `manifest.json`

#### File Upload Issues
- Check file size limits
- Verify file formats (CSV, XLSX)

## 💰 Costs

### Firebase (Free Tier):
- **Functions**: 2M invocations/month
- **Hosting**: 10GB bandwidth/month
- **Storage**: 1GB

### Chrome Web Store:
- **Developer account**: $5 one-time fee
- **Extension hosting**: Free

## 🎯 Next Steps

1. **Deploy to Firebase** using the commands above
2. **Test the extension** with your data
3. **Package for distribution**
4. **Submit to Chrome Web Store**

This approach gives your customer the **easiest possible experience** - just install an extension and start using it!

