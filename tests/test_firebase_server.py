import unittest
from unittest import mock
from types import SimpleNamespace

from smb import server
from smb.firebase_sync import FirebaseSyncError


class FirebaseServerTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.old_values = {
            key: getattr(server.config, key)
            for key in ("firebase_api_key", "firebase_database_url", "firebase_email", "firebase_uid", "firebase_display_name")
        }
        server.config.firebase_api_key = ""
        server.config.firebase_database_url = ""
        server.config.firebase_email = ""
        server.config.firebase_uid = ""
        server.config.firebase_display_name = ""
        self.old_sync_client = server._firebase_sync_client

    def tearDown(self):
        for key, value in self.old_values.items():
            setattr(server.config, key, value)
        server._firebase_sync_client = self.old_sync_client

    def test_firebase_settings_reject_non_https_database_urls(self):
        response = self.client.post("/api/firebase/settings", json={
            "api_key": "public-key", "database_url": "http://example.invalid",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(server.config.firebase_api_key, "")

    def test_firebase_login_persists_uid_but_not_password(self):
        fake = SimpleNamespace(
            sign_in=mock.Mock(return_value={"uid": "uid-1", "email": "a@example.com"}),
            start_live_watch=mock.Mock(),
        )
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake), \
             mock.patch.object(server, "_sync_latest_desktop_history"), \
             mock.patch.object(server.config, "save"):
            response = self.client.post("/api/firebase/login", json={
                "email": "a@example.com", "password": "do-not-save",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(server.config.firebase_uid, "uid-1")
        self.assertEqual(server.config.firebase_email, "a@example.com")
        fake.sign_in.assert_called_once_with("a@example.com", "do-not-save", create_account=False, display_name="")
        fake.start_live_watch.assert_called_once_with()
        self.assertNotIn("do-not-save", repr(server.config))

    def test_firebase_registration_creates_account_and_starts_sync(self):
        fake = SimpleNamespace(
            sign_in=mock.Mock(return_value={"uid": "uid-new", "email": "new@example.com", "display_name": "小影"}),
            start_live_watch=mock.Mock(),
        )
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake), \
             mock.patch.object(server, "_sync_latest_desktop_history"), \
             mock.patch.object(server.config, "save"):
            response = self.client.post("/api/firebase/register", json={
                "email": "new@example.com", "password": "not-persisted", "display_name": "小影",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(server.config.firebase_uid, "uid-new")
        self.assertEqual(server.config.firebase_display_name, "小影")
        fake.sign_in.assert_called_once_with("new@example.com", "not-persisted", create_account=True, display_name="小影")
        fake.start_live_watch.assert_called_once_with()
        self.assertNotIn("not-persisted", repr(server.config))

    def test_firebase_registration_reports_password_policy_errors_clearly(self):
        fake = SimpleNamespace(sign_in=mock.Mock(side_effect=ValueError("WEAK_PASSWORD")))
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake):
            response = self.client.post("/api/firebase/register", json={
                "email": "new@example.com", "password": "temporary-input", "display_name": "小影",
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn("密码未达到 Firebase 要求", response.get_json()["error"])
        self.assertNotIn("temporary-input", repr(server.config))

    def test_firebase_login_reports_safe_transport_diagnostic(self):
        fake = SimpleNamespace(sign_in=mock.Mock(side_effect=FirebaseSyncError(
            "Firebase 返回错误代码 API_KEY_SERVICE_BLOCKED（HTTP 403）。请将错误代码提供给支持人员；不要发送密码。"
        )))
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake):
            response = self.client.post("/api/firebase/login", json={
                "email": "a@example.com", "password": "temporary-input",
            })
        self.assertEqual(response.status_code, 502)
        self.assertIn("API_KEY_SERVICE_BLOCKED（HTTP 403）", response.get_json()["error"])
        self.assertNotIn("temporary-input", response.get_data(as_text=True))

    def test_firebase_login_reports_safe_type_for_unexpected_local_error(self):
        fake = SimpleNamespace(sign_in=mock.Mock(side_effect=OSError("private local detail")))
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake):
            response = self.client.post("/api/firebase/login", json={
                "email": "a@example.com", "password": "temporary-input",
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn("本机错误类型：OSError", response.get_json()["error"])
        self.assertNotIn("private local detail", response.get_data(as_text=True))
        self.assertNotIn("temporary-input", response.get_data(as_text=True))

    def test_firebase_live_endpoint_starts_watch_and_returns_cached_progress(self):
        fake = SimpleNamespace(
            uid="uid-1",
            start_live_watch=mock.Mock(),
            live_snapshot=mock.Mock(return_value={"items": [{"deviceName": "影序 Pocket", "status": "copying"}], "error": "", "updatedAt": 1}),
        )
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake):
            response = self.client.get("/api/firebase/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["items"][0]["status"], "copying")
        fake.start_live_watch.assert_called_once_with()

    def test_firebase_settings_and_cloud_metadata_are_restricted_to_desktop_loopback(self):
        for path in ("/api/firebase/settings", "/api/firebase/history", "/api/firebase/live"):
            with self.subTest(path=path):
                response = self.client.get(path, environ_base={"REMOTE_ADDR": "192.168.31.20"})
                self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
