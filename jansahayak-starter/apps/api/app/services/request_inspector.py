from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any
import uuid


_MAX_ENTRIES = 200
_TEXT_LIMIT = 4000
_BODY_LIMIT = 12000


def _clip_text(value: str, limit: int = _TEXT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}... [truncated {len(value) - limit} chars]"


def _sanitize(value: Any, *, limit: int = _BODY_LIMIT) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _clip_text(value, limit)
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(token in lowered for token in ("token", "secret", "password", "authorization", "signature")):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = _sanitize(item, limit=limit)
        return redacted
    if isinstance(value, list):
        return [_sanitize(item, limit=limit) for item in value]
    return _clip_text(str(value), limit)


class RequestInspector:
    def __init__(self) -> None:
        self._entries: deque[dict[str, Any]] = deque(maxlen=_MAX_ENTRIES)
        self._lock = Lock()

    def record(
        self,
        *,
        path: str,
        method: str,
        channel: str,
        request_data: Any,
        response_data: Any,
        status_code: int = 200,
    ) -> dict[str, Any]:
        entry = {
            "id": uuid.uuid4().hex[:10],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": path,
            "method": method,
            "channel": channel,
            "status_code": status_code,
            "request": _sanitize(request_data),
            "response": _sanitize(response_data),
        }
        with self._lock:
            self._entries.appendleft(entry)
        return entry

    def list_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


inspector = RequestInspector()
