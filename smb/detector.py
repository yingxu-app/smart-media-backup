"""SD 卡 / 可移动磁盘检测器 — 跨平台"""
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Callable

from .config import config


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
                try:
                    st = os.statvfs(mount_point)
                    size_total = st.f_frsize * st.f_blocks
                    size_used = st.f_frsize * (st.f_blocks - st.f_bfree)
                except OSError:
                    size_total = size_used = 0
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
                    try:
                        st = os.statvfs(drive)
                        size_total = st.f_frsize * st.f_blocks
                        size_used = st.f_frsize * (st.f_blocks - st.f_bfree)
                    except OSError:
                        size_total = size_used = 0
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
                try:
                    st = os.statvfs(str(v))
                    size_total = st.f_frsize * st.f_blocks
                    size_used = st.f_frsize * (st.f_blocks - st.f_bfree)
                except OSError:
                    size_total = size_used = 0
                volumes.append({
                    "name": v.name,
                    "mount_point": str(v),
                    "size_total": size_total,
                    "size_used": size_used,
                    "fstype": "unknown",
                })

    return volumes


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
        # 初始化已知卷列表
        for v in list_removable_volumes():
            self._known_volumes.add(v["mount_point"])

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            current = list_removable_volumes()
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
