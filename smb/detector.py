"""SD 卡 / 可移动磁盘检测器 — 跨平台"""
import os
import shutil
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Callable

from .config import config


def _disk_usage(path: str) -> tuple:
    """跨平台磁盘用量 (total, used)。Windows 的 os 模块没有 statvfs，改用 shutil.disk_usage。"""
    try:
        st = os.statvfs(path)
        return st.f_frsize * st.f_blocks, st.f_frsize * (st.f_blocks - st.f_bfree)
    except AttributeError:
        pass
    except OSError:
        return 0, 0
    try:
        usage = shutil.disk_usage(path)
        return usage.total, usage.used
    except OSError:
        return 0, 0


def list_removable_volumes() -> list[dict]:
    """
    列出当前系统所有可移动卷。
    返回: [{name, mount_point, size_total, size_used, fstype}, ...]
    """
    volumes = []

    if sys.platform == "darwin":
        # macOS: /Volumes 下所有非系统挂载点
        volumes_dir = Path("/Volumes")
        if volumes_dir.exists():
            for v in volumes_dir.iterdir():
                if v.is_symlink() or not v.is_dir():
                    continue
                name = v.name
                # 跳过系统卷
                if name.startswith(".") or name in ("MobileBackups", "com.apple.TimeMachine"):
                    continue
                mount_point = str(v)
                size_total, size_used = _disk_usage(mount_point)
                volumes.append({
                    "name": name,
                    "mount_point": mount_point,
                    "size_total": size_total,
                    "size_used": size_used,
                    "fstype": "unknown",
                })

    elif sys.platform == "win32":
        # Windows: 检测可移动驱动器
        import string
        import ctypes
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                # DRIVE_REMOVABLE = 2
                if drive_type == 2:
                    size_total, size_used = _disk_usage(drive)
                    volumes.append({
                        "name": f"{letter}:",
                        "mount_point": drive,
                        "size_total": size_total,
                        "size_used": size_used,
                        "fstype": "removable",
                    })

    else:
        # Linux: 扫描常见挂载点
        for base in config.mount_points:
            base_path = Path(base)
            if not base_path.exists():
                continue
            for v in base_path.iterdir():
                if not v.is_dir():
                    continue
                size_total, size_used = _disk_usage(str(v))
                volumes.append({
                    "name": v.name,
                    "mount_point": str(v),
                    "size_total": size_total,
                    "size_used": size_used,
                    "fstype": "unknown",
                })

    return volumes


def _windows_system_drives() -> set:
    """返回 Windows 上不应被当作备份来源的盘符集合（系统盘、光驱等）。"""
    import ctypes
    import string
    system = set()
    try:
        windir = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or "C:\\"
        system.add(windir[:1].upper() + ":\\")
    except Exception:
        system.add("C:\\")
    # 把纯光驱也排除（DRIVE_CDROM = 5）
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            try:
                if ctypes.windll.kernel32.GetDriveTypeW(drive) == 5:
                    system.add(drive)
            except Exception:
                pass
    return system


def list_candidate_source_volumes() -> list[dict]:
    """列出所有可能作为相机存储卡来源的卷。

    Windows 上不少读卡器把 SD 卡报成 DRIVE_FIXED(3) 而非 DRIVE_REMOVABLE(2)，
    如果只认可移动盘会导致那些机器全程显示“未检测到 SD 卡”。这里在 Windows
    上额外纳入非系统盘的固定卷，再交给 find_likely_media_source 用 DCIM/PRIVATE
    等目录特征甄别，宁可多列出候选也不能漏掉真正的相机卡。
    """
    removable = list_removable_volumes()
    if sys.platform != "win32":
        return removable

    known = {v["mount_point"] for v in removable}
    system = _windows_system_drives()
    merged = list(removable)
    import string
    import ctypes
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if drive in known or drive in system:
            continue
        if not os.path.exists(drive):
            continue
        try:
            drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
        except Exception:
            drive_type = -1
        # DRIVE_FIXED = 3：读卡器常把卡报成固定盘，纳入候选；其余类型跳过。
        if drive_type != 3:
            continue
        size_total, size_used = _disk_usage(drive)
        merged.append({
            "name": f"{letter}:",
            "mount_point": drive,
            "size_total": size_total,
            "size_used": size_used,
            "fstype": "fixed",
        })
    return merged


