"""影序 Pocket 配对、权限边界和移动端 API 回归测试。"""
import tempfile
import time
import unittest
from pathlib import Path

from smb import db
from smb.pocket import PocketNotesStore, PocketPairingManager
from smb import server


class PocketPairingTests(unittest.TestCase):
    def test_code_is_single_use_and_session_expires(self):
        manager = PocketPairingManager(code_ttl_seconds=30, session_hours=1)
        issued = manager.issue_code()
        self.assertRegex(issued["code"], r"^\d{6}$")
        self.assertIsNone(manager.connect("999999"))
        token = manager.connect(issued["code"])
        self.assertTrue(token)
        self.assertTrue(manager.is_authorized(token))
        self.assertIsNone(manager.connect(issued["code"]))
        manager._sessions[token] = time.time() - 1
        self.assertFalse(manager.is_authorized(token))


class PocketApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_db_path = db.DB_PATH
        self.old_pairing = server.pocket_pairing
        self.old_notes = server.pocket_notes
        db.DB_PATH = self.root / "history.db"
        db.init_db()
        server.pocket_pairing = PocketPairingManager()
        server.pocket_notes = PocketNotesStore(self.root / "notes.json")
        server.app.config.update(TESTING=True)
        self.client = server.app.test_client()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        server.pocket_pairing = self.old_pairing
        server.pocket_notes = self.old_notes
        self.temp.cleanup()

    def test_lan_cannot_open_desktop_workbench(self):
        response = self.client.get("/", environ_base={"REMOTE_ADDR": "192.168.1.8"})
        self.assertEqual(response.status_code, 403)
        self.assertIn("仅允许在本机访问", response.get_json()["error"])
        pocket = self.client.get("/pocket/", environ_base={"REMOTE_ADDR": "192.168.1.8"})
        self.assertEqual(pocket.status_code, 200)

    def test_pairing_notes_status_and_sanitized_history(self):
        issued = self.client.post("/api/pocket/pairing").get_json()
        self.assertRegex(issued["code"], r"^\d{6}$")
        connected = self.client.post(
            "/api/pocket/connect",
            json={"code": issued["code"]},
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(connected.status_code, 200)

        saved = self.client.post(
            "/api/pocket/notes",
            json={"event": "上海漫展", "location": "国家会展中心", "device": "Sony A7M4", "notes": "主舞台"},
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(server.pocket_notes.load()["event"], "上海漫展")

        backup_id = db.create_backup("测试项目", "/Users/test/Secret/Desktop/Backup")
        db.finish_backup(backup_id, status="completed")
        history = self.client.get(
            "/api/pocket/history",
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        ).get_json()["items"]
        self.assertEqual(history[0]["target"], "Backup")
        self.assertNotIn("/Users/test", str(history[0]))

        status = self.client.get(
            "/api/pocket/status",
            environ_base={"REMOTE_ADDR": "192.168.1.8"},
        )
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["paired"])

    def test_invalid_code_and_unpaired_api_are_rejected(self):
        self.assertEqual(
            self.client.post("/api/pocket/connect", json={"code": "000000"}, environ_base={"REMOTE_ADDR": "192.168.1.8"}).status_code,
            401,
        )
        self.assertEqual(
            self.client.get("/api/pocket/status", environ_base={"REMOTE_ADDR": "192.168.1.8"}).status_code,
            401,
        )

    def test_desktop_can_read_phone_notes_without_mobile_cookie(self):
        server.pocket_notes.save({"event": "街拍", "location": "外滩"})
        response = self.client.get("/api/pocket/notes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["notes"]["location"], "外滩")


if __name__ == "__main__":
    unittest.main()
