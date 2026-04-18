import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
try:
    from .model_loader import LocalModel
    from .vertex_client import (
        VertexAIError,
        call_vertex_ai,
        call_vertex_ai_analysis,
        cloud_ai_configured,
        vertex_ai_configured,
    )
    from .decision import decide
except ImportError:
    from model_loader import LocalModel
    from vertex_client import (
        VertexAIError,
        call_vertex_ai,
        call_vertex_ai_analysis,
        cloud_ai_configured,
        vertex_ai_configured,
    )
    from decision import decide

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use system env vars

app = FastAPI(title="CyberShield Phishing Detector")

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictRequest(BaseModel):
    url: str

class PredictResponse(BaseModel):
    label: str
    confidence: float
    source: str

class AnalyzeRequest(BaseModel):
    url: Optional[str] = ""
    content: Optional[str] = ""

class AnalyzeResponse(BaseModel):
    riskLevel: str
    score: int
    patterns: List[str]
    reason: str

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = os.getenv("MODEL_PATH", str(BASE_DIR / "model.pkl"))
local_model = LocalModel(model_path=MODEL_PATH)
scan_history: List[dict] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def label_to_risk(label: str, confidence: float) -> tuple[str, int]:
    confidence = max(0.0, min(1.0, float(confidence)))
    if label == "phishing":
        score = max(60, round(confidence * 100))
        if score >= 75:
            return "HIGH", score
        return "MEDIUM", score

    score = max(1, min(39, round((1.0 - confidence) * 100)))
    return "LOW", score


def content_signals(content: str) -> tuple[List[str], int]:
    text = content.lower()
    checks = [
        ("false urgency", ("urgent", "immediately", "act now", "expires today")),
        ("fear", ("suspended", "blocked", "locked", "fraud alert", "security alert")),
        ("impersonation", ("bank", "government", "microsoft support", "courier", "tax")),
        ("credential request", ("password", "otp", "cvv", "pin", "verify account")),
        ("payment request", ("upi", "qr code", "crypto", "gift card", "processing fee")),
        ("remote access", ("anydesk", "teamviewer", "screen share", "remote access")),
    ]

    patterns = [name for name, keywords in checks if any(keyword in text for keyword in keywords)]
    return patterns[:3], min(45, len(patterns) * 18)


def url_signals(url: str) -> tuple[List[str], int]:
    normalized = url.lower()
    patterns: List[str] = []

    if any(tld in normalized for tld in (".xyz", ".tk", ".ml", ".ga", ".cf", ".ru")):
        patterns.append("suspicious TLD")
    if any(brand in normalized for brand in ("paypal", "google", "amazon", "facebook")) and any(
        word in normalized for word in ("login", "verify", "secure", "update")
    ):
        patterns.append("brand impersonation")
    if any(shortener in normalized for shortener in ("bit.ly", "tinyurl", "t.co")):
        patterns.append("shortened link")

    return patterns[:3], min(45, len(patterns) * 18)


def run_prediction(url: str) -> tuple[str, float, str]:
    local_prediction, local_confidence = local_model.predict(url)
    local_label = "phishing" if local_prediction == 1 else "safe"

    try:
        vertex_label, vertex_confidence = call_vertex_ai(url)
    except VertexAIError:
        return local_label, round(local_confidence, 4), "ml_model"

    return decide(local_label, local_confidence, vertex_label, vertex_confidence)


def save_scan(url: str, analysis: AnalyzeResponse) -> None:
    scan_history.insert(
        0,
        {
            "id": f"local-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "url": url or "manual-text-input",
            "riskLevel": analysis.riskLevel,
            "score": analysis.score,
            "patterns": analysis.patterns,
            "reason": analysis.reason,
            "timestamp": now_iso(),
        },
    )
    del scan_history[100:]


@app.get("/")
def root() -> dict:
    return {
        "status": "CyberShield API is live",
        "storageMode": "memory",
        "analysisMode": "ml_model_with_optional_google_ai",
    }


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "status": "ok",
        "model_path": MODEL_PATH,
        "storageMode": "memory",
        "analysisMode": "ml_model_with_optional_google_ai",
        "googleApiConfigured": bool(os.getenv("GOOGLE_API_KEY")),
        "vertexConfigured": vertex_ai_configured(),
        "cloudAiConfigured": cloud_ai_configured(),
        "timestamp": now_iso(),
    }


@app.get("/config-status")
def config_status() -> dict:
    is_cloud_ready = cloud_ai_configured()
    return {
        "storageMode": "memory",
        "analysisMode": "ml_model_with_optional_google_ai",
        "modelPath": MODEL_PATH,
        "googleApiConfigured": bool(os.getenv("GOOGLE_API_KEY")),
        "vertexConfigured": vertex_ai_configured(),
        "cloudAiConfigured": is_cloud_ready,
        "firebaseReady": False,
        "vertexReady": is_cloud_ready,
        "liveScanningReady": is_cloud_ready,
        "gcpProjectIdConfigured": bool(os.getenv("GCP_PROJECT_ID")),
        "gcpLocation": os.getenv("GCP_LOCATION", "us-central1"),
        "vertexModel": os.getenv("VERTEX_MODEL", "gemini-2.5-flash"),
    }


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="A non-empty URL is required")

    try:
        final_label, final_confidence, source = run_prediction(url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Local model error: {exc}")

    return PredictResponse(
        label=final_label,
        confidence=final_confidence,
        source=source,
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    url = (request.url or "").strip()
    content = (request.content or "").strip()
    if not url and not content:
        raise HTTPException(status_code=400, detail="Either url or content is required")

    content_patterns, content_score = content_signals(content)
    url_patterns, url_score = url_signals(url)
    patterns = list(dict.fromkeys([*url_patterns, *content_patterns]))[:3]

    try:
        if cloud_ai_configured():
            cloud_analysis = call_vertex_ai_analysis(url, content)
            analysis = AnalyzeResponse(
                riskLevel=cloud_analysis["riskLevel"],
                score=cloud_analysis["score"],
                patterns=cloud_analysis["patterns"],
                reason=cloud_analysis["reason"],
            )
            save_scan(url, analysis)
            return analysis

        if url:
            label, confidence, source = run_prediction(url)
            risk_level, model_score = label_to_risk(label, confidence)
        else:
            source = "content_rules"
            model_score = 5
            risk_level = "LOW"
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}")

    signal_score = content_score + url_score
    score = min(99, max(model_score, model_score + signal_score if patterns else model_score))
    if score >= 70:
        risk_level = "HIGH"
    elif score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    if not patterns and risk_level != "LOW":
        patterns = ["suspicious URL"]
    elif not patterns:
        patterns = []

    reason = (
        f"Detected {', '.join(patterns)} indicators."
        if patterns
        else f"No major phishing indicators detected by {source}."
    )

    analysis = AnalyzeResponse(
        riskLevel=risk_level,
        score=int(score),
        patterns=patterns,
        reason=reason,
    )
    save_scan(url, analysis)
    return analysis


@app.get("/stats")
def stats() -> dict:
    return {
        "total": len(scan_history),
        "high": sum(scan["riskLevel"] == "HIGH" for scan in scan_history),
        "medium": sum(scan["riskLevel"] == "MEDIUM" for scan in scan_history),
        "low": sum(scan["riskLevel"] == "LOW" for scan in scan_history),
        "recentScans": scan_history[:10],
    }


@app.delete("/stats")
def clear_stats() -> dict:
    deleted = len(scan_history)
    scan_history.clear()
    return {
        "ok": True,
        "deleted": deleted,
        "message": "Dashboard scan history cleared.",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
