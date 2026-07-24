"""Flask + SocketIO Web 服务端 — 仪表盘 + 备份控制"""
import os
import sys
import json
import threading
import webbrowser
import subprocess
import uuid
import base64
import io
import secrets
import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from pathlib import Path

import flask
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

# PyInstaller 打包后资源路径修正
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__,
            template_folder=os.path.join(_base, "smb", "templates"),
            static_folder=os.path.join(_base, "smb", "static"))
app.config["SECRET_KEY"] = os.urandom(16).hex()

from .config import config, CONFIG_DIR
from .detector import list_removable_volumes, list_all_volumes, SDCardWatcher
from .backup import BackupEngine
from . import db

APP_VERSION = "1.0.8"

# 初始化数据库
db.init_db()

socketio = SocketIO(app, cors_allowed_origins="*")

engine = BackupEngine()
_scan_cache = {"files": [], "volumes": []}
_pocket_lock = threading.Lock()
_pocket_imports_file = CONFIG_DIR / "pocket_imports.json"
_pocket_pairings = {}
_POCKET_PUBLIC_ORIGIN = "https://luguanlin20050927.github.io"


def _is_loopback_request():
    return request.remote_addr in {"127.0.0.1", "::1"}


def _local_ipv4_addresses():
    """返回可供同一局域网设备访问的 IPv4 地址，不暴露公网地址。"""
    addresses = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addresses.add(ip)
    except OSError:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 9))
        ip = probe.getsockname()[0]
        probe.close()
        if not ip.startswith("127."):
            addresses.add(ip)
    except OSError:
        pass
    return sorted(addresses)


def _cleanup_pocket_pairings():
    now = time.time()
    for code, pairing in list(_pocket_pairings.items()):
        if pairing["expires_at"] <= now:
            _pocket_pairings.pop(code, None)


def _pairing_token_is_valid(token):
    if not token:
        return False
    _cleanup_pocket_pairings()
    return any(secrets.compare_digest(pairing.get("token", ""), token) for pairing in _pocket_pairings.values())


def _is_remote_pocket_request():
    origin = request.headers.get("Origin", "")
    return bool(origin and not origin.startswith("http://127.0.0.1") and not origin.startswith("http://localhost"))


@app.after_request
def add_pocket_cors_headers(response):
    """只允许官网 PWA 跨域访问 Pocket 接口；其余 API 保持本地同源。"""
    origin = request.headers.get("Origin", "")
    if request.path.startswith("/api/pocket/") and origin == _POCKET_PUBLIC_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Yingxu-Pocket-Token"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return response


