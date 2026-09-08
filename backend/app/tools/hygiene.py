"""Small bounded audit serializer. It is not a general secret-classification service."""
import json
import math
import re
from typing import Any

_SECRET_KEY = re.compile(r"password|passwd|secret|token|authorization|api.?key|cookie|credential", re.I)
_SECRET_TEXT = re.compile(
    r"(?i)(bearer\s+)[\w.\-/+=]+|"
    r"((?:password|passwd|secret|token|api[_ -]?key)[\"']?\s*[=:]\s*)"
    r"(?:\"[^\"]*\"|'[^']*'|[^\s,;\"}]+)|"
    r"\b(?:sk|ghp)_[A-Za-z0-9_-]{8,}|\bsk-[A-Za-z0-9_-]{8,}"
)
MAX_SNAPSHOT_BYTES = 16384


def clean_text(value: str) -> str:
    return _SECRET_TEXT.sub(lambda match: (match.group(1) or match.group(2) or "") + "[REDACTED]", value[:8192])[:2048]


def snapshot(value: Any) -> Any:
    remaining = [256]

    def visit(item, depth=0):
        remaining[0] -= 1
        if depth > 6 or remaining[0] < 0:
            return "[TRUNCATED]"
        if isinstance(item, dict):
            return {clean_text(str(key))[:100]: "[REDACTED]" if _SECRET_KEY.search(str(key)) else visit(val, depth+1)
                    for key, val in list(item.items())[:40]}
        if isinstance(item, (list, tuple)):
            return [visit(val, depth+1) for val in item[:40]]
        if isinstance(item, str):
            return clean_text(item)
        if item is None or isinstance(item, (bool, int)):
            return item
        if isinstance(item, float):
            return item if math.isfinite(item) else "[NON_FINITE]"
        return "[UNSERIALIZABLE]"

    result = visit(value)
    if len(json.dumps(result, ensure_ascii=True).encode()) > MAX_SNAPSHOT_BYTES:
        return {"truncated": True, "reason": "Audit snapshot exceeded size limit."}
    return result
