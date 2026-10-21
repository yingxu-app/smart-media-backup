import unittest
import json
import tempfile
from unittest.mock import patch
from pathlib import Path

from desktop.run import _make_console_output_encoding_safe, _write_json_atomically


class ReconfigurableStream:
    def __init__(self):
        self.errors = None

    def reconfigure(self, *, errors):
        self.errors = errors


class DesktopRunConsoleEncodingTests(unittest.TestCase):
    def test_localized_console_output_uses_fallback_for_unsupported_code_pages(self):
        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            _make_console_output_encoding_safe()

        self.assertEqual(stdout.errors, "backslashreplace")
        self.assertEqual(stderr.errors, "backslashreplace")

    def test_missing_or_non_reconfigurable_streams_are_ignored(self):
        with patch("sys.stdout", None), patch("sys.stderr", object()):
            _make_console_output_encoding_safe()

    def test_windows_ui_probe_targets_the_standalone_dashboard_workspace(self):
        root = Path(__file__).resolve().parents[1]
        probe = (root / "desktop" / "run.py").read_text(encoding="utf-8")
        dashboard = (root / "smb" / "templates" / "dashboard.html").read_text(encoding="utf-8")

        self.assertIn("document.querySelector('#mainContent.main')", probe)
        self.assertIn('<div class="main" id="mainContent">', dashboard)

    def test_ui_probe_report_is_published_atomically_as_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ui-report.json"
            payload = {"passed": True, "results": [{"ok": True, "name": "window"}]}

            _write_json_atomically(path, payload)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), payload)
            self.assertEqual(list(Path(directory).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