def _load_pocket_imports():
    """读取移动端导入清单；损坏文件不影响备份主流程。"""
    try:
        raw = json.loads(_pocket_imports_file.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_pocket_imports(records):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = _pocket_imports_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(_pocket_imports_file)


def _validate_pocket_payload(data):
    """只接收 Pocket 的文件元数据，拒绝路径、二进制内容与超量导入。"""
    if not isinstance(data, dict) or data.get("app") != "影序 Pocket":
        raise ValueError("这不是有效的影序 Pocket 导入清单")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("导入清单中没有素材")
    if len(items) > 10000:
        raise ValueError("单次最多导入 10,000 条素材元数据")
    clean_items = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("素材记录格式无效")
        name = str(item.get("name", "")).strip()
        media_type = str(item.get("type", "application/octet-stream")).strip()
        size = item.get("size", 0)
        if not name or len(name) > 255 or "/" in name or "\\" in name:
            raise ValueError("素材文件名无效")
        if not isinstance(size, (int, float)) or size < 0 or size > 1024 ** 5:
            raise ValueError("素材大小无效")
        clean_items.append({
            "name": name,
            "type": media_type[:100],
            "size": int(size),
            "added_at": str(item.get("addedAt", ""))[:64],
        })
    return clean_items


# ====== SocketIO 实时推送 ======

def broadcast_progress(data):
    """备份进度广播到所有连接的前端"""
    try:
        socketio.emit("backup_progress", data)
    except Exception:
        pass


# 注册进度回调
engine.progress.on_update(broadcast_progress)


# ====== HTTP 路由 ======

@app.route("/")
def dashboard():
    """主仪表盘页面"""
    return render_template("dashboard.html")


@app.route("/history")
def history():
    """历史记录页面"""
    return render_template("history.html")


@app.route("/settings")
def settings():
    """设置页面"""
    return render_template("settings.html")


@app.route("/website")
def website():
    """产品官网 landing page"""
    return flask.send_from_directory(
        os.path.join(_base, "website"), "index.html"
    )


@app.route("/download/macos")
def download_macos():
    """下载 macOS .app"""
    zip_path = os.path.join(_base, "desktop", "dist")
    # 如果 dist 下有 zip 就提供，否则提示
    zip_file = os.path.join(zip_path, "SmartMediaBackup-macOS.zip")
    if os.path.exists(zip_file):
        return flask.send_file(zip_file, as_attachment=True,
                               download_name="SmartMediaBackup-macOS.zip")
    return jsonify({"error": "下载文件未就绪"}), 404


@app.route("/api/open_folder", methods=["POST"])
def api_open_folder():
    """打开目录，或在文件管理器中定位单个文件。"""
    data = request.get_json(silent=True) or {}
    path = data.get("path", "").strip()
    reveal = bool(data.get("reveal", False))
    if not path:
        return jsonify({"error": "路径不能为空"}), 400
    if not os.path.exists(path):
        return jsonify({"error": "路径不存在"}), 404
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path] if reveal and os.path.isfile(path) else ["open", path])
        elif sys.platform.startswith("win"):
            if reveal and os.path.isfile(path):
                subprocess.Popen(["explorer", "/select,", path])
            else:
                os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path) if reveal and os.path.isfile(path) else path])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ====== 百度网盘 API ======

@app.route("/api/baidu/status")
def api_baidu_status():
    """百度网盘配置和授权状态"""
    from .baidu import baidu
    return jsonify({
        "configured": baidu.is_configured(),
        "authorized": baidu.is_authorized(),
        "api_key": baidu.api_key[:6] + "..." if baidu.api_key else "",
    })


@app.route("/api/baidu/settings", methods=["POST"])
def api_baidu_settings():
    """保存百度网盘 API 配置"""
    from .baidu import baidu
    data = request.get_json(silent=True) or {}
    baidu.configure(
        api_key=data.get("api_key", ""),
        secret_key=data.get("secret_key", ""),
        app_id=data.get("app_id", ""),
    )
    return jsonify({"status": "ok"})


@app.route("/api/baidu/auth_url")
def api_baidu_auth_url():
    """获取授权 URL"""
    from .baidu import baidu
    if not baidu.is_configured():
        return jsonify({"error": "请先配置 API Key"}), 400
    return jsonify({"url": baidu.get_auth_url()})


@app.route("/api/baidu/exchange", methods=["POST"])
def api_baidu_exchange():
    """兑换授权码"""
    from .baidu import baidu
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()
    if not code:
        return jsonify({"error": "请输入授权码"}), 400
    ok = baidu.exchange_code(code)
    return jsonify({"ok": ok})


@app.route("/api/baidu/quota")
def api_baidu_quota():
    """网盘容量信息"""
    from .baidu import baidu
    quota = baidu.get_quota()
    return jsonify(quota)


# ====== AI 命名 API ======

@app.route("/api/ai/status")
def api_ai_status():
    """AI 命名配置状态"""
    from .ai_namer import ai_namer
    return jsonify({
        "enabled": ai_namer.is_enabled(),
        "backend": ai_namer.backend,
        "ollama_model": ai_namer.ollama_model,
        "openai_model": ai_namer.openai_model,
    })


