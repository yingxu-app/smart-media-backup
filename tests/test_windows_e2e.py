"""Windows 预览接线回归测试（跨平台可用）。

覆盖 backup.py 两处改动：
1. _copy_to_target 将最终路径回写 f["dest_path"]（供废片审片与预览使用）；
2. run() 在审片之后调用 _generate_windows_previews，生成 _Windows预览 树，
   并把数量计入报告 preview_files。

刻意使用隔离目录与真实备份流程（不 mock 预览/校验），图片带绘制内容，
避免被废片审片误判隔离。
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from smb import backup, db
from smb import config as config_module
from smb.organizer import batch_extract_metadata, scan_sd_card


def _make_photo(path: Path, idx: int) -> None:
    """生成带内容的测试照片（画框+文字），避免触发废片审片。"""
    img = Image.new("RGB", (640, 480), (40, 60, 90))
    draw = ImageDraw.Draw(img)
    draw.rectangle([60, 60, 580, 420], outline=(255, 255, 255), width=4)
    draw.text((200, 220), f"SHOOT-{idx}", fill=(255, 255, 255))
    img.save(path, quality=90)


class WindowsPreviewWiringTests(unittest.TestCase):
    """dest_path 回写 + run() 预览接线"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source-card"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        for i in range(1, 4):
            _make_photo(self.source / f"DSC_{i:04d}.JPG", i)

        self.old = (db.DB_PATH, backup.CONFIG_DIR,
                    config_module.CONFIG_DIR, config_module.CONFIG_FILE)
        db.DB_PATH = self.root / "history.db"
        config_module.CONFIG_DIR = self.root / "config"
        config_module.CONFIG_FILE = config_module.CONFIG_DIR / "config.json"
        backup.CONFIG_DIR = config_module.CONFIG_DIR
        db.init_db()
        backup.config.sort_order = ["device", "event", "type"]

    def tearDown(self):
        db.DB_PATH, backup.CONFIG_DIR, \
            config_module.CONFIG_DIR, config_module.CONFIG_FILE = self.old
        self.temp.cleanup()

    def test_preview_tree_generated_and_counted_in_report(self):
        engine = backup.BackupEngine()
        engine.run(str(self.source), "预览接线验收", str(self.target),
                   enable_verify=True)

        # 预览树与照片一一对应
        previews = list(self.target.rglob("_Windows预览/**/*.jpg"))
        self.assertEqual(len(previews), 3)

        # 报告计入 preview_files
        record = db.get_all_history()[0]
        self.assertEqual(record["status"], "completed")
        report = json.loads(Path(record["report_path"]).read_text(encoding="utf-8"))
        self.assertEqual(report["preview_files"], 3)

    def test_dest_path_written_back_and_files_exist(self):
        engine = backup.BackupEngine()
        engine.run(str(self.source), "预览接线验收", str(self.target),
                   enable_verify=True)

        conn = sqlite3.connect(db.DB_PATH)
        rows = conn.execute(
            "SELECT source_path, dest_path FROM backup_files "
            "WHERE status='completed'"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), 3)
        for _src, dest in rows:
            self.assertTrue(dest, "dest_path 为空")
            self.assertTrue(Path(dest).is_file(), f"dest_path 不存在: {dest}")

    def test_full_chain_with_manifest(self):
        """完整链路: 扫描→元数据→备份→校验→manifest→预览→历史"""
        meta = batch_extract_metadata(scan_sd_card(str(self.source)))
        self.assertEqual(len(meta), 3)
        self.assertTrue(all(m.get("media_type") == "photo" for m in meta))

        engine = backup.BackupEngine()
        engine.run(str(self.source), "预览接线验收", str(self.target),
                   enable_verify=True)

        ck = list(self.target.rglob("checksums.json"))
        self.assertTrue(ck, "无 checksums.json")
        data = json.loads(ck[0].read_text(encoding="utf-8"))
        self.assertEqual(len(data), 3, "manifest 条目数不完整")


if __name__ == "__main__":
    unittest.main()
