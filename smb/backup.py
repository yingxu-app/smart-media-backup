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
    scan_sd_card, batch_extract_metadata, get_media_type, get_dest_dir, date_group_key
)
from .verifier import ChecksumVerifier
from .waste_filter import waste_reviewer
try:
    from .windows_preview import windows_preview
except ImportError:
    windows_preview = None
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
            dest_dir = get_dest_dir(backup_root, camera, event_name, f.get("media_type", "photo"),
                                    config.sort_order, f.get("date"), f.get("gps"))
            dest_path = os.path.join(dest_dir, f["filename"])
            if not os.path.exists(dest_path):
                processed += 1
                continue

            # 本机 Pillow 未具备 HEIC/HEIF 解码能力时，跳过可选审片；
            # 备份与校验已经完成，不应为此输出大量无用失败日志。
            if Path(dest_path).suffix.lower() in (".heic", ".heif"):
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
        source_mount: str = "",
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

        source_total_bytes = None
        if source_mount:
            try:
                source_total_bytes = shutil.disk_usage(source_mount).total
            except OSError:
                pass

        report_path = report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "backup_id": backup_id,
            "event_name": event_name,
            "source_mount": source_mount,
            "source_name": Path(source_mount).name if source_mount else "",
            "source_capacity_bytes": source_total_bytes,
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
            "report_path": str(report_path),
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

        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return str(report_path)

    def _generate_windows_previews(
        self,
        files: list[dict],
        backup_root: str,
        backup_id: int,
    ) -> int:
        """为最终文件生成 Windows 预览树"""
        if not self._preview_builder or not getattr(self._preview_builder, "enabled", True):
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
        """拷贝文件到单个目标路径，并写入每个文件的真实结果。"""
        copied = skipped = 0
        copied_bytes = 0

        for f in files:
            if self._cancel_flag.is_set():
                break
            camera = f.get("camera", "Unknown")
            media_type = f.get("media_type", "other")
            dest_dir = get_dest_dir(target, camera, event_name, media_type,
                                    config.sort_order, f.get("date"), f.get("gps"))
            dest_path = os.path.join(dest_dir, f["filename"])
            os.makedirs(dest_dir, exist_ok=True)

            source_hash = f.get("source_hash") or self._verifier.hash_file(f["path"])
            source_mtime = os.path.getmtime(f["path"]) if os.path.exists(f["path"]) else None
            if not source_hash:
                db.update_file_status(
                    backup_id, f["path"], "failed", dest_path,
                    error="无法读取源文件校验值，未执行复制",
                    source_mtime=source_mtime,
                )
                self.progress.current_file = f"❌ {f['filename']}（无法读取校验值）"
                self.progress.notify()
                continue

            # 只有同一原始路径已完成备份才算重复；不同素材即使内容或文件名
            # 相同，也必须分别保留，不能被全局哈希去重吞掉。
            prior_dest = db.get_prior_destination(target, f["path"], source_hash)
            if prior_dest and os.path.isfile(prior_dest) and self._verifier.hash_file(prior_dest) == source_hash:
                skipped += 1
                db.update_file_status(
                    backup_id, f["path"], "skipped", prior_dest,
                    verified=True,
                    error="目标中已存在相同内容，未重复复制",
                    source_hash=source_hash,
                    source_mtime=source_mtime,
                )
                self.progress.current_file = f"[跳过] {f['filename']}"
                self.progress.skipped_files += 1
                self.progress.notify()
                continue

            # 同一文件夹内重名时加序号，避免覆盖另一张原片。
            if os.path.exists(dest_path):
                stem, suffix = os.path.splitext(f["filename"])
                index = 2
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_dir, f"{stem} ({index}){suffix}")
                    index += 1

            ok, error = self._copy_and_verify_with_retry(
                f["path"], dest_path, source_hash, enable_verify
            )
            if ok:
                copied += 1
                copied_bytes += f.get("size", 0)
                db.update_file_status(
                    backup_id, f["path"], "completed", dest_path,
                    verified=enable_verify,
                    source_hash=source_hash,
                    source_mtime=source_mtime,
                )
                self.progress.current_file = f"✅ {f['filename']}"
                self._throttle(f.get("size", 0))
            else:
                db.update_file_status(
                    backup_id, f["path"], "failed", dest_path,
                    error=error or "复制失败",
                    source_hash=source_hash,
                    source_mtime=source_mtime,
                )
                self.progress.current_file = f"❌ {f['filename']}"

            self.progress.bytes_copied += f.get("size", 0)
            self.progress.copied_files += 1 if ok else 0
            self.progress.notify()

        return {"copied": copied, "skipped": skipped, "bytes": copied_bytes}

    def _finish_cancelled_backup(
        self, backup_id: int, event_name: str, backup_root: str, devices: dict,
        total_files: int, copied_files: int, skipped_files: int,
        reviewed_files: int = 0, preview_files: int = 0,
        review_summary: Optional[dict] = None,
        source_mount: str = "",
    ) -> None:
        """把取消任务写成可恢复的明确结果，原卡始终保持不变。"""
        elapsed = max(0.0, time.time() - self.progress.start_time)
        partially_done = copied_files > 0 or skipped_files > 0
        status = "partial" if partially_done else "cancelled"
        remaining = max(total_files - copied_files - skipped_files, 0)
        message = (
            f"用户取消：已复制 {copied_files} 个，已跳过 {skipped_files} 个，"
            f"尚未处理 {remaining} 个。原始素材未被删除，可重新执行继续备份。"
        )
        report_path = self._write_backup_report(
            backup_id=backup_id,
            event_name=event_name,
            backup_root=backup_root,
            devices=devices,
            total_files=total_files,
            copied_files=copied_files,
            skipped_files=skipped_files,
            reviewed_files=reviewed_files,
            preview_files=preview_files,
            # 未处理文件不是复制失败，避免把用户主动取消误报为错误。
            failed_files=0,
            verified_files=copied_files + skipped_files,
            total_size=self.progress.total_bytes,
            elapsed_seconds=elapsed,
            status=status,
            review_summary=review_summary or {},
            source_mount=source_mount,
        )
        db.finish_backup(backup_id, status, message, report_path)
        self.progress.elapsed_seconds = elapsed
        self.progress.copied_files = copied_files
        self.progress.skipped_files = skipped_files
        self.progress.processed_files = copied_files + skipped_files
        self.progress.status = status
        self.progress.error_message = message
        self.progress.can_cleanup = False
        self.progress.notify()

    def run(self, mount_point: str, event_name: str, backup_root: str,
            enable_verify: bool = True, backup_targets: list[str] | None = None,
            event_names: list[str] | None = None,
            event_groups: list[dict] | None = None):
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
        events = [str(g.get("name", "")).strip() for g in (event_groups or []) if str(g.get("name", "")).strip()]
        if not events:
            events = event_names or [event_name]
        total_events = len(events)

        if total_events == 1:
            backup_id = db.create_backup(events[0], backup_root, backup_targets)
        else:
            backup_id = db.create_backup(f"{events[0]}等{total_events}个事件", backup_root, backup_targets)

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
                self._finish_cancelled_backup(
                    backup_id, events[0], backup_root, {}, total, 0, 0,
                    source_mount=mount_point,
                )
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

            # 每个事件只处理它所属日期的文件。旧逻辑会将整张卡重复复制到
            # 每一个事件名，这是严重的数据重复风险，必须在引擎层阻断。
            requested_names = {
                str(g.get("date_key", "")): str(g.get("name", "")).strip()
                for g in (event_groups or []) if str(g.get("name", "")).strip()
            }
            grouped_files: dict[str, list[dict]] = {}
            for file_info in files:
                grouped_files.setdefault(date_group_key(file_info.get("date")), []).append(file_info)
            event_batches = []
            if requested_names:
                for date_key, name in requested_names.items():
                    selected = grouped_files.get(date_key, [])
                    if selected:
                        event_batches.append({"name": name, "files": selected})
            else:
                event_batches = [{"name": events[0], "files": files}]
            if not event_batches:
                raise RuntimeError("没有可用于归档的日期分组")
            events = [batch["name"] for batch in event_batches]
            total_events = len(event_batches)

            # ---- step 4: 逐个事件拷贝 ----
            targets = [backup_root] + (backup_targets or [])
            targets = list(dict.fromkeys(t for t in targets if t.strip()))

            # 一次性计算源文件哈希
            for f in files:
                f["source_hash"] = self._verifier.hash_file(f["path"])

            all_copied = all_skipped = 0; all_bytes = 0
            reviewed_count = previewed_count = 0
            label_counts = {}

            for ei, batch in enumerate(event_batches):
                ename = batch["name"]
                group_files = batch["files"]
                cur_id = db.create_backup(ename, backup_root, backup_targets) if total_events > 1 else backup_id
                if total_events > 1:
                    db.add_files(cur_id, group_files)
                label = f"[{ei+1}/{total_events}] {ename}"
                self.progress.status = "copying"
                self.progress.current_file = f"事件: {label}"
                self.progress.notify()

                for target in targets:
                    if self._cancel_flag.is_set():
                        break
                    result = self._copy_to_target(
                        group_files, target, ename, cur_id, enable_verify
                    )
                    all_copied += result["copied"]
                    all_skipped += result["skipped"]
                    all_bytes += result["bytes"]

                    if self._cancel_flag.is_set():
                        self._finish_cancelled_backup(
                            cur_id, ename, backup_root, devices, total,
                            all_copied, all_skipped, reviewed_count,
                            previewed_count, label_counts, mount_point,
                        )
                        return

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
                    group_files, backup_root, ename, cur_id
                )
                if self._cancel_flag.is_set():
                    self._finish_cancelled_backup(
                        cur_id, ename, backup_root, devices, total,
                        all_copied, all_skipped, reviewed_count,
                        previewed_count, label_counts, mount_point,
                    )
                    return
                # Windows预览（仅第一个事件）
                if ei == 0:
                    previewed_count = self._generate_windows_previews(group_files, backup_root, cur_id)
                if self._cancel_flag.is_set():
                    self._finish_cancelled_backup(
                        cur_id, ename, backup_root, devices, total,
                        all_copied, all_skipped, reviewed_count,
                        previewed_count, label_counts, mount_point,
                    )
                    return

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
                for ename in events:
                    for target in targets:
                        for cam in devices:
                            cam_dir = os.path.join(target, cam, ename)
                            if os.path.exists(cam_dir):
                                all_files = []
                                for root, _, fnames in os.walk(cam_dir):
                                    for fn in fnames:
                                        if fn != "checksums.json":
                                            all_files.append(os.path.join(root, fn))
                                if all_files:
                                    self._verifier.generate_manifest(all_files, cam_dir)

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
                # 跳过的文件已逐个与目标内容一致，也属于已校验素材。
                verified_files=all_copied + all_skipped,
                total_size=self.progress.total_bytes,
                elapsed_seconds=elapsed,
                status="completed",
                review_summary=label_counts,
                source_mount=mount_point,
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
        try:
            from .baidu import baidu
        except Exception as e:
            # 云端同步是可选功能，依赖或凭证缺失绝不能影响本地备份结果。
            print(f"[百度] 云端同步未启用：{e}")
            return
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
