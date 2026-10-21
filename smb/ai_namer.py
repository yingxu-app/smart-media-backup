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
import sys
from typing import Optional
from pathlib import Path

from .config import CONFIG_DIR

AI_SETTINGS_PATH = CONFIG_DIR / "ai_settings.json"
AI_KEYRING_SERVICE = "com.yingxuapp.smartmediabackup.ai"
CLOUD_PROVIDER_PRESETS = {
    "qwen": {
        "model": "qwen3-vl-flash",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "deepseek": {
        "model": "deepseek-flash",
        "base_url": "https://api.deepseek.com",
    },
    "openrouter": {
        "model": "openrouter/free",
        "base_url": "https://openrouter.ai/api/v1",
    },
}


def _safe_console_print(message: str) -> None:
    """Keep optional AI diagnostics from failing under legacy Windows code pages."""
    stream = sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    try:
        stream.write(message + "\n")
    except UnicodeEncodeError:
        safe_message = message.encode(encoding, errors="backslashreplace").decode(encoding)
        stream.write(safe_message + "\n")


class AINamer:
    """AI 内容识别命名器"""

    def __init__(self):
        # 默认完全离线。AI 是可选的命名建议，不能拖慢插卡扫描或成为依赖。
        self.backend = "disabled"     # "ollama" | "openai" | "disabled"
        self.ollama_model = "llava"   # Ollama 视觉模型
        self.ollama_url = "http://localhost:11434"
        self.openai_key = ""
        self.openai_model = "qwen3-vl-flash"
        self.openai_base = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.cloud_provider = "qwen"
        self.cloud_key_providers = set()
        self._load()

    def _load(self):
        if AI_SETTINGS_PATH.exists():
            try:
                d = json.loads(AI_SETTINGS_PATH.read_text(encoding="utf-8"))
                self.backend = d.get("backend", "disabled")
                self.ollama_model = d.get("ollama_model", "llava")
                self.ollama_url = d.get("ollama_url", "http://localhost:11434")
                legacy_key = d.get("openai_key", "")
                configured_base = str(d.get("openai_base", "https://api.openai.com/v1")).lower()
                inferred_provider = (
                    "qwen" if "dashscope" in configured_base else
                    "deepseek" if "deepseek" in configured_base else
                    "openrouter" if "openrouter" in configured_base else "custom"
                )
                configured_provider = d.get("cloud_provider", inferred_provider)
                # Keep old custom credentials available for migration, but new setup
                # is intentionally limited to the three supported product providers.
                provider_is_supported = configured_provider in CLOUD_PROVIDER_PRESETS
                self.cloud_provider = configured_provider if provider_is_supported else "qwen"
                self.openai_base = CLOUD_PROVIDER_PRESETS[self.cloud_provider]["base_url"]
                self.openai_model = (
                    d.get("openai_model") or CLOUD_PROVIDER_PRESETS[self.cloud_provider]["model"]
                    if provider_is_supported else CLOUD_PROVIDER_PRESETS["qwen"]["model"]
                )
                self.cloud_key_providers = set(d.get("cloud_key_providers", []))
                legacy_keys = d.get("cloud_keys", {})
                if not isinstance(legacy_keys, dict):
                    legacy_keys = {}
                if legacy_key:
                    legacy_key_provider = configured_provider if provider_is_supported else inferred_provider
                    legacy_keys.setdefault(legacy_key_provider, legacy_key)
                migrated_keys = False
                migration_failed = False
                for provider, key in legacy_keys.items():
                    if not key:
                        continue
                    if provider not in {"qwen", "deepseek", "openrouter", "custom"}:
                        migration_failed = True
                        continue
                    try:
                        self._keyring().set_password(AI_KEYRING_SERVICE, provider, key)
                        self.cloud_key_providers.add(provider)
                        migrated_keys = True
                    except Exception:
                        # Keep the legacy file intact until every key is safely stored.
                        migration_failed = True
                        if provider == self.cloud_provider:
                            self.openai_key = key
                self.openai_key = self.get_cloud_key(self.cloud_provider) or self.openai_key
                if self.openai_key:
                    self.cloud_key_providers.add(self.cloud_provider)
                if migrated_keys and not migration_failed:
                    # Remove migrated credentials from the old plaintext JSON config.
                    d.pop("openai_key", None)
                    d.pop("cloud_keys", None)
                    d["cloud_key_providers"] = sorted(self.cloud_key_providers)
                    AI_SETTINGS_PATH.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if self.openai_key:
            self.set_cloud_key(self.cloud_provider, self.openai_key)
        AI_SETTINGS_PATH.write_text(json.dumps({
            "backend": self.backend,
            "ollama_model": self.ollama_model,
            "ollama_url": self.ollama_url,
            "openai_model": self.openai_model,
            "openai_base": self.openai_base,
            "cloud_provider": self.cloud_provider,
            "cloud_key_providers": sorted(self.cloud_key_providers),
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _keyring():
        import keyring
        return keyring

    def get_cloud_key(self, provider: str) -> str:
        try:
            return self._keyring().get_password(AI_KEYRING_SERVICE, provider) or ""
        except Exception:
            return ""

    def set_cloud_key(self, provider: str, key: str) -> None:
        if not key:
            return
        self._keyring().set_password(AI_KEYRING_SERVICE, provider, key)
        self.cloud_key_providers.add(provider)

    def use_cloud_provider(self, provider: str) -> None:
        if provider not in CLOUD_PROVIDER_PRESETS:
            raise ValueError("不支持的云端模型服务")
        self.cloud_provider = provider
        self.openai_key = self.get_cloud_key(provider)
        if self.openai_key:
            self.cloud_key_providers.add(provider)
        self.openai_base = CLOUD_PROVIDER_PRESETS[provider]["base_url"]
        self.openai_model = CLOUD_PROVIDER_PRESETS[provider]["model"]

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
            _safe_console_print(f"[AI命名] 图片处理失败 {filepath}: {e}")
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
                _safe_console_print(f"[AI命名] Ollama 请求失败: {e}")
                continue

        return None

    def _analyze_openai(self, images: list[str]) -> Optional[str]:
        """用 OpenAI 兼容 API 分析"""
        if not self.openai_key:
            return None

        try:
            from openai import OpenAI
        except ImportError:
            _safe_console_print("[AI命名] 需要安装 openai 包: pip install openai")
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
            _safe_console_print(f"[AI命名] OpenAI 请求失败: {e}")

        return None

    def test_cloud_vision(self) -> None:
        """Test auth and image input with a generated 1x1 image, never user media."""
        if not self.openai_key:
            raise ValueError("请先在设置中保存此服务的 API Key")
        try:
            from openai import OpenAI
            from PIL import Image
            import io
        except ImportError as exc:
            raise RuntimeError("缺少云端视觉调用依赖，请更新影序安装包") from exc

        image = Image.new("RGB", (1, 1), color=(0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
        client = OpenAI(api_key=self.openai_key, base_url=self.openai_base)
        response = client.chat.completions.create(
            model=self.openai_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "This is an API connection test. Reply only OK."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "low"}},
                ],
            }],
            max_tokens=8,
            timeout=25,
        )
        if not response.choices or not (response.choices[0].message.content or "").strip():
            raise RuntimeError("服务已响应，但模型没有返回内容")


# 全局单例
ai_namer = AINamer()
