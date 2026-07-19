"""备份引擎 — 扫描 → 整理 → 拷贝 → 校验"""
import os
import time
import shutil
import threading
import json
import re
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from .config import config
from .organizer import (
    scan_sd_card, batch_extract_metadata, get_media_type, get_dest_dir
)
from .verifier import ChecksumVerifier
from .waste_filter import waste_reviewer
from .windows_preview import windows_preview
from . import db


class BackupProgress:
    """备份进度追踪器，通过回调通知前端"""

    def __init__(self):
        self.total_files = 0
        self.copied_files = 0
        self.skipped_files = 0
        self.reviewed_files = 0
        self.processed_files = 0
        self.current_file = ""
        self.current_speed = 0.0      # MB/s
        self.bytes_copied = 0
        self.total_bytes = 0
        self.elapsed_seconds = 0.0
        self.status = "idle"           # idle | scanning | metadata | copying | reviewing | previewing | verifying | done | error
        self.error_message = ""
        self.start_time = 0.0
        self.detected_devices: list[dict] = []
        self.phase_progress = 0.0      # 0-100
        self.current_device = ""
        self.current_media_type = ""
        self.preview_files = 0
        self.can_cleanup = False       # 备份完成可清理SD卡
        self.mount_point = ""          # SD卡挂载点

        self._callbacks: list[Callable] = []

    def to_dict(self):
        return {
            "total_files": self.total_files,
            "copied_files": self.copied_files,
            "skipped_files": self.skipped_files,
            "reviewed_files": self.reviewed_files,
            "processed_files": self.processed_files,
            "preview_files": self.preview_files,
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
            "can_cleanup": self.can_cleanup,
            "mount_point": self.mount_point,
        }

    def notify(self):
        data = self.to_dict()
        for cb in self._callbacks:
            try:
                cb(data)
            except Exception:
                pass

    def on_update(self, cb: Callable):
        self._callbacks.append(cb)


