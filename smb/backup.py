"""备份引擎 — 扫描 → 整理 → 拷贝 → 校验"""
import os
import time
import shutil
import threading
import json
import csv
import tempfile
import re
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

from .config import config, CONFIG_DIR
from .organizer import (
    scan_sd_card, batch_extract_metadata, get_media_type, get_backup_media_dir,
    date_group_key, build_backup_folder_name
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
        self._pause_flag = threading.Event()
        self._verifier = ChecksumVerifier()
        self._preview_builder = windows_preview
        self._speed_bucket: list[tuple[float, int]] = []  # (time, bytes)

    def pause(self):
        """在当前文件完成后暂停；不终止任务、不触碰原卡。"""
        self._pause_flag.set()
        self.progress.status = "paused"
        self.progress.current_file = "任务已暂停；已完成文件保持安全"
        self.progress.notify()

    def resume(self):
        """继续一个已暂停的任务。"""
        self._pause_flag.clear()
        self.progress.status = "copying"
        self.progress.current_file = "正在继续备份..."
        self.progress.notify()

    def _wait_if_paused(self):
        while self._pause_flag.is_set() and not self._cancel_flag.is_set():
            time.sleep(0.1)

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

            # 复制阶段已经把最终路径写回文件对象；不重新拼目录，避免新目录
            # 结构下审片找错文件，也确保多设备素材统一进入一个待确认废片目录。
            dest_path = f.get("dest_path", "")
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
                        backup_root,
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
        """写出 JSON、CSV 和 Markdown 三种可读备份报告。"""
        # 报告属于影序的本地历史资料，不应该混进摄影师选择的素材盘根目录。
        # 不能用多日期批次的拼接名称作为目录名：一张长期未导入的卡可能跨越
        # 数十天，名称会超过 APFS 的 255 字符限制。备份编号稳定且可追溯。
        report_dir = CONFIG_DIR / "reports" / f"backup-{backup_id}"
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

        target_results = db.get_target_results(backup_id)
        payload["target_results"] = target_results
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        csv_path = report_path.with_suffix(".csv")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "source_path", "dest_path", "status", "camera", "media_type",
                "verified", "error",
            ])
            writer.writeheader()
            writer.writerows(payload["files"])

        md_path = report_path.with_suffix(".md")
        target_lines = "\n".join(
            f"- `{item['target_path']}`：{item['status']}，复制 {item['copied_files']}，"
            f"跳过 {item['skipped_files']}，失败 {item['failed_files']}"
            for item in target_results
        ) or f"- `{backup_root}`"
        md_path.write_text(
            f"# 影序备份报告 #{backup_id}\n\n"
            f"- 状态：**{status}**\n- 项目：{event_name}\n"
            f"- 源卡：`{source_mount}`\n- 开始：{started_at}\n"
            f"- 完成：{payload['finished_at']}\n- 文件总数：{total_files}\n"
            f"- 成功复制：{copied_files}\n- 跳过重复：{skipped_files}\n"
            f"- 校验通过：{verified_files}\n- 失败：{failed_files}\n\n"
            f"## 目标结果\n\n{target_lines}\n\n"
            "原始素材不会因备份失败、取消或校验失败而被删除。\n",
            encoding="utf-8",
        )
        payload["csv_report_path"] = str(csv_path)
        payload["markdown_report_path"] = str(md_path)
        report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(report_path)

    def _validate_target(self, source_mount: str, target: str, required_bytes: int):
        """在复制前验证目标目录、权限和剩余空间，并给出可理解错误。"""
        source = Path(source_mount).resolve()
        destination = Path(target).expanduser().resolve()
        if destination == source or source in destination.parents:
            raise RuntimeError("备份位置不能位于原始存储卡内部，请选择电脑或其他磁盘")
        if destination.exists() and not destination.is_dir():
            raise RuntimeError(f"备份位置不是文件夹：{destination}")
        try:
            destination.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix=".yingxu-write-test-", dir=destination, delete=True):
                pass
        except (OSError, PermissionError) as exc:
            raise RuntimeError(f"没有权限写入备份位置：{destination}（{exc}）") from exc
        try:
            free = shutil.disk_usage(destination).free
        except OSError as exc:
            raise RuntimeError(f"备份磁盘当前不可用：{destination}（{exc}）") from exc
        if free < required_bytes:
            need_gb = required_bytes / (1024 ** 3)
            free_gb = free / (1024 ** 3)
            raise RuntimeError(f"备份磁盘空间不足：需要 {need_gb:.2f} GB，可用 {free_gb:.2f} GB")

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
        backup_id: int, enable_verify: bool, record_file_status: bool = True,
    ) -> dict:
        """拷贝文件到单个目标路径，并写入每个文件的真实结果。"""
        copied = skipped = failed = 0
        copied_bytes = 0

        for f in files:
            self._wait_if_paused()
            if self._cancel_flag.is_set():
                break
            media_type = f.get("media_type", "other")
            folder_name = f.get("backup_folder_name") or event_name
            dest_dir = get_backup_media_dir(
                target,
                folder_name,
                media_type,
                f.get("backup_media_folder_name", ""),
            )
            dest_path = os.path.join(dest_dir, f["filename"])
            os.makedirs(dest_dir, exist_ok=True)

            source_hash = f.get("source_hash") or self._verifier.hash_file(f["path"])
            source_mtime = os.path.getmtime(f["path"]) if os.path.exists(f["path"]) else None
            if not source_hash:
                failed += 1
                if record_file_status:
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
            exact_dest_matches = (
                not record_file_status
                and
                os.path.isfile(dest_path)
                and self._verifier.hash_file(dest_path) == source_hash
            )
            if exact_dest_matches or (
                prior_dest and os.path.isfile(prior_dest)
                and self._verifier.hash_file(prior_dest) == source_hash
            ):
                skipped += 1
                matched_dest = dest_path if exact_dest_matches else prior_dest
                f["dest_path"] = matched_dest  # 回写最终路径，供审片/预览使用
                if record_file_status:
                    db.update_file_status(
                        backup_id, f["path"], "skipped", matched_dest,
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
                f["dest_path"] = dest_path  # 回写最终路径，供审片/预览使用
                if record_file_status:
                    db.update_file_status(
                        backup_id, f["path"], "completed", dest_path,
                        verified=enable_verify,
                        source_hash=source_hash,
                        source_mtime=source_mtime,
                    )
                self.progress.current_file = f"✅ {f['filename']}"
                self._throttle(f.get("size", 0))
            else:
                failed += 1
                if record_file_status:
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

        return {"copied": copied, "skipped": skipped, "failed": failed, "bytes": copied_bytes}

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
            event_groups: list[dict] | None = None,
            naming_parts: list[dict] | None = None):
        """
        执行一次完整备份流程。
        mount_point: SD 卡挂载点
        event_name: 用户输入的事件名
        backup_root: 目标备份根目录
        """
        self._cancel_flag.clear()
        self._pause_flag.clear()
        self.progress.status = "scanning"
        self.progress.start_time = time.time()
        self.progress.notify()

        # ---- step 1: 解析命名规则 ----
        # 每天都是一个独立的主备份文件夹。事件名只是可选的人工补充，
        # 即使用户不填事件，也能按日期安全归档。
        manual_event = (event_name or "").strip()
        events = event_names or ([manual_event] if manual_event else ["按日期归档"])
        backup_id = db.create_backup(manual_event or "按日期归档", backup_root, backup_targets)

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

            # 以真实拍摄日期拆分，而不是把同一张卡整批塞进一个月份目录。
            # event_groups 仍兼容旧界面：若它带有人工名称，作为对应日期的事件补充。
            requested_names = {
                str(g.get("date_key", "")): str(g.get("name", "")).strip()
                for g in (event_groups or []) if str(g.get("name", "")).strip()
            }
            requested_folders = {
                str(g.get("date_key", "")): str(g.get("folder_name", "")).strip()
                for g in (event_groups or []) if str(g.get("folder_name", "")).strip()
            }
            requested_media_folders = {
                str(g.get("date_key", "")): {
                    "photo": str(g.get("photo_folder_name", "")).strip(),
                    "video": str(g.get("video_folder_name", "")).strip(),
                }
                for g in (event_groups or [])
            }
            grouped_files: dict[str, list[dict]] = {}
            for file_info in files:
                grouped_files.setdefault(date_group_key(file_info.get("date")), []).append(file_info)
            event_batches = []
            for date_key, selected in sorted(grouped_files.items()):
                event_value = requested_names.get(date_key, manual_event)
                # 即使旧版调用没有传 naming_parts，也保留“时间/事件/地点/设备/类型”
                # 的默认语义，避免人工填写的事件名称在新目录中丢失。
                effective_naming_parts = naming_parts or [
                    {"kind": "date"}, {"kind": "event"}, {"kind": "location"},
                    {"kind": "device"}, {"kind": "type"},
                ]
                folder_name = requested_folders.get(date_key) or build_backup_folder_name(
                    selected, effective_naming_parts
                )
                if event_value:
                    parts_with_event = []
                    for part in effective_naming_parts:
                        copy_part = dict(part)
                        if copy_part.get("kind") == "event" and not copy_part.get("value"):
                            copy_part["value"] = event_value
                        parts_with_event.append(copy_part)
                    if date_key not in requested_folders:
                        folder_name = build_backup_folder_name(selected, parts_with_event)
                media_names = requested_media_folders.get(date_key, {})
                for item in selected:
                    item["backup_folder_name"] = folder_name
                    media_type = item.get("media_type", "other")
                    if media_type in ("photo", "raw"):
                        item["backup_media_folder_name"] = media_names.get("photo", "")
                    elif media_type == "video":
                        item["backup_media_folder_name"] = media_names.get("video", "")
                event_batches.append({"name": folder_name, "files": selected})
            if not event_batches:
                raise RuntimeError("没有可用于归档的日期分组")
            events = [batch["name"] for batch in event_batches]
            total_events = len(event_batches)

            # ---- step 4: 逐个事件拷贝 ----
            targets = [backup_root] + (backup_targets or [])
            targets = list(dict.fromkeys(t for t in targets if t.strip()))

            for target in targets:
                self._validate_target(mount_point, target, self.progress.total_bytes)

            # 一次性计算源文件哈希
            for f in files:
                f["source_hash"] = self._verifier.hash_file(f["path"])

            all_copied = all_skipped = 0; all_bytes = 0
            primary_copied = primary_skipped = primary_bytes = 0
            reviewed_count = previewed_count = 0
            label_counts = {}

            for ei, batch in enumerate(event_batches):
                ename = batch["name"]
                group_files = batch["files"]
                cur_id = backup_id if ei == 0 else db.create_backup(ename, backup_root, backup_targets)
                if ei > 0:
                    db.add_files(cur_id, group_files)
                else:
                    db.rename_backup(cur_id, ename)
                label = f"[{ei+1}/{total_events}] {ename}"
                self.progress.status = "copying"
                self.progress.current_file = f"事件: {label}"
                self.progress.notify()

                batch_copied = batch_skipped = batch_bytes = 0

                batch_target_results = []
                for target in targets:
                    if self._cancel_flag.is_set():
                        break
                    result = self._copy_to_target(
                        group_files, target, ename, cur_id, enable_verify,
                        record_file_status=(target == backup_root),
                    )
                    all_copied += result["copied"]
                    all_skipped += result["skipped"]
                    all_bytes += result["bytes"]
                    if target == backup_root:
                        batch_copied += result["copied"]
                        batch_skipped += result["skipped"]
                        batch_bytes += result["bytes"]
                        primary_copied += result["copied"]
                        primary_skipped += result["skipped"]
                        primary_bytes += result["bytes"]
                    target_status = "completed" if result["failed"] == 0 else "partial"
                    target_error = "" if result["failed"] == 0 else f"{result['failed']} 个文件未完成"
                    db.upsert_target_result(
                        cur_id, target, result["copied"], result["skipped"],
                        result["failed"], result["copied"] + result["skipped"],
                        target_status, target_error,
                    )
                    batch_target_results.append({"target": target, **result, "status": target_status})

                    if self._cancel_flag.is_set():
                        self._finish_cancelled_backup(
                            cur_id, ename, backup_root, devices, total,
                            primary_copied, primary_skipped, reviewed_count,
                            previewed_count, label_counts, mount_point,
                        )
                        return

                    if enable_verify:
                        event_dir = os.path.join(target, ename)
                        if os.path.exists(event_dir):
                            flist = []
                            for root, _, fnames in os.walk(event_dir):
                                for fn in fnames:
                                    if fn != "checksums.json":
                                        flist.append(os.path.join(root, fn))
                            if flist:
                                self._verifier.generate_manifest(flist, event_dir)

                # 废片审片
                reviewed_count, label_counts = self._review_and_quarantine(
                    group_files, backup_root, ename, cur_id
                )
                if self._cancel_flag.is_set():
                    self._finish_cancelled_backup(
                        cur_id, ename, backup_root, devices, total,
                        primary_copied, primary_skipped, reviewed_count,
                        previewed_count, label_counts, mount_point,
                    )
                    return
                # Windows 预览是后续可选导出，不再默认在素材盘根目录生成技术目录。
                if self._cancel_flag.is_set():
                    self._finish_cancelled_backup(
                        cur_id, ename, backup_root, devices, total,
                        primary_copied, primary_skipped, reviewed_count,
                        previewed_count, label_counts, mount_point,
                    )
                    return
                # 在审片之后生成（审片可能改名/移走废片，需用最终 dest_path）
                previewed_in_batch = self._generate_windows_previews(
                    group_files, backup_root, cur_id
                )
                previewed_count += previewed_in_batch

                # 每个日期文件夹各有一条可打开的报告；避免多日期任务中只有
                # 第一条历史记录有报告、其他记录显示为空。
                batch_failed = sum(item["failed"] for item in batch_target_results)
                batch_status = "completed" if batch_failed == 0 else "partial"
                batch_report = self._write_backup_report(
                    backup_id=cur_id,
                    event_name=ename,
                    backup_root=backup_root,
                    devices=devices,
                    total_files=len(group_files),
                    copied_files=batch_copied,
                    skipped_files=batch_skipped,
                    reviewed_files=reviewed_count,
                    preview_files=previewed_in_batch,
                    failed_files=batch_failed,
                    verified_files=batch_copied + batch_skipped,
                    total_size=sum(item.get("size", 0) for item in group_files),
                    elapsed_seconds=time.time() - self.progress.start_time,
                    status=batch_status,
                    review_summary=label_counts,
                    source_mount=mount_point,
                )
                db.finish_backup(cur_id, batch_status, "" if batch_failed == 0 else "部分目标或文件未完成，原卡安全，可重新执行", batch_report)

            self.progress.copied_files = primary_copied
            self.progress.skipped_files = primary_skipped
            self.progress.bytes_copied = primary_bytes
            self.progress.notify()

            # 生成校验清单（所有事件）
            if enable_verify:
                self.progress.status = "verifying"
                self.progress.current_file = "生成校验清单..."
                self.progress.phase_progress = 0
                self.progress.notify()

                # 按每日主备份文件夹生成校验清单
                for ename in events:
                    for target in targets:
                        event_dir = os.path.join(target, ename)
                        if os.path.exists(event_dir):
                            all_files = []
                            for root, _, fnames in os.walk(event_dir):
                                for fn in fnames:
                                    if fn != "checksums.json":
                                        all_files.append(os.path.join(root, fn))
                            if all_files:
                                self._verifier.generate_manifest(all_files, event_dir)

            # ---- step 8: 完成 ----
            elapsed = time.time() - self.progress.start_time
            self.progress.elapsed_seconds = elapsed
            self.progress.copied_files = primary_copied
            self.progress.skipped_files = primary_skipped
            self.progress.reviewed_files = reviewed_count if total_events > 0 else 0
            self.progress.preview_files = previewed_count if total_events > 0 else 0
            self.progress.processed_files = primary_copied + primary_skipped
            self.progress.bytes_copied = primary_bytes
            self.progress.phase_progress = 100

            target_results = db.get_target_results(backup_id)
            failed_count = sum(item.get("failed_files", 0) for item in target_results)
            final_status = "completed" if failed_count == 0 else "partial"
            report_path = self._write_backup_report(
                backup_id=backup_id,
                event_name=" + ".join(events) if total_events > 1 else events[0],
                backup_root=backup_root,
                devices=devices,
                total_files=total,
                copied_files=primary_copied,
                skipped_files=primary_skipped,
                reviewed_files=reviewed_count,
                preview_files=previewed_count,
                failed_files=failed_count,
                # 跳过的文件已逐个与目标内容一致，也属于已校验素材。
                verified_files=primary_copied + primary_skipped,
                total_size=self.progress.total_bytes,
                elapsed_seconds=elapsed,
                status=final_status,
                review_summary=label_counts,
                source_mount=mount_point,
            )

            db.finish_backup(backup_id, final_status, "" if failed_count == 0 else "部分目标或文件未完成，原卡安全，可重新执行", report_path)
            self.progress.status = "done" if failed_count == 0 else "partial"
            self.progress.can_cleanup = failed_count == 0
            self.progress.mount_point = mount_point
            self.progress.notify()

            # 通知推送
            if config.webhook_url:
                self._send_webhook(total, primary_copied, primary_skipped, events)

            # 后台触发百度网盘上传
            self._trigger_baidu_upload(backup_root, event_name)

        except Exception as e:
            report_path = ""
            try:
                report_path = self._write_backup_report(
                    backup_id=backup_id,
                    event_name=manual_event or "按日期归档",
                    backup_root=backup_root,
                    devices=locals().get("devices", {}),
                    total_files=self.progress.total_files,
                    copied_files=self.progress.copied_files,
                    skipped_files=self.progress.skipped_files,
                    reviewed_files=self.progress.reviewed_files,
                    preview_files=self.progress.preview_files,
                    failed_files=max(
                        self.progress.total_files
                        - self.progress.copied_files
                        - self.progress.skipped_files,
                        0,
                    ),
                    verified_files=self.progress.copied_files + self.progress.skipped_files,
                    total_size=self.progress.total_bytes,
                    elapsed_seconds=max(time.time() - self.progress.start_time, 0),
                    status="error",
                    review_summary={},
                    source_mount=mount_point,
                )
            except Exception:
                pass
            db.finish_backup(backup_id, "error", str(e), report_path)
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
