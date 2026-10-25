import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smb import server
from smb.pocket_tcp import MobileInbox


class Pairing:
    def __init__(self):
        self.tokens = set()

    def connect(self, code):
        if code != "123456":
            return None
        self.tokens.add("test-pocket-token")
        return "test-pocket-token"

    def is_authorized(self, token):
        return token in self.tokens

    def revoke(self, token):
        self.tokens.discard(token)


class PocketHttpUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "backup"
        self.root.mkdir()
        self.pairing = Pairing()
        self.files = []
        self.statuses = []
        self.backup_ids = []
        self.stack = [
            patch.object(server, "pocket_pairing", self.pairing),
            patch.object(server, "_pocket_mobile_inbox", MobileInbox(lambda: self.root)),
            patch.object(server, "_pocket_mobile_inbox_root", lambda: str(self.root)),
            patch.object(server.db, "create_backup", lambda *args: self.backup_ids.append(41) or 41),
            patch.object(server.db, "get_known_hashes", lambda _root: set()),
            patch.object(server.db, "add_files", lambda backup_id, files: self.files.extend(files)),
            patch.object(server.db, "update_file_status", lambda *args, **kwargs: self.statuses.append((args, kwargs))),
            patch.object(server.db, "finish_backup", lambda *args, **kwargs: None),
            patch.object(server, "_sync_latest_desktop_history", lambda: None),
        ]
        for manager in self.stack:
            manager.start()
        server._pocket_upload_sessions.clear()
        self.client = server.app.test_client()

    def tearDown(self):
        server._pocket_upload_sessions.clear()
        for manager in reversed(self.stack):
            manager.stop()
        self.temp.cleanup()

    def pair(self):
        response = self.client.post("/api/pocket/connect", json={"code": "123456"})
        self.assertEqual(response.status_code, 200)

    def test_phone_upload_requires_pairing(self):
        response = self.client.post("/api/pocket/inbox/plan", json={"files": []},
                                    environ_overrides={"REMOTE_ADDR": "192.168.1.90"})
        self.assertEqual(response.status_code, 401)

    def test_authenticated_upload_is_verified_recorded_and_visible_in_history(self):
        content = b"phone photo for verified LAN backup"
        digest = hashlib.sha256(content).hexdigest()
        self.pair()

        planned = self.client.post("/api/pocket/inbox/plan", json={
            "event_name": "手机验收",
            "files": [{"relative_path": "手机验收/照片/IMG_0001.JPG", "size": len(content),
                       "sha256": digest, "media_type": "photo"}],
        })
        self.assertEqual(planned.status_code, 200, planned.get_json())
        self.assertEqual(planned.get_json()["total_files"], 1)
        self.assertEqual(self.files[0]["media_type"], "photo")

        began = self.client.post("/api/pocket/inbox/begin", json={"index": 0})
        self.assertEqual(began.status_code, 200, began.get_json())
        chunk = self.client.post("/api/pocket/inbox/chunk", json={
            "index": 0, "offset": 0, "data": base64.b64encode(content).decode("ascii"),
        })
        self.assertEqual(chunk.status_code, 200, chunk.get_json())
        self.assertEqual(chunk.get_json()["received"], len(content))

        finished = self.client.post("/api/pocket/inbox/finish", json={"index": 0})
        self.assertEqual(finished.status_code, 200, finished.get_json())
        self.assertEqual(finished.get_json()["sha256"], digest)
        saved = self.root / "影序手机备份/手机验收/照片/IMG_0001.JPG"
        self.assertEqual(saved.read_bytes(), content)
        self.assertTrue(self.statuses[-1][1]["verified"])

        completed = self.client.post("/api/pocket/inbox/complete", json={"status": "completed"})
        self.assertEqual(completed.status_code, 200, completed.get_json())
        history = self.client.get("/api/pocket/history")
        self.assertEqual(history.status_code, 200)

    def test_upload_rejects_wrong_content_hash_and_cleans_partial_file(self):
        content = b"original"
        self.pair()
        planned = self.client.post("/api/pocket/inbox/plan", json={
            "files": [{"relative_path": "event/照片/fail.jpg", "size": len(content),
                       "sha256": "0" * 64, "media_type": "photo"}],
        })
        self.assertEqual(planned.status_code, 200)
        self.client.post("/api/pocket/inbox/begin", json={"index": 0})
        self.client.post("/api/pocket/inbox/chunk", json={
            "index": 0, "offset": 0, "data": base64.b64encode(content).decode("ascii"),
        })
        failed = self.client.post("/api/pocket/inbox/finish", json={"index": 0})
        self.assertEqual(failed.status_code, 400)
        self.assertFalse((self.root / "影序手机备份/event/照片/fail.jpg").exists())

    def test_known_sha256_is_skipped_before_transfer_and_recorded(self):
        content = b"already archived photo"
        digest = hashlib.sha256(content).hexdigest()
        self.pair()
        with patch.object(server.db, "get_known_hashes", return_value={digest}):
            response = self.client.post("/api/pocket/inbox/plan", json={
                "files": [{"relative_path": "event/照片/duplicate.jpg", "size": len(content),
                           "sha256": digest, "media_type": "photo"}],
            })
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["skip_indices"], [0])
        self.assertEqual(self.statuses[-1][0][2], "skipped")
        self.assertTrue(self.statuses[-1][1]["verified"])
        finished = self.client.post("/api/pocket/inbox/complete", json={"status": "completed"})
        self.assertEqual(finished.status_code, 200, finished.get_json())
        self.assertFalse((self.root / "影序手机备份/event/照片/duplicate.jpg").exists())


if __name__ == "__main__":
    unittest.main()
