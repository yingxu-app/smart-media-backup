"""Opt-in, LAN-only newline-framed TCP bridge for the WeChat Mini Program.

The bridge deliberately exposes only Pocket collaboration data. It is disabled
unless the desktop user enables it in Preferences.
"""
from __future__ import annotations

import json
import socketserver
import threading
import time
from collections.abc import Callable
from urllib.parse import quote, unquote


MAX_REQUEST_BYTES = 8 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
PAIR_WINDOW_SECONDS = 10 * 60
MAX_PAIR_FAILURES = 5


class PocketTcpBridge:
    """Serve the allowlisted Pocket API over a small text-framed TCP protocol."""

    def __init__(
        self,
        pairing,
        status_provider: Callable[[], dict],
        history_provider: Callable[[int], list],
        notes_store,
        host: str = "0.0.0.0",
        port: int = 18080,
    ):
        self.pairing = pairing
        self.status_provider = status_provider
        self.history_provider = history_provider
        self.notes_store = notes_store
        self.host = host
        self.port = int(port)
        self._server = None
        self._thread = None
        self._lock = threading.Lock()
        self._pair_failures: dict[str, list[float]] = {}

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def bound_port(self) -> int:
        if self._server is None:
            return self.port
        return int(self._server.server_address[1])

    def start(self) -> int:
        with self._lock:
            if self._server is not None:
                return self.bound_port
            bridge = self

            class Handler(socketserver.StreamRequestHandler):
                def handle(self):
                    self.connection.settimeout(60)
                    while True:
                        raw = self.rfile.readline(MAX_REQUEST_BYTES + 1)
                        if not raw:
                            return
                        if len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
                            self._write_response({"ok": False, "error": "请求过长或格式错误"})
                            return
                        try:
                            encoded = raw.decode("ascii").strip()
                            request = json.loads(unquote(encoded))
                            response = bridge.handle_message(
                                request, str(self.client_address[0])
                            )
                        except (UnicodeDecodeError, ValueError, TypeError):
                            response = {"ok": False, "error": "请求格式错误"}
                        if not self._write_response(response):
                            return

                def _write_response(self, response: dict) -> bool:
                    encoded = quote(
                        json.dumps(response, ensure_ascii=False, separators=(",", ":")),
                        safe="",
                    ).encode("ascii") + b"\n"
                    if len(encoded) > MAX_RESPONSE_BYTES:
                        encoded = quote(
                            json.dumps({"ok": False, "error": "响应过大"}), safe=""
                        ).encode("ascii") + b"\n"
                    try:
                        self.wfile.write(encoded)
                        self.wfile.flush()
                        return True
                    except OSError:
                        return False

            class Server(socketserver.ThreadingTCPServer):
                allow_reuse_address = True
                daemon_threads = True

                def __init__(self, *args, **kwargs):
                    self._connection_slots = threading.BoundedSemaphore(8)
                    super().__init__(*args, **kwargs)

                def process_request(self, request, client_address):
                    if not self._connection_slots.acquire(blocking=False):
                        request.close()
                        return
                    try:
                        super().process_request(request, client_address)
                    except Exception:
                        self._connection_slots.release()
                        raise

                def process_request_thread(self, request, client_address):
                    try:
                        super().process_request_thread(request, client_address)
                    finally:
                        self._connection_slots.release()

            server = Server(
                (self.host, self.port), Handler, bind_and_activate=True
            )
            self._server = server
            self._thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.25},
                name="yingxu-pocket-tcp",
                daemon=True,
            )
            self._thread.start()
            return self.bound_port

    def stop(self) -> None:
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _recent_failures(self, peer: str, now: float) -> list[float]:
        recent = [
            timestamp for timestamp in self._pair_failures.get(peer, [])
            if now - timestamp < PAIR_WINDOW_SECONDS
        ]
        self._pair_failures[peer] = recent
        return recent

    def _pair(self, peer: str, code: str) -> dict:
        now = time.time()
        with self._lock:
            failures = self._recent_failures(peer, now)
            if len(failures) >= MAX_PAIR_FAILURES:
                return {"ok": False, "error": "尝试次数过多，请稍后重试"}
        token = self.pairing.connect(code)
        if not token:
            with self._lock:
                self._pair_failures.setdefault(peer, []).append(now)
            return {"ok": False, "error": "配对码无效或已过期"}
        with self._lock:
            self._pair_failures.pop(peer, None)
        return {"ok": True, "token": token}

    def handle_message(self, request: dict, peer: str = "unknown") -> dict:
        if not isinstance(request, dict):
            return {"ok": False, "error": "请求格式错误"}
        request_id = request.get("id")
        if not isinstance(request_id, (str, int)) or len(str(request_id)) > 64:
            request_id = None
        command = str(request.get("command", ""))
        if command == "pair":
            code = str(request.get("code", "")).strip()
            result = self._pair(peer, code)
        elif command in {"status", "history", "notes.get", "notes.save", "disconnect"}:
            token = str(request.get("token", ""))
            if not self.pairing.is_authorized(token):
                result = {"ok": False, "error": "未配对或会话已过期"}
            elif command == "status":
                result = {"ok": True, "data": self.status_provider()}
            elif command == "history":
                try:
                    limit = max(1, min(int(request.get("limit", 20)), 50))
                except (TypeError, ValueError):
                    limit = 20
                result = {"ok": True, "items": self.history_provider(limit)}
            elif command == "notes.get":
                result = {"ok": True, "notes": self.notes_store.load()}
            elif command == "notes.save":
                data = request.get("data")
                if not isinstance(data, dict):
                    result = {"ok": False, "error": "拍摄信息格式错误"}
                else:
                    result = {"ok": True, "notes": self.notes_store.save(data)}
            else:
                self.pairing.revoke(token)
                result = {"ok": True, "disconnected": True}
        else:
            result = {"ok": False, "error": "不支持的操作"}
        result["id"] = request_id
        return result
