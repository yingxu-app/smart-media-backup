"""感知哈希去重 — 识别连拍/相似照片"""
import os
from typing import Optional

from .config import config

try:
    from PIL import Image
    import imagehash
    HAS_IMAGEHASH = True
except ImportError:
    HAS_IMAGEHASH = False


def find_similar_photos(
    directory: str,
    threshold: Optional[int] = None,
    recursive: bool = True,
) -> list[list[str]]:
    """扫描目录，按感知哈希分组的相似照片列表"""
    if not HAS_IMAGEHASH:
        return []
    thresh = threshold if threshold is not None else config.phash_threshold
    if thresh <= 0:
        return []
    exts = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".tiff", ".tif"}
    hashes: dict[str, list[str]] = {}
    for root, _, files in os.walk(directory) if recursive else [(directory, [], os.listdir(directory))]:
        for f in files:
            if os.path.splitext(f)[1].lower() not in exts:
                continue
            fp = os.path.join(root, f)
            try:
                h = str(imagehash.phash(Image.open(fp)))
            except Exception:
                continue
            hashes.setdefault(h, []).append(fp)
    # Group similar (within hamming distance)
    groups = []
    keys = list(hashes.keys())
    used = set()
    for i, k1 in enumerate(keys):
        if k1 in used:
            continue
        group = list(hashes[k1])
        used.add(k1)
        for j, k2 in enumerate(keys):
            if k2 in used:
                continue
            d = sum(a != b for a, b in zip(k1, k2))
            if d <= thresh:
                group.extend(hashes[k2])
                used.add(k2)
        if len(group) > 1:
            groups.append(group)
    return groups
