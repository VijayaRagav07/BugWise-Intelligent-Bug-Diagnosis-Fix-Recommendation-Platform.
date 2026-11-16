import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "defects.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bug_submissions (
                bug_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                stack_trace TEXT,
                environment TEXT,
                component TEXT,
                uploaded_files TEXT,
                detected_exceptions TEXT,
                status TEXT DEFAULT 'SUBMITTED',
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()