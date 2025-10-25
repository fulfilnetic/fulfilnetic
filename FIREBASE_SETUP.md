# 🔥 Firebase Setup & Deployment Guide

## ✅ What's Ready
- ✅ **Node.js**: v20.10.0 installed
- ✅ **Firebase CLI**: v14.22.0 installed
- ✅ **Deployment files**: All prepared

## 🚧 Manual Setup Required

### Step 1: Login to Firebase
Open Terminal and run:
```bash
export PATH=~/.npm-global/bin:$PATH
firebase login
```
- This will open a browser window
- Sign in with your Google account
- Allow Firebase CLI access

### Step 2: Initialize Firebase Project
```bash
firebase init
```
- Select **Functions** and **Hosting**
- Choose your Firebase project
- Use **Python** for Functions
- Use `public` as public directory
- Use `functions` as functions directory

### Step 3: Deploy
```bash
firebase deploy
```

## 🎯 Alternative: Use Firebase Console

### Option 1: Web Console
1. **Go to**: https://console.firebase.google.com/
2. **Create new project** or select existing
3. **Enable Functions** and **Hosting**
4. **Upload files** manually

### Option 2: Manual Upload
1. **Create Firebase project** in console
2. **Upload `functions/main.py`** to Functions
3. **Upload `public/index.html`** to Hosting
4. **Configure** in Firebase console

## 📋 After Deployment

### Get Your Firebase URL
You'll get a URL like: `https://your-project.web.app`

### Update Chrome Extension
1. **Edit**: `chrome-extension/popup.js`
2. **Change**: `const API_BASE_URL = 'https://your-project.web.app';`
3. **Reload extension** in Chrome

## 🚀 Benefits After Deployment

- ✅ **Free hosting** on Firebase
- ✅ **Professional delivery** method
- ✅ **Chrome extension** works from anywhere
- ✅ **No local setup** required for customers

## 💡 Quick Test

Once deployed, test with:
```bash
curl https://your-project.web.app/api/health
```

---

**Ready to deploy?** Run the commands above in your Terminal!

