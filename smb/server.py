"""Flask + SocketIO Web 服务端 — 仪表盘 + 备份控制"""
import os
import sys
import json
import threading
import webbrowser
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
from .detector import list_removable_volumes, list_all_volumes
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

    return jsonify({
        "devices": device_list,
        "files": file_list,
        "total_files": len(files),
        "total_size": sum(f.get("size", 0) for f in files),
        "mount_point": mount_point,
    })


@app.route("/api/start_backup", methods=["POST"])
def api_start_backup():
    """开始备份"""
    if engine.progress.status in ("copying", "verifying"):
        return jsonify({"error": "正在备份中，请等待完成"})

    data = request.get_json() or {}
    mount_point = data.get("mount_point", "")
    event_name = data.get("event_name", "").strip()
    backup_root = data.get("backup_root", "")

    if not event_name:
        return jsonify({"error": "请输入事件文件夹名"})
    if not backup_root:
        return jsonify({"error": "请选择备份目标位置"})
    if not mount_point:
        vols = list_removable_volumes()
        if vols:
            mount_point = vols[0]["mount_point"]
    if not mount_point or not os.path.isdir(mount_point):
        return jsonify({"error": "未检测到 SD 卡"})

    # 保存配置
    config.last_backup_root = backup_root
    config.save()

    # 在新线程运行备份
    def _run():
        try:
            engine.run(mount_point, event_name, backup_root,
                       enable_verify=config.verify_method == "sha256")
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


@app.route("/api/history")
def api_history():
    """获取历史记录"""
    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)
    records = db.get_backups(limit, offset)
    return jsonify(records)


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
