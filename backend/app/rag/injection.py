from __future__ import annotations

import re

PATTERN_DEFINITIONS = [
    ("ignore previous instructions", r"ignore\s+(all\s+|any\s+|the\s+)?(previous|prior)\s+instructions?", "high"),
    ("system override", r"system\s+override", "high"),
    ("developer message", r"developer\s+message", "medium"),
    ("reveal secrets", r"reveal\s+(the\s+)?secrets?", "high"),
    ("exfiltrate", r"exfiltrat(e|ion)", "high"),
    ("disable safety", r"disable\s+safety", "high"),
    ("disregard policy", r"disregard\s+(the\s+)?polic(y|ies)", "high"),
    ("tool output says", r"tool\s+output\s+says", "medium"),
    ("run shell command", r"run\s+shell\s+command", "high"),
    ("curl http", r"curl\s+https?://", "high"),
    ("base64 decode", r"base64\s+decode", "medium"),
]


def detect_prompt_injection(text: str) -> dict[str, object]:
    normalized = text.lower()
    matched_patterns: list[str] = []
    severities: list[str] = []

    for label, pattern, severity in PATTERN_DEFINITIONS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            matched_patterns.append(label)
            severities.append(severity)

    if not matched_patterns:
        risk_level = "low"
    elif "high" in severities or len(matched_patterns) >= 3:
        risk_level = "high"
    else:
        risk_level = "medium"

    return {
        "is_suspicious": bool(matched_patterns),
        "matched_patterns": matched_patterns,
        "risk_level": risk_level,
    }
