import json
import os
import re
from typing import Any, Dict, List, Tuple

import requests


class VertexAIError(Exception):
    pass


PLACEHOLDER_KEYS = {"your_google_ai_studio_api_key", "your-actual-api-key-here"}


def get_cloud_config() -> Dict[str, str]:
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    location = os.getenv("GCP_LOCATION", "us-central1").strip() or "us-central1"
    model = os.getenv("VERTEX_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"

    if project_id and credentials_path:
        return {
            "mode": "vertex",
            "project_id": project_id,
            "credentials_path": credentials_path,
            "location": location,
            "model": model,
        }

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if api_key and api_key not in PLACEHOLDER_KEYS:
        return {
            "mode": "api_key",
            "api_key": api_key,
            "model": os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash").strip() or "gemini-1.5-flash",
        }

    raise VertexAIError("Cloud AI credentials are not configured")


def cloud_ai_configured() -> bool:
    try:
        get_cloud_config()
    except VertexAIError:
        return False
    return True


def vertex_ai_configured() -> bool:
    project_id = os.getenv("GCP_PROJECT_ID", "").strip()
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    return bool(project_id and credentials_path)


def build_fraud_prompt(url: str, content: str = "") -> str:
    safe_url = (url or "").strip() or "No URL provided"
    safe_content = (content or "").strip()[:2000] or "No page content provided"

    return f"""You are a cybersecurity fraud detection assistant.

Analyze the URL and page content for phishing, scams, impersonation, credential theft, payment fraud, job scams, investment scams, and remote access fraud.

Return only valid JSON in this exact shape:
{{
  "riskLevel": "LOW" or "MEDIUM" or "HIGH",
  "score": number from 0 to 100,
  "patterns": ["max 3 short fraud indicators"],
  "reason": "max 20 words"
}}

Use HIGH for clear credential/payment/impersonation fraud.
Use MEDIUM for suspicious but uncertain signals.
Use LOW for normal or trusted pages.

URL:
{safe_url}

CONTENT:
{safe_content}
"""


def parse_json_text(raw_text: str) -> Dict[str, Any]:
    clean_text = re.sub(r"```(?:json)?|```", "", raw_text or "").strip()
    match = re.search(r"\{.*\}", clean_text, flags=re.DOTALL)
    if match:
        clean_text = match.group(0)

    try:
        payload = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        raise VertexAIError(f"Cloud AI returned invalid JSON: {raw_text[:200]}") from exc

    risk_level = str(payload.get("riskLevel", "MEDIUM")).upper()
    if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
        risk_level = "MEDIUM"

    try:
        score = int(round(float(payload.get("score", 50))))
    except (TypeError, ValueError):
        score = 50
    score = max(0, min(100, score))

    patterns = payload.get("patterns", [])
    if not isinstance(patterns, list):
        patterns = []
    patterns = [str(pattern)[:40] for pattern in patterns[:3]]

    reason = str(payload.get("reason", "Cloud AI completed fraud analysis."))[:160]

    return {
        "riskLevel": risk_level,
        "score": score,
        "patterns": patterns,
        "reason": reason,
    }


def get_response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if part_text:
                return str(part_text)

    raise VertexAIError("Cloud AI returned an empty response")


def generate_with_vertex(config: Dict[str, str], prompt: str) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise VertexAIError("google-genai package is not installed") from exc

    client = genai.Client(
        vertexai=True,
        project=config["project_id"],
        location=config["location"],
    )
    response = client.models.generate_content(
        model=config["model"],
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=220,
            response_mime_type="application/json",
        ),
    )
    return get_response_text(response)


def generate_with_api_key(config: Dict[str, str], prompt: str) -> str:
    endpoint = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config['model']}:generateContent?key={config['api_key']}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 220,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=20)
    except requests.RequestException as exc:
        raise VertexAIError(f"Cloud AI request failed: {exc}") from exc

    if not response.ok:
        raise VertexAIError(f"Cloud AI request failed: {response.status_code} - {response.text}")

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise VertexAIError("Cloud AI returned no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise VertexAIError("Cloud AI returned no content parts")

    return str(parts[0].get("text", ""))


def call_vertex_ai_analysis(url: str, content: str = "") -> Dict[str, Any]:
    config = get_cloud_config()
    prompt = build_fraud_prompt(url, content)

    if config["mode"] == "vertex":
        raw_text = generate_with_vertex(config, prompt)
    else:
        raw_text = generate_with_api_key(config, prompt)

    return parse_json_text(raw_text)


def call_vertex_ai(url: str) -> Tuple[str, float]:
    analysis = call_vertex_ai_analysis(url)
    risk_level = analysis["riskLevel"]
    score = float(analysis["score"])

    if risk_level == "LOW":
        return "safe", max(0.5, min(0.99, 1.0 - (score / 100.0)))

    return "phishing", max(0.5, min(0.99, score / 100.0))
