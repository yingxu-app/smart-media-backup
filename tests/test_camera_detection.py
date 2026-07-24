"""设备识别兜底规则：优先相信存储卡目录，再使用文件名。"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_ROOT = tempfile.TemporaryDirectory()
os.environ["SMB_CONFIG_DIR"] = str(Path(TEST_ROOT.name) / "config")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smb.organizer import detect_camera_model  # noqa: E402


class CameraDetectionTests(unittest.TestCase):
    def test_card_directory_hints_override_ambiguous_filenames(self):
        with patch("smb.organizer.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(
                detect_camera_model("/Volumes/Card/DCIM/115LEICA/漫展/L1150600.JPG"),
                "Leica",
            )
            self.assertEqual(
                detect_camera_model("/Volumes/Card/DCIM/142_FUJI/DSCF2205.RAF"),
                "Fujifilm",
            )

    def test_filename_fallbacks_cover_fujifilm_and_sony(self):
        with patch("smb.organizer.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(detect_camera_model("/tmp/DSCF2205.RAF"), "Fujifilm")
            self.assertEqual(detect_camera_model("/tmp/DSC00001.ARW"), "Sony")


if __name__ == "__main__":
    unittest.main()
