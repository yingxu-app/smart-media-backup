"""Windows 平台安全回归：清理原卡必须可恢复，备份启动失败必须可见。

这两条都是 Windows 实机验收时暴露的问题：
1. /api/cleanup_sd 在非 macOS 分支用 os.remove 永久删除原卡素材，而 macOS 走
   Finder 废纸篓；产品对用户的承诺是"清理"可恢复，Windows 上却是不可逆硬删。
2. /api/start_backup 校验失败统一返回 HTTP 200，前端又完全不读响应，导致来源
   缺失时界面直接停在 0% 进度面板，用户看不到任何原因。
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from smb import db
from smb import server
from smb import config as config_module


class StartBackupErrorVisibilityTests(unittest.TestCase):
    """备份启动失败必须通过 HTTP 状态码暴露，不能伪装成 200。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_db_path = db.DB_PATH
        self.old_config_dir = config_module.CONFIG_DIR
        db.DB_PATH = self.root / "history.db"
        config_module.CONFIG_DIR = self.root / "config"
        config_module.CONFIG_DIR.mkdir(parents=True)
        db.init_db()
        self.old_status = server.engine.progress.status
        server.engine.progress.status = "idle"
        server.app.config.update(TESTING=True)
        self.client = server.app.test_client()

    def tearDown(self):
        server.engine.progress.status = self.old_status
        db.DB_PATH = self.old_db_path
        config_module.CONFIG_DIR = self.old_config_dir
        self.temp.cleanup()

    def test_missing_backup_target_returns_400(self):
        with mock.patch.object(server, "list_removable_volumes", return_value=[]):
            response = self.client.post("/api/start_backup", json={"mount_point": "", "event_name": "x"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("备份目标", response.get_json()["error"])

    def test_missing_source_card_returns_400(self):
        with mock.patch.object(server, "list_removable_volumes", return_value=[]):
            response = self.client.post(
                "/api/start_backup",
                json={"mount_point": "", "event_name": "x", "backup_root": str(self.root / "target")},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("SD 卡", response.get_json()["error"])

    def test_busy_engine_returns_409(self):
        self.old_status = "copying"
        server.engine.progress.status = "copying"
        response = self.client.post(
            "/api/start_backup",
            json={"mount_point": str(self.root), "event_name": "x", "backup_root": str(self.root)},
        )
        self.assertEqual(response.status_code, 409)

    def test_dashboard_surfaces_start_failure_to_user(self):
        """前端必须检查响应，否则失败会表现为"永远停在 0%"。"""
        dashboard = (
            Path(__file__).resolve().parents[1] / "smb" / "templates" / "dashboard.html"
        ).read_text(encoding="utf-8")
        self.assertIn("backupStartFailed", dashboard)
        self.assertIn("if(!r.ok||d.error)", dashboard)


class CleanupSafetyTests(unittest.TestCase):
    """清理原卡在任何平台都不得变成不可逆的永久删除。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.card = self.root / "card"
        (self.card / "DCIM").mkdir(parents=True)
        (self.card / "DCIM" / "DSC0001.JPG").write_bytes(b"photo")
        (self.card / "DCIM" / "C0001.MP4").write_bytes(b"video")
        self.old_db_path = db.DB_PATH
        self.old_config_dir = config_module.CONFIG_DIR
        db.DB_PATH = self.root / "history.db"
        config_module.CONFIG_DIR = self.root / "config"
        config_module.CONFIG_DIR.mkdir(parents=True)
        db.init_db()
        self.old_mount = server.engine.progress.mount_point
        self.old_can_cleanup = server.engine.progress.can_cleanup
        server.engine.progress.mount_point = str(self.card)
        server.engine.progress.can_cleanup = True
        server.app.config.update(TESTING=True)
        self.client = server.app.test_client()

    def tearDown(self):
        server.engine.progress.mount_point = self.old_mount
        server.engine.progress.can_cleanup = self.old_can_cleanup
        db.DB_PATH = self.old_db_path
        config_module.CONFIG_DIR = self.old_config_dir
        self.temp.cleanup()

    def test_cleanup_refused_before_backup_completes(self):
        server.engine.progress.can_cleanup = False
        response = self.client.post("/api/cleanup_sd")
        self.assertEqual(response.status_code, 400)
        self.assertTrue((self.card / "DCIM" / "DSC0001.JPG").exists())

    def test_windows_cleanup_never_calls_os_remove(self):
        """Windows 分支必须走回收站；一旦回退到 os.remove 就是不可逆数据丢失。"""
        called = {}

        def fake_recycle(paths):
            called["paths"] = list(paths)
            return True, ""

        with mock.patch.object(server, "_windows_send_to_recycle_bin", side_effect=fake_recycle), \
             mock.patch.object(server, "_remove_empty_dirs"), \
             mock.patch.object(sys, "platform", "win32"), \
             mock.patch.object(os, "remove", side_effect=AssertionError("不允许直接永久删除")):
            response = self.client.post("/api/cleanup_sd")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["deleted"], 2)
        self.assertEqual(len(called.get("paths", [])), 2)

    def test_cleanup_stops_when_recycle_bin_unavailable(self):
        """回收站不可用时必须失败退出，原卡素材保持原样。"""
        with mock.patch.object(server, "_windows_send_to_recycle_bin",
                               return_value=(False, "系统回收站不可用")), \
             mock.patch.object(sys, "platform", "win32"):
            response = self.client.post("/api/cleanup_sd")
        self.assertEqual(response.status_code, 500)
        self.assertIn("回收站", response.get_json()["error"])
        self.assertTrue((self.card / "DCIM" / "DSC0001.JPG").exists())
        self.assertTrue((self.card / "DCIM" / "C0001.MP4").exists())

    @unittest.skipUnless(sys.platform.startswith("win"), "仅在 Windows 上验证真实回收站")
    def test_recycle_bin_helper_moves_file_off_card(self):
        target = self.card / "DCIM" / "TO_RECYCLE.JPG"
        target.write_bytes(b"recyclable")
        ok, reason = server._windows_send_to_recycle_bin([str(target)])
        self.assertTrue(ok, reason)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
