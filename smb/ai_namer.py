"""
AI 内容识别命名模块
──────────────────
自动分析照片/视频内容，生成事件文件夹名建议。
支持本地 Ollama 或云端 OpenAI 兼容 API。
"""

import os
import json
import base64
import threading
from typing import Optional
from pathlib import Path

from .config import CONFIG_DIR

AI_SETTINGS_PATH = CONFIG_DIR / "ai_settings.json"


class AINamer:
    """AI 内容识别命名器"""

    def __init__(self):
        # AI is opt-in: a fresh install must never make background network
        # requests or print connection errors before the user configures it.
        self.backend = "disabled"     # "ollama" | "openai" | "disabled"
        self.ollama_model = "llava"   # Ollama 视觉模型
        self.ollama_url = "http://localhost:11434"
        self.openai_key = ""
        self.openai_model = "gpt-4o-mini"
        self.openai_base = "https://api.openai.com/v1"
        self._load()

    def _load(self):
        if AI_SETTINGS_PATH.exists():
            try:
                d = json.loads(AI_SETTINGS_PATH.read_text())
                self.backend = d.get("backend", "disabled")
                self.ollama_model = d.get("ollama_model", "llava")
                self.ollama_url = d.get("ollama_url", "http://localhost:11434")
                self.openai_key = d.get("openai_key", "")
                self.openai_model = d.get("openai_model", "gpt-4o-mini")
                self.openai_base = d.get("openai_base", "https://api.openai.com/v1")
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        AI_SETTINGS_PATH.write_text(json.dumps({
            "backend": self.backend,
            "ollama_model": self.ollama_model,
            "ollama_url": self.ollama_url,
            "openai_key": self.openai_key,
            "openai_model": self.openai_model,
            "openai_base": self.openai_base,
        }, indent=2, ensure_ascii=False))

    def is_enabled(self) -> bool:
        return self.backend != "disabled"

    def suggest_event_name(self, sample_images: list[str]) -> Optional[str]:
        """
        分析样张图片，返回建议的事件名。
        sample_images: 待分析的图片路径列表（取前 3 张）
        """
        if not self.is_enabled() or not sample_images:
            return None

        # 取前 3 张
        images = sample_images[:3]
        image_count = len(images)

        if self.backend == "ollama":
            return self._analyze_ollama(images)
        elif self.backend == "openai":
            return self._analyze_openai(images)
        return None

    def _prepare_image(self, filepath: str, max_size: int = 800) -> Optional[str]:
        """读取图片并压缩为 base64（小图）"""
        try:
            from PIL import Image
            import io
            img = Image.open(filepath)
            # 转 RGB
            if img.mode != "RGB":
                img = img.convert("RGB")
            # 缩放到最大边长
            w, h = img.size
            if max(w, h) > max_size:
                ratio = max_size / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[AI命名] 图片处理失败 {filepath}: {e}")
            return None

    def _build_prompt(self, image_count: int) -> str:
        if image_count == 1:
            return (
                "看这张照片，用一个中文短语（2-6个字）描述这是什么活动/场景。"
                "例如：'漫展'、'婚礼'、'航拍'、'海边日落'、'产品拍摄'、'聚会'。"
                "只输出短语本身，不要解释。"
            )
        return (
            f"看这 {image_count} 张照片，它们来自同一个 SD 卡，属于同一次拍摄活动。"
            "用一个中文短语（2-6个字）概括这是什么活动。"
            "例如：'2025漫展'、'海边婚礼'、'城市航拍'、'产品静物'。"
            "只输出短语本身，不要解释。"
        )

    def _analyze_ollama(self, images: list[str]) -> Optional[str]:
        """用本地 Ollama 视觉模型分析"""
        import requests

        prompt = self._build_prompt(len(images))

        for img_path in images:
            b64 = self._prepare_image(img_path)
            if not b64:
                continue

            try:
                resp = requests.post(
                    f"{self.ollama_url}/api/chat",
                    json={
                        "model": self.ollama_model,
                        "messages": [{
                            "role": "user",
                            "content": prompt,
                            "images": [b64],
                        }],
                        "stream": False,
                    },
                    timeout=30,
                )
                data = resp.json()
                reply = data.get("message", {}).get("content", "").strip()
                if reply:
                    # 清理可能的多余字符
                    reply = reply.strip('"').strip("'").strip()
                    if len(reply) <= 20:
                        return reply
            except Exception as e:
                print(f"[AI命名] Ollama 请求失败: {e}")
                continue

        return None

    def _analyze_openai(self, images: list[str]) -> Optional[str]:
        """用 OpenAI 兼容 API 分析"""
        if not self.openai_key:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            print("[AI命名] 需要安装 openai 包: pip install openai")
            return None

        client = OpenAI(
            api_key=self.openai_key,
            base_url=self.openai_base,
        )

        prompt = self._build_prompt(len(images))
        content = [{"type": "text", "text": prompt}]

        for img_path in images[:2]:  # OpenAI 限 2 张
            b64 = self._prepare_image(img_path)
            if b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "low"},
                })

        try:
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": content}],
                max_tokens=20,
                timeout=30,
            )
            reply = resp.choices[0].message.content.strip().strip('"').strip("'")
            if reply and len(reply) <= 20:
                return reply
        except Exception as e:
            print(f"[AI命名] OpenAI 请求失败: {e}")

        return None


# 全局单例
ai_namer = AINamer()
