"""配置升级与原子保存回归测试。"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from smb import config as config_module


class ConfigMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_config_dir = config_module.CONFIG_DIR
        self.old_config_file = config_module.CONFIG_FILE
        self.old_schema_file = config_module.CONFIG_SCHEMA_FILE
        config_module.CONFIG_DIR = self.root
        config_module.CONFIG_FILE = self.root / "config.json"
        config_module.CONFIG_SCHEMA_FILE = self.root / "config.schema.json"

    def tearDown(self):
        config_module.CONFIG_DIR = self.old_config_dir
        config_module.CONFIG_FILE = self.old_config_file
        config_module.CONFIG_SCHEMA_FILE = self.old_schema_file
        self.temp.cleanup()

    def _write(self, data):
        config_module.CONFIG_FILE.write_text(json.dumps(data), encoding="utf-8")

    def test_v1_config_migrates_pocket_defaults_without_eager_write(self):
        legacy = {
            "backup_root": "/Volumes/Archive",
            "last_backup_root": "/Volumes/Archive",
            "auto_open_browser": False,
            "raw_extensions": [".arw"],
            "photo_extensions": [".jpg"],
            "video_extensions": [".mp4"],
            "audio_extensions": [".wav"],
            "max_speed_mbps": 80,
            "webhook_url": "https://example.invalid/hook",
            "phash_threshold": 7,
            "dark_mode": False,
            "backup_targets": ["/Volumes/Archive", "/Volumes/Second"],
            "sort_order": ["device", "event", "type"],
            "verify_method": "sha256",
            "web_host": "127.0.0.1",
            "web_port": 8080,
            "mount_points": ["/Volumes"],
        }
        self._write(legacy)
        original = config_module.CONFIG_FILE.read_bytes()

        config = config_module.AppConfig.load()

        self.assertEqual(config.pocket_enabled, True)
        self.assertEqual(config.pocket_session_hours, 12)
        self.assertFalse(config.pocket_tcp_enabled)
        self.assertEqual(config.backup_targets, legacy["backup_targets"])
        self.assertEqual(config.max_speed_mbps, 80)
        self.assertEqual(config_module.CONFIG_FILE.read_bytes(), original)
        self.assertFalse(config_module.CONFIG_SCHEMA_FILE.exists())

    def test_migrated_config_round_trips_with_current_schema(self):
        self._write({"backup_root": "/Volumes/Archive"})

        config = config_module.AppConfig.load()
        config.pocket_enabled = False
        config.pocket_session_hours = 6
        config.pocket_tcp_enabled = True
        config.save()
        reloaded = config_module.AppConfig.load()

        self.assertFalse(reloaded.pocket_enabled)
        self.assertEqual(reloaded.pocket_session_hours, 6)
        self.assertTrue(reloaded.pocket_tcp_enabled)
        self.assertEqual(reloaded.backup_root, "/Volumes/Archive")
        saved_config = json.loads(config_module.CONFIG_FILE.read_text(encoding="utf-8"))
        self.assertNotIn("schema_version", saved_config)
        self.assertEqual(
            json.loads(config_module.CONFIG_SCHEMA_FILE.read_text(encoding="utf-8")),
            {"schema_version": 3},
        )
        # Released v1.0.34 reads config.json directly; keep its fields backward compatible.
        self.assertIn("pocket_enabled", saved_config)
        self.assertIn("pocket_session_hours", saved_config)

    def test_v2_config_adds_firebase_project_fields_without_credentials(self):
        self._write({"backup_root": "/Volumes/Archive", "pocket_tcp_enabled": False})
        config_module.CONFIG_SCHEMA_FILE.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")

        migrated = config_module.AppConfig.load()

        self.assertEqual(migrated.firebase_api_key, "")
        self.assertEqual(migrated.firebase_database_url, "")
        self.assertEqual(migrated.firebase_email, "")
        self.assertEqual(migrated.firebase_uid, "")
        self.assertTrue(migrated.firebase_device_id.startswith("desktop-"))

    def test_failed_atomic_replace_keeps_existing_config_and_cleans_temp_file(self):
        self._write({"backup_root": "/Volumes/Old"})
        original = config_module.CONFIG_FILE.read_bytes()
        config = config_module.AppConfig(backup_root="/Volumes/New")

        with mock.patch.object(config_module.os, "replace", side_effect=OSError("disk error")):
            with self.assertRaisesRegex(OSError, "disk error"):
                config.save()

        self.assertEqual(config_module.CONFIG_FILE.read_bytes(), original)
        self.assertEqual(list(self.root.glob("config.json.*.tmp")), [])

    def test_newer_schema_is_rejected_without_modifying_file(self):
        self._write({"backup_root": "/Volumes/Newer"})
        config_module.CONFIG_SCHEMA_FILE.write_text(
            json.dumps({"schema_version": 99}), encoding="utf-8"
        )
        original = config_module.CONFIG_FILE.read_bytes()
        original_schema = config_module.CONFIG_SCHEMA_FILE.read_bytes()

        with self.assertRaisesRegex(ValueError, "更新版本创建"):
            config_module.AppConfig.load()

        self.assertEqual(config_module.CONFIG_FILE.read_bytes(), original)
        self.assertEqual(config_module.CONFIG_SCHEMA_FILE.read_bytes(), original_schema)

    def test_reset_removes_config_and_schema_sidecar(self):
        self._write({"backup_root": "/Volumes/Archive"})
        config_module.CONFIG_SCHEMA_FILE.write_text(
            json.dumps({"schema_version": 3}), encoding="utf-8"
        )

        config_module.AppConfig.reset()

        self.assertFalse(config_module.CONFIG_FILE.exists())
        self.assertFalse(config_module.CONFIG_SCHEMA_FILE.exists())

    def test_non_object_json_is_rejected(self):
        config_module.CONFIG_FILE.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "JSON 对象"):
            config_module.AppConfig.load()


if __name__ == "__main__":
    unittest.main()
