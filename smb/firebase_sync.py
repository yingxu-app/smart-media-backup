"""Firebase email authentication and metadata-only Realtime Database sync."""
from __future__ import annotations

import threading
import time
import re
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from .config import CONFIG_DIR


SERVICE_NAME = "com.yingxuapp.smartmediabackup.firebase"
TERMINAL_STATES = {"done", "completed", "partial", "cancelled", "error", "failed"}


class FirebaseSyncError(ConnectionError):
    """Safe, actionable Firebase failure text suitable for the local UI."""


class KeyringTokenStore:
    """Keep refresh tokens in the OS credential store, never in app config."""

    def __init__(self, keyring_module=None):
        if keyring_module is None:
            import keyring as keyring_module
        self.keyring = keyring_module

    def get(self, uid: str) -> str | None:
        return self.keyring.get_password(SERVICE_NAME, uid)

    def set(self, uid: str, refresh_token: str) -> None:
        self.keyring.set_password(SERVICE_NAME, uid, refresh_token)

    def remove(self, uid: str) -> None:
        try:
            self.keyring.delete_password(SERVICE_NAME, uid)
        except self.keyring.errors.PasswordDeleteError:
            pass


def public_metadata(record: dict[str, Any], *, device_id: str, device_name: str) -> dict[str, Any]:
    """Select approved history fields and explicitly discard local paths/secrets."""
    raw_files = record.get("files")
    files = []
    if isinstance(raw_files, list):
        for item in raw_files[:5000]:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("name") or item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
            files.append({
                "name": str(filename)[:255],
                "size": max(0, int(item.get("size") or 0)),
                "status": str(item.get("status") or "unknown")[:40],
                "mediaType": str(item.get("mediaType") or item.get("media_type") or "")[:20],
            })
    started = record.get("startedAt", record.get("started_at"))
    target_name = str(record.get("targetName", record.get("target_name", "")) or "")
    if target_name:
        target_name = target_name.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return {
        "id": str(record.get("id") or "")[:100],
        "deviceId": str(device_id)[:80],
        "deviceName": str(device_name)[:100],
        "eventName": str(record.get("eventName", record.get("event_name", "")) or "")[:160],
        "location": str(record.get("location") or "")[:160],
        "cameraDevice": str(record.get("cameraDevice", record.get("device_name", "")) or "")[:160],
        "notes": str(record.get("notes") or "")[:2000],
        "targetName": target_name[:100],
        "startedAt": started,
        "finishedAt": record.get("finishedAt", record.get("finished_at")),
        "updatedAt": int(record.get("updatedAt") or time.time() * 1000),
        "status": str(record.get("status") or "unknown")[:40],
        "currentFile": str(record.get("currentFile", record.get("current_file", "")) or "").replace("\\", "/").rsplit("/", 1)[-1][:255],
        "totalFiles": max(0, int(record.get("totalFiles", record.get("total_files", 0)) or 0)),
        "totalBytes": max(0, int(record.get("totalBytes", record.get("total_size", 0)) or 0)),
        "processedFiles": max(0, int(record.get("processedFiles", record.get("processed_files", 0)) or 0)),
        "copiedFiles": max(0, int(record.get("copiedFiles", record.get("copied_files", 0)) or 0)),
        "skippedFiles": max(0, int(record.get("skippedFiles", record.get("skipped_files", 0)) or 0)),
        "verifiedFiles": max(0, int(record.get("verifiedFiles", record.get("verified_files", 0)) or 0)),
        "failedFiles": max(0, int(record.get("failedFiles", record.get("failed_files", 0)) or 0)),
        "files": files,
    }


