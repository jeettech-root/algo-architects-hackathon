from typing import Tuple


def normalize_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized not in {"safe", "phishing"}:
        return "phishing" if "phish" in normalized else "safe"
    return normalized


def decide(
    local_label: str,
    local_confidence: float,
    vertex_label: str,
    vertex_confidence: float,
) -> Tuple[str, float, str]:
    local_label = normalize_label(local_label)
    vertex_label = normalize_label(vertex_label)
    local_confidence = float(max(0.0, min(1.0, local_confidence)))
    vertex_confidence = float(max(0.0, min(1.0, vertex_confidence)))

    if local_label == vertex_label:
        confidence = round((local_confidence + vertex_confidence) / 2.0, 4)
        return local_label, confidence, "both"

    if local_confidence >= vertex_confidence:
        return local_label, round(local_confidence, 4), "ml_model"

    return vertex_label, round(vertex_confidence, 4), "vertex_ai"
