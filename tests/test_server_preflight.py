"""开始备份前的安全拦截测试：无卡、目标不可写、空间不足。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


TEST_ROOT = tempfile.TemporaryDirectory()
os.environ["SMB_CONFIG_DIR"] = str(Path(TEST_ROOT.name) / "config")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smb import server  # noqa: E402


class StartBackupPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sd = self.root / "SDCARD"
        self.target = self.root / "ARCHIVE"
        self.sd.mkdir()
        self.target.mkdir()
        server.app.config["TESTING"] = True
        server.engine.progress.status = "idle"
        self.original_settings = (
            server.config.web_port, server.config.auto_open_browser, server.config.verify_method,
        )

    def tearDown(self):
        server.config.web_port, server.config.auto_open_browser, server.config.verify_method = self.original_settings
        self.tmp.cleanup()

    def post(self, mount=None):
        return server.app.test_client().post("/api/start_backup", json={
            "mount_point": mount or str(self.sd), "event_name": "test",
            "backup_root": str(self.target),
        })

    def test_missing_sd_card_is_explained(self):
        response = self.post(str(self.root / "missing-card"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("未检测到 SD 卡", response.get_json()["error"])

    def test_unwritable_target_is_blocked_before_copy(self):
        with patch.object(server.os, "access", return_value=False), patch(
            "smb.organizer.scan_sd_card", return_value=[]
        ):
            response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertIn("不可写", response.get_json()["error"])

    def test_full_target_is_blocked_before_copy(self):
        media = [{"size": 1024 * 1024, "path": "DCIM/clip.jpg"}]
        tiny_disk = SimpleNamespace(f_bavail=1, f_frsize=1)
        with patch("smb.organizer.scan_sd_card", return_value=media), patch.object(
            server.os, "statvfs", return_value=tiny_disk
        ):
            response = self.post()
        payload = response.get_json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("空间不足", payload["error"])
        self.assertGreater(payload["required_bytes"], payload["free_bytes"])

    def test_settings_are_saved_to_the_app_not_only_the_browser(self):
        response = server.app.test_client().post("/api/settings", json={
            "web_port": 9090, "auto_open_browser": False, "verify_method": "skip",
        })
        self.assertEqual(response.status_code, 200)
        settings = server.app.test_client().get("/api/settings").get_json()
        self.assertEqual(settings["web_port"], 9090)
        self.assertFalse(settings["auto_open_browser"])
        self.assertEqual(settings["verify_method"], "skip")
        status = server.app.test_client().get("/api/status").get_json()
        self.assertEqual(status["version"], "1.0.10")


if __name__ == "__main__":
    unittest.main()
