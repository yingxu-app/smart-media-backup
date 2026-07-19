"""文件整理器 — EXIF 元数据提取 + 分类"""
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import config


def detect_camera_model(filepath: str) -> str:
    """通过 exiftool 提取相机型号，失败则用文件名启发式"""
    try:
        result = subprocess.run(
            ["exiftool", "-Model", "-s", "-s", "-s", filepath],
            capture_output=True, text=True, timeout=10
        )
        model = result.stdout.strip()
        if model:
            # 清理多余空格
            return re.sub(r'\s+', ' ', model)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    fname = Path(filepath).name.upper()
    if fname.startswith("DSC"):
        return "Sony"
    elif fname.startswith("DJI"):
        return "DJI"
    elif fname.startswith("GOPR") or fname.startswith("GH"):
        return "GoPro"
    elif fname.startswith("IMG_"):
        return "iPhone"
    return "Unknown"


def extract_date(filepath: str) -> Optional[datetime]:
    """从 EXIF DateTimeOriginal 提取拍摄日期，回退文件修改时间"""
    try:
        result = subprocess.run(
            ["exiftool", "-DateTimeOriginal", "-d", "%Y-%m-%d %H:%M:%S", "-s3", filepath],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return datetime.strptime(result.stdout.strip(), "%Y-%m-%d %H:%M:%S")
    except (subprocess.TimeoutExpired, ValueError):
        pass
    try:
        return datetime.fromtimestamp(os.path.getmtime(filepath))
    except OSError:
        return None


def extract_gps(filepath: str) -> Optional[dict]:
    """提取 GPS 坐标"""
    try:
        lat = subprocess.run(
            ["exiftool", "-GPSLatitude", "-s3", filepath],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        lon = subprocess.run(
            ["exiftool", "-GPSLongitude", "-s3", filepath],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        if lat and lon and lat != "0" and lon != "0":
            return {"lat": float(lat), "lon": float(lon)}
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None


def get_media_type(ext: str) -> str:
    """判断媒体类型: photo / raw / video / audio / other"""
    ext = ext.lower()
    if ext in config.raw_extensions or ext in config.photo_extensions:
        return "photo"
    if ext in config.video_extensions:
        return "video"
    if ext in config.audio_extensions:
        return "audio"
    return "other"


def get_dest_dir(backup_root: str, camera_model: str, event_name: str,
                 media_type: str, sort_mode: str = "device",
                 file_date: object = None, file_gps: dict = None) -> str:
    """
    生成目标目录路径。
    排序模式:
      "device"   — {root}/{设备}/{事件}/{类型}
      "date"     — {root}/{年月}/{设备}/{事件}/{类型}
      "location" — {root}/{地点}/{设备}/{事件}/{类型}
    """
    camera_clean = re.sub(r'[<>:"/\\|?*]', '_', camera_model)
    event_clean = re.sub(r'[<>:"/\\|?*]', '_', event_name or "未命名事件")
    media_dir = "照片" if media_type in ("photo", "raw") else "视频"

    if sort_mode == "date" and file_date:
        prefix = file_date.strftime("%Y年%m月")
    elif sort_mode == "location" and file_gps:
        lat = file_gps.get("lat", 0)
        lng = file_gps.get("lng", 0)
        lat_dir = "北纬" if lat >= 0 else "南纬"
        lng_dir = "东经" if lng >= 0 else "西经"
        prefix = f"{lat_dir}{abs(lat):.1f}_{lng_dir}{abs(lng):.1f}"
    else:
        prefix = None

    if prefix:
        return str(Path(backup_root) / prefix / camera_clean / event_clean / media_dir)
    return str(Path(backup_root) / camera_clean / event_clean / media_dir)


def scan_sd_card(mount_path: str) -> list[dict]:
    """
    扫描 SD 卡，返回媒体文件信息列表。
    每项: {path, filename, ext, camera, date, gps, media_type, size}
    """
    results = []
    media_exts = set(config.all_media_extensions)

    for root, dirs, files in os.walk(mount_path):
        # 跳过隐藏目录、系统目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
            'System Volume Information', '$RECYCLE.BIN', '.Spotlight-V100')]

        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in media_exts:
                continue

            fpath = os.path.join(root, fname)
            try:
                fsize = os.path.getsize(fpath)
            except OSError:
                continue

            info = {
                "path": fpath,
                "filename": fname,
                "ext": ext,
                "size": fsize,
                "camera": "",
                "date": None,
                "gps": None,
                "media_type": get_media_type(ext),
            }
            results.append(info)

    return results


def batch_extract_metadata(files: list[dict], progress_callback=None) -> list[dict]:
    """批量提取元数据（可做进度回调）"""
    total = len(files)
    for i, f in enumerate(files):
        f["camera"] = detect_camera_model(f["path"])
        f["date"] = extract_date(f["path"])
        f["gps"] = extract_gps(f["path"])
        if progress_callback:
            progress_callback(i + 1, total, f["filename"])
    return files
