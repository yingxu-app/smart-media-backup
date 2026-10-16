"""ExifTool-free scanning must not start a failing process for every file."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from smb import organizer


class ExifToolFallbackTests(unittest.TestCase):
    def setUp(self):
        organizer._exiftool_executable.cache_clear()

    def tearDown(self):
        organizer._exiftool_executable.cache_clear()

    def test_missing_exiftool_is_looked_up_once_and_uses_existing_fallbacks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "DJI_0001.JPG"
            second = Path(temp_dir) / "IMG_0002.JPG"
            first.write_bytes(b"media")
            second.write_bytes(b"media")

            with mock.patch.object(organizer.shutil, "which", return_value=None) as which, \
                 mock.patch.object(organizer.subprocess, "run", side_effect=AssertionError("must not spawn")):
                self.assertEqual(organizer.detect_camera_model(str(first)), "DJI")
                self.assertEqual(organizer.detect_camera_model(str(second)), "iPhone")
                self.assertIsNotNone(organizer.extract_date(str(first)))
                self.assertIsNone(organizer.extract_gps(str(first)))

            which.assert_called_once_with("exiftool")

    def test_available_exiftool_path_is_used(self):
        with mock.patch.object(organizer.shutil, "which", return_value="/opt/homebrew/bin/exiftool"), \
             mock.patch.object(organizer.subprocess, "run", return_value=mock.Mock(stdout="Canon EOS", returncode=0)) as run:
            self.assertEqual(organizer.detect_camera_model("IMG_0001.JPG"), "Canon EOS")

        self.assertEqual(run.call_args.args[0][0], "/opt/homebrew/bin/exiftool")


if __name__ == "__main__":
    unittest.main()
