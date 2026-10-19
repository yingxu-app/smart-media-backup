import json
import ssl
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
                {"name": "YINGXU-macOS-v1.0.41.dmg", "browser_download_url": "https://example.test/app.dmg", "size": 120},
                {"name": "YINGXU-Windows-v1.0.41.exe", "browser_download_url": "https://example.test/app.exe", "size": 240},
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
        self.assertIn("更新服务", response.get_json()["error"])

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


if __name__ == "__main__":
    unittest.main()
