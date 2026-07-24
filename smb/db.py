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
            copied_files INTEGER DEFAULT 0,
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

    def ensure_column(table: str, column: str, ddl: str):
        cols = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

    ensure_column("backup_history", "skipped_files", "INTEGER DEFAULT 0")
    ensure_column("backup_history", "copied_files", "INTEGER DEFAULT 0")
    ensure_column("backup_history", "reviewed_files", "INTEGER DEFAULT 0")
    ensure_column("backup_history", "preview_files", "INTEGER DEFAULT 0")
    ensure_column("backup_history", "report_path", "TEXT")
    ensure_column("backup_history", "backup_targets", "TEXT DEFAULT '[]'")

    ensure_column("backup_files", "source_hash", "TEXT")
    ensure_column("backup_files", "source_mtime", "REAL")
    ensure_column("backup_files", "preview_path", "TEXT")

    conn.commit()
    conn.close()


def create_backup(event_name: str, backup_root: str, backup_targets: list | None = None) -> int:
    """创建备份记录，返回 backup_id"""
    conn = get_conn()
    now = datetime.now().isoformat()
    targets_json = json.dumps(backup_targets or [])
    cur = conn.execute(
        "INSERT INTO backup_history (event_name, backup_root, backup_targets, started_at, status) VALUES (?, ?, ?, ?, 'running')",
        (event_name, backup_root, targets_json, now)
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
                       verified: bool = False, error: str = "",
                       source_hash: str = "", source_mtime: Optional[float] = None):
    """更新单个文件状态"""
    conn = get_conn()
    params = [status, dest_path, 1 if verified else 0, error, backup_id, source_path]
    sql = (
        "UPDATE backup_files SET status=?, dest_path=?, verified=?, error=?"
    )
    if source_hash:
        sql += ", source_hash=?"
        params.insert(4, source_hash)
    if source_mtime is not None:
        sql += ", source_mtime=?"
        params.insert(5 if source_hash else 4, source_mtime)
    sql += " WHERE backup_id=? AND source_path=?"
    conn.execute(sql, tuple(params))
    conn.commit()
    conn.close()


def update_file_preview(backup_id: int, source_path: str, preview_path: str):
    """更新单个文件的预览路径"""
    conn = get_conn()
    conn.execute(
        "UPDATE backup_files SET preview_path=? WHERE backup_id=? AND source_path=?",
        (preview_path, backup_id, source_path)
    )
    conn.commit()
    conn.close()


