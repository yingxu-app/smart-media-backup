"""系统配置管理"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path(os.environ.get("SMB_CONFIG_DIR", "~/.config/smb")).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"
DB_PATH = CONFIG_DIR / "backup_history.db"


@dataclass
class AppConfig:
    # === 备份设置 ===
    backup_root: str = ""
    last_backup_root: str = ""       # 记住上次选的盘
    auto_open_browser: bool = True

    # === 文件检测 ===
    raw_extensions: list = field(default_factory=lambda: [
        ".arw", ".cr2", ".cr3", ".nef", ".nrw",
        ".dng", ".orf", ".rw2", ".raf", ".srw",
        ".x3f", ".3fr", ".fff", ".mef", ".mos",
    ])
    photo_extensions: list = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".tiff", ".tif",
        ".gif", ".bmp", ".webp", ".heic", ".heif",
    ])
    video_extensions: list = field(default_factory=lambda: [
        ".mp4", ".mov", ".avi", ".mxf", ".braw",
        ".mpg", ".mts", ".m2ts", ".insv", ".webm",
        ".mkv", ".wmv", ".flv", ".3gp",
    ])
    audio_extensions: list = field(default_factory=lambda: [
        ".wav", ".aac", ".mp3", ".flac", ".ogg", ".wma",
    ])

    # === 多目标备份 ===
    backup_targets: list = field(default_factory=list)

    # === 校验 ===
    verify_method: str = "sha256"     # "sha256" | "skip"

    # === Web 服务 ===
    web_host: str = "127.0.0.1"
    web_port: int = 8080

    # === 扫描目录（平台自动探测） ===
    mount_points: list = field(default_factory=lambda: [
        "/media", "/mnt", "/run/media", "/media/pi", "/Volumes",
    ])

    def __post_init__(self):
        pass

    @property
    def all_media_extensions(self) -> list:
        return self.raw_extensions + self.photo_extensions + self.video_extensions + self.audio_extensions

    @property
    def photo_extensions_all(self) -> list:
        return self.raw_extensions + self.photo_extensions

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items()}
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return self

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            return cls(**data)
        return cls()

    @classmethod
    def reset(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        return cls()


config: AppConfig = AppConfig.load()
