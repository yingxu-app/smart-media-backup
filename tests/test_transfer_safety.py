import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smb.transfer import TransferManager, TransferCancelled


class TransferSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        self.src = self.source / "photo.jpg"
        self.src.write_bytes(b"original media" * 100)
        self.dest = self.target / "photo.jpg"
        self.manager = TransferManager()
        self.digest = self.manager.verifier.hash_file(str(self.src))

    def copy(self):
        self.manager._copy_verified(self.src, self.dest, self.digest, True)

    def test_verified_transfer(self):
        original = self.src.read_bytes()
        self.copy()
        self.assertFalse(self.src.exists())
        self.assertEqual(self.dest.read_bytes(), original)

    def test_cancel_preserves_source(self):
        self.manager.cancel()
        with self.assertRaises(TransferCancelled):
            self.copy()
        self.assertTrue(self.src.exists())
        self.assertEqual(list(self.target.iterdir()), [])

    def test_failed_verification_preserves_source(self):
        with patch.object(self.manager.verifier, "verify_single", return_value=(False, "injected")):
            with self.assertRaises(OSError):
                self.copy()
        self.assertTrue(self.src.exists())
        self.assertEqual(list(self.target.iterdir()), [])

    def test_existing_destination_is_not_overwritten(self):
        self.dest.write_bytes(b"different original")
        with self.assertRaises(FileExistsError):
            self.copy()
        self.assertEqual(self.dest.read_bytes(), b"different original")
        self.assertTrue(self.src.exists())

    def test_source_changed_after_verification_is_retained(self):
        verify = self.manager.verifier.verify_single
        def mutate(*args):
            result = verify(*args)
            self.src.write_bytes(b"new source content")
            return result
        with patch.object(self.manager.verifier, "verify_single", side_effect=mutate):
            with self.assertRaises(OSError):
                self.copy()
        self.assertEqual(self.src.read_bytes(), b"new source content")
        self.assertEqual(self.manager.verifier.hash_file(str(self.dest)), self.digest)

    def test_cancel_after_verification_retains_source(self):
        verify = self.manager.verifier.verify_single
        def cancel(*args):
            result = verify(*args)
            self.manager.cancel()
            return result
        with patch.object(self.manager.verifier, "verify_single", side_effect=cancel):
            with self.assertRaises(TransferCancelled):
                self.copy()
        self.assertTrue(self.src.exists())

    def test_duplicate_detection_requires_equal_content(self):
        self.dest.write_bytes(self.src.read_bytes())
        other = self.source / "other.jpg"
        other.write_bytes(b"x" * self.src.stat().st_size)
        items = [{"path": str(p), "size": p.stat().st_size} for p in (self.src, other)]
        result = self.manager._find_exact_duplicates(items, str(self.target))
        self.assertEqual(result, {str(self.src): str(self.dest)})

    def test_empty_paths_rejected(self):
        with self.assertRaises(ValueError):
            self.manager.start_scan("")
        with self.assertRaises(ValueError):
            self.manager.start([], "")

    def test_destination_created_during_commit_is_not_overwritten(self):
        original_open = Path.open
        def racing_open(path, mode="r", *args, **kwargs):
            if path == self.dest and mode == "xb":
                with original_open(path, "wb") as stream:
                    stream.write(b"other application data")
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, "open", racing_open):
            with self.assertRaises(FileExistsError):
                self.copy()
        self.assertEqual(self.dest.read_bytes(), b"other application data")
        self.assertTrue(self.src.exists())

    def test_batch_transfer_ignores_duplicate_from_old_target(self):
        old = self.root / "old-target.jpg"
        old.write_bytes(self.src.read_bytes())
        second = self.source / "second.jpg"
        second.write_bytes(b"second media")
        items = [{"path": str(p), "relative": p.name, "size": p.stat().st_size,
                  "date": "", "camera": "Unknown", "media_type": "photo",
                  "exact_match_path": str(old)} for p in (self.src, second)]
        self.manager._run(items, str(self.target), "", True, str(self.source))
        self.assertEqual(self.manager.job["status"], "done")
        self.assertEqual(self.manager.job["copied"], 2)
        self.assertEqual(self.manager.job["duplicates"], 0)
        self.assertEqual(len(list(self.target.rglob("*.jpg"))), 2)
        self.assertFalse(self.src.exists())
        self.assertFalse(second.exists())
        self.assertTrue(old.exists())


if __name__ == "__main__":
    unittest.main()