def list_all_volumes() -> list[dict]:
    """列出所有挂载卷（包括内置磁盘）用于目标选择"""
    volumes = []
    try:
        import psutil
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (PermissionError, OSError):
                usage = None
            volumes.append({
                "name": Path(part.mountpoint).name or part.mountpoint,
                "mount_point": part.mountpoint,
                "size_total": usage.total if usage else 0,
                "size_used": usage.used if usage else 0,
                "fstype": part.fstype,
                "device": part.device,
            })
    except ImportError:
        # 没有 psutil 时回退简单扫描
        return list_removable_volumes()

    return volumes


def is_sd_card(volume: dict) -> bool:
    """启发式判断是否为 SD 卡/可移动设备"""
    name = volume.get("name", "").lower()
    fstype = volume.get("fstype", "").lower()

    # 排除系统盘
    if sys.platform == "darwin":
        if name == "macintosh hd":
            return False
    elif sys.platform == "win32":
        if fstype in ("ntfs", "local fixed"):
            if volume.get("device", "").startswith("C:"):
                return False

    # 大小判断：SD 卡通常 < 1TB
    total = volume.get("size_total", 0)
    if total > 2 * 1024 ** 4:  # > 2TB
        return False

    return True


def find_likely_media_source(volumes: Optional[list[dict]] = None) -> Optional[dict]:
    """从已挂载的可移动卷中选出最像相机存储卡的来源。

    macOS 会把外置 SSD 和 SD 卡都挂载在 /Volumes，不能再依赖枚举顺序。
    这里仅检查根目录结构和卷名，不读取、更改任何素材。没有足够证据时返回
    ``None``，宁可提示用户插卡，也不能把备份盘误当成来源。
    """
    candidates = volumes if volumes is not None else list_removable_volumes()
    best: Optional[dict] = None
    best_score = 0

    for volume in candidates:
        mount_point = volume.get("mount_point", "")
        if not mount_point or not os.path.ismount(mount_point):
            continue
        try:
            root_names = {entry.name.upper() for entry in Path(mount_point).iterdir()}
        except OSError:
            continue

        name = str(volume.get("name", "")).lower()
        score = 0
        if any(token in name for token in ("sd", "tf", "card", "存储卡", "内存卡", "卡")):
            score += 30
        if "DCIM" in root_names:
            score += 80
        if "PRIVATE" in root_names:
            score += 25
        if "MISC" in root_names:
            score += 15
        if "MP_ROOT" in root_names or "AVCHD" in root_names:
            score += 20
        if "IPHONE" in root_names:
            score += 10
        # 常见备份盘命名不会单独否决，但会降低误选优先级。
        if any(token in name for token in ("ssd", "固态", "backup", "archive", "nas")):
            score -= 20

        if score > best_score:
            best = volume
            best_score = score

    return best if best_score >= 40 else None


class SDCardWatcher:
    """后台线程探测 SD 卡插拔，通过回调通知"""

    def __init__(self, on_insert: Optional[Callable] = None,
                 on_remove: Optional[Callable] = None,
                 interval: float = 2.0):
        self.on_insert = on_insert
        self.on_remove = on_remove
        self.interval = interval
        self._known_volumes: set = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        # 初始化已知卷列表（含读卡器报成固定盘的候选来源）
        for v in list_candidate_source_volumes():
            self._known_volumes.add(v["mount_point"])

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            current = list_candidate_source_volumes()
            current_mounts = {v["mount_point"] for v in current}

            # 检测新插入
            new_mounts = current_mounts - self._known_volumes
            for mount in new_mounts:
                vol = next((v for v in current if v["mount_point"] == mount), None)
                if vol and is_sd_card(vol) and self.on_insert:
                    self.on_insert(vol)

            # 检测拔出
            removed = self._known_volumes - current_mounts
            for mount in removed:
                if self.on_remove:
                    self.on_remove(mount)

            self._known_volumes = current_mounts
            time.sleep(self.interval)
