"""Safe transfer of already-archived media between local folders/volumes."""
from __future__ import annotations

import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from .config import config
from .organizer import (
    build_backup_folder_name, detect_camera_model, extract_date, get_media_type,
    scan_sd_card,
)
from .verifier import ChecksumVerifier


class TransferCancelled(Exception):
    pass


class TransferManager:
    """In-memory scan and job state; source files are removed only after SHA256 verification."""

    def __init__(self):
        self.lock = threading.RLock()
        self.scan_state = {"status": "idle", "source": "", "items": [], "error": ""}
        self.job = {"status": "idle", "total": 0, "done": 0, "copied": 0,
                    "duplicates": 0, "failed": 0, "current": "", "speed": 0,
                    "error": "", "bytes_done": 0}
        self.cancel_event = threading.Event()
        self.verifier = ChecksumVerifier()

    def start_scan(self, source: str):
        if not source.strip():
            raise ValueError("请选择来源文件夹")
        source_path = Path(source).expanduser().resolve()
        if not source_path.is_dir():
            raise ValueError("请选择存在的素材文件夹或磁盘")
        with self.lock:
            if self.job["status"] == "running":
                raise RuntimeError("转移任务执行期间不能更换扫描来源")
            if self.scan_state["status"] == "scanning":
                raise RuntimeError("正在扫描，请稍候")
            self.scan_state = {"status": "scanning", "source": str(source_path), "items": [], "error": ""}
        threading.Thread(target=self._scan, args=(str(source_path),), daemon=True).start()

    def _scan(self, source: str):
        try:
            found = scan_sd_card(source)
            items = []
            for file in found:
                path = Path(file["path"])
                try:
                    resolved = path.resolve(strict=True)
                    resolved.relative_to(Path(source))
                    if path.is_symlink() or not resolved.is_file():
                        continue
                    stat = resolved.stat()
                except (OSError, ValueError):
                    continue
                date = extract_date(str(resolved))
                camera = detect_camera_model(str(resolved))
                rel = resolved.relative_to(Path(source)).as_posix()
                item_id = uuid.uuid4().hex
                items.append({
                    "id": item_id, "path": str(resolved), "relative": rel,
                    "name": resolved.name, "ext": resolved.suffix.lower(),
                    "size": stat.st_size, "mtime": stat.st_mtime,
                    "date": date.isoformat(timespec="seconds") if date else "",
                    "date_label": date.strftime("%Y-%m-%d") if date else "日期待确认",
                    "camera": camera, "media_type": get_media_type(resolved.suffix),
                    "selected": True, "waste": None, "similar": False,
                })
            with self.lock:
                self.scan_state.update(status="ready", items=items)
        except Exception as exc:
            with self.lock:
                self.scan_state.update(status="error", error=str(exc), items=[])

    def snapshot_scan(self):
        with self.lock:
            return {**self.scan_state, "items": [dict(x) for x in self.scan_state["items"]]}

    def analyze(self, item_ids: list[str], target: str, check_waste: bool, check_similar: bool):
        item_ids = item_ids if isinstance(item_ids, list) else []
        with self.lock:
            items = [dict(x) for x in self.scan_state["items"] if x["id"] in set(item_ids)]
            source_root = Path(self.scan_state["source"]).resolve() if self.scan_state["source"] else None
        if not items:
            raise ValueError("请先选择素材")
        if not target:
            raise ValueError("请先选择目标文件夹")
        target_root = Path(target).expanduser().resolve()
        if not target_root.is_dir():
            raise ValueError("请选择已存在的目标文件夹")
        if source_root and (target_root == source_root or source_root in target_root.parents or target_root in source_root.parents):
            raise ValueError("来源与目标不能相同，也不能互相包含")
        paths = [x["path"] for x in items]
        similar_paths = set()
        if check_similar:
            try:
                from .phash import HAS_IMAGEHASH
                if HAS_IMAGEHASH:
                    from PIL import Image
                    import imagehash
                    hashes = []
                    for path in paths:
                        try:
                            with Image.open(path) as image:
                                hashes.append((path, imagehash.phash(image)))
                        except Exception:
                            continue
                    threshold = max(0, int(config.phash_threshold))
                    for i, (path_a, hash_a) in enumerate(hashes):
                        for path_b, hash_b in hashes[i + 1:]:
                            if hash_a - hash_b <= threshold:
                                similar_paths.update((path_a, path_b))
            except Exception:
                pass
        waste_by_path = {}
        if check_waste:
            from .waste_filter import waste_reviewer
            for item in items:
                if item["media_type"] == "photo":
                    try:
                        waste_by_path[item["path"]] = waste_reviewer.review(item["path"])
                    except Exception as exc:
                        waste_by_path[item["path"]] = {"label": "待人工确认", "reason": str(exc)}
        exact = self._find_exact_duplicates(items, target)
        for item in items:
            item["similar"] = item["path"] in similar_paths
            item["waste"] = waste_by_path.get(item["path"])
            item["exact_match_path"] = exact.get(item["path"], "")
            item["exact_duplicate"] = bool(item["exact_match_path"])
        with self.lock:
            by_id = {x["id"]: x for x in self.scan_state["items"]}
            for item in items:
                if item["id"] in by_id:
                    by_id[item["id"]].update({k: item[k] for k in ("similar", "waste", "exact_duplicate", "exact_match_path")})
        return items

    def _find_exact_duplicates(self, items, target):
        root = Path(target).expanduser().resolve()
        if not root.is_dir():
            return {}
        wanted_sizes = {item["size"] for item in items}
        existing = {}
        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(current) / d).is_symlink()]
            for name in files:
                path = Path(current) / name
                try:
                    if path.is_symlink():
                        continue
                    size = path.stat().st_size
                    if size in wanted_sizes:
                        existing.setdefault(size, []).append(str(path))
                except OSError:
                    continue
        duplicates = {}
        for item in items:
            source_hash = self.verifier.hash_file(item["path"])
            if not source_hash:
                continue
            for candidate in existing.get(item["size"], []):
                if self.verifier.hash_file(candidate) == source_hash:
                    duplicates[item["path"]] = candidate
                    break
        return duplicates

    def start(self, item_ids: list[str], target: str, event: str = "", move: bool = True):
        if not target.strip():
            raise ValueError("请选择目标文件夹")
        item_ids = item_ids if isinstance(item_ids, list) else []
        with self.lock:
            if self.job["status"] == "running":
                raise RuntimeError("已有转移任务正在进行")
            scan = self.scan_state
            if scan["status"] != "ready":
                raise ValueError("请先扫描来源文件夹")
            items = [dict(x) for x in scan["items"] if x["id"] in set(item_ids)]
            if not items:
                raise ValueError("请选择至少一个素材")
            source_root = Path(scan["source"]).resolve()
            target_root = Path(target).expanduser().resolve()
            if not target_root.is_dir():
                raise ValueError("请选择已存在的目标文件夹")
            if target_root == source_root or source_root in target_root.parents or target_root in source_root.parents:
                raise ValueError("来源与目标不能相同，也不能互相包含")
            required = sum(int(item.get("size", 0)) for item in items)
            try:
                if shutil.disk_usage(target_root).free < required + max(int(x["size"]) for x in items):
                    raise ValueError("目标位置可用空间不足，无法安全完成转移")
            except OSError as exc:
                raise ValueError(f"无法读取目标位置剩余空间：{exc}") from exc
            self.cancel_event.clear()
            self.job = {"status": "running", "total": len(items), "done": 0, "copied": 0,
                        "duplicates": 0, "failed": 0, "current": "准备中", "speed": 0,
                        "error": "", "move": bool(move), "bytes_done": 0,
                        "total_bytes": required}
        threading.Thread(target=self._run, args=(items, str(target_root), event.strip(), bool(move), str(source_root)), daemon=True).start()

    def _run(self, items, target, event, move, source_root):
        from .waste_filter import waste_reviewer
        started = time.monotonic()
        try:
            for item in items:
                if self.cancel_event.is_set():
                    break
                src = Path(item["path"])
                with self.lock:
                    self.job["current"] = item["relative"]
                try:
                    source_root = Path(source_root).resolve()
                    resolved_src = src.resolve(strict=True)
                    if src.is_symlink() or not resolved_src.is_relative_to(source_root) or not resolved_src.is_file():
                        raise OSError("源文件已不存在或是符号链接")
                    date = datetime.fromisoformat(item["date"]) if item.get("date") else None
                    naming = [{"kind": "date"}, {"kind": "event", "value": event},
                              {"kind": "device"}, {"kind": "type"}]
                    source_hash = self.verifier.hash_file(str(src))
                    if not source_hash:
                        raise OSError("无法读取源文件校验值")
                    matched_copy = item.get("exact_match_path")
                    if (matched_copy and Path(matched_copy).resolve().is_relative_to(Path(target).resolve())
                            and not Path(matched_copy).is_symlink() and Path(matched_copy).is_file()
                            and self.verifier.hash_file(matched_copy) == source_hash):
                        if move:
                            self._remove_source(src, source_hash)
                        with self.lock:
                            self.job["duplicates"] += 1
                            self.job["bytes_done"] += int(item["size"])
                        continue
                    if item.get("waste") and item["waste"].get("label") in waste_reviewer.WASTE_LABELS:
                        folder, media_dir = "待确认废片", "照片" if item.get("media_type") == "photo" else "视频"
                    else:
                        folder = build_backup_folder_name([{
                            "date": date, "camera": item.get("camera", "Unknown"),
                            "media_type": item.get("media_type", "other"),
                        }], naming)
                        media_dir = "照片" if item.get("media_type") == "photo" else "视频" if item.get("media_type") == "video" else "其他素材"
                    dest_dir = Path(target) / folder / media_dir
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if not dest_dir.resolve().is_relative_to(Path(target).resolve()):
                        raise OSError("目标子目录指向目标位置以外，来源已保留")
                    dest = dest_dir / src.name
                    if dest.exists():
                        if not dest.is_symlink() and self.verifier.hash_file(str(dest)) == source_hash:
                            if move:
                                self._remove_source(src, source_hash)
                            with self.lock:
                                self.job["duplicates"] += 1
                                self.job["bytes_done"] += int(item["size"])
                        else:
                            stem, suffix = src.stem, src.suffix
                            index = 2
                            while os.path.lexists(dest):
                                dest = dest_dir / f"{stem}_{index}{suffix}"
                                index += 1
                            self._copy_verified(src, dest, source_hash, move)
                            with self.lock:
                                self.job["copied"] += 1
                    else:
                        self._copy_verified(src, dest, source_hash, move)
                        with self.lock:
                            self.job["copied"] += 1
                except TransferCancelled:
                    pass
                except Exception as exc:
                    with self.lock:
                        self.job["failed"] += 1
                        self.job["error"] = str(exc)
                finally:
                    with self.lock:
                        self.job["done"] += 1
                        elapsed = max(time.monotonic() - started, 0.001)
                        self.job["speed"] = int(self.job["bytes_done"] / elapsed)
            with self.lock:
                self.job["status"] = "cancelled" if self.cancel_event.is_set() else ("partial" if self.job["failed"] else "done")
                self.job["current"] = "已取消" if self.cancel_event.is_set() else "完成"
        except Exception as exc:
            with self.lock:
                self.job.update(status="error", error=str(exc))

    def _copy_verified(self, src: Path, dest: Path, source_hash: str, move: bool):
        temp = dest.with_name(dest.name + f".yingxu-{uuid.uuid4().hex}.partial")
        written = 0
        committed = False
        try:
            with src.open("rb") as source, temp.open("xb") as output:
                while True:
                    if self.cancel_event.is_set():
                        raise TransferCancelled()
                    block = source.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    written += len(block)
                    with self.lock:
                        self.job["bytes_done"] += len(block)
                output.flush()
                os.fsync(output.fileno())
            shutil.copystat(src, temp)
            if self.cancel_event.is_set():
                raise TransferCancelled()
            ok, detail = self.verifier.verify_single(str(src), str(temp), source_hash)
            if not ok:
                raise OSError(f"SHA-256 校验失败：{detail}")
            if dest.exists():
                raise FileExistsError("目标文件刚刚被其他程序创建；来源素材已保留，请重新分析后再试")
            # Exclusive creation also protects against another process creating
            # the same destination after the existence check (including exFAT).
            created = False
            try:
                with dest.open("xb") as output, temp.open("rb") as verified:
                    created = True
                    while True:
                        if self.cancel_event.is_set():
                            raise TransferCancelled()
                        block = verified.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
                    output.flush()
                    os.fsync(output.fileno())
                if self.verifier.hash_file(str(dest)) != source_hash:
                    raise OSError("最终目标校验失败，来源已保留")
                shutil.copystat(temp, dest)
            except Exception:
                if created:
                    dest.unlink(missing_ok=True)
                raise
            committed = True
            if move:
                self._remove_source(src, source_hash)
        finally:
            if not committed and written:
                with self.lock:
                    self.job["bytes_done"] = max(0, self.job["bytes_done"] - written)
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def cancel(self):
        self.cancel_event.set()

    def _remove_source(self, src, expected_hash):
        if self.cancel_event.is_set():
            raise TransferCancelled()
        if src.is_symlink() or self.verifier.hash_file(str(src)) != expected_hash:
            raise OSError("来源在转移期间发生变化，已保留来源")
        if self.cancel_event.is_set():
            raise TransferCancelled()
        src.unlink()

    def snapshot_job(self):
        with self.lock:
            return dict(self.job)


transfer_manager = TransferManager()
