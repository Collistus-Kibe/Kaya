import sqlite3
import pytest
from pathlib import Path
from kayasearch.db import connect, init_db, insert_recording, insert_segment, update_recording_status, insert_word, add_to_vocab

@pytest.fixture
def db_conn(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    init_db(conn)
    yield conn
    conn.close()

def test_fts5_available(db_conn):
    cursor = db_conn.execute("SELECT * FROM pragma_compile_options WHERE compile_options LIKE 'ENABLE_FTS5'")
    assert cursor.fetchone() is not None, "FTS5 is not enabled in this SQLite build"

def test_init_db_idempotent(db_conn):
    init_db(db_conn)

def test_insert_recording_and_update(db_conn):
    rec_id = insert_recording(db_conn, "test.wav", 10.5)
    
    cursor = db_conn.execute("SELECT * FROM recordings WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    assert row["path"] == "test.wav"
    assert row["status"] == "pending"
    
    update_recording_status(db_conn, rec_id, "done")
    cursor = db_conn.execute("SELECT * FROM recordings WHERE id = ?", (rec_id,))
    row = cursor.fetchone()
    assert row["status"] == "done"

def test_insert_segment_and_fts(db_conn):
    rec_id = insert_recording(db_conn, "test.wav", 10.5)
    seg_id = insert_segment(db_conn, rec_id, 0.0, 5.0, "hello world", 0.9, "small", "settings")
    db_conn.commit()
    
    cursor = db_conn.execute("SELECT * FROM segments_fts WHERE segments_fts MATCH 'hello'")
    row = cursor.fetchone()
    assert row is not None
    assert row["text"] == "hello world"
    
def test_vocab(db_conn):
    add_to_vocab(db_conn, "hello")
    add_to_vocab(db_conn, "hello")
    db_conn.commit()
    
    cursor = db_conn.execute("SELECT freq FROM vocab WHERE norm = 'hello'")
    row = cursor.fetchone()
    assert row["freq"] == 2
