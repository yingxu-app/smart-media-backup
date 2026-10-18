import unittest
import tempfile
import time
from pathlib import Path

from smb.firebase_sync import FirebaseSyncClient, public_metadata


class MemoryTokenStore:
    def __init__(self):
        self.values = {}

    def get(self, uid):
        return self.values.get(uid)

    def set(self, uid, token):
        self.values[uid] = token

    def remove(self, uid):
        self.values.pop(uid, None)


class FakeResponse:
    def __init__(self, status, payload):
        self.status_code = status
        self.payload = payload

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class FirebaseSyncTests(unittest.TestCase):
    def test_metadata_omits_paths_and_credentials_but_keeps_file_names(self):
        value = public_metadata({
            "id": 7, "event_name": "旅行", "backup_root": "/Volumes/PRIVATE/Photos",
            "token": "never-share", "target_name": "/Volumes/PRIVATE/Backup",
            "total_files": 1, "files": [{"path": "/secret/DCIM/IMG_1.JPG", "filename": "IMG_1.JPG", "size": 42}],
        }, device_id="desktop-1", device_name="影序桌面")
        encoded = str(value)
        self.assertEqual(value["files"][0]["name"], "IMG_1.JPG")
        self.assertEqual(value["targetName"], "Backup")
        self.assertNotIn("PRIVATE", encoded)
        self.assertNotIn("secret", encoded)
        self.assertNotIn("never-share", encoded)

    def test_sign_in_stores_refresh_token_and_publishes_user_scoped_metadata(self):
        session = FakeSession([
            FakeResponse(200, {"localId": "uid-1", "email": "photo@example.com", "idToken": "id-token", "refreshToken": "refresh-token", "expiresIn": "3600"}),
            FakeResponse(200, {"name": "-Krecord"}),
        ])
        store = MemoryTokenStore()
        with tempfile.TemporaryDirectory() as directory:
            client = FirebaseSyncClient("api-key", "https://yingxu.firebaseio.com", store, "desktop-1", session=session,
                                        outbox_path=Path(directory) / "outbox.json")
            account = client.sign_in("photo@example.com", "not-persisted")
            client.publish_history({"id": 17, "status": "done", "backup_root": "/Volumes/Private"}, [
                {"filename": "DSC_1.ARW", "path": "/Volumes/Private/DSC_1.ARW", "size": 64, "status": "copied"},
            ])
        self.assertEqual(account["uid"], "uid-1")
        self.assertEqual(store.get("uid-1"), "refresh-token")
        method, url, request = session.calls[-1]
        self.assertEqual(method, "PUT")
        self.assertIn("/users/uid-1/history/17.json", url)
        self.assertEqual(request["json"]["files"][0]["name"], "DSC_1.ARW")
        self.assertNotIn("backup_root", request["json"])
        self.assertNotIn("Private", str(request["json"]))

    def test_unauthenticated_publish_is_rejected_before_network_access(self):
        session = FakeSession([])
        with tempfile.TemporaryDirectory() as directory:
            client = FirebaseSyncClient("api-key", "https://yingxu.firebaseio.com", MemoryTokenStore(), "desktop-1",
                                        session=session, outbox_path=Path(directory) / "outbox.json")
            with self.assertRaises(PermissionError):
                client.publish_history({"id": 1})
            self.assertEqual(session.calls, [])

    def test_database_path_rejects_traversal_before_request(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FirebaseSyncClient("api-key", "https://yingxu.firebaseio.com", MemoryTokenStore(), "desktop-1",
                                        outbox_path=Path(directory) / "outbox.json")
            for path in ("../../other-user/history", "history/record.with.dots", "history/$invalid"):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, "无效字段"):
                    client._encode_database_path(path)

    def test_failed_progress_is_persisted_as_sanitized_outbox_and_flushes_later(self):
        with tempfile.TemporaryDirectory() as directory:
            session = FakeSession([FakeResponse(503, {"error": {"message": "offline"}})])
            outbox = Path(directory) / "firebase-outbox.json"
            client = FirebaseSyncClient("api-key", "https://yingxu.firebaseio.com", MemoryTokenStore(), "desktop-1",
                                        session=session, outbox_path=outbox)
            client.uid = "uid-1"
            client._id_token = "id-token"
            client._expires_at = time.time() + 3600
            with self.assertRaises(ConnectionError):
                client.publish_progress({"id": "active-1", "status": "copying", "current_file": "IMG_1.JPG",
                                          "source_path": "/private/DCIM", "token": "never-store"}, force=True)
            queued = outbox.read_text(encoding="utf-8")
            self.assertIn("IMG_1.JPG", queued)
            self.assertNotIn("/private", queued)
            self.assertNotIn("never-store", queued)
            session.responses.append(FakeResponse(200, {"name": "ok"}))
            self.assertTrue(client.flush_outbox())
            self.assertFalse(outbox.exists())


if __name__ == "__main__":
    unittest.main()
