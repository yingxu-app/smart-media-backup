"""系统配置管理"""
import json
import os
import tempfile
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path(os.environ.get("SMB_CONFIG_DIR", "~/.config/smb")).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_SCHEMA_FILE = CONFIG_DIR / "config.schema.json"
DB_PATH = CONFIG_DIR / "backup_history.db"
CONFIG_SCHEMA_VERSION = 2


def _migrate_config_v1_to_v2(data: dict) -> dict:
    """为增加 Pocket 的旧配置补齐安全默认值。"""
    migrated = dict(data)
    migrated.setdefault("pocket_enabled", True)
    migrated.setdefault("pocket_session_hours", 12)
    return migrated


_CONFIG_MIGRATIONS = {
    1: _migrate_config_v1_to_v2,
}


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

    # === 速度限制 ===
    max_speed_mbps: int = 0               # 0 = 不限速

    # === 通知推送 ===
    webhook_url: str = ""

    # === 感知哈希去重 ===
    phash_threshold: int = 8              # 0=关闭, 1-20敏感度

    # === 亮色主题 ===
    dark_mode: bool = True

    # === 多目标备份 ===
    backup_targets: list = field(default_factory=list)

    # === 目录层级顺序 ===
    sort_order: list = field(default_factory=lambda: ["device", "event", "type"])

    # === 校验 ===
    verify_method: str = "sha256"     # "sha256" | "skip"

    # === Web 服务 ===
    web_host: str = "127.0.0.1"
    web_port: int = 8080

    # === 影序 Pocket（同一局域网内的手机协作页） ===
    pocket_enabled: bool = True
    pocket_session_hours: int = 12

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
        _atomic_write_json(CONFIG_FILE, asdict(self))
        # Keep schema metadata separate so older released apps ignore it instead of
        # rejecting an otherwise compatible config.json with an unknown field.
        _atomic_write_json(CONFIG_SCHEMA_FILE, {"schema_version": CONFIG_SCHEMA_VERSION})
        return self

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("影序配置文件必须是 JSON 对象")
            # A schema marker was briefly used in an unreleased draft. Ignore it
            # during migration and keep the supported on-disk config backward compatible.
            data.pop("schema_version", None)
            version = 1
            if CONFIG_SCHEMA_FILE.exists():
                metadata = json.loads(CONFIG_SCHEMA_FILE.read_text(encoding="utf-8"))
                if not isinstance(metadata, dict):
                    raise ValueError("影序配置版本文件必须是 JSON 对象")
                version = metadata.get("schema_version", 1)
                if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                    raise ValueError("影序配置版本号无效")
            if version > CONFIG_SCHEMA_VERSION:
                raise ValueError(
                    f"配置由更新版本创建（schema {version}），当前版本最多支持 {CONFIG_SCHEMA_VERSION}；"
                    "为避免覆盖新设置，未加载或修改该文件"
                )
            while version < CONFIG_SCHEMA_VERSION:
                migrate = _CONFIG_MIGRATIONS.get(version)
                if migrate is None:
                    raise ValueError(f"没有从配置版本 {version} 升级的迁移规则")
                data = migrate(data)
                version += 1
            return cls(**data)
        return cls()

    @classmethod
    def reset(cls) -> "AppConfig":
        for path in (CONFIG_FILE, CONFIG_SCHEMA_FILE):
            if path.exists():
                path.unlink()
        return cls()


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix=f"{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass


config: AppConfig = AppConfig.load()