class FirebaseSyncClient:
    def __init__(self, api_key: str, database_url: str, token_store, device_id: str,
                 *, session=None, timeout: float = 8.0, outbox_path: str | Path | None = None):
        self.api_key = str(api_key or "").strip()
        self.database_url = str(database_url or "").rstrip("/")
        self.token_store = token_store
        self.device_id = str(device_id or "desktop").strip()[:80]
        self.session = session or requests.Session()
        self.timeout = timeout
        self.uid = ""
        self.email = ""
        self.display_name = ""
        self._id_token = ""
        self._expires_at = 0.0
        self._lock = threading.RLock()
        self._last_progress_at = 0.0
        self.outbox_path = Path(outbox_path) if outbox_path else CONFIG_DIR / "firebase_sync_outbox.json"
        self._outbox_lock = threading.RLock()
        self._live_lock = threading.RLock()
        self._live_stop: threading.Event | None = None
        self._live_thread: threading.Thread | None = None
        self._live_response = None
        self._live_value: dict[str, Any] = {}
        self._live_error = ""
        self._live_updated_at = 0.0
        self._live_updated = threading.Event()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.database_url and self.token_store)

    def _json_request(self, method: str, url: str, *, body=None, data=None):
        try:
            response = self.session.request(method, url, json=body, data=data, timeout=self.timeout)
        except requests.exceptions.Timeout as error:
            raise FirebaseSyncError("连接 Firebase 超时，请检查网络、代理或防火墙后重试。") from error
        except requests.exceptions.SSLError as error:
            raise FirebaseSyncError("与 Firebase 的 TLS 安全连接失败，请检查系统时间、证书或代理设置。") from error
        except requests.exceptions.ConnectionError as error:
            raise FirebaseSyncError("无法连接 Firebase，请检查网络、代理或防火墙。") from error
        except requests.exceptions.RequestException as error:
            raise FirebaseSyncError("Firebase 网络请求未完成，请检查网络后重试。") from error
        try:
            payload = response.json()
        except (ValueError, AttributeError):
            payload = {}
        if not 200 <= int(getattr(response, "status_code", 0)) < 300:
            message = payload.get("error", {}).get("message", "") if isinstance(payload, dict) else ""
            code = str(message).split(":", 1)[0].strip()
            if code in {"EMAIL_EXISTS", "EMAIL_NOT_FOUND", "INVALID_EMAIL", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS", "USER_DISABLED", "TOO_MANY_ATTEMPTS_TRY_LATER", "WEAK_PASSWORD", "OPERATION_NOT_ALLOWED", "API_KEY_INVALID", "CONFIGURATION_NOT_FOUND"}:
                raise ValueError(code)
            status = int(getattr(response, "status_code", 0))
            safe_code = code if re.fullmatch(r"[A-Z0-9_]{1,60}", code) else f"HTTP_{status}"
            raise FirebaseSyncError(
                f"Firebase 返回错误代码 {safe_code}（HTTP {status}）。请将错误代码提供给支持人员；不要发送密码。"
            )
        return payload

    def sign_in(self, email: str, password: str, *, create_account: bool = False,
                display_name: str = "") -> dict:
        if not self.configured:
            raise RuntimeError("尚未配置 Firebase 项目")
        endpoint = "accounts:signUp" if create_account else "accounts:signInWithPassword"
        body = {"email": email.strip(), "password": password, "returnSecureToken": True}
        username = str(display_name or "").strip()[:40]
        payload = self._json_request(
            "POST", f"https://identitytoolkit.googleapis.com/v1/{endpoint}?key={quote(self.api_key, safe='')}",
            body=body,
        )
        if (create_account or username) and username:
            try:
                updated = self._json_request(
                    "POST", f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={quote(self.api_key, safe='')}",
                    body={"idToken": payload.get("idToken", ""), "displayName": username, "returnSecureToken": True},
                )
                payload = {**payload, **updated}
            except Exception as error:
                message = (
                    "账号已创建，但用户名暂未同步。请用登录按钮重试，并保留用户名字段。"
                    if create_account else "账号已登录，但用户名暂未同步；请检查网络后重试。"
                )
                raise RuntimeError(message) from error
        uid = str(payload.get("localId") or "")
        refresh = str(payload.get("refreshToken") or "")
        if not uid or not refresh:
            raise ConnectionError("Firebase 登录响应缺少账号会话信息")
        try:
            self.token_store.set(uid, refresh)
        except Exception as error:
            raise FirebaseSyncError(
                "Firebase 已验证账号，但系统凭据库无法保存安全令牌。请检查钥匙串/系统凭据库状态后重试。"
            ) from error
        with self._lock:
            self.uid = uid
            self.email = str(payload.get("email") or email.strip())
            self.display_name = str(payload.get("displayName") or username or "").strip()[:40]
            self._id_token = str(payload.get("idToken") or "")
            self._expires_at = time.time() + max(60, int(payload.get("expiresIn") or 3600))
        return {"uid": uid, "email": self.email, "display_name": self.display_name}

    def restore_session(self, uid: str, email: str = "", display_name: str = "") -> bool:
        if not self.configured:
            return False
        refresh = self.token_store.get(uid)
        if not refresh:
            return False
        payload = self._json_request(
            "POST", f"https://securetoken.googleapis.com/v1/token?key={quote(self.api_key, safe='')}",
            data={"grant_type": "refresh_token", "refresh_token": refresh},
        )
        with self._lock:
            self.uid = str(payload.get("user_id") or uid)
            self.email = email
            self.display_name = str(display_name or "").strip()[:40]
            self._id_token = str(payload.get("id_token") or "")
            self._expires_at = time.time() + max(60, int(payload.get("expires_in") or 3600))
            replacement = str(payload.get("refresh_token") or refresh)
            self.token_store.set(self.uid, replacement)
        return bool(self._id_token)

    def sign_out(self) -> None:
        self.stop_live_watch()
        with self._lock:
            uid = self.uid
            self.uid = self.email = self.display_name = self._id_token = ""
            self._expires_at = 0
        if uid:
            self.token_store.remove(uid)

    def _token(self) -> str:
        with self._lock:
            if self._id_token and self._expires_at > time.time() + 60:
                return self._id_token
            uid = self.uid
            email = self.email
        if not uid or not self.restore_session(uid, email):
            raise PermissionError("请先登录影序云同步账号")
        return self._id_token

    def put(self, path: str, value):
        if not self.uid:
            raise PermissionError("请先登录影序云同步账号")
        token = self._token()
        encoded_path = self._encode_database_path(path)
        url = f"{self.database_url}/users/{quote(self.uid, safe='')}/{encoded_path}.json?auth={quote(token, safe='')}"
        return self._json_request("PUT", url, body=value)

    def get(self, path: str):
        if not self.uid:
            raise PermissionError("请先登录影序云同步账号")
        token = self._token()
        encoded_path = self._encode_database_path(path)
        url = f"{self.database_url}/users/{quote(self.uid, safe='')}/{encoded_path}.json?auth={quote(token, safe='')}"
        return self._json_request("GET", url)

    def start_live_watch(self) -> None:
        """Subscribe to other devices' active progress using RTDB's SSE endpoint."""
        if not self.uid:
            raise PermissionError("请先登录影序云同步账号")
        with self._live_lock:
            if self._live_thread and self._live_thread.is_alive():
                return
            self._live_stop = threading.Event()
            self._live_error = ""
            self._live_thread = threading.Thread(
                target=self._live_watch_loop, args=(self._live_stop,),
                daemon=True, name="yingxu-firebase-live-watch",
            )
            self._live_thread.start()

    def stop_live_watch(self) -> None:
        with self._live_lock:
            stop = self._live_stop
            response = self._live_response
            thread = self._live_thread
            self._live_stop = None
            self._live_response = None
            self._live_thread = None
        if stop:
            stop.set()
        if response:
            try:
                response.close()
            except Exception:
                pass
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2)

    def live_snapshot(self) -> dict[str, Any]:
        with self._live_lock:
            return {
                "items": [dict(item) for item in self._live_value.values() if isinstance(item, dict)],
                "error": self._live_error,
                "updatedAt": self._live_updated_at,
            }

    def wait_for_live_update(self, timeout: float = 1.0) -> bool:
        updated = self._live_updated.wait(timeout)
        self._live_updated.clear()
        return updated

    def _apply_live_event(self, event: str, payload: dict[str, Any]) -> None:
        path = str(payload.get("path") or "/")
        segments = [part for part in path.split("/") if part]
        data = payload.get("data")
        with self._live_lock:
            if not segments and event == "put":
                self._live_value = data if isinstance(data, dict) else {}
            elif not segments and event == "patch" and isinstance(data, dict):
                self._live_value.update(data)
            elif segments:
                target: dict[str, Any] = self._live_value
                for segment in segments[:-1]:
                    child = target.get(segment)
                    if not isinstance(child, dict):
                        child = {}
                        target[segment] = child
                    target = child
                if event == "patch" and isinstance(data, dict):
                    current = target.get(segments[-1])
                    if not isinstance(current, dict):
                        current = {}
                        target[segments[-1]] = current
                    current.update(data)
                elif data is None:
                    target.pop(segments[-1], None)
                else:
                    target[segments[-1]] = data
            self._live_error = ""
            self._live_updated_at = time.time()
        self._live_updated.set()

    def _live_watch_loop(self, stop: threading.Event) -> None:
        while not stop.is_set():
            response = None
            try:
                token = self._token()
                url = f"{self.database_url}/users/{quote(self.uid, safe='')}/live.json?auth={quote(token, safe='')}"
                response = self.session.request(
                    "GET", url, headers={"Accept": "text/event-stream"},
                    stream=True, timeout=(self.timeout, max(30, self.timeout * 4)),
                )
                if not 200 <= int(getattr(response, "status_code", 0)) < 300:
                    raise ConnectionError("Firebase 实时进度订阅失败；请检查账号、规则或网络。")
                with self._live_lock:
                    self._live_response = response
                    self._live_error = ""
                lines: list[str] = []
                for raw_line in response.iter_lines(decode_unicode=True):
                    if stop.is_set():
                        break
                    line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else str(raw_line or "")
                    if line == "":
                        block = "\n".join(lines)
                        lines.clear()
                        event = re.search(r"^event:\s*(.+)$", block, re.MULTILINE)
                        data = re.search(r"^data:\s*(.+)$", block, re.MULTILINE)
                        if event and data:
                            event_name = event.group(1).strip()
                            try:
                                payload = json.loads(data.group(1))
                            except (TypeError, ValueError):
                                continue
                            if event_name in {"put", "patch"} and isinstance(payload, dict):
                                self._apply_live_event(event_name, payload)
                            elif event_name in {"cancel", "auth_revoked"}:
                                with self._live_lock:
                                    self._live_error = "Firebase 拒绝实时订阅；请检查账号和数据库规则。"
                                break
                    elif not line.startswith(":"):
                        lines.append(line)
            except Exception:
                if not stop.is_set():
                    with self._live_lock:
                        self._live_error = "云端实时进度暂不可用，正在重连。"
            finally:
                if response:
                    try:
                        response.close()
                    except Exception:
                        pass
                with self._live_lock:
                    if self._live_response is response:
                        self._live_response = None
            stop.wait(1.5)

    @staticmethod
    def _encode_database_path(path: str) -> str:
        segments = str(path or "").split("/")
        if not segments or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", segment) for segment in segments):
            raise ValueError("Firebase 数据路径包含无效字段")
        return "/".join(quote(segment, safe="") for segment in segments)

    def publish_progress(self, record: dict[str, Any], *, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and now - self._last_progress_at < 2.0:
            return False
        self._last_progress_at = now
        data = public_metadata(record, device_id=self.device_id, device_name="影序桌面")
        data["id"] = data["id"] or f"active-{self.device_id}"
        try:
            if self._outbox_pending():
                self.flush_outbox()
            self.put(f"live/{self.device_id}", data)
            if data["status"] in TERMINAL_STATES:
                if not data["id"].startswith("active-"):
                    self.put(f"history/{data['id']}", data)
                self.put(f"live/{self.device_id}", None)
            self._clear_progress_if_same(data)
        except Exception:
            self._queue_progress(data)
            if data["status"] in TERMINAL_STATES and not data["id"].startswith("active-"):
                self._queue_history(data)
            raise
        return True

    def publish_history(self, record: dict[str, Any], files: list[dict[str, Any]] | None = None):
        data = public_metadata({**record, "files": files or []}, device_id=self.device_id, device_name="影序桌面")
        if not data["id"]:
            return False
        try:
            if self._outbox_pending():
                self.flush_outbox()
            self.put(f"history/{data['id']}", data)
            self._clear_history_if_same(data)
        except Exception:
            self._queue_history(data)
            raise
        return True

    def _read_outbox(self) -> dict:
        try:
            value = json.loads(self.outbox_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                return {"progress": None, "history": []}
            history = value.get("history")
            return {"progress": value.get("progress"), "history": history if isinstance(history, list) else []}
        except (OSError, ValueError, TypeError):
            return {"progress": None, "history": []}

    def _outbox_pending(self) -> bool:
        with self._outbox_lock:
            value = self._read_outbox()
        return bool(value.get("progress") or value.get("history"))

    def _write_outbox(self, value: dict) -> None:
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".firebase-outbox-", suffix=".tmp", dir=self.outbox_path.parent)
        try:
            os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.outbox_path)
            try:
                os.chmod(self.outbox_path, 0o600)
            except OSError:
                pass
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            Path(temporary).unlink(missing_ok=True)
            raise

    def _update_outbox(self, update) -> None:
        with self._outbox_lock:
            value = self._read_outbox()
            update(value)
            if value.get("progress") is None and not value.get("history"):
                self.outbox_path.unlink(missing_ok=True)
            else:
                self._write_outbox(value)

    def _queue_progress(self, record: dict) -> None:
        safe = public_metadata(record, device_id=self.device_id, device_name="影序桌面")
        self._update_outbox(lambda value: value.update(progress=safe))

    def _queue_history(self, record: dict) -> None:
        safe = public_metadata(record, device_id=self.device_id, device_name="影序桌面")
        if not safe["id"]:
            return
        def update(value):
            current = [item for item in value.get("history", []) if item.get("id") != safe["id"]]
            value["history"] = ([safe] + current)[:500]
        self._update_outbox(update)

    def _clear_progress_if_same(self, expected: dict) -> None:
        safe = public_metadata(expected, device_id=self.device_id, device_name="影序桌面")
        def update(value):
            if value.get("progress") == safe:
                value["progress"] = None
        self._update_outbox(update)

    def _clear_history_if_same(self, expected: dict) -> None:
        safe = public_metadata(expected, device_id=self.device_id, device_name="影序桌面")
        def update(value):
            value["history"] = [item for item in value.get("history", []) if item != safe]
        self._update_outbox(update)

    def flush_outbox(self) -> bool:
        if not self.uid:
            raise PermissionError("请先登录影序云同步账号")
        with self._outbox_lock:
            snapshot = self._read_outbox()
        if snapshot["progress"]:
            data = snapshot["progress"]
            self.put(f"live/{self.device_id}", data)
            if data.get("status") in TERMINAL_STATES:
                if not str(data.get("id", "")).startswith("active-"):
                    self.put(f"history/{data['id']}", data)
                self.put(f"live/{self.device_id}", None)
            self._clear_progress_if_same(data)
        for data in snapshot["history"]:
            if data.get("id"):
                self.put(f"history/{data['id']}", data)
                self._clear_history_if_same(data)
        return True
