import sqlite3
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

def connect(db_path: Path, check_same_thread: bool = False) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), check_same_thread=check_same_thread)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            duration_s REAL,
            status TEXT,
            error TEXT,
            added_at TEXT,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS segments (
            id INTEGER PRIMARY KEY,
            recording_id INTEGER,
            start_s REAL,
            end_s REAL,
            text TEXT,
            confidence REAL,
            model TEXT,
            settings TEXT,
            created_at TEXT,
            FOREIGN KEY(recording_id) REFERENCES recordings(id)
        );

        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            segment_id INTEGER,
            word TEXT,
            norm TEXT,
            start_s REAL,
            end_s REAL,
            confidence REAL,
            FOREIGN KEY(segment_id) REFERENCES segments(id)
        );

        CREATE TABLE IF NOT EXISTS vocab (
            norm TEXT PRIMARY KEY,
            freq INTEGER
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts USING fts5(
            text,
            content='segments',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
            INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
        END;

        CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
            INSERT INTO segments_fts(segments_fts, rowid, text) VALUES ('delete', old.id, old.text);
        END;

        CREATE TRIGGER IF NOT EXISTS segments_au AFTER UPDATE ON segments BEGIN
            INSERT INTO segments_fts(segments_fts, rowid, text) VALUES ('delete', old.id, old.text);
            INSERT INTO segments_fts(rowid, text) VALUES (new.id, new.text);
        END;

        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY,
            term TEXT,
            variant TEXT,
            note TEXT
        );

        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY,
            segment_id INTEGER,
            corrected_text TEXT,
            reviewer TEXT,
            created_at TEXT,
            FOREIGN KEY(segment_id) REFERENCES segments(id)
        );
    """)
    conn.commit()

def insert_recording(conn: sqlite3.Connection, path: str, duration_s: float, status: str = 'pending') -> int:
    cursor = conn.execute(
        "INSERT INTO recordings (path, duration_s, status, added_at) VALUES (?, ?, ?, datetime('now'))",
        (path, duration_s, status)
    )
    return cursor.lastrowid

def update_recording_status(conn: sqlite3.Connection, recording_id: int, status: str, error: Optional[str] = None) -> None:
    conn.execute(
        "UPDATE recordings SET status = ?, error = ?, processed_at = datetime('now') WHERE id = ?",
        (status, error, recording_id)
    )

def insert_segment(conn: sqlite3.Connection, recording_id: int, start_s: float, end_s: float, text: str, confidence: float, model: str, settings: str) -> int:
    cursor = conn.execute(
        "INSERT INTO segments (recording_id, start_s, end_s, text, confidence, model, settings, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
        (recording_id, start_s, end_s, text, confidence, model, settings)
    )
    return cursor.lastrowid

def insert_word(conn: sqlite3.Connection, segment_id: int, word: str, norm: str, start_s: float, end_s: float, confidence: float) -> None:
    conn.execute(
        "INSERT INTO words (segment_id, word, norm, start_s, end_s, confidence) VALUES (?, ?, ?, ?, ?, ?)",
        (segment_id, word, norm, start_s, end_s, confidence)
    )

def add_to_vocab(conn: sqlite3.Connection, norm: str) -> None:
    conn.execute(
        "INSERT INTO vocab (norm, freq) VALUES (?, 1) ON CONFLICT(norm) DO UPDATE SET freq = freq + 1",
        (norm,)
    )