def get_known_hashes(backup_root: str) -> set[str]:
    """获取指定备份目标下已完成备份的文件哈希集合"""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT DISTINCT bf.source_hash
        FROM backup_files bf
        JOIN backup_history bh ON bh.id = bf.backup_id
        WHERE bh.backup_root = ?
          AND bh.status = 'completed'
          AND bf.source_hash IS NOT NULL
          AND bf.source_hash != ''
        """,
        (backup_root,)
    ).fetchall()
    conn.close()
    return {row["source_hash"] for row in rows if row["source_hash"]}


def finish_backup(backup_id: int, status: str = "completed", error: str = "",
                  report_path: str = ""):
    """完成备份记录"""
    conn = get_conn()
    now = datetime.now().isoformat()

    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            COALESCE(SUM(file_size), 0) as total_size,
            COALESCE(SUM(CASE WHEN verified=1 THEN 1 ELSE 0 END), 0) as verified,
            COALESCE(SUM(CASE WHEN status='skipped' OR error='已验证现有文件，未重复复制' THEN 1 ELSE 0 END), 0) as skipped,
            COALESCE(SUM(CASE WHEN status='reviewed' THEN 1 ELSE 0 END), 0) as reviewed,
            COALESCE(SUM(CASE WHEN preview_path IS NOT NULL AND preview_path != '' THEN 1 ELSE 0 END), 0) as previewed,
            COALESCE(SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END), 0) as failed
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

    copied = max(0, stats["total"] - stats["skipped"] - stats["failed"])
    conn.execute(
        "UPDATE backup_history SET finished_at=?, total_files=?, total_size=?, "
        "copied_files=?, verified_files=?, skipped_files=?, reviewed_files=?, preview_files=?, failed_files=?, duration_seconds=?, status=?, error=?, devices_json=?, report_path=? WHERE id=?",
        (now, stats["total"], stats["total_size"], copied, stats["verified"],
         stats["skipped"], stats["reviewed"], stats["previewed"], stats["failed"], duration, status, error, json.dumps(devices_dict, ensure_ascii=False), report_path,
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


def get_backups(
    limit: int = 20,
    offset: int = 0,
    query: str = "",
    status: str = "",
    device: str = "",
    date_from: str = "",
    date_to: str = "",
) -> list[dict]:
    """查询备份历史，支持关键词/设备/状态/日期过滤"""
    conn = get_conn()
    sql = "SELECT * FROM backup_history WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (event_name LIKE ? OR backup_root LIKE ? OR devices_json LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])

    if status:
        sql += " AND status = ?"
        params.append(status)

    if device:
        sql += " AND EXISTS (SELECT 1 FROM backup_files bf WHERE bf.backup_id = backup_history.id AND bf.camera LIKE ?)"
        params.append(f"%{device}%")

    if date_from:
        sql += " AND started_at >= ?"
        params.append(date_from)

    if date_to:
        sql += " AND started_at <= ?"
        params.append(date_to)

    sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_backups(
    query: str = "",
    status: str = "",
    device: str = "",
    date_from: str = "",
    date_to: str = "",
) -> int:
    """统计符合条件的历史数量"""
    conn = get_conn()
    sql = "SELECT COUNT(*) AS cnt FROM backup_history WHERE 1=1"
    params: list = []

    if query:
        sql += " AND (event_name LIKE ? OR backup_root LIKE ? OR devices_json LIKE ?)"
        like = f"%{query}%"
        params.extend([like, like, like])

    if status:
        sql += " AND status = ?"
        params.append(status)

    if device:
        sql += " AND EXISTS (SELECT 1 FROM backup_files bf WHERE bf.backup_id = backup_history.id AND bf.camera LIKE ?)"
        params.append(f"%{device}%")

    if date_from:
        sql += " AND started_at >= ?"
        params.append(date_from)

    if date_to:
        sql += " AND started_at <= ?"
        params.append(date_to)

    row = conn.execute(sql, params).fetchone()
    conn.close()
    return int(row["cnt"] if row else 0)


def get_backup_files(backup_id: int, limit: int = 100) -> list[dict]:
    """查询备份中的文件列表"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM backup_files WHERE backup_id=? LIMIT ?",
        (backup_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_library(
    query: str = "",
    device: str = "",
    media_type: str = "",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """检索已归档的素材文件，返回文件、任务和备份位置的联合记录。"""
    conn = get_conn()
    sql = """
        SELECT bf.*, bh.event_name, bh.backup_root, bh.started_at AS backup_started_at,
               bh.status AS backup_status
        FROM backup_files bf
        JOIN backup_history bh ON bh.id = bf.backup_id
        WHERE bh.status = 'completed'
    """
    params: list = []

    if query:
        like = f"%{query}%"
        sql += " AND (bf.source_path LIKE ? OR bf.dest_path LIKE ? OR bf.camera LIKE ? OR bh.event_name LIKE ?)"
        params.extend([like, like, like, like])
    if device:
        sql += " AND bf.camera LIKE ?"
        params.append(f"%{device}%")
    if media_type:
        sql += " AND bf.media_type = ?"
        params.append(media_type)

    sql += " ORDER BY bh.started_at DESC, bf.id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def count_library(query: str = "", device: str = "", media_type: str = "") -> int:
    """统计素材检索结果数量。"""
    conn = get_conn()
    sql = """
        SELECT COUNT(*) AS cnt
        FROM backup_files bf
        JOIN backup_history bh ON bh.id = bf.backup_id
        WHERE bh.status = 'completed'
    """
    params: list = []
    if query:
        like = f"%{query}%"
        sql += " AND (bf.source_path LIKE ? OR bf.dest_path LIKE ? OR bf.camera LIKE ? OR bh.event_name LIKE ?)"
        params.extend([like, like, like, like])
    if device:
        sql += " AND bf.camera LIKE ?"
        params.append(f"%{device}%")
    if media_type:
        sql += " AND bf.media_type = ?"
        params.append(media_type)
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return int(row["cnt"] if row else 0)


def get_all_history() -> list[dict]:
    """获取全部备份历史（供跨电脑同步导出）"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM backup_history ORDER BY started_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def import_history(records: list[dict]) -> int:
    """导入备份历史记录，返回新增数"""
    conn = get_conn()
    imported = 0
    existing = {
        r["id"]
        for r in conn.execute(
            "SELECT id FROM backup_history"
        ).fetchall()
    }
    for rec in records:
        rid = rec.get("id")
        if rid in existing:
            continue
        conn.execute(
            """INSERT INTO backup_history
               (id, event_name, backup_root, backup_targets, started_at, finished_at,
                total_files, total_size, verified_files, skipped_files,
                reviewed_files, preview_files, failed_files,
                duration_seconds, status, devices_json, report_path, error)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rid, rec.get("event_name"), rec.get("backup_root"),
                rec.get("backup_targets", "[]"), rec.get("started_at"),
                rec.get("finished_at"), rec.get("total_files", 0),
                rec.get("total_size", 0), rec.get("verified_files", 0),
                rec.get("skipped_files", 0), rec.get("reviewed_files", 0),
                rec.get("preview_files", 0), rec.get("failed_files", 0),
                rec.get("duration_seconds"), rec.get("status", "completed"),
                rec.get("devices_json", "{}"), rec.get("report_path"),
                rec.get("error"),
            )
        )
        imported += 1
    conn.commit()
    conn.close()
    return imported