class BackupEngine:
    """备份引擎 — 扫描→整理→拷贝→校验 全流程"""

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 0.6

    def __init__(self):
        self.progress = BackupProgress()
        self._cancel_flag = threading.Event()
        self._verifier = ChecksumVerifier()
        self._preview_builder = windows_preview
        self._speed_bucket: list[tuple[float, int]] = []  # (time, bytes)

    def _throttle(self, bytes_copied: int):
        """根据 max_speed_mbps 限速"""
        limit = config.max_speed_mbps
        if limit <= 0:
            return
        now = time.time()
        self._speed_bucket.append((now, bytes_copied))
        cutoff = now - 1.0
        self._speed_bucket = [(t, b) for t, b in self._speed_bucket if t > cutoff]
        total = sum(b for _, b in self._speed_bucket)
        max_bytes = limit * 1024 * 1024
        if total > max_bytes:
            sleep_for = (total - max_bytes) / (limit * 1024 * 1024)
            time.sleep(min(sleep_for, 0.5))

    def cancel(self):
        self._cancel_flag.set()

    def _sleep_with_cancel(self, seconds: float):
        """支持取消的短暂等待"""
        end = time.time() + seconds
        while time.time() < end:
            if self._cancel_flag.is_set():
                return
            time.sleep(min(0.1, end - time.time()))

    def _copy_and_verify_with_retry(
        self,
        src_path: str,
        dest_path: str,
        source_hash: str,
        enable_verify: bool,
    ) -> tuple[bool, str]:
        """
        带重试的拷贝 + 校验。
        返回: (是否成功, 错误信息)
        """
        last_error = ""
        for attempt in range(1, self.MAX_RETRIES + 1):
            if self._cancel_flag.is_set():
                return False, "cancelled"

            try:
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass

                shutil.copy2(src_path, dest_path)

                if enable_verify:
                    ok, info = self._verifier.verify_single(
                        src_path, dest_path, src_hash=source_hash
                    )
                    if not ok:
                        raise IOError(f"校验失败: {info}")

                return True, ""

            except Exception as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES and not self._cancel_flag.is_set():
                    self.progress.current_file = (
                        f"[重试 {attempt}/{self.MAX_RETRIES}] "
                        f"{os.path.basename(src_path)}"
                    )
                    self.progress.notify()
                    self._sleep_with_cancel(self.RETRY_DELAY_SECONDS * attempt)

        return False, last_error

    def _review_and_quarantine(
        self,
        files: list[dict],
        backup_root: str,
        event_name: str,
        backup_id: int,
    ) -> tuple[int, dict[str, int]]:
        """对已备份的照片做废片筛选，并移动到待确认目录"""
        reviewed_count = 0
        label_counts: dict[str, int] = {}

        photo_files = [
            f for f in files
            if f.get("media_type") in ("photo", "raw")
        ]
        total = len(photo_files)
        if total == 0:
            return 0, label_counts

        self.progress.status = "reviewing"
        self.progress.current_file = "AI 审片中..."
        self.progress.phase_progress = 0
        self.progress.notify()

        processed = 0
        for f in photo_files:
            if self._cancel_flag.is_set():
                break

            camera = f.get("camera", "Unknown")
            dest_dir = get_dest_dir(backup_root, camera, event_name, f.get("media_type", "photo"))
            dest_path = os.path.join(dest_dir, f["filename"])
            if not os.path.exists(dest_path):
                processed += 1
                continue

            result = waste_reviewer.review(dest_path)
            label = result.get("label", "正常")
            if label in waste_reviewer.WASTE_LABELS:
                try:
                    new_path = waste_reviewer.move_to_review_folder(
                        dest_path,
                        os.path.join(backup_root, camera, event_name),
                        label,
                        f.get("media_type", "photo"),
                    )
                    db.update_file_status(
                        backup_id,
                        f["path"],
                        "reviewed",
                        new_path,
                        verified=True,
                        error=label,
                        source_hash=f.get("source_hash", ""),
                        source_mtime=os.path.getmtime(f["path"]) if os.path.exists(f["path"]) else None,
                    )
                    f["dest_path"] = new_path
                    reviewed_count += 1
                    label_counts[label] = label_counts.get(label, 0) + 1
                    self.progress.reviewed_files = reviewed_count
                except Exception as e:
                    db.update_file_status(
                        backup_id,
                        f["path"],
                        "failed",
                        dest_path,
                        verified=True,
                        error=f"审片移动失败: {e}",
                        source_hash=f.get("source_hash", ""),
                        source_mtime=os.path.getmtime(f["path"]) if os.path.exists(f["path"]) else None,
                    )

            processed += 1
            self.progress.current_file = f"审片: {f['filename']}"
            self.progress.reviewed_files = reviewed_count
            self.progress.phase_progress = (processed / total) * 100 if total else 0
            self.progress.notify()

        return reviewed_count, label_counts

    def _safe_name(self, value: str) -> str:
        """生成适合文件名的安全字符串"""
        cleaned = re.sub(r'[<>:"/\\|?*\s]+', "_", value or "").strip("_")
        return cleaned or "event"

    def _write_backup_report(
        self,
        backup_id: int,
        event_name: str,
        backup_root: str,
        devices: dict,
        total_files: int,
        copied_files: int,
        skipped_files: int,
        reviewed_files: int,
        preview_files: int,
        failed_files: int,
        verified_files: int,
        total_size: int,
        elapsed_seconds: float,
        status: str,
        review_summary: dict,
    ) -> str:
        """写出 JSON 格式的备份报告"""
        report_dir = Path(backup_root) / "_reports" / self._safe_name(event_name)
        report_dir.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now().isoformat()
        try:
            record = db.get_backup(backup_id)
            if record and record.get("started_at"):
                started_at = record["started_at"]
        except Exception:
            pass

        payload = {
            "backup_id": backup_id,
            "event_name": event_name,
            "backup_root": backup_root,
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(),
            "status": status,
            "total_files": total_files,
            "copied_files": copied_files,
            "skipped_files": skipped_files,
            "reviewed_files": reviewed_files,
            "preview_files": preview_files,
            "failed_files": failed_files,
            "verified_files": verified_files,
            "total_size": total_size,
            "elapsed_seconds": round(elapsed_seconds, 1),
            "devices": devices,
            "review_summary": review_summary,
        }

        try:
            samples = db.get_backup_files(backup_id, total_files + 20)
            payload["files"] = [
                {
                    "source_path": f.get("source_path", ""),
                    "dest_path": f.get("dest_path", ""),
                    "status": f.get("status", ""),
                    "camera": f.get("camera", ""),
                    "media_type": f.get("media_type", ""),
                    "verified": bool(f.get("verified", 0)),
                    "error": f.get("error", ""),
                }
                for f in samples
            ]
        except Exception:
            payload["files"] = []

        report_path = report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return str(report_path)

    def _generate_windows_previews(
        self,
        files: list[dict],
        backup_root: str,
        backup_id: int,
    ) -> int:
        """为最终文件生成 Windows 预览树"""
        if not getattr(self._preview_builder, "enabled", True):
            return 0

        preview_candidates = [
            f for f in files
            if f.get("media_type") in ("photo", "raw", "video")
            and f.get("dest_path")
        ]
        total = len(preview_candidates)
        if total == 0:
            return 0

        self.progress.status = "previewing"
        self.progress.current_file = "生成 Windows 预览中..."
        self.progress.phase_progress = 0
        self.progress.notify()

        previewed_count = 0
        processed = 0
        for f in preview_candidates:
            if self._cancel_flag.is_set():
                break

            final_path = f.get("dest_path", "")
            if not final_path or not os.path.exists(final_path):
                processed += 1
                continue

            try:
                preview_path = self._preview_builder.build_preview_for_path(
                    final_path,
                    backup_root,
                    f.get("media_type", "photo"),
                )
                if preview_path:
                    previewed_count += 1
                    db.update_file_preview(backup_id, f["path"], preview_path)
            except Exception as e:
                print(f"[SMB] 生成 Windows 预览失败: {e}")

            processed += 1
            self.progress.preview_files = previewed_count
            self.progress.current_file = f"预览: {f['filename']}"
            self.progress.phase_progress = (processed / total) * 100 if total else 0
            self.progress.notify()

        return previewed_count

    def _copy_to_target(
        self, files: list[dict], target: str, event_name: str,
        backup_id: int, enable_verify: bool,
    ) -> dict:
        """拷贝文件到单个目标路径，返回 {copied, skipped, bytes, errors}"""
        known_hashes = db.get_known_hashes(target)
        hashes: set[str] = set(known_hashes)
        copied = skipped = 0
        copied_bytes = 0

        for f in files:
            if self._cancel_flag.is_set():
                break
            camera = f.get("camera", "Unknown")
            media_type = f.get("media_type", "other")
            dest_dir = get_dest_dir(target, camera, event_name, media_type)
            dest_path = os.path.join(dest_dir, f["filename"])
            os.makedirs(dest_dir, exist_ok=True)

            source_hash = f.get("source_hash") or self._verifier.hash_file(f["path"])
            if not source_hash or source_hash in hashes:
                skipped += 1
                self.progress.current_file = f"[跳过] {f['filename']}"
                self.progress.notify()
                continue

            hashes.add(source_hash)
            ok, _ = self._copy_and_verify_with_retry(
                f["path"], dest_path, source_hash, enable_verify
            )
            if ok:
                copied += 1
                copied_bytes += f.get("size", 0)
                self.progress.current_file = f"✅ {f['filename']}"
                self._throttle(f.get("size", 0))
            else:
                self.progress.current_file = f"❌ {f['filename']}"

            self.progress.bytes_copied += f.get("size", 0)
            self.progress.copied_files = copied
            self.progress.skipped_files += skipped
            self.progress.notify()

        return {"copied": copied, "skipped": skipped, "bytes": copied_bytes}

    def run(self, mount_point: str, event_name: str, backup_root: str,
            enable_verify: bool = True, backup_targets: list[str] | None = None,
            event_names: list[str] | None = None):
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

        # ---- step 1: 解析事件名 ----
        events = event_names or [event_name]
        total_events = len(events)

        if total_events == 1:
            backup_id = db.create_backup(events[0], backup_root, backup_targets)
        else:
            backup_id = db.create_backup(f"{events[0]}等{total_events}个事件", backup_root, backup_targets)
            for ename in events:
                db.create_backup(ename, backup_root, backup_targets)

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
            known_hashes = db.get_known_hashes(backup_root)
            current_hashes: set[str] = set(known_hashes)

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

            # ---- step 4: 逐个事件拷贝 ----
            targets = [backup_root] + (backup_targets or [])
            targets = list(dict.fromkeys(t for t in targets if t.strip()))

            # 一次性计算源文件哈希
            for f in files:
                f["source_hash"] = self._verifier.hash_file(f["path"])

            all_copied = all_skipped = 0; all_bytes = 0

            for ei, ename in enumerate(events):
                cur_id = db.create_backup(ename, backup_root, backup_targets) if total_events > 1 else backup_id
                label = f"[{ei+1}/{total_events}] {ename}"
                self.progress.status = "copying"
                self.progress.current_file = f"事件: {label}"
                self.progress.notify()

                for target in targets:
                    if self._cancel_flag.is_set():
                        break
                    result = self._copy_to_target(
                        files, target, ename, cur_id, enable_verify
                    )
                    all_copied += result["copied"]
                    all_skipped += result["skipped"]
                    all_bytes += result["bytes"]

                    if enable_verify:
                        for cam in devices:
                            cam_dir = os.path.join(target, cam, ename)
                            if os.path.exists(cam_dir):
                                flist = []
                                for root, _, fnames in os.walk(cam_dir):
                                    for fn in fnames:
                                        if fn != "checksums.json":
                                            flist.append(os.path.join(root, fn))
                                if flist:
                                    self._verifier.generate_manifest(flist, cam_dir)

                # 废片审片
                reviewed_count, label_counts = self._review_and_quarantine(
                    files, backup_root, ename, cur_id
                )
                # Windows预览（仅第一个事件）
                if ei == 0:
                    previewed_count = self._generate_windows_previews(files, backup_root, cur_id)

                db.finish_backup(cur_id, "completed")

            self.progress.copied_files = all_copied
            self.progress.skipped_files = all_skipped
            self.progress.bytes_copied = all_bytes
            self.progress.notify()

            # 生成校验清单（所有事件）
            if enable_verify:
                self.progress.status = "verifying"
                self.progress.current_file = "生成校验清单..."
                self.progress.phase_progress = 0
                self.progress.notify()

                # 按设备+事件目录生成
                for ei, ename in enumerate(events):
                    for cam in devices:
                        cam_dir = os.path.join(backup_root, cam, ename)
                        if os.path.exists(cam_dir):
                            all_files = []
                            for root, _, fnames in os.walk(cam_dir):
                                for fn in fnames:
                                    if fn != "checksums.json":
                                        all_files.append(os.path.join(root, fn))
                            if all_files:
                                self._verifier.generate_manifest(all_files, cam_dir)
                    if ei == 0:
                        break

            # ---- step 8: 完成 ----
            elapsed = time.time() - self.progress.start_time
            self.progress.elapsed_seconds = elapsed
            self.progress.copied_files = all_copied
            self.progress.skipped_files = all_skipped
            self.progress.reviewed_files = reviewed_count if total_events > 0 else 0
            self.progress.preview_files = previewed_count if total_events > 0 else 0
            self.progress.processed_files = all_copied + all_skipped
            self.progress.bytes_copied = all_bytes
            self.progress.phase_progress = 100

            failed_count = max(total - all_copied - all_skipped, 0)
            report_path = self._write_backup_report(
                backup_id=backup_id,
                event_name=" + ".join(events) if total_events > 1 else events[0],
                backup_root=backup_root,
                devices=devices,
                total_files=total,
                copied_files=all_copied,
                skipped_files=all_skipped,
                reviewed_files=reviewed_count,
                preview_files=previewed_count,
                failed_files=failed_count,
                verified_files=all_copied,
                total_size=self.progress.total_bytes,
                elapsed_seconds=elapsed,
                status="completed",
                review_summary=label_counts,
            )

            db.finish_backup(backup_id, "completed", report_path=report_path)
            self.progress.status = "done"
            self.progress.can_cleanup = True
            self.progress.mount_point = mount_point
            self.progress.notify()

            # 通知推送
            if config.webhook_url:
                self._send_webhook(total, all_copied, all_skipped, events)

            # Lightroom 目录生成
            try:
                from .lightroom import generate_lr_catalog
                generate_lr_catalog(backup_root, events[0], self.progress.detected_devices,
                                    total, datetime.now().isoformat())
            except Exception as e:
                print(f"[SMB] Lightroom 目录生成失败: {e}")

            # 后台触发百度网盘上传
            self._trigger_baidu_upload(backup_root, event_name)

        except Exception as e:
            db.finish_backup(backup_id, "error", str(e))
            self.progress.status = "error"
            self.progress.error_message = str(e)
            self.progress.notify()
            raise

    def _send_webhook(self, total, copied, skipped, events):
        """备份完成后推送通知"""
        import urllib.request
        try:
            payload = json.dumps({
                "event": "backup_complete",
                "total_files": total,
                "copied": copied,
                "skipped": skipped,
                "events": events,
                "time": datetime.now().isoformat(),
            }).encode()
            urllib.request.urlopen(config.webhook_url, data=payload, timeout=10)
        except Exception as e:
            print(f"[SMB] Webhook 发送失败: {e}")

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
