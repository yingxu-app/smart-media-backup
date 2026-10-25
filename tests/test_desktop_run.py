import unittest
import json
import io
import tempfile
import threading
from unittest.mock import patch
from pathlib import Path

from desktop.run import _make_console_output_encoding_safe, _write_json_atomically


class ReconfigurableStream:
    def __init__(self):
        self.encoding = "cp1252"
        self.errors = None

    def reconfigure(self, *, encoding, errors):
        self.encoding = encoding
        self.errors = errors


class DesktopRunConsoleEncodingTests(unittest.TestCase):
    def test_localized_console_output_uses_fallback_for_unsupported_code_pages(self):
        stdout = ReconfigurableStream()
        stderr = ReconfigurableStream()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            _make_console_output_encoding_safe()

        for stream in (stdout, stderr):
            self.assertEqual(stream.encoding, "utf-8")
            self.assertEqual(stream.errors, "backslashreplace")

    def test_localized_output_is_writable_after_cp1252_stream_is_reconfigured(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        try:
            with patch("sys.stdout", stream), patch("sys.stderr", stream):
                _make_console_output_encoding_safe()
                print("服务线程：影序已启动", file=stream)

            stream.flush()
            self.assertIn("服务线程：影序已启动", raw.getvalue().decode("utf-8"))
        finally:
            stream.detach()

    def test_service_thread_can_log_chinese_without_uncaught_encoding_error(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252")
        errors = []

        def log_from_service_thread():
            try:
                print("服务线程：影序已启动", file=stream)
            except Exception as exc:  # surfaced by the test instead of the thread hook
                errors.append(exc)

        try:
            with patch("sys.stdout", stream), patch("sys.stderr", stream):
                _make_console_output_encoding_safe()
                worker = threading.Thread(target=log_from_service_thread)
                worker.start()
                worker.join(timeout=2)

            self.assertFalse(worker.is_alive(), "service logging thread did not finish")
            self.assertEqual(errors, [])
            stream.flush()
            self.assertIn("服务线程：影序已启动", raw.getvalue().decode("utf-8"))
        finally:
            stream.detach()

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
