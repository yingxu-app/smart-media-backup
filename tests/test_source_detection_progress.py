"""读卡器兼容与实时校验字段回归。

1. Windows 读卡器常把 SD 卡报成 DRIVE_FIXED，若只认 DRIVE_REMOVABLE 会漏掉来源。
   list_candidate_source_volumes 必须把非系统盘的固定卷也纳入候选。
2. BackupProgress.to_dict 必须暴露 verified_files / failed_files，前端才能实时展示校验结果。
"""
import sys
import unittest
from unittest import mock

from smb import detector
from smb.backup import BackupProgress


class CandidateSourceVolumeTests(unittest.TestCase):
    """来源候选卷必须覆盖读卡器报成固定盘的情况。"""

    def test_windows_includes_fixed_drives_except_system(self):
        if sys.platform != "win32":
            self.skipTest("Windows 特定行为")
        fake_removable = [
            {"name": "E:", "mount_point": "E:\\", "size_total": 0, "size_used": 0, "fstype": "removable"},
        ]

        def fake_list_removable():
            return fake_removable

        def fake_exists(path):
            return path in ("C:\\", "D:\\", "E:\\")

        def fake_get_drive_type(path):
            # C: 系统盘 fixed, D: 数据盘 fixed, E: 已在前面的 removable
            if path == "C:\\":
                return 3
            if path == "D:\\":
                return 3
            if path == "E:\\":
                return 2
            return 1

        def fake_disk_usage(path):
            return 0, 0

        with mock.patch.object(detector, "list_removable_volumes", side_effect=fake_list_removable), \
             mock.patch.object(detector, "_windows_system_drives", return_value={"C:\\"}), \
             mock.patch.object(detector, "_disk_usage", side_effect=fake_disk_usage):
            # 替换模块内的 os.path.exists 与 ctypes 调用
            with mock.patch("os.path.exists", side_effect=fake_exists), \
                 mock.patch("ctypes.windll.kernel32.GetDriveTypeW", side_effect=fake_get_drive_type):
                vols = detector.list_candidate_source_volumes()

        mounts = {v["mount_point"] for v in vols}
        # 固定数据盘 D: 应被纳入（读卡器场景），系统盘 C: 不应出现
        self.assertIn("D:\\", mounts)
        self.assertNotIn("C:\\", mounts)
        self.assertIn("E:\\", mounts)

    def test_non_windows_returns_removable_only(self):
        if sys.platform == "win32":
            self.skipTest("仅验证非 Windows 语义")
        fake = [{"name": "UNTITLED", "mount_point": "/Volumes/UNTITLED"}]
        with mock.patch.object(detector, "list_removable_volumes", return_value=fake):
            self.assertEqual(detector.list_candidate_source_volumes(), fake)


class ProgressFieldsTests(unittest.TestCase):
    """实时进度必须包含校验通过/失败数量。"""

    def test_to_dict_includes_verified_and_failed(self):
        p = BackupProgress()
        p.verified_files = 7
        p.failed_files = 2
        d = p.to_dict()
        self.assertEqual(d["verified_files"], 7)
        self.assertEqual(d["failed_files"], 2)

    def test_progress_defaults_are_zero(self):
        d = BackupProgress().to_dict()
        self.assertEqual(d["verified_files"], 0)
        self.assertEqual(d["failed_files"], 0)


if __name__ == "__main__":
    unittest.main()
