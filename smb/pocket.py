"""影序 Pocket 的局域网配对与轻量拍摄信息存储。"""
from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path

from .config import CONFIG_DIR


class PocketPairingManager:
    """短效配对码换取长随机会话令牌；仅保存在当前桌面进程内。"""

    def __init__(self, code_ttl_seconds: int = 600, session_hours: int = 12):
        self.code_ttl_seconds = code_ttl_seconds
        self.session_seconds = max(1, session_hours) * 3600
        self._code = ""
        self._code_expires_at = 0.0
        self._sessions: dict[str, float] = {}
        self._lock = threading.Lock()

    def issue_code(self) -> dict:
        with self._lock:
            self._code = f"{secrets.randbelow(1_000_000):06d}"
            self._code_expires_at = time.time() + self.code_ttl_seconds
            return {
                "code": self._code,
                "expires_at": self._code_expires_at,
                "ttl_seconds": self.code_ttl_seconds,
            }

    def connect(self, code: str) -> str | None:
        now = time.time()
        with self._lock:
            if not self._code or now >= self._code_expires_at:
                return None
            if not secrets.compare_digest(str(code).strip(), self._code):
                return None
            token = secrets.token_urlsafe(32)
            self._sessions[token] = now + self.session_seconds
            self._code = ""
            self._code_expires_at = 0.0
            self._purge_locked(now)
            return token

    def is_authorized(self, token: str | None) -> bool:
        if not token:
            return False
        now = time.time()
        with self._lock:
            self._purge_locked(now)
            return self._sessions.get(token, 0) > now

    def revoke(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def _purge_locked(self, now: float) -> None:
        expired = [token for token, expiry in self._sessions.items() if expiry <= now]
        for token in expired:
            self._sessions.pop(token, None)


class PocketNotesStore:
    """保存手机端填写的拍摄信息，不接触或上传原始素材。"""

    def __init__(self, path: Path | None = None):
        self.path = path or (CONFIG_DIR / "pocket_notes.json")
        self._lock = threading.Lock()

    def load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return self._defaults()
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return self._defaults()
            return {**self._defaults(), **{k: str(v)[:200] for k, v in data.items()}}

    def save(self, data: dict) -> dict:
        allowed = ("event", "location", "device", "notes")
        clean = {key: str(data.get(key, "")).strip()[:200] for key in allowed}
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        return clean

    @staticmethod
    def _defaults() -> dict:
        return {"event": "", "location": "", "device": "", "notes": ""}
