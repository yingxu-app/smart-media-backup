"""备份引擎 — 扫描 → 整理 → 拷贝 → 校验"""
import os
import time
import shutil
import threading
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from .config import config
from .organizer import (
    scan_sd_card, batch_extract_metadata, get_media_type, get_dest_dir
)
from .verifier import ChecksumVerifier
from . import db


class BackupProgress:
    """备份进度追踪器，通过回调通知前端"""

    def __init__(self):
        self.total_files = 0
        self.copied_files = 0
        self.current_file = ""
        self.current_speed = 0.0      # MB/s
        self.bytes_copied = 0
        self.total_bytes = 0
        self.elapsed_seconds = 0.0
        self.status = "idle"           # idle | scanning | metadata | copying | verifying | done | error
        self.error_message = ""
        self.start_time = 0.0
        self.detected_devices: list[dict] = []
        self.phase_progress = 0.0      # 0-100
        self.current_device = ""
        self.current_media_type = ""

        self._callbacks: list[Callable] = []

    def to_dict(self):
        return {
            "total_files": self.total_files,
            "copied_files": self.copied_files,
            "current_file": self.current_file,
            "current_speed": round(self.current_speed, 1),
            "bytes_copied": self.bytes_copied,
            "total_bytes": self.total_bytes,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "status": self.status,
            "error_message": self.error_message,
            "phase_progress": round(self.phase_progress, 1),
            "current_device": self.current_device,
            "current_media_type": self.current_media_type,
            "detected_devices": self.detected_devices,
        }

    def notify(self):
        data = self.to_dict()
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception:
                pass

    def on_update(self, cb: Callable):
        self._callbacks.append(callable)


