"""重复备份的幂等性回归：同一张卡备份多次不得留下越来越多的垃圾文件。

Windows 实机验收时发现的两个真实缺陷：
1. 审片阶段对"上一轮已经归档进待确认废片"的文件再调用一次 move_to_review_folder，
   由于目标名与自身同名，文件被反复改名成 xxx_1、xxx_1_1…
2. 预览生成每次都走 ``while out_path.exists()``，第二轮备份又产出一张 xxx_1.jpg，
   预览树随备份次数无上限膨胀。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image

from smb.waste_filter import WasteReviewer
from smb.windows_preview import WindowsPreviewBuilder, PREVIEW_MANIFEST_NAME


class ReviewFolderIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.card = self.root / "card"
        self.card.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_file_already_in_review_folder_is_not_renamed_again(self):
        reviewer = WasteReviewer()
        photo = self.card / "DSC01000.JPG"
        Image.new("RGB", (32, 32), (10, 20, 30)).save(photo, "JPEG")

        first = reviewer.move_to_review_folder(str(photo), str(self.root), "构图差", "photo")
        self.assertEqual(Path(first).name, "DSC01000.JPG")
        self.assertFalse(photo.exists())

        # 第二轮备份：审片步骤会把 dest_path 指向已经归档的文件，必须原地返回。
        second = reviewer.move_to_review_folder(str(first), str(self.root), "构图差", "photo")
        self.assertEqual(second, first)
        self.assertEqual(Path(second).name, "DSC01000.JPG")
        self.assertEqual(sorted(p.name for p in Path(first).parent.iterdir()),
                         ["DSC01000.JPG"])

    def test_repeat_reviews_never_grow_the_name(self):
        reviewer = WasteReviewer()
        photo = self.card / "DSC07777.JPG"
        Image.new("RGB", (32, 32), (7, 7, 7)).save(photo, "JPEG")
        current = reviewer.move_to_review_folder(str(photo), str(self.root), "构图差", "photo")
        for _ in range(5):
            current = reviewer.move_to_review_folder(str(current), str(self.root), "构图差", "photo")
        self.assertEqual(Path(current).name, "DSC07777.JPG")


class PreviewIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.backup_root = self.root / "backup"
        self.event_dir = self.backup_root / "2026年09月11日_测试_照片"
        self.event_dir.mkdir(parents=True)
        self.photo = self.event_dir / "DSC02000.JPG"
        Image.new("RGB", (64, 48), (90, 120, 40)).save(self.photo, "JPEG")
        self.builder = WindowsPreviewBuilder()
        self.builder.enabled = True

    def tearDown(self):
        self.temp.cleanup()

    def test_second_run_reuses_same_preview_file(self):
        first = self.builder.build_preview_for_path(str(self.photo), str(self.backup_root), "photo")
        second = self.builder.build_preview_for_path(str(self.photo), str(self.backup_root), "photo")
        self.assertEqual(first, second)
        previews = sorted(
            p.name for p in (self.backup_root / "_Windows预览" / self.event_dir.name).iterdir()
            if p.suffix.lower() == ".jpg"
        )
        self.assertEqual(previews, ["DSC02000.jpg"])

    def test_repeated_runs_do_not_inflate_preview_tree(self):
        for _ in range(4):
            self.builder.build_preview_for_path(str(self.photo), str(self.backup_root), "photo")
        previews = [
            p for p in (self.backup_root / "_Windows预览").rglob("*.jpg")
        ]
        self.assertEqual(len(previews), 1, [p.name for p in previews])
        manifest_path = self.backup_root / "_Windows预览" / PREVIEW_MANIFEST_NAME
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 1)


if __name__ == "__main__":
    unittest.main()
