import unittest
from unittest.mock import patch

from desktop.run import _make_console_output_encoding_safe


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


if __name__ == "__main__":
    unittest.main()