@app.route("/api/ai/settings", methods=["POST"])
def api_ai_settings():
    """保存 AI 命名配置"""
    from .ai_namer import ai_namer
    data = request.get_json(silent=True) or {}
    ai_namer.backend = data.get("backend", ai_namer.backend)
    ai_namer.ollama_model = data.get("ollama_model", ai_namer.ollama_model)
    ai_namer.ollama_url = data.get("ollama_url", ai_namer.ollama_url)
    ai_namer.openai_key = data.get("openai_key", ai_namer.openai_key)
    ai_namer.openai_model = data.get("openai_model", ai_namer.openai_model)
    ai_namer.openai_base = data.get("openai_base", ai_namer.openai_base)
    ai_namer.save()
    return jsonify({"status": "ok"})


# ====== API ======

@app.route("/api/status")
def api_status():
    """返回当前状态"""
    return jsonify({
        "status": engine.progress.status,
        "progress": engine.progress.to_dict(),
        "version": APP_VERSION,
    })


@app.route("/api/volumes")
def api_volumes():
    """列出所有可用卷（用于目标磁盘选择）"""
    all_vols = list_all_volumes()
    # 过滤系统卷
    system_mounts = {"/", "/System/Volumes/", "/System/Volumes/VM", "/System/Volumes/Preboot",
                     "/System/Volumes/Update", "/System/Volumes/xarts", "/System/Volumes/iSCPreboot",
                     "/System/Volumes/Hardware", "/System/Volumes/Data"}
    result = []
    for v in all_vols:
        mount = v["mount_point"]
        # 排除系统卷
        if mount.rstrip("/") in system_mounts or any(mount.startswith(s) for s in system_mounts):
            continue
        # macOS: 排除 Macintosh HD
        if sys.platform == "darwin" and "macintosh" in mount.lower():
            continue
        # 排除根目录
        if mount == "/":
            continue
        # 排除 >5TB (NAS)
        total = v.get("size_total", 0)
        if total > 5 * 1024**4:
            continue
        result.append(v)
    return jsonify(result)


@app.route("/api/scan", methods=["GET", "POST"])
def api_scan():
    """扫描 SD 卡内容 (GET 和 POST 均可)"""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        data = {}
    mount_point = data.get("mount_point", "")

    if not mount_point:
        # 如果没有指定，使用第一个检测到的可移动卷
        vols = list_removable_volumes()
        if vols:
            mount_point = vols[0]["mount_point"]

    if not mount_point or not os.path.ismount(mount_point):
        return jsonify({"error": "未检测到 SD 卡", "files": [], "devices": []})

    from .organizer import scan_sd_card, batch_extract_metadata
    raw = scan_sd_card(mount_point)
    if not raw:
        return jsonify({"error": "未找到照片或视频文件", "files": [], "devices": []})

    files = batch_extract_metadata(raw)

    # 按设备统计
    devices = {}
    for f in files:
        cam = f.get("camera", "Unknown")
        if cam not in devices:
            devices[cam] = {"files": 0, "photos": 0, "videos": 0, "size": 0}
        devices[cam]["files"] += 1
        devices[cam]["size"] += f.get("size", 0)
        mt = f.get("media_type", "other")
        if mt in ("photo", "raw"):
            devices[cam]["photos"] += 1
        elif mt == "video":
            devices[cam]["videos"] += 1

    # 构建返回
    device_list = [{"name": k, **v} for k, v in devices.items()]
    file_list = [{
        "filename": f["filename"],
        "camera": f.get("camera", ""),
        "media_type": f.get("media_type", ""),
        "size": f.get("size", 0),
    } for f in files[:500]]  # 前端只展示前 500 个

    global _scan_cache
    _scan_cache = {"files": raw, "devices": device_list}

    # AI 自动命名建议
    suggested_name = ""
    if files:
        from .ai_namer import ai_namer
        sample_paths = [f["path"] for f in files[:5] if f.get("media_type") in ("photo", "raw")]
        if sample_paths:
            suggested_name = ai_namer.suggest_event_name(sample_paths) or ""

    return jsonify({
        "devices": device_list,
        "files": file_list,
        "total_files": len(files),
        "total_size": sum(f.get("size", 0) for f in files),
        "mount_point": mount_point,
        "suggested_name": suggested_name,
    })


