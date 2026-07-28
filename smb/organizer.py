"""文件整理器 — EXIF 元数据提取 + 分类"""
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import config


# 面向用户的中文显示名。内部仍保留原始识别值，避免影响已有历史记录；
# 新的备份目录和界面不再把 Unknown 直接暴露给摄影师。
DEVICE_DISPLAY_NAMES = {
    "Unknown": "未知设备",
    "iPhone": "手机",
    "Sony": "索尼相机",
    "DJI": "大疆设备",
    "GoPro": "GoPro",
}


def display_device_name(camera: str) -> str:
    """把识别结果转换为中文界面名称。"""
    value = (camera or "Unknown").strip()
    return DEVICE_DISPLAY_NAMES.get(value, value)


def device_category(camera: str) -> str:
    """目录名称使用摄影师一眼能读懂的设备类别，而不是具体英文机型。"""
    value = (camera or "Unknown").lower()
    if value in {"iphone", "android", "phone", "手机"}:
        return "手机"
    if any(token in value for token in ("dji", "mavic", "mini", "air", "avata", "drone", "无人机")):
        return "无人机"
    if value in {"unknown", "未知设备", ""}:
        return "未知设备"
    return "相机"


def media_summary(files: list[dict]) -> str:
    """根据真实扫描结果生成“照片及视频原片”等可读摘要。"""
    has_photo = any(item.get("media_type") in ("photo", "raw") for item in files)
    has_video = any(item.get("media_type") == "video" for item in files)
    if has_photo and has_video:
        return "照片及视频原片"
    if has_video:
        return "视频原片"
    if has_photo:
        return "照片原片"
    return "素材原片"


