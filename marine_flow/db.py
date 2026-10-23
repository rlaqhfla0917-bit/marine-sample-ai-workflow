"""SQLite database helpers."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB = Path(os.environ.get("MARINE_FLOW_DB", "marine_flow_demo.db"))

@contextmanager
def connect(path=None):
    con = sqlite3.connect(str(path if path is not None else DEFAULT_DB))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def initialize(path=None):
    with connect(path) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS samples (
          sample_id TEXT PRIMARY KEY, project TEXT NOT NULL,
          station TEXT NOT NULL, collected_at TEXT NOT NULL,
          material TEXT NOT NULL, expected_analytes TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS handoffs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sample_id TEXT NOT NULL, handed_at TEXT NOT NULL,
          sender TEXT NOT NULL, receiver TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(sample_id) REFERENCES samples(sample_id)
        );
        CREATE TABLE IF NOT EXISTS results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          sample_id TEXT NOT NULL, analyte TEXT NOT NULL,
          result REAL NOT NULL, unit TEXT NOT NULL,
          analyzed_at TEXT NOT NULL, source_file TEXT NOT NULL,
          UNIQUE(sample_id,analyte,source_file)
        );
        """)