@app.route("/api/start_backup", methods=["POST"])
def api_start_backup():
    """开始备份"""
    if engine.progress.status in ("copying", "verifying"):
        return jsonify({"error": "正在备份中，请等待完成"}), 409

    data = request.get_json() or {}
    mount_point = data.get("mount_point", "")
    event_name = data.get("event_name", "").strip()
    event_names = data.get("event_names") or []
    if not event_names and event_name:
        event_names = [e.strip() for e in event_name.replace("，", ",").split(",") if e.strip()]
    backup_root = data.get("backup_root", "")
    backup_targets = data.get("backup_targets") or []

    if not event_name and not event_names:
        return jsonify({"error": "请输入事件文件夹名"}), 400
    if not event_names and event_name:
        event_names = [e.strip() for e in event_name.replace("，", ",").split(",") if e.strip()]
    if not backup_root and not backup_targets:
        return jsonify({"error": "请选择备份目标位置"}), 400
    if not mount_point:
        vols = list_removable_volumes()
        if vols:
            mount_point = vols[0]["mount_point"]
    if not mount_point or not os.path.isdir(mount_point):
        return jsonify({"error": "未检测到 SD 卡"}), 400

    # 开始前检查目标是否可用、可写且有足够空间，避免进行到一半才发现备份失败。
    targets = list(dict.fromkeys(t.strip() for t in [backup_root, *backup_targets] if t and t.strip()))
    if not targets:
        return jsonify({"error": "请选择至少一个备份目标位置"}), 400
    from .organizer import scan_sd_card
    source_files = scan_sd_card(mount_point)
    required_bytes = sum(item.get("size", 0) for item in source_files)
    for target in targets:
        if not os.path.isdir(target):
            return jsonify({"error": f"备份目标不存在：{target}"}), 400
        if not os.access(target, os.W_OK):
            return jsonify({"error": f"备份目标不可写：{target}"}), 400
        try:
            free_bytes = os.statvfs(target).f_bavail * os.statvfs(target).f_frsize
        except OSError as exc:
            return jsonify({"error": f"无法读取目标盘空间：{target}（{exc}）"}), 400
        if required_bytes > free_bytes:
            return jsonify({
                "error": f"目标盘空间不足：{target}",
                "required_bytes": required_bytes,
                "free_bytes": free_bytes,
            }), 400

    # 保存配置
    config.last_backup_root = backup_root
    if backup_targets:
        config.backup_targets = list(dict.fromkeys(backup_targets))
        config.save()

    # 在新线程运行备份
    def _run():
        try:
            engine.run(mount_point, event_name, backup_root,
                       enable_verify=config.verify_method == "sha256",
                       backup_targets=backup_targets or None,
                       event_names=event_names or None)
        except Exception as e:
            print(f"[SMB] 备份失败: {e}", file=sys.stderr)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({"status": "started"})


@app.route("/api/cancel_backup", methods=["POST"])
def api_cancel_backup():
    """取消备份"""
    engine.cancel()
    return jsonify({"status": "cancelling"})


@app.route("/api/cleanup_sd", methods=["POST"])
def api_cleanup_sd():
    """备份完成后删除SD卡文件（移到废纸篓）"""
    mp = engine.progress.mount_point
    if not mp:
        return jsonify({"error": "没有可清理的SD卡"})
    if not engine.progress.can_cleanup:
        return jsonify({"error": "备份未完成，不能清理"})
    try:
        deleted = []
        for root, dirs, files in os.walk(mp):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if sys.platform == "darwin":
                        import subprocess
                        subprocess.run(["osascript", "-e",
                            f'tell app "Finder" to delete (POSIX file "{fp}" as alias)'],
                            capture_output=True, timeout=30)
                    elif sys.platform.startswith("win"):
                        # 使用 Windows 回收站，而不是不可恢复的 os.remove。
                        escaped = fp.replace("'", "''")
                        command = (
                            "Add-Type -AssemblyName Microsoft.VisualBasic; "
                            "[Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile("
                            f"'{escaped}', 'OnlyErrorDialogs', 'SendToRecycleBin')"
                        )
                        subprocess.run(
                            ["powershell", "-NoProfile", "-Command", command],
                            capture_output=True, text=True, timeout=30, check=True,
                        )
                    else:
                        # Linux 桌面环境不保证存在回收站 API；宁可拒绝删除，也不做永久删除。
                        raise RuntimeError("当前系统未配置安全回收站，已阻止永久删除")
                    deleted.append(f)
                except Exception:
                    pass
        engine.progress.can_cleanup = False
        engine.progress.notify()
        return jsonify({"status": "cleaned", "deleted": len(deleted)})
    except Exception as e:
        return jsonify({"error": f"清理失败: {e}"})


