import unittest
from unittest import mock
from types import SimpleNamespace

from smb import server


class FirebaseServerTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        self.old_values = {
            key: getattr(server.config, key)
            for key in ("firebase_api_key", "firebase_database_url", "firebase_email", "firebase_uid")
        }
        server.config.firebase_api_key = ""
        server.config.firebase_database_url = ""
        server.config.firebase_email = ""
        server.config.firebase_uid = ""
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
        fake = SimpleNamespace(sign_in=mock.Mock(return_value={"uid": "uid-1", "email": "a@example.com"}))
        with mock.patch.object(server, "_get_firebase_sync_client", return_value=fake), \
             mock.patch.object(server, "_sync_latest_desktop_history"), \
             mock.patch.object(server.config, "save"):
            response = self.client.post("/api/firebase/login", json={
                "email": "a@example.com", "password": "do-not-save",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(server.config.firebase_uid, "uid-1")
        self.assertEqual(server.config.firebase_email, "a@example.com")
        fake.sign_in.assert_called_once_with("a@example.com", "do-not-save")
        self.assertNotIn("do-not-save", repr(server.config))


if __name__ == "__main__":
    unittest.main()
