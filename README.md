# CyberShield - AI-Powered Phishing Detection

## Quick Start

### Option 1: One-Click Start

Double-click `start.bat` or run `start.ps1` in PowerShell.

### Option 2: Manual Start

Start the backend API:

```bash
cd backend
python main.py
```

Start the dashboard:

```bash
cd dashboard
npm run dev
```

## Local Access

- Backend API: `http://localhost:8000`
- Dashboard: `http://localhost:5173`
- Extension: Chrome browser extension

## Render Backend Deployment

This repo includes `render.yaml`, so the easiest deployment path is:

1. Push the repo to GitHub.
2. In Render, choose **New +** -> **Blueprint** and select this repository.
3. Render will create the `cybershield-backend` web service from `backend/`.

If you create the service manually, use:

- Root Directory: leave empty, or use `backend`
- Environment: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

Environment variables:

- `MODEL_PATH=model.pkl`
- `CORS_ORIGINS=*`
- `GOOGLE_API_KEY=...` optional, used for Google AI cross-checking

For Vertex AI fraud detection, add a Render secret file named:

```text
vertex-service-account.json
```

Paste your Google Cloud service account JSON into that secret file. Render mounts it at:

```text
/etc/secrets/vertex-service-account.json
```

Then add these Render environment variables:

```text
GCP_PROJECT_ID=your-google-cloud-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/etc/secrets/vertex-service-account.json
VERTEX_MODEL=gemini-2.5-flash
```

After deployment, set the dashboard environment variable to your Render URL:

```bash
VITE_API_BASE_URL=https://your-render-service.onrender.com
```

For the Chrome extension, replace the local API URL in `extension/background.js` and
`extension/popup.js` with the same Render URL when you want the extension to use the
hosted backend.

## System Requirements

- Python 3.8+
- Node.js 16+
- Google Chrome
- ML model at `backend/model.pkl`

## Features

- Real-time URL phishing detection
- Machine learning model integration
- Optional Google AI model support
- Chrome browser extension
- React dashboard for monitoring