@app.route("/api/sync/export")
def api_sync_export():
    """导出备份历史（供其他实例同步）"""
    history = db.get_all_history()
    db_path = str(db.DB_PATH)
    return jsonify({
        "version": APP_VERSION,
        "exported_at": datetime.now().isoformat(),
        "history": history,
    })


@app.route("/api/sync/import", methods=["POST"])
def api_sync_import():
    """导入外部备份历史记录"""
    data = request.get_json() or {}
    records = data.get("history", [])
    imported = db.import_history(records)
    return jsonify({"imported": imported})


@app.route("/api/sync/pull", methods=["POST"])
def api_sync_pull():
    """从远程实例拉取备份历史"""
    data = request.get_json() or {}
    remote_url = data.get("url", "").strip().rstrip("/")
    if not remote_url:
        return jsonify({"error": "请输入远程地址"})
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{remote_url}/api/sync/export", timeout=15)
        remote_data = json.loads(resp.read().decode())
        imported = db.import_history(remote_data.get("history", []))
        return jsonify({"imported": imported, "source": remote_url})
    except Exception as e:
        return jsonify({"error": f"同步失败: {e}"})


@app.route("/api/pocket/imports")
def api_pocket_imports():
    """列出由影序 Pocket 导入的移动端素材清单。"""
    with _pocket_lock:
        records = _load_pocket_imports()
    return jsonify({"imports": records})


@app.route("/api/pocket/lan-status")
def api_pocket_lan_status():
    """供桌面工作台显示局域网配对状态；只允许本机读取。"""
    if not _is_loopback_request():
        return jsonify({"error": "此接口仅限桌面端本机访问"}), 403
    return jsonify({
        "enabled": config.pocket_lan_enabled,
        "addresses": _local_ipv4_addresses() if config.pocket_lan_enabled else [],
        "port": config.web_port,
        "restart_required": False,
    })


@app.route("/api/pocket/pairing", methods=["POST"])
def api_pocket_pairing():
    """在本机生成五分钟有效的扫码配对信息。"""
    if not _is_loopback_request():
        return jsonify({"error": "配对码只能在桌面端生成"}), 403
    if not config.pocket_lan_enabled:
        return jsonify({"error": "请先在设置中开启“允许影序 Pocket 局域网连接”，然后重启影序"}), 409
    addresses = _local_ipv4_addresses()
    if not addresses:
        return jsonify({"error": "未找到可用局域网地址，请确认电脑已连接 Wi-Fi 或网线"}), 409
    _cleanup_pocket_pairings()
    code = f"{secrets.randbelow(1_000_000):06d}"
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + 300
    _pocket_pairings[code] = {"token": token, "expires_at": expires_at}
    desktop_url = f"http://{addresses[0]}:{config.web_port}"
    mobile_url = "https://luguanlin20050927.github.io/smart-media-backup/mobile-v22.html?" + urlencode({"desktop": desktop_url, "code": code})
    try:
        import qrcode
        image = qrcode.make(mobile_url)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        qr_data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:
        return jsonify({"error": f"二维码生成失败: {exc}"}), 500
    return jsonify({
        "code": code,
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
        "desktop_url": desktop_url,
        "mobile_url": mobile_url,
        "qr_data_url": qr_data_url,
        "expires_in": 300,
    })


