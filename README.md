# CyberShield AI

CyberShield AI is a real-time phishing and scam detection project with 3 parts:

- `extension/`: Chrome extension that scans the active page and shows risk alerts.
- `backend/`: Node.js API and Vertex AI that analyzes page content and stores scan results.
- `dashboard/`: React dashboard that shows scan stats and recent detections.

The extension sends page URL/content to the backend (`/analyze`), and the dashboard reads live stats from backend endpoints like `/stats` and `/health`.

## Project Structure

```
.
|- extension   # Chrome extension (Manifest v3)
|- backend     # Express API + AI analysis
|- dashboard   # React (Vite) analytics dashboard
|- render.yaml # Render deployment config
```

## Prerequisites

- Node.js 20+
- Google Chrome (or Chromium browser with extension support)

## Render Free Trial Note (Important)

This project may use Render free tier for backend hosting. Free services can go to sleep after inactivity.

- First request can be slow (cold start).
- If extension scan or health check looks stuck, wait around **30-90 seconds** and try again.
- Once awakened, next requests are usually fast.

So if the extension says backend is offline right away, please wait a bit and refresh the popup/scan once.

## Run Locally (Recommended Order)

### 1) Load the Extension First

1. Open Chrome and go to `chrome://extensions/`.
2. Enable **Developer mode**.
3. Click **Load unpacked**.
4. Select the `extension` folder from this project.

Optional (if using local backend):

- Open `extension/config.js`
- Set:
  - `var API_BASE_URL = 'http://localhost:8080';`

If you keep the default Render URL, extension requests go to deployed backend.

### 2) Start Backend

```bash
cd backend
npm install
npm run dev
```

Backend runs on `http://localhost:8080` by default.

Useful endpoints:

- `GET /health`
- `POST /analyze`
- `GET /stats`

### 3) Start Dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open the local Vite URL shown in terminal (usually `http://localhost:5173`).

If needed, set `VITE_API_BASE_URL` to your backend URL.

4)Dashbard Deployment Link
https://cyber-shield-eishe7tio-mehtakaran23s-projects.vercel.app/

## Quick Usage

1. Load extension in browser.
2. Open any website tab.
3. Click CyberShield extension icon.
4. Click **Scan current tab**.
5. Check risk level (`LOW`, `MEDIUM`, `HIGH`) and reason/patterns.
6. Open dashboard to monitor totals and recent scans.
