"""不依赖真实存储卡的核心可靠性回归测试。

这些测试刻意使用隔离目录：验证跳过、报告、取消和目标不可用时，源文件
都不会被删除或修改。真实 TF 卡验收另行在发布前执行。
"""
import json
import os
import tempfile
import unittest
from unittest import mock
from datetime import datetime
from pathlib import Path

from smb import backup, db
from smb import config as config_module


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
        self.old_config_dir = backup.CONFIG_DIR
        self.old_module_config_dir = config_module.CONFIG_DIR
        self.old_config_file = config_module.CONFIG_FILE
        db.DB_PATH = self.root / "history.db"
        config_module.CONFIG_DIR = self.root / "config"
        config_module.CONFIG_FILE = config_module.CONFIG_DIR / "config.json"
        backup.CONFIG_DIR = config_module.CONFIG_DIR
        db.init_db()
        backup.config.sort_order = ["device", "event", "type"]
        backup.config.verify_method = "sha256"

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        backup.CONFIG_DIR = self.old_config_dir
        config_module.CONFIG_DIR = self.old_module_config_dir
        config_module.CONFIG_FILE = self.old_config_file
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
            self.assertTrue(Path(record["report_path"]).with_suffix(".csv").is_file())
            self.assertTrue(Path(record["report_path"]).with_suffix(".md").is_file())
            self.assertEqual(first_report["target_results"][0]["status"], "completed")

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

    def test_daily_folder_is_readable_and_keeps_technical_outputs_off_media_disk(self):
        """新目录以每日主文件夹呈现，素材盘根目录不再出现技术辅助目录。"""
        engine = self._engine()
        try:
            engine.run(
                str(self.source), "", str(self.target), enable_verify=True,
                naming_parts=[
                    {"kind": "date"}, {"kind": "event", "value": ""},
                    {"kind": "location", "value": ""}, {"kind": "device"},
                    {"kind": "type"},
                ],
            )
            daily = self.target / "2026年07月28日_相机拍摄_照片原片"
            self.assertTrue((daily / "照片").is_dir())
            self.assertEqual(len(list((daily / "照片").glob("*.JPG"))), 4)
            self.assertFalse((self.target / "_Lightroom").exists())
            self.assertFalse((self.target / "_Windows预览").exists())
            self.assertFalse((self.target / "_reports").exists())
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_edited_preview_names_are_used_by_real_backup(self):
        """层级预览中的主目录和子目录改名必须真实影响最终复制路径。"""
        engine = self._engine()
        try:
            engine.run(
                str(self.source), "", str(self.target), enable_verify=True,
                event_groups=[{
                    "date_key": "2026-07-28",
                    "folder_name": "2026年07月28日_漫展素材",
                    "photo_folder_name": "相机照片原片",
                    "video_folder_name": "现场视频",
                }],
            )
            edited = self.target / "2026年07月28日_漫展素材" / "相机照片原片"
            self.assertTrue(edited.is_dir())
            self.assertEqual(len(list(edited.glob("*.JPG"))), 4)
            self.assertFalse((self.target / "2026年07月28日_漫展素材" / "照片").exists())
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_target_space_shortage_is_reported_before_copy_and_source_is_safe(self):
        engine = self._engine()
        usage = type("Usage", (), {"total": 100, "used": 99, "free": 1})()
        original = (self.source / "IMG_0001.JPG").read_bytes()
        try:
            with mock.patch.object(backup.shutil, "disk_usage", return_value=usage):
                with self.assertRaisesRegex(RuntimeError, "空间不足"):
                    engine.run(str(self.source), "空间不足", str(self.target), enable_verify=True)
            self.assertEqual((self.source / "IMG_0001.JPG").read_bytes(), original)
            self.assertEqual(db.get_all_history()[0]["status"], "error")
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_permission_error_is_clear_and_source_is_safe(self):
        engine = self._engine()
        original = (self.source / "IMG_0001.JPG").read_bytes()
        try:
            with mock.patch.object(backup.tempfile, "NamedTemporaryFile", side_effect=PermissionError("denied")):
                with self.assertRaisesRegex(RuntimeError, "没有权限写入"):
                    engine.run(str(self.source), "权限不足", str(self.target), enable_verify=True)
            self.assertEqual((self.source / "IMG_0001.JPG").read_bytes(), original)
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_source_disappearing_mid_copy_becomes_partial_and_never_allows_cleanup(self):
        engine = self._engine()
        calls = {"count": 0}
        original_copy = engine._copy_and_verify_with_retry
        def flaky_copy(src, dest, source_hash, enable_verify):
            calls["count"] += 1
            if calls["count"] == 2:
                return False, "原始存储卡已断开"
            return original_copy(src, dest, source_hash, enable_verify)
        engine._copy_and_verify_with_retry = flaky_copy
        try:
            engine.run(str(self.source), "拔卡恢复", str(self.target), enable_verify=True)
            record = db.get_all_history()[0]
            self.assertEqual(record["status"], "partial")
            self.assertGreater(record["failed_files"], 0)
            self.assertFalse(engine.progress.can_cleanup)
            report = json.loads(Path(record["report_path"]).read_text())
            self.assertEqual(report["status"], "partial")
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_multi_target_records_each_target_independently(self):
        engine = self._engine()
        second = self.root / "second-target"
        second.mkdir()
        original = engine._copy_to_target
        def target_copy(files, target, event_name, backup_id, enable_verify,
                        record_file_status=True):
            if target == str(second):
                return {"copied": 0, "skipped": 0, "failed": len(files), "bytes": 0}
            return original(
                files, target, event_name, backup_id, enable_verify,
                record_file_status=record_file_status,
            )
        engine._copy_to_target = target_copy
        try:
            engine.run(
                str(self.source), "双目标", str(self.target), enable_verify=True,
                backup_targets=[str(second)],
            )
            record = db.get_all_history()[0]
            self.assertEqual(record["status"], "partial")
            results = db.get_target_results(record["id"])
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0]["status"], "completed")
            self.assertEqual(results[1]["status"], "partial")
            self.assertTrue(list(self.target.rglob("*.JPG")))
            self.assertTrue((self.source / "IMG_0001.JPG").exists())
        finally:
            backup.batch_extract_metadata = self._old_metadata

    def test_database_migrates_old_schema_without_losing_history(self):
        old_path = self.root / "old.db"
        import sqlite3
        conn = sqlite3.connect(old_path)
        conn.execute("CREATE TABLE backup_history (id INTEGER PRIMARY KEY, event_name TEXT NOT NULL, backup_root TEXT NOT NULL, started_at TEXT NOT NULL, status TEXT)")
        conn.execute("CREATE TABLE backup_files (id INTEGER PRIMARY KEY, backup_id INTEGER NOT NULL, source_path TEXT NOT NULL)")
        conn.execute("INSERT INTO backup_history VALUES (1, '旧记录', '/old', '2026-01-01T00:00:00', 'completed')")
        conn.commit(); conn.close()
        db.DB_PATH = old_path
        db.init_db()
        migrated = db.get_backup(1)
        self.assertEqual(migrated["event_name"], "旧记录")
        self.assertIn("skipped_files", migrated)
        self.assertEqual(db.get_target_results(1), [])


if __name__ == "__main__":
    unittest.main()