class BackupEngine:
    """备份引擎 — 扫描→整理→拷贝→校验 全流程"""

    def __init__(self):
        self.progress = BackupProgress()
        self._cancel_flag = threading.Event()
        self._verifier = ChecksumVerifier()

    def cancel(self):
        self._cancel_flag.set()

    def run(self, mount_point: str, event_name: str, backup_root: str,
            enable_verify: bool = True):
        """
        执行一次完整备份流程。
        mount_point: SD 卡挂载点
        event_name: 用户输入的事件名
        backup_root: 目标备份根目录
        """
        self._cancel_flag.clear()
        self.progress.status = "scanning"
        self.progress.start_time = time.time()
        self.progress.notify()

        # ---- step 1: 备份对象创建 ----
        backup_id = db.create_backup(event_name, backup_root)

        try:
            # ---- step 2: 扫描 SD 卡 ----
            self.progress.phase_progress = 0
            self.progress.status = "scanning"
            self.progress.current_file = "扫描 SD 卡中..."
            self.progress.notify()

            raw_files = scan_sd_card(mount_point)
            if not raw_files:
                raise RuntimeError("未在 SD 卡上找到照片或视频文件")

            total = len(raw_files)
            self.progress.total_files = total
            self.progress.total_bytes = sum(f["size"] for f in raw_files)

            # 写入数据库
            db.add_files(backup_id, raw_files)

            # ---- step 3: 提取元数据 ----
            self.progress.status = "metadata"
            self.progress.current_file = "读取 EXIF 元数据..."
            self.progress.notify()

            def on_meta_progress(curr, total, fname):
                if self._cancel_flag.is_set():
                    return
                self.progress.phase_progress = (curr / total) * 100
                self.progress.current_file = f"读取: {fname}"
                self.progress.notify()

            files = batch_extract_metadata(raw_files, on_meta_progress)

            if self._cancel_flag.is_set():
                db.finish_backup(backup_id, "cancelled")
                self.progress.status = "cancelled"
                self.progress.notify()
                return

            # 统计设备
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

            self.progress.detected_devices = [
                {"name": k, **v} for k, v in devices.items()
            ]
            self.progress.notify()

            # ---- step 4: 拷贝文件 ----
            self.progress.status = "copying"
            self.progress.copied_files = 0
            self.progress.bytes_copied = 0
            self.progress.notify()

            copied_bytes = 0
            verified_ok = 0

            for i, f in enumerate(files):
                if self._cancel_flag.is_set():
                    db.finish_backup(backup_id, "cancelled")
                    self.progress.status = "cancelled"
                    self.progress.notify()
                    return

                camera = f.get("camera", "Unknown")
                media_type = f.get("media_type", "other")
                self.progress.current_device = camera
                self.progress.current_media_type = "照片" if media_type in ("photo", "raw") else "视频"

                # 目标路径
                dest_dir = get_dest_dir(backup_root, camera, event_name, media_type)
                dest_path = os.path.join(dest_dir, f["filename"])

                os.makedirs(dest_dir, exist_ok=True)

                # 进度
                self.progress.current_file = f["filename"]
                self.progress.copied_files = i
                self.progress.bytes_copied = copied_bytes
                self.progress.phase_progress = (i / total) * 100

                # 速度计算
                elapsed = time.time() - self.progress.start_time
                self.progress.elapsed_seconds = elapsed
                if elapsed > 0:
                    self.progress.current_speed = (copied_bytes / elapsed) / (1024 * 1024)

                self.progress.notify()

                # 拷贝
                try:
                    shutil.copy2(f["path"], dest_path)
                    copied_bytes += f.get("size", 0)

                    # 校验
                    if enable_verify:
                        ok, info = self._verifier.verify_single(f["path"], dest_path)
                        if ok:
                            verified_ok += 1
                            db.update_file_status(backup_id, f["path"], "completed", dest_path, verified=True)
                        else:
                            db.update_file_status(backup_id, f["path"], "failed", dest_path, verified=False, error=info)
                    else:
                        db.update_file_status(backup_id, f["path"], "completed", dest_path)

                except (OSError, shutil.Error) as e:
                    db.update_file_status(backup_id, f["path"], "failed", error=str(e))
                    continue

            # ---- step 5: 生成校验清单 ----
            if enable_verify:
                self.progress.status = "verifying"
                self.progress.current_file = "生成校验清单..."
                self.progress.phase_progress = 0
                self.progress.notify()

                # 按设备目录生成
                for cam in devices:
                    cam_dir = os.path.join(backup_root, cam, event_name)
                    if os.path.exists(cam_dir):
                        all_files = []
                        for root, _, fnames in os.walk(cam_dir):
                            for fn in fnames:
                                if fn != "checksums.json":
                                    all_files.append(os.path.join(root, fn))
                        if all_files:
                            self._verifier.generate_manifest(all_files, cam_dir)

            # ---- step 6: 完成 ----
            elapsed = time.time() - self.progress.start_time
            self.progress.elapsed_seconds = elapsed
            self.progress.copied_files = total
            self.progress.bytes_copied = copied_bytes
            self.progress.phase_progress = 100

            db.finish_backup(backup_id, "completed")
            self.progress.status = "done"
            self.progress.notify()

            # 后台触发百度网盘上传
            self._trigger_baidu_upload(backup_root, event_name)

        except Exception as e:
            db.finish_backup(backup_id, "error", str(e))
            self.progress.status = "error"
            self.progress.error_message = str(e)
            self.progress.notify()
            raise

    def _trigger_baidu_upload(self, backup_root: str, event_name: str):
        """后台线程触发百度网盘上传"""
        from .baidu import baidu
        if not baidu.is_configured() or not baidu.is_authorized():
            return  # 用户没配置百度网盘

        def _upload():
            try:
                print(f"[百度] 开始上传 {event_name} ...")
                baidu.mkdir(f"/{event_name}")
                for root, dirs, files in os.walk(backup_root):
                    for fname in files:
                        if fname == "checksums.json":
                            continue
                        local = os.path.join(root, fname)
                        rel_path = os.path.relpath(root, backup_root)
                        remote_dir = f"/{event_name}/{rel_path.replace(os.sep, '/')}"
                        baidu.mkdir(remote_dir)
                        ok = baidu.upload_file(local, remote_dir)
                        print(f"[百度] {'✅' if ok else '❌'} {fname} → {remote_dir}")
                print(f"[百度] 上传完成: {event_name}")
            except Exception as e:
                print(f"[百度] 上传失败: {e}")

        t = threading.Thread(target=_upload, daemon=True)
        t.start()
