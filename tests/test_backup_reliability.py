"""关键备份可靠性回归测试：重复备份、校验失败与可安全续传。"""
import os
import sys
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch


TEST_ROOT = tempfile.TemporaryDirectory()
os.environ["SMB_CONFIG_DIR"] = str(Path(TEST_ROOT.name) / "config")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from smb import backup, db  # noqa: E402
from smb.config import config  # noqa: E402


class BackupReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sd = self.root / "SDCARD"
        self.target = self.root / "ARCHIVE"
        self.sd.mkdir()
        self.target.mkdir()
        self.source = self.sd / "clip.jpg"
        self.source.write_bytes(b"camera-original-bytes")
        self.old_db_path = db.DB_PATH
        db.DB_PATH = self.root / "history.sqlite3"
        db.init_db()
        config.sort_order = ["device", "event", "type"]

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    def media_file(self):
        return {
            "path": str(self.source), "filename": self.source.name,
            "size": self.source.stat().st_size, "camera": "Sony A7M4",
            "media_type": "photo", "date": None, "gps": None,
        }

    def configured_engine(self):
        engine = backup.BackupEngine()
        engine._review_and_quarantine = Mock(return_value=(0, {}))
        engine._generate_windows_previews = Mock(return_value=0)
        engine._verifier.generate_manifest = Mock()
        return engine

    def test_incremental_backup_skips_already_verified_content(self):
        original_scan = backup.scan_sd_card
        original_metadata = backup.batch_extract_metadata
        backup.scan_sd_card = lambda _mount: [self.media_file()]
        backup.batch_extract_metadata = lambda files, _progress: files
        try:
            first = self.configured_engine()
            first.run(str(self.sd), "portrait", str(self.target), enable_verify=True)
            self.assertEqual(first.progress.status, "done")
            self.assertTrue(first.progress.can_cleanup)
            reports = list((self.target / "_reports" / "portrait").glob("report_*.json"))
            self.assertTrue(reports)
            self.assertEqual(json.loads(reports[0].read_text())["status"], "completed")
            found = db.search_library(query="portrait")
            self.assertEqual(len(found), 1)
            self.assertIn("Sony A7M4", found[0]["dest_path"])

            second = self.configured_engine()
            second.run(str(self.sd), "portrait", str(self.target), enable_verify=True)
            self.assertEqual(second.progress.status, "done")
            self.assertGreaterEqual(second.progress.skipped_files, 1)
        finally:
            backup.scan_sd_card = original_scan
            backup.batch_extract_metadata = original_metadata

    def test_corrupt_copy_retries_then_reports_failure(self):
        engine = self.configured_engine()
        engine.RETRY_DELAY_SECONDS = 0
        engine._verifier.verify_single = Mock(return_value=(False, "checksum mismatch"))
        target = self.target / "copy.jpg"
        ok, error = engine._copy_and_verify_with_retry(
            str(self.source), str(target), "source-hash", enable_verify=True
        )
        self.assertFalse(ok)
        self.assertIn("校验失败", error)
        self.assertEqual(engine._verifier.verify_single.call_count, engine.MAX_RETRIES)

    def test_removed_sd_file_is_retried_and_never_marked_safe(self):
        engine = self.configured_engine()
        engine.RETRY_DELAY_SECONDS = 0
        self.source.unlink()  # 模拟复制期间 SD 卡被拔出或文件不可读取。
        ok, error = engine._copy_and_verify_with_retry(
            str(self.source), str(self.target / "missing.jpg"), "source-hash", enable_verify=False
        )
        self.assertFalse(ok)
        self.assertTrue(error)

    def test_network_notification_failure_does_not_interrupt_local_workflow(self):
        previous_url = backup.config.webhook_url
        backup.config.webhook_url = "http://127.0.0.1:1/unavailable"
        try:
            # _send_webhook catches network errors by design; this must not propagate.
            engine = self.configured_engine()
            with patch("urllib.request.urlopen", side_effect=OSError("network unavailable")):
                engine._send_webhook(1, 1, 0, ["offline-test"])
        finally:
            backup.config.webhook_url = previous_url

    def test_partial_result_never_allows_sd_cleanup(self):
        original_scan = backup.scan_sd_card
        original_metadata = backup.batch_extract_metadata
        backup.scan_sd_card = lambda _mount: [self.media_file()]
        backup.batch_extract_metadata = lambda files, _progress: files
        try:
            engine = self.configured_engine()
            engine._copy_to_target = Mock(return_value={"copied": 0, "skipped": 0, "failed": 1, "bytes": 0})
            engine.run(str(self.sd), "interrupted", str(self.target), enable_verify=False)
            self.assertEqual(engine.progress.status, "partial")
            self.assertFalse(engine.progress.can_cleanup)
            self.assertIn("原始 SD 卡", engine.progress.current_file)
        finally:
            backup.scan_sd_card = original_scan
            backup.batch_extract_metadata = original_metadata


if __name__ == "__main__":
    unittest.main()
