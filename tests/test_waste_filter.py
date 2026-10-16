"""废片启发式在支持与不支持 Pillow 扁平像素 API 的版本上都可运行。"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from smb.waste_filter import WasteReviewer


class WasteHeuristicPixelAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.image_path = Path(self.temp.name) / "black.jpg"
        Image.new("RGB", (32, 32), (0, 0, 0)).save(self.image_path, "JPEG")
        self.reviewer = WasteReviewer()

    def tearDown(self):
        self.temp.cleanup()

    def test_classifies_black_image_with_current_pillow_pixel_api(self):
        result = self.reviewer._heuristic_review(str(self.image_path))
        self.assertEqual(result["label"], "黑图")
        self.assertEqual(result["source"], "heuristic")

    def test_falls_back_when_flattened_pixel_api_is_unavailable(self):
        with mock.patch.object(Image.Image, "get_flattened_data", None, create=True):
            result = self.reviewer._heuristic_review(str(self.image_path))
        self.assertEqual(result["label"], "黑图")


if __name__ == "__main__":
    unittest.main()
