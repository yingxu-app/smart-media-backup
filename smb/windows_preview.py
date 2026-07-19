"""Windows 预览缩略图生成器
────────────────────────
给备份结果生成一个单独的预览树，方便 Windows 资源管理器直接看到缩略图。

输出结构:
{backup_root}/_Windows预览/{设备}/{事件}/{照片|视频}/{原文件名}.jpg
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


class WindowsPreviewBuilder:
    """Windows 预览树生成器"""

    def __init__(self, enabled: bool = True, max_size: int = 1024):
        self.enabled = enabled
        self.max_size = max_size

    def _safe_name(self, value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\s]+', "_", value or "").strip("_")
        return cleaned or "event"

    def _preview_root(self, backup_root: str, camera: str, event_name: str, media_type: str) -> Path:
        media_dir = "照片" if media_type in ("photo", "raw") else "视频"
        return (
            Path(backup_root)
            / "_Windows预览"
            / self._safe_name(camera)
            / self._safe_name(event_name)
            / media_dir
        )

    def _load_image_from_bytes(self, data: bytes) -> Optional[Image.Image]:
        try:
            return Image.open(io.BytesIO(data))
        except Exception:
            return None

    def _extract_embedded_preview(self, filepath: str) -> Optional[Image.Image]:
        """从 RAW / 特殊格式里提取嵌入预览"""
        tags = ["-PreviewImage", "-ThumbnailImage"]
        for tag in tags:
            try:
                result = subprocess.run(
                    ["exiftool", "-b", tag, filepath],
                    capture_output=True,
                    timeout=12,
                )
                if result.returncode == 0 and result.stdout:
                    img = self._load_image_from_bytes(result.stdout)
                    if img:
                        return img
            except (FileNotFoundError, subprocess.TimeoutExpired):
                break
            except Exception:
                continue
        return None

    def _fit_image(self, img: Image.Image) -> Image.Image:
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) <= self.max_size:
            return img
        ratio = self.max_size / max(w, h)
        size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        return img.resize(size, Image.LANCZOS)

    def _make_placeholder(self, filename: str, media_type: str) -> Image.Image:
        """为视频或无法解码的文件生成占位预览"""
        canvas = Image.new("RGB", (1280, 720), (15, 19, 30))
        draw = ImageDraw.Draw(canvas)

        title = "VIDEO" if media_type == "video" else "PREVIEW"
        subtitle = Path(filename).name

        # 中央图形
        cx, cy = 640, 320
        draw.ellipse((cx - 110, cy - 110, cx + 110, cy + 110), fill=(30, 41, 59), outline=(74, 222, 128), width=6)
        draw.polygon(
            [(cx - 28, cy - 50), (cx - 28, cy + 50), (cx + 48, cy)],
            fill=(74, 222, 128),
        )

        # 文本
        try:
            font_big = ImageFont.truetype("Arial.ttf", 64)
            font_mid = ImageFont.truetype("Arial.ttf", 30)
        except Exception:
            font_big = ImageFont.load_default()
            font_mid = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), title, font=font_big)
        draw.text(((1280 - (bbox[2] - bbox[0])) / 2, 80), title, fill=(232, 237, 245), font=font_big)
        bbox2 = draw.textbbox((0, 0), subtitle, font=font_mid)
        draw.text(((1280 - (bbox2[2] - bbox2[0])) / 2, 610), subtitle, fill=(148, 163, 184), font=font_mid)
        return canvas

    def _extract_video_frame(self, filepath: str) -> Optional[Image.Image]:
        """用 ffmpeg 抽取视频第一帧"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out = Path(tmpdir) / "frame.jpg"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-ss",
                        "00:00:01",
                        "-i",
                        filepath,
                        "-frames:v",
                        "1",
                        "-q:v",
                        "4",
                        str(out),
                    ],
                    capture_output=True,
                    timeout=20,
                )
                if out.exists():
                    return Image.open(out)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        except Exception:
            return None
        return None

    def _create_preview_image(self, filepath: str, media_type: str) -> Image.Image:
        """尝试为文件生成预览图"""
        try:
            img = Image.open(filepath)
            img = self._fit_image(img)
            return img
        except Exception:
            pass

        if media_type in ("photo", "raw"):
            img = self._extract_embedded_preview(filepath)
            if img:
                try:
                    return self._fit_image(img)
                except Exception:
                    pass

        if media_type == "video":
            img = self._extract_video_frame(filepath)
            if img:
                try:
                    return self._fit_image(img)
                except Exception:
                    pass

        return self._make_placeholder(filepath, media_type)

    def build_preview(self, src_path: str, backup_root: str, camera: str, event_name: str, media_type: str) -> Optional[str]:
        """生成一个预览文件，返回路径"""
        if not self.enabled:
            return None

        preview_dir = self._preview_root(backup_root, camera, event_name, media_type)
        preview_dir.mkdir(parents=True, exist_ok=True)

        src = Path(src_path)
        out_path = preview_dir / f"{src.stem}.jpg"
        idx = 1
        while out_path.exists():
            out_path = preview_dir / f"{src.stem}_{idx}.jpg"
            idx += 1

        image = self._create_preview_image(src_path, media_type)
        image.save(out_path, format="JPEG", quality=85, optimize=True)
        return str(out_path)

    def build_preview_for_path(self, final_path: str, backup_root: str, media_type: str) -> Optional[str]:
        """
        根据最终备份路径生成对应预览。
        预览树会镜像真实目录结构，只是统一放在 _Windows预览 下。
        """
        if not self.enabled:
            return None

        final = Path(final_path)
        base = Path(backup_root)
        try:
            rel_dir = final.parent.relative_to(base)
        except Exception:
            rel_dir = final.parent.name
            rel_dir = Path(rel_dir)

        preview_dir = base / "_Windows预览" / rel_dir
        preview_dir.mkdir(parents=True, exist_ok=True)

        out_path = preview_dir / f"{final.stem}.jpg"
        idx = 1
        while out_path.exists():
            out_path = preview_dir / f"{final.stem}_{idx}.jpg"
            idx += 1

        image = self._create_preview_image(str(final), media_type)
        image.save(out_path, format="JPEG", quality=85, optimize=True)
        return str(out_path)

    def build_contact_sheet(self, files: list[str], output_path: str, title: str = "") -> Optional[str]:
        """可选：生成一张拼图式总览缩略图"""
        if not files:
            return None

        thumbs = []
        for fp in files[:20]:
            try:
                img = self._create_preview_image(fp, "photo")
                img.thumbnail((320, 240), Image.LANCZOS)
                thumbs.append(img)
            except Exception:
                continue

        if not thumbs:
            return None

        cols = 4
        rows = (len(thumbs) + cols - 1) // cols
        canvas = Image.new("RGB", (cols * 340, rows * 260 + 80), (15, 19, 30))
        draw = ImageDraw.Draw(canvas)
        try:
            font = ImageFont.truetype("Arial.ttf", 40)
        except Exception:
            font = ImageFont.load_default()
        if title:
            draw.text((20, 20), title, fill=(232, 237, 245), font=font)
        for i, img in enumerate(thumbs):
            x = (i % cols) * 340 + 10
            y = (i // cols) * 260 + 70
            canvas.paste(img, (x + 10, y + 10))
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, format="JPEG", quality=85, optimize=True)
        return output_path


windows_preview = WindowsPreviewBuilder()
