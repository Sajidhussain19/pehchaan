"""
app/store/db.py — the SQLite database file behind reminders and pending questions.

WHAT: connect() opens data/app.db (creating the file and tables on first use) and returns a connection
      whose rows behave like dicts. Two tables:
        reminders: the real stored Remind actions (Module 9's one real action)
        pending:   clarify questions waiting for the user's answer
WHY:  A reminder must be REAL: it has to survive a server restart and be listable and openable later.
      SQLite is built into Python (the `sqlite3` module): one file, no server to install, no ORM to learn.
      Every SQL statement here is plain and readable.

Tests point DB_PATH at a temporary file, so they never touch the demo database.
"""

import sqlite3
from contextlib import contextmanager

from app.config import PROJECT_ROOT, settings

# git-ignored: it is runtime state, not project data. STATE_DIR (Docker) moves it to a mounted volume.
DB_PATH = (settings.state_dir or PROJECT_ROOT / "data") / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at        TEXT NOT NULL,           -- ISO 8601, e.g. 2026-11-21T18:05:00
    contact_book      TEXT NOT NULL,           -- whose contacts were used: default / A / B
    heard_transcript  TEXT NOT NULL,           -- exactly what speech-to-text heard (never hidden)
    output_transcript TEXT NOT NULL,           -- after Pehchaan's corrections
    target_entity_id  TEXT,                    -- who/what the reminder is about
    target_name       TEXT,
    target_role       TEXT,                    -- e.g. "dentist", "family doctor", "restaurant"
    place_entity_id   TEXT,
    place_name        TEXT,
    time              TEXT,                    -- "HH:MM" or NULL when no clear clock time was said
    raw_time_text     TEXT,                    -- the time words as heard, e.g. "tomorrow at 10 a.m."
    entities_json     TEXT NOT NULL,           -- [{heard_text, resolved_entity_id, confidence, reason}]
    resolution        TEXT NOT NULL CHECK (resolution IN
                          ('auto', 'clarified_this_time', 'clarified_always', 'preference')),
    status            TEXT NOT NULL DEFAULT 'created'
);
CREATE TABLE IF NOT EXISTS pending (
    id                TEXT PRIMARY KEY,        -- random hex id, safe to put in a URL
    created_at        TEXT NOT NULL,
    contact_book      TEXT NOT NULL,
    heard_transcript  TEXT NOT NULL,
    direction         TEXT NOT NULL,
    caller_contact_id TEXT,
    phrase            TEXT NOT NULL,           -- the words we asked about, e.g. "my doctor"
    reason            TEXT NOT NULL,           -- why we asked
    candidates_json   TEXT NOT NULL,           -- [{entity_id, name, role, reason}]
    status            TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered')),
    reminder_id       INTEGER                  -- the reminder created from the answer
);
"""


@contextmanager
def connect():
    """`with connect() as conn:` -> a connection that COMMITS on success, ROLLS BACK on error, then closes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows can be read like dicts: row["target_name"]
    try:
        if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
            # First open, including upgrades from the original shared DB. Existing rows
            # keep a NULL owner and cannot be read or claimed by any browser.
            conn.executescript("BEGIN IMMEDIATE;\n" + SCHEMA)
            for table in ("reminders", "pending"):
                columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
                if not any(column["name"] == "visitor_id" for column in columns):
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN visitor_id TEXT")
            conn.execute("PRAGMA user_version = 1")
            conn.commit()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
