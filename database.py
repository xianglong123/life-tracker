"""
Life Tracker 数据库层（SQLite）
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from config import DB_PATH


def get_conn():
    """获取数据库连接（自动创建表）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_db(conn)
    return conn


def _init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            app_name TEXT NOT NULL,
            window_title TEXT,
            duration_seconds INTEGER DEFAULT 0,
            is_idle INTEGER DEFAULT 0,
            screenshot_path TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            summary TEXT,
            total_active_minutes INTEGER DEFAULT 0,
            top_apps TEXT,
            screenshots_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS app_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            app_name TEXT NOT NULL,
            total_minutes INTEGER DEFAULT 0,
            UNIQUE(date, app_name)
        );

        CREATE INDEX IF NOT EXISTS idx_activity_date ON activity_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_activity_app ON activity_log(app_name);
    """)


# ---- Activity Log ----

def record_activity(timestamp, app_name, window_title, duration=0, is_idle=False):
    conn = get_conn()
    conn.execute(
        "INSERT INTO activity_log (timestamp, app_name, window_title, duration_seconds, is_idle) VALUES (?, ?, ?, ?, ?)",
        (timestamp, app_name, window_title, duration, 1 if is_idle else 0)
    )
    conn.commit()
    conn.close()


def get_activities(today=None):
    """获取某天的活动记录，按时间排序"""
    if today is None:
        today = date.today().isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM activity_log WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
        (f"{today} 00:00:00", f"{today} 23:59:59")
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- App Stats ----

def update_app_stats(today, app_name, minutes):
    conn = get_conn()
    conn.execute("""
        INSERT INTO app_stats (date, app_name, total_minutes)
        VALUES (?, ?, ?)
        ON CONFLICT(date, app_name) DO UPDATE SET
            total_minutes = total_minutes + ?
    """, (today, app_name, minutes, minutes))
    conn.commit()
    conn.close()


def get_app_stats(today=None, limit=10):
    if today is None:
        today = date.today().isoformat()
    conn = get_conn()
    rows = conn.execute(
        "SELECT app_name, total_minutes FROM app_stats WHERE date = ? ORDER BY total_minutes DESC LIMIT ?",
        (today, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Daily Summary ----

def save_daily_summary(today, summary_text, total_active_minutes, top_apps, screenshots_count=0):
    conn = get_conn()
    conn.execute("""
        INSERT INTO daily_summary (date, summary, total_active_minutes, top_apps, screenshots_count)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            summary = excluded.summary,
            total_active_minutes = excluded.total_active_minutes,
            top_apps = excluded.top_apps,
            screenshots_count = excluded.screenshots_count
    """, (today, summary_text, total_active_minutes, json.dumps(top_apps, ensure_ascii=False), screenshots_count))
    conn.commit()
    conn.close()


def get_daily_summaries(limit=30):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM daily_summary ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["top_apps"] = json.loads(d["top_apps"]) if d.get("top_apps") else []
        result.append(d)
    return result


def get_daily_summary(today=None):
    if today is None:
        today = date.today().isoformat()
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM daily_summary WHERE date = ?", (today,)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["top_apps"] = json.loads(d["top_apps"]) if d.get("top_apps") else []
        return d
    return None


# ---- 日报列表（带分页） ----

def get_summary_list(page=1, per_page=20):
    conn = get_conn()
    offset = (page - 1) * per_page
    rows = conn.execute(
        "SELECT date, total_active_minutes, screenshots_count, created_at FROM daily_summary ORDER BY date DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    count = conn.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], count


# ---- 截图记录 ----

def save_screenshot_path(timestamp, path):
    conn = get_conn()
    # 找到最近的一条 activity 记录，把截图路径关联上去
    conn.execute(
        "UPDATE activity_log SET screenshot_path = ? WHERE timestamp <= ? AND screenshot_path IS NULL ORDER BY timestamp DESC LIMIT 1",
        (path, timestamp)
    )
    conn.commit()
    conn.close()