@app.route("/api/pocket/pair", methods=["POST", "OPTIONS"])
def api_pocket_pair():
    """PWA 用一次性配对码换取短期令牌；仅返回给已扫码的同一用户。"""
    if request.method == "OPTIONS":
        return ("", 204)
    data = request.get_json(silent=True) or {}
    code = str(data.get("code", "")).strip()
    _cleanup_pocket_pairings()
    pairing = _pocket_pairings.get(code)
    if not pairing or pairing["expires_at"] <= time.time():
        return jsonify({"error": "配对码无效或已过期，请回到桌面端重新生成"}), 401
    return jsonify({"token": pairing["token"], "expires_at": datetime.fromtimestamp(pairing["expires_at"], timezone.utc).isoformat()})


@app.route("/api/pocket/import", methods=["POST"])
def api_pocket_import():
    """导入移动端导出的 JSON 元数据清单，不上传、不复制原始文件。"""
    if _is_remote_pocket_request() and not _pairing_token_is_valid(request.headers.get("X-Yingxu-Pocket-Token", "")):
        return jsonify({"error": "请先通过桌面端二维码完成配对"}), 401
    data = request.get_json(silent=True)
    try:
        items = _validate_pocket_payload(data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    photos = sum(item["type"].startswith("image/") for item in items)
    videos = sum(item["type"].startswith("video/") for item in items)
    imported_at = datetime.now(timezone.utc).isoformat()
    record = {
        "id": uuid.uuid4().hex,
        "created_at": str(data.get("createdAt", ""))[:64],
        "imported_at": imported_at,
        "item_count": len(items),
        "photo_count": photos,
        "video_count": videos,
        "total_bytes": sum(item["size"] for item in items),
        "suggested_event_name": f"手机素材_{datetime.now().strftime('%Y%m%d_%H%M')}",
        "items": items,
    }
    with _pocket_lock:
        records = _load_pocket_imports()
        records.insert(0, record)
        _save_pocket_imports(records[:100])
    return jsonify({"import": record}), 201


@app.route("/api/pocket/imports/<import_id>", methods=["DELETE"])
def api_delete_pocket_import(import_id):
    """仅移除本地元数据记录，绝不影响手机或桌面的原始文件。"""
    with _pocket_lock:
        records = _load_pocket_imports()
        updated = [record for record in records if record.get("id") != import_id]
        if len(updated) == len(records):
            return jsonify({"error": "导入记录不存在"}), 404
        _save_pocket_imports(updated)
    return jsonify({"status": "deleted"})


@app.route("/api/history")
def api_history():
    """获取历史记录"""
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    query = request.args.get("query", "", type=str).strip()
    status = request.args.get("status", "", type=str).strip()
    device = request.args.get("device", "", type=str).strip()
    date_from = request.args.get("date_from", "", type=str).strip()
    date_to = request.args.get("date_to", "", type=str).strip()
    records = db.get_backups(limit, offset, query, status, device, date_from, date_to)
    total = db.count_backups(query, status, device, date_from, date_to)
    return jsonify({
        "items": records,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "query": query,
            "status": status,
            "device": device,
            "date_from": date_from,
            "date_to": date_to,
        }
    })


@app.route("/api/history/<int:backup_id>")
def api_history_detail(backup_id):
    """获取单条历史详情"""
    record = db.get_backup(backup_id)
    if not record:
        return jsonify({"error": "未找到这条备份记录"}), 404
    files = db.get_backup_files(backup_id, 500)
    target_results = {}
    report_path = record.get("report_path") or ""
    if report_path and os.path.isfile(report_path):
        try:
            with open(report_path, "r", encoding="utf-8") as report_file:
                target_results = json.load(report_file).get("target_results", {})
        except (OSError, json.JSONDecodeError):
            pass
    return jsonify({"record": record, "files": files, "target_results": target_results})


@app.route("/api/history/<int:backup_id>/report")
def api_history_report(backup_id):
    """下载或查看某次备份的 JSON 报告。"""
    record = db.get_backup(backup_id)
    if not record:
        return jsonify({"error": "未找到这条备份记录"}), 404
    report_path = record.get("report_path") or ""
    if not report_path or not os.path.isfile(report_path):
        return jsonify({"error": "这次备份尚未生成报告"}), 404
    return flask.send_file(report_path, as_attachment=True, download_name=os.path.basename(report_path))


