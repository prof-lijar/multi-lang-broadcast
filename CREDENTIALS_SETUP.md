# Google Cloud Credentials Setup

## Quick Setup Instructions

1. **Download credentials.json from Google Cloud Console:**
   - Go to: https://console.cloud.google.com/
   - Navigate to: IAM & Admin → Service Accounts
   - Create a service account (or use existing)
   - Create a JSON key and download it

2. **Place the file in the project root:**
   ```bash
   cp ~/Downloads/your-credentials-file.json /home/pi/Desktop/multi-lang-broadcast/credentials.json
   ```

3. **Or set environment variable:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/credentials.json"
   ```

## Required APIs

Make sure these APIs are enabled in your Google Cloud project:
- Cloud Speech-to-Text API
- Cloud Translation API  
- Cloud Text-to-Speech API

## Verify Setup

After placing credentials.json, restart the application:
```bash
./run_app.sh
```

You should see: "✓ Google Speech-to-Text client initialized"
