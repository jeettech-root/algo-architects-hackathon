import os
from typing import Any, Dict, Tuple
import requests

class VertexAIError(Exception):
    pass


def get_vertex_config() -> Dict[str, str]:
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key or api_key in {"your_google_ai_studio_api_key", "your-actual-api-key-here"}:
        raise VertexAIError("GOOGLE_API_KEY is missing")

    return {
        "api_key": api_key,
    }


def parse_vertex_response(data: Dict[str, Any]) -> Tuple[str, float]:
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            raise VertexAIError("No response candidates")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise VertexAIError("No content parts")

        text = parts[0].get("text", "").lower().strip()

        # Simple classification based on response text
        if "phishing" in text or "suspicious" in text or "malicious" in text:
            label = "phishing"
            confidence = 0.8
        elif "safe" in text or "legitimate" in text or "benign" in text:
            label = "safe"
            confidence = 0.7
        else:
            # Default to phishing if unclear
            label = "phishing"
            confidence = 0.6

        return label, confidence

    except Exception as e:
        raise VertexAIError(f"Failed to parse response: {e}")


def call_vertex_ai(url: str) -> Tuple[str, float]:
    config = get_vertex_config()

    # Use Google AI Studio API (simpler than Vertex AI)
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={config['api_key']}"

    prompt = f"""Analyze this URL for phishing: {url}

Is this URL safe or phishing? Respond with only one word: either "safe" or "phishing"."""

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 50
        }
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=15)
    except requests.RequestException as exc:
        raise VertexAIError(f"API request failed: {exc}") from exc

    if not response.ok:
        raise VertexAIError(f"API request failed: {response.status_code} - {response.text}")

    data = response.json()
    return parse_vertex_response(data)
