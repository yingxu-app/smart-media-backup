"""Flask + SocketIO Web 服务端 — 仪表盘 + 备份控制"""
import os
import sys
import json
import threading
import webbrowser
import subprocess
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

from .config import config
from .detector import list_removable_volumes, list_all_volumes, SDCardWatcher
from .backup import BackupEngine
from . import db

# 初始化数据库
db.init_db()

socketio = SocketIO(app, cors_allowed_origins="*")

engine = BackupEngine()
_scan_cache = {"files": [], "volumes": []}


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
    """打开目标文件夹"""
    data = request.get_json(silent=True) or {}
    path = data.get("path", "").strip()
    if not path:
        return jsonify({"error": "路径不能为空"}), 400
    if not os.path.exists(path):
        return jsonify({"error": "路径不存在"}), 404
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", path])
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
        "version": "1.0.0",
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
        return jsonify({"error": "正在备份中，请等待完成"})

    data = request.get_json() or {}
    mount_point = data.get("mount_point", "")
    event_name = data.get("event_name", "").strip()
    event_names = data.get("event_names") or []
    if not event_names and event_name:
        event_names = [e.strip() for e in event_name.replace("，", ",").split(",") if e.strip()]
    backup_root = data.get("backup_root", "")
    backup_targets = data.get("backup_targets") or []

    if not event_name and not event_names:
        return jsonify({"error": "请输入事件文件夹名"})
    if not event_names and event_name:
        event_names = [e.strip() for e in event_name.replace("，", ",").split(",") if e.strip()]
    if not backup_root and not backup_targets:
        return jsonify({"error": "请选择备份目标位置"})
    if not mount_point:
        vols = list_removable_volumes()
        if vols:
            mount_point = vols[0]["mount_point"]
    if not mount_point or not os.path.isdir(mount_point):
        return jsonify({"error": "未检测到 SD 卡"})

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
                    else:
                        os.remove(fp)
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
        "version": "1.0",
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
    files = db.get_backup_files(backup_id, 500)
    return jsonify({"record": record, "files": files})


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
        if "webhook_url" in data:
            config.webhook_url = data["webhook_url"]
        if "max_speed_mbps" in data:
            config.max_speed_mbps = int(data["max_speed_mbps"])
        if "phash_threshold" in data:
            config.phash_threshold = int(data["phash_threshold"])
        config.save()
        return jsonify({"status": "saved"})
    return jsonify({
        "webhook_url": config.webhook_url,
        "max_speed_mbps": config.max_speed_mbps,
        "phash_threshold": config.phash_threshold,
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
    host = config.web_host

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
║     🖼  Smart Media Backup  v1.0         ║
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