@app.route("/api/history/<int:backup_id>/reverify", methods=["POST"])
def api_history_reverify(backup_id):
    """用存档中的 SHA256 再次核验文件，确认归档盘内容仍然完整。"""
    record = db.get_backup(backup_id)
    if not record:
        return jsonify({"error": "未找到这条备份记录"}), 404
    from .verifier import ChecksumVerifier
    verifier = ChecksumVerifier()
    checked = passed = missing = mismatched = unavailable = 0
    failures = []
    for item in db.get_backup_files(backup_id, 500):
        if item.get("status") not in ("completed", "reviewed"):
            continue
        dest_path = item.get("dest_path") or ""
        expected_hash = item.get("source_hash") or ""
        if not dest_path or not expected_hash:
            unavailable += 1
            continue
        checked += 1
        actual_hash = verifier.hash_file(dest_path)
        if not actual_hash:
            missing += 1
            failures.append({"path": dest_path, "reason": "文件不存在或无法读取"})
        elif actual_hash != expected_hash:
            mismatched += 1
            failures.append({"path": dest_path, "reason": "SHA256 不一致"})
        else:
            passed += 1
    return jsonify({
        "backup_id": backup_id,
        "checked": checked,
        "passed": passed,
        "missing": missing,
        "mismatched": mismatched,
        "unavailable": unavailable,
        "ok": checked > 0 and missing == 0 and mismatched == 0,
        "failures": failures[:20],
    })


@app.route("/api/history/<int:backup_id>/retry", methods=["POST"])
def api_history_retry(backup_id):
    """用原任务参数重新执行，已完整落盘的文件会自动跳过。"""
    if engine.progress.status in ("scanning", "metadata", "copying", "verifying", "reviewing"):
        return jsonify({"error": "当前已有任务在运行"}), 409
    record = db.get_backup(backup_id)
    if not record:
        return jsonify({"error": "未找到这条备份记录"}), 404
    data = request.get_json(silent=True) or {}
    mount_point = data.get("mount_point", "").strip()
    if not mount_point:
        volumes = list_removable_volumes()
        if volumes:
            mount_point = volumes[0]["mount_point"]
    if not mount_point or not os.path.isdir(mount_point):
        return jsonify({"error": "请重新插入原始 SD 卡后再重试"}), 400
    try:
        backup_targets = json.loads(record.get("backup_targets") or "[]")
    except (TypeError, json.JSONDecodeError):
        backup_targets = []

    def _run_retry():
        try:
            engine.run(
                mount_point, record["event_name"], record["backup_root"],
                enable_verify=config.verify_method == "sha256",
                backup_targets=backup_targets or None,
            )
        except Exception as exc:
            print(f"[SMB] 重试失败: {exc}", file=sys.stderr)

    threading.Thread(target=_run_retry, daemon=True).start()
    return jsonify({"status": "started", "message": "已开始重试；完整文件会自动跳过"})


@app.route("/api/library/search")
def api_library_search():
    """从已完成的备份中检索素材，解决“备份后找不到文件”的问题。"""
    limit = max(1, min(request.args.get("limit", 100, type=int), 500))
    offset = max(0, request.args.get("offset", 0, type=int))
    query = request.args.get("query", "", type=str).strip()
    device = request.args.get("device", "", type=str).strip()
    media_type = request.args.get("media_type", "", type=str).strip()
    items = db.search_library(query, device, media_type, limit, offset)
    total = db.count_library(query, device, media_type)
    return jsonify({
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {"query": query, "device": device, "media_type": media_type},
    })


# ====== SocketIO ======

@socketio.on("connect")
def on_connect():
    emit("connected", {"status": "ok"})


