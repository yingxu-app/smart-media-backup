import json
import hashlib
import ssl
import urllib.error
import unittest
from unittest import mock

from smb import server


class UpdateCheckerTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def _mock_release(self, tag="v1.0.41"):
        payload = {
            "tag_name": tag,
            "html_url": "https://github.com/yingxu-app/smart-media-backup/releases/tag/v1.0.41",
            "published_at": "2026-10-19T00:00:00Z",
            "assets": [
                {"name": "YINGXU-macOS-v1.0.41.dmg", "browser_download_url": "https://github.com/yingxu-app/smart-media-backup/releases/download/v1.0.41/YINGXU-macOS-v1.0.41.dmg", "size": 120, "digest": "sha256:" + "a" * 64},
                {"name": "YINGXU-Windows-v1.0.41.exe", "browser_download_url": "https://github.com/yingxu-app/smart-media-backup/releases/download/v1.0.41/YINGXU-Windows-v1.0.41.exe", "size": 240, "digest": "sha256:" + "b" * 64},
                {"name": "SHA256SUMS.txt", "browser_download_url": "https://example.test/SHA256SUMS.txt", "size": 32},
            ],
        }
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return mock.patch("urllib.request.urlopen", return_value=response)

    def test_reports_newer_macos_release_and_only_compatible_assets(self):
        with self._mock_release(), mock.patch("sys.platform", "darwin"), mock.patch("smb.__version__", "1.0.40"):
            response = self.client.get("/api/updates/latest")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["update_available"])
        self.assertEqual(payload["platform"], "macOS")
        self.assertEqual([asset["name"] for asset in payload["assets"]], ["YINGXU-macOS-v1.0.41.dmg"])
        self.assertEqual(payload["assets"][0]["digest"], "sha256:" + "a" * 64)

    def test_reports_windows_installer_and_current_release_comparison(self):
        with self._mock_release(), mock.patch("sys.platform", "win32"), mock.patch("smb.__version__", "1.0.42"):
            response = self.client.get("/api/updates/latest")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertFalse(payload["update_available"])
        self.assertEqual(payload["platform"], "Windows")
        self.assertEqual([asset["name"] for asset in payload["assets"]], ["YINGXU-Windows-v1.0.41.exe"])

    def test_returns_clear_error_when_release_service_is_unavailable(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("offline")):
            response = self.client.get("/api/updates/latest")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["diagnostic_code"], "TIMEOUT")
        self.assertIn("更新服务", response.get_json()["error"])
        self.assertNotIn("offline", response.get_json()["error"])

    def test_tls_failure_uses_safe_diagnostic_without_exposing_reason(self):
        failure = urllib.error.URLError(ssl.SSLError("private certificate detail"))
        with mock.patch("urllib.request.urlopen", side_effect=failure):
            response = self.client.get("/api/updates/latest")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()["diagnostic_code"], "TLS_ERROR")
        self.assertNotIn("private certificate detail", response.get_json()["error"])

    def test_uses_certifi_trust_roots_without_disabling_tls_verification(self):
        context = ssl.create_default_context()
        with (
            self._mock_release() as open_release,
            mock.patch("sys.platform", "darwin"),
            mock.patch("certifi.where", return_value="/trusted/ca-bundle.pem") as certifi_bundle,
            mock.patch("ssl.create_default_context", return_value=context) as create_context,
        ):
            response = self.client.get("/api/updates/latest")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        certifi_bundle.assert_called_once()
        create_context.assert_called_once_with(cafile="/trusted/ca-bundle.pem")
        open_release.assert_called_once()
        self.assertEqual(open_release.call_args.kwargs["context"], context)

    def test_update_download_is_only_served_after_size_and_sha256_match(self):
        app_bytes = b"verified-dmg-content"
        name = "YINGXU-macOS-v1.0.41.dmg"
        release = {
            "assets": [{"name": name,
                        "browser_download_url": f"https://github.com/yingxu-app/smart-media-backup/releases/download/v1.0.41/{name}",
                        "size": len(app_bytes), "digest": "sha256:" + hashlib.sha256(app_bytes).hexdigest()}],
        }
        api_response = mock.MagicMock()
        api_response.__enter__.return_value.read.return_value = json.dumps(release).encode()
        file_response = mock.MagicMock()
        file_response.__enter__.return_value.read.side_effect = [app_bytes, b""]
        with (mock.patch("urllib.request.urlopen", side_effect=[api_response, file_response]),
              mock.patch("sys.platform", "darwin")):
            response = self.client.get(f"/api/updates/download?asset={name}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, app_bytes)
        self.assertEqual(response.headers["X-Yingxu-SHA256"], hashlib.sha256(app_bytes).hexdigest())
        self.assertEqual(response.headers["X-Yingxu-Verified"], "true")
        response.close()

    def test_update_download_rejects_a_package_with_wrong_sha256(self):
        name = "YINGXU-macOS-v1.0.41.dmg"
        release = {
            "assets": [{"name": name,
                        "browser_download_url": f"https://github.com/yingxu-app/smart-media-backup/releases/download/v1.0.41/{name}",
                        "size": 4, "digest": "sha256:" + "0" * 64}],
        }
        api_response = mock.MagicMock()
        api_response.__enter__.return_value.read.return_value = json.dumps(release).encode()
        file_response = mock.MagicMock()
        file_response.__enter__.return_value.read.side_effect = [b"evil", b""]
        with (mock.patch("urllib.request.urlopen", side_effect=[api_response, file_response]),
              mock.patch("sys.platform", "darwin")):
            response = self.client.get(f"/api/updates/download?asset={name}")

        self.assertEqual(response.status_code, 502)
        self.assertIn("SHA-256", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
