"""不依赖真实存储卡的核心可靠性回归测试。

这些测试刻意使用隔离目录：验证跳过、报告、取消和目标不可用时，源文件
都不会被删除或修改。真实 TF 卡验收另行在发布前执行。
"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from smb import backup, db


class BackupReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source-card"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        # 同内容、不同文件名是摄影原始素材的合法情况，首次备份必须都保留。
        (self.source / "IMG_0001.JPG").write_bytes(b"same-photo-content")
        (self.source / "IMG_0002.JPG").write_bytes(b"same-photo-content")
        (self.source / "IMG_0003.JPG").write_bytes(b"different-photo-content")
        # 不同目录的同名原片也必须保留，不能相互覆盖。
        nested = self.source / "DCIM" / "SECOND"
        nested.mkdir(parents=True)
        (nested / "IMG_0001.JPG").write_bytes(b"same-photo-content")

        self.old_db_path = db.DB_PATH
        db.DB_PATH = self.root / "history.db"
        db.init_db()
        backup.config.sort_order = ["device", "event", "type"]
        backup.config.verify_method = "sha256"

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.temp.cleanup()

    def _engine(self):
        engine = backup.BackupEngine()
        # 元数据读取与审片本身分别有专门测试；这里固定元数据，聚焦可靠性。
        def fake_metadata(files, _callback=None):
            result = []
            for item in files:
                data = dict(item)
                data.update(camera="TestCam", media_type="photo", date=datetime(2026, 7, 28), gps=None)
                result.append(data)
            return result
        engine._review_and_quarantine = lambda *args: (0, {})
        engine._generate_windows_previews = lambda *args: 0
        engine._trigger_baidu_upload = lambda *args: None
        self._old_metadata = backup.batch_extract_metadata
        backup.batch_extract_metadata = fake_metadata
        return engine

    def test_first_backup_preserves_same_content_files_and_second_run_skips(self):
        engine = self._engine()
        try:
            engine.run(str(self.source), "可靠性验收", str(self.target), enable_verify=True)
            record = db.get_all_history()[0]
            self.assertEqual(record["status"], "completed")
            self.assertEqual(record["skipped_files"], 0)
            self.assertEqual(record["total_files"], 4)
            files = [p for p in self.target.rglob("*.JPG") if p.is_file()]
            self.assertEqual(len(files), 4)
            first_report = json.loads(Path(record["report_path"]).read_text())
            self.assertEqual(first_report["copied_files"], 4)
            self.assertEqual(first_report["skipped_files"], 0)
            self.assertEqual(first_report["verified_files"], 4)
            self.assertEqual(first_report["source_mount"], str(self.source))
            self.assertEqual(first_report["source_name"], "source-card")
            self.assertEqual(first_report["report_path"], record["report_path"])

            engine.run(str(self.source), "可靠性验收", str(self.target), enable_verify=True)
            second = db.get_all_history()[0]
            self.assertEqual(second["status"], "completed")
            self.assertEqual(second["skipped_files"], 4)
            report = json.loads(Path(second["report_path"]).read_text())
            self.assertEqual(report["copied_files"], 0)
            self.assertEqual(report["skipped_files"], 4)
            self.assertEqual(report["verified_files"], 4)
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_cancelled_task_has_recoverable_report_and_keeps_source(self):
        backup_id = db.create_backup("取消验收", str(self.target))
        source_file = self.source / "IMG_0001.JPG"
        db.add_files(backup_id, [{"path": str(source_file), "filename": source_file.name, "size": source_file.stat().st_size}])
        engine = backup.BackupEngine()
        engine.progress.start_time = 1
        engine.progress.total_bytes = source_file.stat().st_size
        engine._finish_cancelled_backup(backup_id, "取消验收", str(self.target), {}, 1, 1, 0, source_mount=str(self.source))
        record = db.get_backup(backup_id)
        self.assertEqual(record["status"], "partial")
        self.assertTrue(source_file.exists())
        report = json.loads(Path(record["report_path"]).read_text())
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["verified_files"], 1)

    def test_target_that_is_a_file_fails_without_touching_source(self):
        engine = self._engine()
        bad_target = self.root / "not-a-folder"
        bad_target.write_text("not a folder")
        source_bytes = (self.source / "IMG_0001.JPG").read_bytes()
        try:
            with self.assertRaises(Exception):
                engine.run(str(self.source), "目标错误", str(bad_target), enable_verify=True)
            self.assertEqual((self.source / "IMG_0001.JPG").read_bytes(), source_bytes)
            record = db.get_all_history()[0]
            self.assertEqual(record["status"], "error")
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_empty_card_is_rejected_before_any_history_or_copy(self):
        """未插卡或空卡不能伪装成一次成功备份。"""
        empty_card = self.root / "empty-card"
        empty_card.mkdir()
        engine = self._engine()
        try:
            with self.assertRaises(RuntimeError):
                engine.run(str(empty_card), "空卡验收", str(self.target), enable_verify=True)
            self.assertFalse(list(self.target.rglob("*")))
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_checksum_detects_a_corrupted_destination(self):
        """复制后若目标文件被篡改，校验必须明确失败，源文件仍保持原样。"""
        source_file = self.source / "IMG_0003.JPG"
        destination = self.target / "IMG_0003.JPG"
        destination.write_bytes(source_file.read_bytes())
        destination.write_bytes(b"corrupted-after-copy")
        ok, detail = backup.ChecksumVerifier().verify_single(str(source_file), str(destination))
        self.assertFalse(ok)
        self.assertIn("src=", detail)
        self.assertEqual(source_file.read_bytes(), b"different-photo-content")


if __name__ == "__main__":
    unittest.main()
