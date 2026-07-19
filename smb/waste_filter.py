"""废片筛选器
────────────────
对照片做质量判断，输出可疑废片标签。

第一版策略：
- 先用本地启发式规则识别过曝、过暗、模糊、黑图、白图
- 如果启用 AI 命名后端，则额外使用 Ollama / OpenAI 兼容 API 做软废片判断
- 命中的照片不会删除，只会在备份盘里移动到“废片待确认”
"""

from __future__ import annotations

import base64
import io
import json
import math
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from .ai_namer import ai_namer


class WasteReviewer:
    """照片废片筛选器"""

    HARD_LABELS = {"过曝", "过暗", "模糊", "黑图", "白图"}
    SOFT_LABELS = {"闭眼", "主体被挡", "构图差", "重复"}
    WASTE_LABELS = HARD_LABELS | SOFT_LABELS

    def __init__(self):
        pass

    def _safe_name(self, value: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\s]+', "_", value or "").strip("_")
        return cleaned or "event"

    def _prepare_image(self, filepath: str, max_size: int = 960) -> Optional[str]:
        """将图片缩放并编码为 base64，供 AI 调用"""
        try:
            from PIL import Image

            img = Image.open(filepath)
            if img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size
            if max(w, h) > max_size:
                ratio = max_size / max(w, h)
                img = img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))), Image.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=72)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[废片筛选] 图片准备失败 {filepath}: {e}")
            return None

    def _heuristic_review(self, filepath: str) -> dict:
        """基于亮度/对比度/锐度的启发式判断"""
        try:
            from PIL import Image
        except ImportError:
            return {"label": "正常", "confidence": 0.0, "reason": "缺少 Pillow，跳过启发式分析", "source": "heuristic"}

        try:
            img = Image.open(filepath).convert("RGB")
        except Exception as e:
            return {"label": "正常", "confidence": 0.0, "reason": f"无法打开图片: {e}", "source": "heuristic"}

        # 缩小后做分析，兼顾速度
        img = img.resize((96, 96), Image.LANCZOS)
        gray = img.convert("L")
        pixels = list(gray.getdata())
        if not pixels:
            return {"label": "正常", "confidence": 0.0, "reason": "空图像", "source": "heuristic"}

        n = len(pixels)
        mean = sum(pixels) / n
        var = sum((p - mean) ** 2 for p in pixels) / n
        std = math.sqrt(var)

        dark_ratio = sum(1 for p in pixels if p < 40) / n
        bright_ratio = sum(1 for p in pixels if p > 220) / n
        black_ratio = sum(1 for p in pixels if p < 10) / n
        white_ratio = sum(1 for p in pixels if p > 245) / n

        # 简单锐度：相邻像素差分均值
        width, height = gray.size
        diff_sum = 0.0
        diff_count = 0
        for y in range(height):
            row = y * width
            for x in range(width - 1):
                diff_sum += abs(pixels[row + x] - pixels[row + x + 1])
                diff_count += 1
        for y in range(height - 1):
            row = y * width
            next_row = (y + 1) * width
            for x in range(width):
                diff_sum += abs(pixels[row + x] - pixels[next_row + x])
                diff_count += 1
        sharpness = diff_sum / diff_count if diff_count else 0.0

        label = "正常"
        confidence = 0.0
        reason = "画面质量正常"

        if mean < 18 and black_ratio > 0.5:
            label = "黑图"
            confidence = 0.95
            reason = "几乎全黑，疑似盖镜头或误拍"
        elif mean > 240 and white_ratio > 0.5:
            label = "白图"
            confidence = 0.95
            reason = "几乎全白，疑似过曝或误拍"
        elif mean < 42 and dark_ratio > 0.68:
            label = "过暗"
            confidence = 0.88
            reason = "整体亮度过低"
        elif mean > 220 and bright_ratio > 0.6:
            label = "过曝"
            confidence = 0.88
            reason = "整体亮度过高"
        elif std < 6 and 20 < mean < 235:
            label = "构图差"
            confidence = 0.6
            reason = "画面纹理过少，信息量偏低"
        elif sharpness < 3.0 and std < 15:
            label = "模糊"
            confidence = 0.82
            reason = "边缘变化很弱，疑似模糊或失焦"

        return {
            "label": label,
            "confidence": confidence,
            "reason": reason,
            "source": "heuristic",
            "metrics": {
                "mean": round(mean, 2),
                "std": round(std, 2),
                "dark_ratio": round(dark_ratio, 3),
                "bright_ratio": round(bright_ratio, 3),
                "sharpness": round(sharpness, 2),
            },
        }

    def _parse_ai_reply(self, reply: str) -> dict:
        """尽量把 AI 回复规整成标签结果"""
        reply = (reply or "").strip()
        if not reply:
            return {}

        # 优先解析 JSON
        try:
            data = json.loads(reply)
            if isinstance(data, dict):
                label = str(data.get("label", "")).strip()
                if label:
                    return {
                        "label": self._normalize_label(label),
                        "confidence": float(data.get("confidence", 0.7) or 0.7),
                        "reason": str(data.get("reason", "")).strip() or "AI 判断",
                        "source": "ai",
                    }
        except Exception:
            pass

        # 兜底：关键词解析
        label = "正常"
        for candidate in ["过曝", "过暗", "模糊", "闭眼", "主体被挡", "构图差", "重复", "黑图", "白图"]:
            if candidate in reply:
                label = candidate
                break

        confidence = 0.75 if label != "正常" else 0.5
        return {
            "label": label,
            "confidence": confidence,
            "reason": reply[:120],
            "source": "ai",
        }

    def _normalize_label(self, label: str) -> str:
        label = label.strip()
        mapping = {
            "过度曝光": "过曝",
            "欠曝": "过暗",
            "过暗": "过暗",
            "曝光过度": "过曝",
            "模糊不清": "模糊",
            "失焦": "模糊",
            "构图不好": "构图差",
            "闭眼睛": "闭眼",
            "遮挡": "主体被挡",
        }
        return mapping.get(label, label if label else "正常")

    def _ai_review(self, filepath: str) -> Optional[dict]:
        """使用现有 AI 后端做软废片判断"""
        if not ai_namer.is_enabled():
            return None

        image_b64 = self._prepare_image(filepath)
        if not image_b64:
            return None

        prompt = (
            "请判断这张照片是否属于废片。"
            "可选标签只有这些：正常、过曝、过暗、模糊、闭眼、主体被挡、构图差、重复、黑图、白图。"
            "如果判断为废片，请返回最贴切的单一标签。"
            "请严格输出 JSON，格式为："
            "{\"label\":\"...\",\"confidence\":0.0-1.0,\"reason\":\"...\"}。"
            "不要输出多余解释。"
        )

        try:
            if ai_namer.backend == "ollama":
                try:
                    import requests
                except ImportError:
                    return None

                resp = requests.post(
                    f"{ai_namer.ollama_url}/api/chat",
                    json={
                        "model": ai_namer.ollama_model,
                        "messages": [{
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64],
                        }],
                        "stream": False,
                    },
                    timeout=35,
                )
                data = resp.json()
                reply = data.get("message", {}).get("content", "")
                result = self._parse_ai_reply(reply)
                if result:
                    result["source"] = "ai"
                    return result

            elif ai_namer.backend == "openai":
                if not ai_namer.openai_key:
                    return None
                try:
                    from openai import OpenAI
                except ImportError:
                    return None

                client = OpenAI(api_key=ai_namer.openai_key, base_url=ai_namer.openai_base)
                content = [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "low"},
                    },
                ]
                resp = client.chat.completions.create(
                    model=ai_namer.openai_model,
                    messages=[{"role": "user", "content": content}],
                    max_tokens=120,
                    timeout=35,
                )
                reply = resp.choices[0].message.content or ""
                result = self._parse_ai_reply(reply)
                if result:
                    result["source"] = "ai"
                    return result
        except Exception as e:
            if "No module named" not in str(e):
                print(f"[废片筛选] AI 识别失败 {filepath}: {e}")

        return None

    def review(self, filepath: str) -> dict:
        """综合 AI + 启发式判断，返回最终结果"""
        heuristic = self._heuristic_review(filepath)
        ai_result = self._ai_review(filepath)

        # 先信硬规则；如果 AI 明确给出废片标签，也可覆盖
        final = heuristic
        if ai_result and ai_result.get("label") in self.WASTE_LABELS:
            if ai_result.get("confidence", 0.0) >= 0.6:
                final = ai_result

        final["label"] = self._normalize_label(final.get("label", "正常"))
        if final["label"] not in self.WASTE_LABELS:
            final["label"] = "正常"
            final["confidence"] = max(float(final.get("confidence", 0.0)), 0.2)

        if final["label"] == "正常":
            final["reason"] = final.get("reason") or "未发现明显废片特征"

        return final

    def move_to_review_folder(
        self,
        src_path: str,
        review_root: str,
        label: str,
        media_type: str,
    ) -> str:
        """把废片移动到待确认目录，返回新路径"""
        label_clean = self._safe_name(label)
        media_dir = "照片" if media_type in ("photo", "raw") else "视频"
        dst_dir = Path(review_root) / "废片待确认" / label_clean / media_dir
        dst_dir.mkdir(parents=True, exist_ok=True)

        src = Path(src_path)
        dst = dst_dir / src.name
        idx = 1
        while dst.exists():
            dst = dst_dir / f"{src.stem}_{idx}{src.suffix}"
            idx += 1

        shutil.move(str(src), str(dst))
        return str(dst)


waste_reviewer = WasteReviewer()
