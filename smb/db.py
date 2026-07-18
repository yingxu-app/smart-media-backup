"""SQLite 备份历史记录"""
import json
import sqlite3
import os
from datetime import datetime
from typing import Optional

from .config import DB_PATH


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """建表"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT NOT NULL,
            backup_root TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            total_files INTEGER DEFAULT 0,
            total_size INTEGER DEFAULT 0,
            verified_files INTEGER DEFAULT 0,
            failed_files INTEGER DEFAULT 0,
            duration_seconds REAL,
            status TEXT DEFAULT 'running',
            devices_json TEXT DEFAULT '{}',
            error TEXT
        );

        CREATE TABLE IF NOT EXISTS backup_files (
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

        CREATE INDEX IF NOT EXISTS idx_backup_history_started
            ON backup_history(started_at DESC);
    """)
    conn.commit()
    conn.close()


def create_backup(event_name: str, backup_root: str) -> int:
    """创建备份记录，返回 backup_id"""
    conn = get_conn()
    now = datetime.now().isoformat()
    cur = conn.execute(
        "INSERT INTO backup_history (event_name, backup_root, started_at, status) VALUES (?, ?, ?, 'running')",
        (event_name, backup_root, now)
    )
    backup_id = cur.lastrowid
    conn.commit()
    conn.close()
    return backup_id


def add_files(backup_id: int, files: list[dict]):
    """批量写入文件记录"""
    conn = get_conn()
    rows = []
    for f in files:
        rows.append((
            backup_id,
            f["path"],
            "",
            f.get("camera", ""),
            f.get("media_type", "other"),
            f.get("size", 0),
            0,
            "pending",
            "",
        ))
    conn.executemany(
        "INSERT INTO backup_files (backup_id, source_path, dest_path, camera, media_type, file_size, verified, status, error) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()


def update_file_status(backup_id: int, source_path: str, status: str, dest_path: str = "",
                       verified: bool = False, error: str = ""):
    """更新单个文件状态"""
    conn = get_conn()
    conn.execute(
        "UPDATE backup_files SET status=?, dest_path=?, verified=?, error=? "
        "WHERE backup_id=? AND source_path=?",
        (status, dest_path, 1 if verified else 0, error, backup_id, source_path)
    )
    conn.commit()
    conn.close()


def finish_backup(backup_id: int, status: str = "completed", error: str = ""):
    """完成备份记录"""
    conn = get_conn()
    now = datetime.now().isoformat()

    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            COALESCE(SUM(file_size), 0) as total_size,
            SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END) as verified,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
        FROM backup_files WHERE backup_id=?
    """, (backup_id,)).fetchone()

    devices = conn.execute("""
        SELECT camera, COUNT(*) as count
        FROM backup_files WHERE backup_id=?
        GROUP BY camera ORDER BY count DESC
    """, (backup_id,)).fetchall()

    devices_dict = {row["camera"]: row["count"] for row in devices if row["camera"]}

    start_time = conn.execute(
        "SELECT started_at FROM backup_history WHERE id=?",
        (backup_id,)
    ).fetchone()["started_at"]

    duration = None
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(now)
        duration = (end_dt - start_dt).total_seconds()
    except (ValueError, TypeError):
        pass

    conn.execute(
        "UPDATE backup_history SET finished_at=?, total_files=?, total_size=?, "
        "verified_files=?, failed_files=?, duration_seconds=?, status=?, error=?, devices_json=? WHERE id=?",
        (now, stats["total"], stats["total_size"], stats["verified"],
         stats["failed"], duration, status, error, json.dumps(devices_dict, ensure_ascii=False),
         backup_id)
    )
    conn.commit()
    conn.close()


def get_backup(backup_id: int) -> Optional[dict]:
    """查询单条备份记录"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM backup_history WHERE id=?", (backup_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_backups(limit: int = 20, offset: int = 0) -> list[dict]:
    """查询备份历史"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM backup_history ORDER BY started_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_backup_files(backup_id: int, limit: int = 100) -> list[dict]:
    """查询备份中的文件列表"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM backup_files WHERE backup_id=? LIMIT ?",
        (backup_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