@socketio.on("request_status")
def on_request_status():
    emit("backup_progress", engine.progress.to_dict())


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    """读写高级设置"""
    from .config import config
    if request.method == "POST":
        data = request.get_json() or {}
        if "web_port" in data:
            port = int(data["web_port"])
            if not 1024 <= port <= 65535:
                return jsonify({"error": "端口必须在 1024 到 65535 之间"}), 400
            config.web_port = port
        if "auto_open_browser" in data:
            config.auto_open_browser = bool(data["auto_open_browser"])
        if "verify_method" in data:
            method = data["verify_method"]
            if method not in {"sha256", "skip"}:
                return jsonify({"error": "不支持的校验方式"}), 400
            config.verify_method = method
        if "webhook_url" in data:
            config.webhook_url = data["webhook_url"]
        if "max_speed_mbps" in data:
            config.max_speed_mbps = int(data["max_speed_mbps"])
        if "phash_threshold" in data:
            config.phash_threshold = int(data["phash_threshold"])
        if "sort_order" in data:
            config.sort_order = data["sort_order"]
        if "pocket_lan_enabled" in data:
            config.pocket_lan_enabled = bool(data["pocket_lan_enabled"])
        config.save()
        return jsonify({"status": "saved"})
    return jsonify({
        "web_port": config.web_port,
        "auto_open_browser": config.auto_open_browser,
        "verify_method": config.verify_method,
        "webhook_url": config.webhook_url,
        "max_speed_mbps": config.max_speed_mbps,
        "phash_threshold": config.phash_threshold,
        "sort_order": config.sort_order,
        "pocket_lan_enabled": config.pocket_lan_enabled,
    })


@app.route("/api/setup/status")
def api_setup_status():
    """返回当前安装状态（用于首次启动引导）"""
    import shutil
    ollama_installed = shutil.which("ollama") is not None
    from .ai_namer import ai_namer
    return jsonify({
        "ollama_installed": ollama_installed,
        "ai_enabled": ai_namer.is_enabled(),
        "show_setup": not ollama_installed and not ai_namer.is_enabled(),
    })


@app.route("/api/setup/install_ollama", methods=["POST"])
def api_setup_install_ollama():
    """静默安装 Ollama（命令行版，无图标）"""
    import subprocess, shutil
    if shutil.which("ollama"):
        return jsonify({"status": "already_installed"})
    try:
        # brew install ollama = CLI only, no GUI icon
        result = subprocess.run(
            ["brew", "install", "ollama"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr[:200]})
        # 启动 ollama 后台服务
        subprocess.run(["ollama", "serve"], capture_output=True, timeout=5)
        return jsonify({"status": "installed"})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/setup/pull_ai_model", methods=["POST"])
def api_setup_pull_model():
    """下载 AI 视觉模型（llava）"""
    import subprocess
    try:
        result = subprocess.run(
            ["ollama", "pull", "llava"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr[:200]})
        # 自动启用 AI 命名
        from .ai_namer import ai_namer
        ai_namer.backend = "ollama"
        ai_namer.ollama_model = "llava"
        ai_namer.save()
        return jsonify({"status": "ready"})
    except Exception as e:
        return jsonify({"error": str(e)})


# ====== 启动 ======

def main():
    """启动 Web 服务"""
    import socket

    # 找可用端口
    port = config.web_port
    host = "0.0.0.0" if config.pocket_lan_enabled else config.web_host

    # 数据库初始化
    db.init_db()

    # 确保配置目录存在
    from .config import CONFIG_DIR
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 启动 SD 卡监听
    def _on_sd_insert(volume: dict):
        import webbrowser
        if config.auto_open_browser:
            webbrowser.open(f"http://{host}:{port}")
        print(f"[SMB] 📸 SD 卡已插入: {volume['name']} ({volume['mount_point']})")

    watcher = SDCardWatcher(on_insert=_on_sd_insert)
    watcher.start()

    print(f"""
╔══════════════════════════════════════════╗
║     🖼  影序 YINGXU                      ║
║                                          ║
║  打开浏览器访问:                         ║
║    http://localhost:{port}                ║
║                                          ║
║  按 Ctrl+C 停止服务                      ║
╚══════════════════════════════════════════╝
""")

    # 自动打开浏览器
    if config.auto_open_browser:
        webbrowser.open(f"http://localhost:{port}")

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
