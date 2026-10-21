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

    def test_reads_pixels_without_flattened_or_deprecated_pixel_api(self):
        with mock.patch.object(Image.Image, "get_flattened_data", None, create=True), \
             mock.patch.object(Image.Image, "getdata", side_effect=AssertionError("deprecated API used")):
            result = self.reviewer._heuristic_review(str(self.image_path))
        self.assertEqual(result["label"], "黑图")

    def test_single_image_ai_result_cannot_classify_cross_image_duplicate(self):
        with mock.patch.object(self.reviewer, "_heuristic_review", return_value={
            "label": "正常", "confidence": 0.2, "reason": "画面正常", "source": "heuristic"
        }), mock.patch.object(self.reviewer, "_ai_review", return_value={
            "label": "重复", "confidence": 0.99, "reason": "看起来重复", "source": "ai"
        }):
            result = self.reviewer.review(str(self.image_path))
        self.assertEqual(result["label"], "正常")


if __name__ == "__main__":
    unittest.main()