def _safe_folder_name(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", (value or "").strip())
    return re.sub(r"\s+", " ", cleaned).strip(" ._")


def _date_label(files: list[dict]) -> str:
    dates = sorted({item.get("date").date() for item in files if item.get("date")})
    if len(dates) == 1:
        return dates[0].strftime("%Y年%m月%d日")
    if not dates:
        return "日期待确认"
    return f"{dates[0].strftime('%Y年%m月%d日')}至{dates[-1].strftime('%m月%d日')}"


def build_backup_folder_name(files: list[dict], naming_parts: list[dict] | None = None) -> str:
    """生成每日主备份文件夹名称。

    例如：2026年04月29日_手机拍摄_照片及视频原片。
    未识别或未填写的字段会省略，绝不以“未知地点”等占位词污染用户目录。
    """
    naming_parts = naming_parts or [
        {"kind": "date"}, {"kind": "event"}, {"kind": "location"},
        {"kind": "device"}, {"kind": "type"},
    ]
    categories = []
    for item in files:
        category = device_category(item.get("camera", "Unknown"))
        if category not in categories:
            categories.append(category)
    device_value = "及".join(categories) + "拍摄" if categories else ""
    values = {
        "date": _date_label(files),
        "device": device_value,
        "type": media_summary(files),
        # 事件和地点只能来自用户输入或可信的上游识别；当前离线扫描不会编造。
        "event": "",
        "location": "",
    }
    result = []
    for part in naming_parts:
        kind = str(part.get("kind", "")).strip()
        if kind == "custom":
            value = str(part.get("value", "")).strip()
        elif kind in {"event", "location"}:
            value = str(part.get("value", "")).strip() or values[kind]
        elif kind == "omit":
            value = ""
        else:
            value = values.get(kind, "")
        value = _safe_folder_name(value)
        if value and value not in result:
            result.append(value)
    return "_".join(result) or _date_label(files)


def get_backup_media_dir(backup_root: str, folder_name: str, media_type: str) -> str:
    """新的清晰目录：目标 / 每日主文件夹 / 照片或视频。"""
    media_dir = "照片" if media_type in ("photo", "raw") else "视频" if media_type == "video" else "其他素材"
    return str(Path(backup_root) / _safe_folder_name(folder_name) / media_dir)


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
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
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


def _field_value(field: str, camera: str, event: str, mtype: str,
                 fdate=None, fgps=None) -> str:
    """返回单个层级字段的目录名"""
    if field == "device":
        return _safe_folder_name(display_device_name(camera)) or "未知设备"
    if field == "event":
        return re.sub(r'[<>:"/\\|?*]', '_', event or "未命名事件")
    if field == "type":
        return "照片" if mtype in ("photo", "raw") else "视频"
    if field == "date" and fdate:
        return fdate.strftime("%Y年%m月%d日")
    if field == "date":
        return "未知日期"
    if field == "location" and fgps:
        lat = fgps.get("lat", 0)
        lng = fgps.get("lng", 0)
        return f"{'北纬' if lat>=0 else '南纬'}{abs(lat):.1f}_{'东经' if lng>=0 else '西经'}{abs(lng):.1f}"
    if field == "location":
        return "未知地点"
    return field


def get_dest_dir(backup_root: str, camera: str, event: str, mtype: str,
                 sort_order: list = None, fdate=None, fgps=None) -> str:
    """
    按自定义层级顺序生成目标目录路径。
    sort_order: ["device","event","type"]  # 默认
    可选字段: device / event / type / date / location
    """
    order = sort_order or ["device", "event", "type"]
    parts = [backup_root.rstrip("/")]
    for field in order:
        parts.append(_field_value(field, camera, event, mtype, fdate, fgps))
    return str(Path(*parts))


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
            # macOS 在 FAT/exFAT 卡上生成的 AppleDouble 资源叉文件。
            # 它们与原片同名但以 ._ 开头，绝不能作为独立素材归档。
            if fname.startswith("._"):
                continue
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


def date_group_key(value: Optional[datetime]) -> str:
    """为单日归档生成稳定键；缺少可靠拍摄时间时单独列为待确认。"""
    return value.strftime("%Y-%m-%d") if value else "unknown-date"


def build_date_groups(files: list[dict]) -> list[dict]:
    """按拍摄日拆分素材，供预览和真实备份共用。

    地点与场景不能在没有可靠元数据或人工确认时擅自编造，因此只给出
    可编辑的日期基础名称，并把 GPS 是否存在明确告诉界面。
    """
    groups: dict[str, dict] = {}
    for f in files:
        key = date_group_key(f.get("date"))
        if key not in groups:
            if key == "unknown-date":
                suggested = "日期待确认"
                display_date = "日期待确认"
            else:
                dt = f["date"]
                display_date = dt.strftime("%Y年%m月%d日")
                suggested = f"{display_date}拍摄"
            groups[key] = {
                "date_key": key,
                "date_label": display_date,
                "suggested_name": suggested,
                "files": [],
                "total_size": 0,
                "devices": set(),
                "has_gps": False,
            }
        group = groups[key]
        group["files"].append(f)
        group["total_size"] += f.get("size", 0)
        group["devices"].add(display_device_name(f.get("camera") or "Unknown"))
        group["has_gps"] = group["has_gps"] or bool(f.get("gps"))

    ordered = sorted(groups.values(), key=lambda item: item["date_key"], reverse=True)
    return [
        {
            "date_key": item["date_key"],
            "date_label": item["date_label"],
            "suggested_name": item["suggested_name"],
            "file_count": len(item["files"]),
            "total_size": item["total_size"],
            "devices": sorted(item["devices"]),
            "location_status": "检测到 GPS，地点待确认" if item["has_gps"] else "未记录地点，可补充",
            "photos": sum(1 for f in item["files"] if f.get("media_type") in ("photo", "raw")),
            "videos": sum(1 for f in item["files"] if f.get("media_type") == "video"),
            "media_summary": media_summary(item["files"]),
            "folder_name": build_backup_folder_name(item["files"]),
        }
        for item in ordered
    ]


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
