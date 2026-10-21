"""Create a disposable v1.0.34 SQLite history for Windows upgrade E2E."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def main() -> None:
    config_dir = Path(os.environ["SMB_CONFIG_DIR"])
    config_dir.mkdir(parents=True, exist_ok=True)
    database = config_dir / "backup_history.db"
    with sqlite3.connect(database) as conn:
        conn.executescript(
            """
            CREATE TABLE backup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                backup_root TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                total_files INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                verified_files INTEGER DEFAULT 0,
                skipped_files INTEGER DEFAULT 0,
                reviewed_files INTEGER DEFAULT 0,
                preview_files INTEGER DEFAULT 0,
                failed_files INTEGER DEFAULT 0,
                duration_seconds REAL,
                status TEXT DEFAULT 'running',
                devices_json TEXT DEFAULT '{}',
                report_path TEXT,
                error TEXT
            );
            CREATE TABLE backup_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id INTEGER NOT NULL,
                source_path TEXT NOT NULL,
                dest_path TEXT,
                camera TEXT,
                media_type TEXT,
                file_size INTEGER,
                verified INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error TEXT,
                FOREIGN KEY (backup_id) REFERENCES backup_history(id)
            );
            CREATE INDEX idx_backup_history_started ON backup_history(started_at DESC);
            CREATE TABLE backup_target_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id INTEGER NOT NULL,
                target_path TEXT NOT NULL,
                copied_files INTEGER DEFAULT 0,
                skipped_files INTEGER DEFAULT 0,
                failed_files INTEGER DEFAULT 0,
                verified_files INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error TEXT DEFAULT '',
                UNIQUE(backup_id, target_path),
                FOREIGN KEY (backup_id) REFERENCES backup_history(id)
            );
            """
        )
        conn.execute(
            """
            INSERT INTO backup_history (
                event_name, backup_root, started_at, finished_at,
                total_files, total_size, verified_files, status, devices_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "v1.0.34 upgrade fixture",
                r"D:\YINGXU-Legacy-Fixture",
                "2026-01-15T10:30:00",
                "2026-01-15T10:31:00",
                1,
                4096,
                1,
                "done",
                "{}",
            ),
        )
        conn.execute(
            """
            INSERT INTO backup_files (
                backup_id, source_path, dest_path, media_type, file_size,
                verified, status
            ) VALUES (1, ?, ?, 'photo', 4096, 1, 'verified')
            """,
            (r"E:\Camera\IMG_0001.JPG", r"D:\YINGXU-Legacy-Fixture\IMG_0001.JPG"),
        )
    print(f"Seeded v1.0.34 history fixture: {database}")


if __name__ == "__main__":
    main()
